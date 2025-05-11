import string
import time
import random
import os
import json
import logging

from PIL import Image

from django.core.cache import cache
from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import gettext as _
from django.utils.module_loading import import_string

from django.apps import apps
from django.conf import settings
from django.core.files import File
from django.template.defaultfilters import slugify
from django.core.files.images import ImageFile as DjangoImageFile
from django.db.models.fields.files import FieldFile as DjangoFieldFile, FileField as DjangoFileField
from django.core.files.uploadhandler import FileUploadHandler
from django.views.generic import TemplateView

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.response import Response

from request.utils import BearerAuthentication
from request.models import to_dict, get_preview_from_extension

logger = logging.getLogger('easypro')


class Upload(TemplateView):
    template_name = 'request/upload.html'

class ProgressUploadHandler(FileUploadHandler):
    UPLOAD_DIR = getattr(settings, 'UPLOAD_DIR', 'uploads')

    def __init__(self, request=None):
        super(ProgressUploadHandler, self).__init__(request)
        if 'upload_hash' in self.request.GET:
            self.upload_hash = self.request.GET['upload_hash']
            cache.add(self.upload_hash, {})
            self.activated = True
        else:
            self.activated = False

    def new_file(self, *args, **kwargs):
        super(ProgressUploadHandler, self).new_file(*args, **kwargs)
        if self.activated:
            fields = cache.get(self.upload_hash)
            fields[self.field_name] = 0
            cache.set(self.upload_hash, fields)

    def receive_data_chunk(self, raw_data, start):
        if getattr(settings, 'LOCAL_DEV', False):
            time.sleep(1)  # for local test, it slow down the upload speed
        if self.activated:
            fields = cache.get(self.upload_hash)
            fields[self.field_name] = start
            cache.set(self.upload_hash, fields)
        return raw_data

    def file_complete(self, file_size):
        if self.activated:
            fields = cache.get(self.upload_hash)
            fields[self.field_name] = -1
            cache.set(self.upload_hash, fields)

    def upload_complete(self):
        if self.activated:
            fields = cache.get(self.upload_hash)
            fields[self.upload_hash] = -1
            cache.set(self.upload_hash, fields)


class UploadFileForm(forms.Form):
    title = forms.CharField(max_length=50, required=False)
    file = forms.FileField()


class FieldFile(DjangoFieldFile):

    def save(self, name, content, save=True):
        super(FieldFile, self).save(name, content, save)
        if self.field.callback:
            if type(self.field.callback) == str:
                fn = import_string(self.field.callback)
            else:
                fn = self.field.callback
            fn(self.name)


class FileField(DjangoFileField):
    """
    An extension of the django FileField that accepts a callback option in field declaration.
    The callback is run when the associated FieldFile is saved.
    """
    attr_class = FieldFile

    def __init__(self, callback=None, read_only=False, allowed_extensions=None, *args, **kwargs):
        self.callback = callback
        self.read_only = read_only
        self.allowed_extensions = allowed_extensions  # List of allowed extensions. Eg: ['csv', 'pdf', 'doc']
        super(FileField, self).__init__(*args, **kwargs)


def _add_suffix(suffix, s):
    """
    Modifies a string (filename, URL) containing an image filename, to insert
    '.suffix' (Eg: .small, .thumb, etc.) before the file extension (which is changed to be '.jpg').
    """
    parts = s.split(".")
    parts.insert(-1, suffix)
    return ".".join(parts)


class MultiImageFieldFile(DjangoFileField):

    def _get_lowqual_name(self):
        return _add_suffix('lowqual', self.name)
    lowqual_name = property(_get_lowqual_name)

    def _get_lowqual_path(self):
        return _add_suffix('lowqual', self.path)
    lowqual_path = property(_get_lowqual_path)

    def _get_lowqual_url(self):
        return _add_suffix('lowqual', self.url)
    lowqual_url = property(_get_lowqual_url)

    def _get_small_name(self):
        return _add_suffix('small', self.name)
    small_name = property(_get_small_name)

    def _get_small_path(self):
        return _add_suffix('small', self.path)
    small_path = property(_get_small_path)

    def _get_small_url(self):
        return _add_suffix('small', self.url)
    small_url = property(_get_small_url)

    def _get_thumb_name(self):
        return _add_suffix('thumb', self.name)
    thumb_name = property(_get_thumb_name)

    def _get_thumb_path(self):
        return _add_suffix('thumb', self.path)
    thumb_path = property(_get_thumb_path)

    def _get_thumb_url(self):
        return _add_suffix('thumb', self.url)
    thumb_url = property(_get_thumb_url)

    def save(self, name, content, save=True):
        super(MultiImageFieldFile, self).save(name, content, save)

        # Save the .small version of the image
        img = Image.open(self.path)
        img.thumbnail(
            (self.field.small_size, self.field.small_size),
            Image.ANTIALIAS
        )
        img.save(self.small_path, quality=96)

        # Save the .thumb version of the image
        img = Image.open(self.path)
        img.thumbnail(
            (self.field.thumb_size, self.field.thumb_size),
            Image.ANTIALIAS
        )
        img.save(self.thumb_path, quality=96)

        # Save the low quality version of the image with the original dimensions
        if self.field.lowqual > 0:  # Create the Low Quality version only if lowqual is set
            img = Image.open(self.path)
            IMAGE_WIDTH_LIMIT = 1600  # Too big img are of no use on this web site
            lowqual_size = img.size if img.size[0] <= IMAGE_WIDTH_LIMIT else IMAGE_WIDTH_LIMIT, IMAGE_WIDTH_LIMIT
            img.thumbnail(lowqual_size, Image.NEAREST)
            img.save(self.lowqual_path, quality=self.field.lowqual)

    def delete(self, save=True):
        if os.path.exists(self.lowqual_path):
            os.remove(self.lowqual_path)
        if os.path.exists(self.small_path):
            os.remove(self.small_path)
        if os.path.exists(self.thumb_path):
            os.remove(self.thumb_path)
        super(MultiImageFieldFile, self).delete(save)


class MultiImageField(DjangoImageFile):
    """
    Behaves like a regular ImageField, but stores extra (JPEG) img providing get_FIELD_lowqual_url(), get_FIELD_small_url(),
    get_FIELD_thumb_url(), get_FIELD_small_filename(), get_FIELD_lowqual_filename() and get_FIELD_thumb_filename().
    Accepts three additional, optional arguments: lowqual, small_size and thumb_size,
    respectively defaulting to 15(%), 250 and 60 (pixels).
    """
    attr_class = MultiImageFieldFile

    def __init__(self, small_size=480, thumb_size=150, lowqual=0, *args, **kwargs):
        self.small_size = small_size
        self.thumb_size = thumb_size
        self.lowqual = lowqual
        super(MultiImageField, self).__init__(*args, **kwargs)


@csrf_exempt
@authentication_classes([BearerAuthentication])
@permission_classes([IsAuthenticated])
def upload_file(request, *args, **kwargs):
    if request.method == 'POST':
        request.upload_handlers.insert(0, ProgressUploadHandler(request))
        form = UploadFileForm(request.POST, request.FILES)
        response = {'error': form.errors}
        if form.is_valid():
            response = handle_uploaded_file(request, **kwargs)
            response["success"] = True
            return HttpResponse(json.dumps(response))
        return HttpResponse(json.dumps(response))
    elif request.method == 'GET':  # GET access returns the upload progress
        upload_hash = request.GET['upload_hash']
        upload_status = cache.get(upload_hash)
        return HttpResponse(json.dumps(upload_status))


def handle_uploaded_file(request, **kwargs):
    f = request.FILES['file']
    upload_dir = ProgressUploadHandler.UPLOAD_DIR.strip("/")
    filename_no_extension, extension = os.path.splitext(f.name)
    filename_no_extension = slugify(filename_no_extension)
    filename = filename_no_extension + extension
    if extension.lower() in ['.gif', '.jpeg', '.jpg', '.png', '.svg', '.webp']:
        is_image = True
    else:
        is_image = False

    media_root = getattr(settings, 'MEDIA_ROOT')
    tmp_dir = media_root + upload_dir
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    unique_filename = False
    filename_suffix = 0
    if os.path.isfile(os.path.join(tmp_dir, filename)):
        while not unique_filename:
            try:
                if filename_suffix == 0:
                    open(os.path.join(tmp_dir, filename))
                else:
                    open(os.path.join(tmp_dir, filename_no_extension + str(filename_suffix) + extension))
                filename_suffix += 1
            except IOError:
                unique_filename = True
        if filename_suffix > 0:
            filename = filename_no_extension + str(filename_suffix) + extension
    tmp_dest = os.path.join(tmp_dir, filename)
    with open(tmp_dest, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    media_url = getattr(settings, 'MEDIA_URL')
    path = os.path.join(upload_dir, filename)
    model_name = request.POST.get('model_name', kwargs.get('model_name'))
    object_id = request.POST.get('object_id', kwargs.get('object_id'))
    host_model_name = request.POST.get('host_model_name', kwargs.get('host_model_name'))  # Model holding the list of photos
    host_object_id = request.POST.get('host_object_id', kwargs.get('host_object_id'))  # ID of the model object
    db_alias = request.GET.get('db_alias', 'default')  # Database to search the object from
    if host_model_name:
        from request.models import Attachment, Photo
        attachment_obj = Photo.objects.create() if is_image else Attachment.objects.create()
        model_name = 'core.photo' if is_image else 'core.attachment'
        object_id = attachment_obj.id
    required_width = request.POST.get('required_width')
    required_height = request.POST.get('required_height')
    rand = ''.join([random.SystemRandom().choice(string.ascii_letters) for i in range(6)])
    full_path = media_root + path
    if required_width and required_height:
        img = Image.open(full_path)
        if img.size != (int(required_width), int(required_height)):
            return {'error': _('Expected size is %(width)s x %(height)s px.' % {'width': required_width, 'height': required_height}),
                    'wrong_size': True}
    if model_name and object_id:
        media_field = request.POST.get('media_field', kwargs.get('media_field'))
        if host_model_name:
            media_field = 'image' if is_image else 'file'
        elif not media_field:
            media_field = request.POST.get('image_field', 'image')
        tokens = model_name.split('.')
        model = apps.get_model(tokens[0], tokens[1])
        try:
            obj = model.objects.using(db_alias).get(pk=object_id)
        except model.DoesNotExist:
            raise Http404(f"{model_name} not found with pk={object_id}")
        media = obj.__getattribute__(media_field)
        if media.field.read_only and media.name and time.time() - os.path.getctime(media.path) > 3600:
            return {'error': _('Cannot modify a read-only image.')}
        try:
            with open(media_root + path, 'rb') as f:
                content = File(f)
                current_media_path = media.path if media.name else None
                upload_to = media.field.upload_to
                if callable(upload_to):
                    upload_to = upload_to(obj, filename)
                _dir = media_root + upload_to
                unique_filename = False
                filename_suffix = 0
                filename_no_extension, extension = os.path.splitext(filename)
                if is_image:
                    filename = f'easypro_{filename}'
                filepath = os.path.join(_dir, filename)
                if os.path.isfile(filepath):
                    # If file was created a few seconds ago, it is probably a duplicate, so stop here and return
                    if time.time() - os.path.getctime(filepath) < 60:
                        try:
                            kwargs = {media_field: os.path.join(upload_to, filename)}
                            obj = model._default_manager.filter(**kwargs).order_by('-id')[0]
                            media = obj.__getattribute__(media_field)
                            url, preview_url = get_uploaded_media_urls(media, is_image)
                            return {
                                'id': str(obj.id),
                                'path': url,
                                'url': url,
                                'preview': preview_url + '?rand=' + rand
                            }
                        except:
                            pass
                    while not unique_filename:
                        try:
                            if filename_suffix == 0:
                                open(os.path.join(_dir, filename))
                            else:
                                open(os.path.join(_dir, filename_no_extension + str(filename_suffix) + extension))
                            filename_suffix += 1
                        except IOError:
                            unique_filename = True
                if filename_suffix > 0:
                    filename = filename_no_extension + str(filename_suffix) + extension

                destination = os.path.join(media_root + upload_to, filename)
                if not os.path.exists(_dir):
                    os.makedirs(_dir)
                media.save(filename, content)
                url, preview_url = get_uploaded_media_urls(media, is_image)
            try:
                if media and os.path.exists(media_root + path):
                    os.unlink(media_root + path)  # Remove file from upload tmp folder
            except Exception as e:
                if getattr(settings, 'DEBUG', False):
                    raise e
            if current_media_path:
                try:
                    if destination != current_media_path and os.path.exists(current_media_path):
                        os.unlink(current_media_path)
                except OSError as e:
                    if getattr(settings, 'DEBUG', False):
                        raise e
            if host_model_name and host_object_id:
                # Save host model when a new photo is uploaded.
                tokens = host_model_name.split('.')
                host_model = apps.get_model(tokens[0], tokens[1])
                try:
                    host_obj = host_model.objects.using(db_alias).get(pk=host_object_id)
                except model.DoesNotExist:
                    raise Http404(f"{model_name} not found with pk={host_object_id}")
                attachment_list_field = request.POST.get('attachment_list_field',
                                                         kwargs.get('attachment_list_field', 'images'))
                attachments = host_obj.__getattribute__(attachment_list_field)
                attachments.append(to_dict(obj, generate_file_url_keys=False))
                attachments.sort(key=lambda elt: elt['id'] if type(elt) == dict else elt.id)
                host_obj.__dict__[attachment_list_field] = attachments
                host_obj.save()

            events = getattr(settings, 'UPLOAD_CALLBACKS', ())
            for path in events:
                try:
                    event = import_string(path)
                    event(request, obj)
                except:
                    logger.error("Error in upload callback on object %s" % obj, exc_info=True)

            return {
                'id': str(obj.id),
                'path': url,
                'url': url,
                'preview': preview_url + '?rand=' + rand
            }
        except ObjectDoesNotExist:
            if host_model_name:
                error_message = f"No {host_model_name} found with id {host_object_id}."
            else:
                error_message = f"No {model_name} found with id {object_id}."
            logger.error(error_message, exc_info=True)
            return {'error': error_message}
        except Exception as e:
            logger.error(f"Upload failed: {e}", exc_info=True)
            return {'error': f"Upload failed: {e}"}
    else:
        raw_filename, extension = os.path.splitext(filename)
        url = f"{media_url}{path}"
        resp = {"path": path, "url": url, "preview": url}
        if extension.lower() not in ['.gif', '.jpeg', '.jpg', '.png', '.svg', '.webp']:
            resp["preview"] = get_preview_from_extension(filename)
        handlers = getattr(settings, 'FILE_UPLOAD_COMPLETE_HANDLERS', ())
        for handler in handlers:
            try:
                handler = import_string(handler)
                handler_resp = handler(request, path)
                if handler_resp:
                    resp.update(handler_resp)
            except:
                logger.error(f"Error while running upload handler on {filename}", exc_info=True)
        return resp


@api_view(['DELETE'])
@authentication_classes([BearerAuthentication])
@permission_classes([IsAuthenticated])
def delete_single_media(request, pk=None, *args, **kwargs):
    model_name = request.data.get("model_name", request.GET.get("model_name"))
    media_field = request.data.get("media_field", request.GET.get("media_field", "image"))
    object_id = request.data.get("object_id", request.GET.get("object_id", pk))
    if not object_id:
        return Response({"error": "Object doesn't exist"}, status=status.HTTP_404_NOT_FOUND)

    try:
        tokens = model_name.split('.')
        model = apps.get_model(tokens[0], tokens[1])
        obj = model._default_manager.get(pk=object_id)
        media = obj.__getattribute__(media_field)
        if media.field.read_only and media.name and time.time() - os.path.getctime(media.path) > 3600:
            return {'error': _('Cannot delete a read-only image.')}
        filename = getattr(settings, 'MEDIA_ROOT') + media.name
        try:
            if os.path.exists(filename):
                os.unlink(filename)
        except:
            logger.error("Could not delete file %s" % filename)
        obj.__setattr__(media_field, "")
        obj.save()
    except model.DoesNotExist:
        return Response({"error": "Object doesn't exist"}, status=status.HTTP_404_NOT_FOUND)
    return Response(status=status.HTTP_204_NO_CONTENT)


def get_uploaded_media_urls(media, is_image):
    """Returns URLs of the file uploaded, and the preview URL"""
    media_url = getattr(settings, 'MEDIA_URL')
    if isinstance(media, MultiImageFieldFile):
        url = media_url + media.small_name
        preview_url = url
    elif is_image:
        url = media_url + media.name
        preview_url = url
    else:
        url = media_url + media.name
        preview_url = get_preview_from_extension(media.name)
    return url, preview_url

