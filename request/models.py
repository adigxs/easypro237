from bson import ObjectId
import uuid
import json
import os
import typing
from datetime import datetime, date, timezone
from copy import deepcopy

from django.db import models
from django.contrib import admin
from django.contrib.auth.models import AbstractUser, Permission, Group, UserManager
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils.module_loading import import_string
from django.core.files.images import ImageFile as DjangoImageFile

from django.apps import apps
from django.conf import settings
from django.core.files import File
from django.template.defaultfilters import slugify
from django.core.files.images import ImageFile as DjangoImageFile
from django.db.models import Field, Model, ForeignKey
from django.db.models.fields.files import FieldFile as DjangoFieldFile, FileField as DjangoFileField
from django.db.models.fields.files import ImageFieldFile
from django.db.models.fields.files import ImageFieldFile as DjangoImageFieldFile
from django.core.files.uploadhandler import FileUploadHandler


from request.constants import REQUEST_STATUS, REQUEST_FORMATS, MARITAL_STATUS, TYPE_OF_DOCUMENT, GENDERS, COURT_TYPES, \
    STARTED, DELIVERY_STATUSES, CIVILITIES, PENDING


def get_preview_from_extension(filename):
    raw_filename, extension = os.path.splitext(filename)
    extension = extension.lower()
    if extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']:
        return f"{getattr(settings, 'MEDIA_URL')}{filename}"
    if extension == '.pdf' and os.path.exists(f"{getattr(settings, 'MEDIA_ROOT')}{raw_filename}.jpg"):
        return f"{getattr(settings, 'MEDIA_URL')}{raw_filename}.jpg"
    if extension in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.pdf', '.mp3', '.mp4', '.zip', '.xz', '.gz',
                     '.7z', '.rar', '.ods']:
        extension = extension[1:]
    else:
        extension = 'unknown'
    return getattr(settings, 'CLUSTER_STATIC_URL') + 'request/img/ext/%s.png' % extension


class FieldFile(DjangoFieldFile):

    def save(self, name, content, save=True):
        super(FieldFile, self).save(name, content, save)
        if self.field.callback:
            if type(self.field.callback) == str:
                fn = import_string(self.field.callback)
            else:
                fn = self.field.callback
            fn(self.name)

def get_object_id():
    """Generates a string version of bson ObjectId."""
    return str(ObjectId())

def get_object_id():
    """Generates a string version of bson ObjectId."""
    # return str(ObjectId())
    return str(uuid.uuid4())


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


class BaseAdapterModel(models.Model):
    """
    This abstract model uses id as a string version of
    bson ObjectId. This is done to support models coming
    from the MongoDB storage; so those models must inherit
    this class to work properly.
    """
    id = models.CharField(max_length=36, primary_key=True, default=get_object_id, editable=True)

    class Meta:
        abstract = True


class BaseModel(models.Model):
    """
    Helper base Model that defines two fields: created_on and updated_on.
    Both are DateTimeField. updated_on automatically receives the current
    datetime whenever the model is updated in the database
    """
    created_on = models.DateTimeField(auto_now_add=True, null=True, editable=False, db_index=True)
    updated_on = models.DateTimeField(auto_now=True, null=True, db_index=True)

    class Meta:
        abstract = True

    def save(self, **kwargs):
        for field in self._meta.fields:
            if type(field) == JSONField and isinstance(self.__getattribute__(field.name), models.Model):
                self.__setattr__(field.name, to_dict(self.__getattribute__(field.name), False))
        super(BaseModel, self).save(**kwargs)

    def to_dict(self):
        return to_dict(self)

    def _get_display_date(self):
        if not self.created_on:
            return ''
        now = timezone.now()
        if self.created_on.year == now.year and self.created_on.month == now.month \
                and self.created_on.day == now.day:
            return self.created_on.strftime('%H:%M')
        return self.created_on.strftime('%Y-%m-%d')
    display_date = property(_get_display_date)



class Model(BaseAdapterModel, BaseModel):
    """
    Helper base Model that creates a model suitable for save in MongoDB
    with fields created_on and updated_on.
    """

    def get_from(self, db):
        add_database_to_settings(db)
        return type(self).objects.using(db).get(pk=self.id)

    class Meta:
        abstract = True


class Attachment(Model):
    file = FileField(upload_to='attachments', blank=True, null=True)

    def delete(self, *args, **kwargs):
        try:
            os.unlink(self.file.path)
        except:
            pass
        super(Attachment, self).delete(*args, **kwargs)

    def __str__(self):
        return f"{getattr(settings, 'MEDIA_URL')}{self.file.name}"

class JSONField(Field):
    """
    Field that allows arbitrary JSON as an object or list. A model_container
    may be used for inclusion of a model as the object or in the list
    """
    empty_strings_allowed = False

    def db_type(self, connection):
        if connection.settings_dict['ENGINE'] == 'django.db.backends.sqlite3':
            return 'text'
        else:
            return 'json'

    def __init__(self,
                 model_container: (typing.Type[Model], str) = None,
                 *args, **kwargs):
        self.model_container = model_container
        super().__init__(*args, **kwargs)

    def get_model_container(self):
        model_container = self.model_container
        if isinstance(model_container, str):
            model_container = apps.get_model(*model_container.split('.'))
        return model_container

    def __load_obj_from_value_and_model_container(self, value, model_container, foreign_keys):
        foreign_keys_values = {}
        for fkey, related_model in foreign_keys.items():
            try:
                foreign_keys_values[fkey] = related_model.objects.get(pk=value[fkey + '_id'])
            except:
                foreign_keys_values[fkey] = None
            try:
                del(value[fkey + '_id'])
            except:
                pass
        field_names = [field.name for field in model_container._meta.fields]
        fields = dict(value)
        for key in fields.keys():
            if key not in field_names:
                del(value[key])
        obj = model_container(**value)
        for fkey, val in foreign_keys_values.items():
            obj.__setattr__(fkey, val)
        return obj

    def get_prep_value(self, value):
        from ikwen.core.utils import to_dict
        model_container = None
        if self.model_container:
            model_container = self.get_model_container()
        if isinstance(value, models.Model):
            if model_container and not isinstance(value, model_container):
                raise ValueError(f'Value: {value} must be of type {model_container}.')
            value = to_dict(value, generate_file_url_keys=False)
        elif isinstance(value, list):
            data = deepcopy(value)
            value = []
            for elt in data:
                if isinstance(elt, dict):
                    value.append(elt)
                elif isinstance(elt, models.Model):
                    if model_container and not isinstance(elt, model_container):
                        raise ValueError(f'Value: {elt} must be of type {model_container}.')
                    value.append(to_dict(elt, generate_file_url_keys=False))
                elif isinstance(elt, object) \
                    and not (elt is None or isinstance(elt, int) or isinstance(elt, float)
                             or isinstance(elt, bool) or isinstance(elt, dict)):
                    value.append(str(elt))
                else:
                    value.append(elt)
        elif not isinstance(value, (dict, list)):
            raise ValueError(f'Value: {value} must be of type dict/list')
        return json.dumps(value)

    def get_db_prep_save(self, value, connection):
        return self.get_prep_value(value)

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def to_python(self, value):
        model_container = None
        if value is None:
            return None
        if self.model_container:
            model_container = self.get_model_container()
        if isinstance(value, models.Model):
            if model_container and not isinstance(value, model_container):
                raise ValueError(f'Value: {value} must be of type {model_container}.')
        elif not isinstance(value, (dict, list)):
            try:
                value = json.loads(value)
            except:
                raise ValueError(
                    f'Value: {value} stored in DB must be of type dict/list'
                    'Did you miss any Migrations?'
                )
        if model_container:
            foreign_keys = {}
            for field in model_container._meta.fields:
                if isinstance(field, ForeignKey):
                    foreign_keys[field.name] = field.related_model
            # if isinstance(value, dict):
            #     value = self.__load_obj_from_value_and_model_container(value, model_container, foreign_keys)
            if isinstance(value, list):
                data = list(value)
                value = []
                for elt in data:
                    obj = self.__load_obj_from_value_and_model_container(elt, model_container, foreign_keys)
                    value.append(obj)
        return value


class ImageFieldFile(DjangoImageFile, FieldFile):

    def delete(self, save=True):
        # Clear the image dimensions cache
        if hasattr(self, '_dimensions_cache'):
            del self._dimensions_cache
        super(ImageFieldFile, self).delete(save)

    def save(self, name, content, save=True):
        super(ImageFieldFile, self).save(name, content, save)
        img = Image.open(self.path)
        if self.field.required_width and img.size[0] != self.field.required_width:
            raise ValueError("%s requires a %dx%d image." % (self.field.name, self.field.required_width,
                                                             self.field.required_height))
        if self.field.required_height and img.size[1] != self.field.required_height:
            raise ValueError("%s requires a %dx%d image." % (self.field.name, self.field.required_width,
                                                             self.field.required_height))

        max_size = self.field.max_size
        if max_size > 0:  # Create a new version of image if too large
            img = Image.open(self.path)
            if img.size[0] > max_size or img.size[1] > max_size:
                new_size = (max_size, max_size)
            else:
                new_size = img.size
            img.thumbnail(new_size, Image.ANTIALIAS)
            img.save(self.path, quality=96)


class ImageField(DjangoFileField):
    """
    An extension of the django FileField that accepts a callback option in field declaration.
    The callback is run when the associated FieldFile is saved.
    """
    attr_class = ImageFieldFile

    def __init__(self, required_width=None, required_height=None, max_size=0,
                 allowed_extensions=None, callback=None, read_only=False, *args, **kwargs):
        self.required_width = required_width
        self.required_height = required_height
        self.max_size = max_size
        self.allowed_extensions = allowed_extensions  # List of allowed extensions. Eg: ['csv', 'pdf', 'doc']
        self.callback = callback
        self.read_only = read_only
        super(ImageField, self).__init__(*args, **kwargs)





class MultiImageFieldFile(ImageFieldFile):

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


class MultiImageField(ImageField):
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

def to_dict(var, generate_file_url_keys=True):
    try:
        dict_var = deepcopy(var).__dict__
    except AttributeError:
        return var
    keys_to_remove = []
    updates = {}
    for key in dict_var.keys():
        if key[0] == '_':
            keys_to_remove.append(key)
            continue
        elif type(dict_var[key]) is datetime:
            dict_var[key] = dict_var[key].strftime('%Y-%m-%d %H:%M:%S')
        elif type(dict_var[key]) is date:
            dict_var[key] = dict_var[key].strftime('%Y-%m-%d')
        elif type(dict_var[key]) is list:
            try:
                dict_var[key] = [item.to_dict() for item in dict_var[key]]
            except AttributeError:
                dict_var[key] = [to_dict(item) for item in dict_var[key]]
        elif isinstance(var.__getattribute__(key), DjangoImageFieldFile)\
                or isinstance(var.__getattribute__(key), ImageFieldFile)\
                or isinstance(var.__getattribute__(key), FieldFile):
            if generate_file_url_keys:
                if var.__getattribute__(key).name:
                    updates[key + '_url'] = var.__getattribute__(key).url
                else:
                    updates[key + '_url'] = ''
                updates[key] = var.__getattribute__(key).name
            elif var.__getattribute__(key).name:
                updates[key] = var.__getattribute__(key).name
            else:
                updates[key] = ''
        elif isinstance(var.__getattribute__(key), MultiImageFieldFile):
            if generate_file_url_keys:
                if var.__getattribute__(key).name:
                    updates[key + '_url'] = var.__getattribute__(key).url
                    updates[key + '_small_url'] = var.__getattribute__(key).small_url
                    updates[key + '_thumb_url'] = var.__getattribute__(key).thumb_url
                else:
                    updates[key + '_url'] = ''
                    updates[key + '_small_url'] = ''
                    updates[key + '_thumb_url'] = ''
                updates[key] = var.__getattribute__(key).name
            elif var.__getattribute__(key).name:
                updates[key] = var.__getattribute__(key).name
            else:
                updates[key] = ''
        elif isinstance(dict_var[key], Model):
            try:
                dict_var[key] = dict_var[key].to_dict()
            except AttributeError:
                dict_var[key] = to_dict(dict_var[key])
        elif isinstance(dict_var[key], object) \
                and not (dict_var[key] is None or isinstance(dict_var[key], int) or isinstance(dict_var[key], float)
                         or isinstance(dict_var[key], bool) or isinstance(dict_var[key], dict)):
            dict_var[key] = str(dict_var[key])
    for key in keys_to_remove:
        del(dict_var[key])
    dict_var.update(updates)
    return dict_var

class Photo(Model):
    UPLOAD_TO = 'photos'
    image = MultiImageField(upload_to=UPLOAD_TO, blank=True, null=True, max_size=800)

    def delete(self, *args, **kwargs):
        try:
            os.unlink(self.image.path)
        except:
            pass
        try:
            os.unlink(self.image.small_path)
        except:
            pass
        try:
            os.unlink(self.image.thumb_path)
        except:
            pass
        super(Photo, self).delete(*args, **kwargs)

    def __str__(self):
        return f"{getattr(settings, 'MEDIA_URL')}{self.image.name}"



class TrashQuerySet(models.QuerySet):
    """
    QuerySet whose delete() does not delete items, but instead marks the
    rows as not active, and updates the timestamps
    """
    def delete(self):
        count = self.count()
        for obj in self:
            obj.delete()
        return count


class TrashManager(models.Manager):
    def get_queryset(self):
        return TrashQuerySet(self.model, using=self._db)


class TrashMixin(models.Model):
    objects = TrashManager()

    class Meta:
        abstract = True

    def delete(self, **kwargs):
        try:
            TrashModel.objects.create(model_name=self._meta.label, data=self.to_dict())
        except:
            pass
        super(TrashMixin, self).delete(**kwargs)


def add_database_to_settings(db_url):
    """
    Adds a database connection to the global settings on the fly.
    That is equivalent to do the following in Django settings file:

    DATABASES = {
        'default': {
            'ENGINE': 'current_database_engine',
            'NAME': 'default_database',
            ...
        },
        'alias': {
            'ENGINE': 'engine_in_db_info',
            'NAME': database,
            ...
        }
    }

    That connection is named 'database'
    @param db_url: string representing database under the form engine://<username>:<password>@<host>[:<port>]/database
    """
    # Defaults
    engine = getattr(settings, 'DATABASES')['default']['ENGINE']
    host = getattr(settings, 'DATABASES')['default'].get('HOST', '127.0.0.1')
    port = getattr(settings, 'DATABASES')['default'].get('PORT')
    username = getattr(settings, 'DATABASES')['default'].get('USER')
    password = getattr(settings, 'DATABASES')['default'].get('PASSWORD')

    tokens = db_url.strip().split('://')
    if len(tokens) == 1:
        alias = tokens[0]
    else:
        engine = tokens[0]
        db_tokens = tokens[1].split('/')
        if len(db_tokens) == 1:
            alias = db_tokens[0]
        else:
            access = db_tokens[0]
            alias = db_tokens[1]
            access_tokens = access.split('@')
            credentials = access_tokens[0].split(':')
            location = access_tokens[1].split(':')
            username = credentials[0]
            password = credentials[1]
            host = location[0]
            if len(location) > 1:
                port = location[1]
    DATABASES = getattr(settings, 'DATABASES')
    if DATABASES.get(alias) is None:  # If this alias was not yet added
        name = alias
        if engine == 'sqlite':
            engine = 'django.db.backends.sqlite3'
            name = os.path.join(getattr(settings, 'BASE_DIR'), '%s.sqlite3' % alias)
        elif engine == 'mysql':
            engine = 'django.db.backends.mysql'
        elif engine == 'postgres':
            engine = 'django.db.backends.postgresql_psycopg2'
        elif engine == 'oracle':
            engine = 'django.db.backends.oracle'
        DATABASES[alias] = {
            'ENGINE': engine,
            'NAME': name,
            'HOST': host
        }
        if port:
            DATABASES[alias]['PORT'] = port
        if username:
            DATABASES[alias]['USER'] = username
            DATABASES[alias]['PASSWORD'] = password
    setattr(settings, 'DATABASES', DATABASES)
    return alias


class Model(BaseAdapterModel, BaseModel):
    """
    Helper base Model that creates a model suitable for save in MongoDB
    with fields created_on and updated_on.
    """

    def get_from(self, db):
        add_database_to_settings(db)
        return type(self).objects.using(db).get(pk=self.id)

    class Meta:
        abstract = True


class TrashModel(Model):
    model_name = models.CharField(max_length=100, db_index=True)
    data = models.JSONField()


class BaseUUIDModel(BaseModel, TrashMixin):
    """Base model using UUID4 as primary key"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=True)

    class Meta:
        abstract = True


class Country(models.Model):
    name = models.CharField(max_length=150)
    iso2 = models.CharField(max_length=2, db_index=True)
    iso3 = models.CharField(max_length=3, db_index=True)
    lang = models.CharField(max_length=2, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    slug = models.SlugField(null=True, blank=True, max_length=150, db_index=True, editable=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Countries"
        unique_together = (
            ('name', 'lang'),
            ('iso2', 'lang'),
            ('iso3', 'lang'),
        )


class Region(models.Model):
    name = models.CharField(max_length=150, null=False, db_index=True)
    slug = models.SlugField(null=True, blank=True, max_length=150, db_index=True, editable=False)
    code = models.CharField(max_length=2, null=False, db_index=True)
    lang = models.CharField(max_length=2, db_index=True)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = (
            ('code', 'lang'),
        )


class Department(models.Model):
    region_code = models.CharField(max_length=2, db_index=True, blank=True, null=True, help_text=_("Region code"))
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True, max_length=150, db_index=True)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = (
            ('region_code', 'name')
        )

    @property
    def region(self, language):
        return get_object_or_404(Region, code=self.region_code, lang=language)

class Court(models.Model):
    name = models.CharField(max_length=150, db_index=True, unique=True)
    slug = models.SlugField(unique=True, db_index=True)
    type = models.CharField(max_length=150, db_index=True, choices=COURT_TYPES)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, db_index=True, null=True, blank=True, default=None)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'{self.name}'

    @property
    def region(self, language=None):
        return get_object_or_404(Region, code=self.department.region_code, lang=language if language else 'en') if self.department else ''

    @property
    def region_code(self):
        return self.department.region_code if self.department else ''


class Municipality(models.Model):
    name = models.CharField(max_length=150, db_index=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, db_index=True)
    slug = models.SlugField(unique=True, max_length=150)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Municipalities"

    @admin.display(description="Region")
    def region(self, language):
        return get_object_or_404(Region, code=self.department.region_code, lang=language) if self.department else ''
        
    @property
    def region(self, language):
        return get_object_or_404(Region, code=self.department.region_code, lang=language) if self.department else ''


class Town(models.Model):
    municipality = models.ForeignKey(Municipality, on_delete=models.CASCADE, db_index=True)
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True, max_length=150, db_index=True)

    def __str__(self):
        return self.name

class Service(models.Model):
    type_of_document = models.CharField(max_length=150, choices=TYPE_OF_DOCUMENT)
    format = models.CharField(max_length=150, choices=REQUEST_FORMATS)
    rob_code = models.CharField(max_length=2, help_text=_("Region of birth"), blank=True, null=True)
    ror_code = models.CharField(max_length=2, help_text=_("Region of residency"), blank=True, null=True)
    cor_code = models.CharField(max_length=2, help_text=_("Country of residency"), blank=True, null=True)
    cost = models.PositiveIntegerField(default=0)
    disbursement = models.FloatField(_("Disbursement fee of the service"), default=0)
    stamp_fee = models.FloatField(_("Recognized stamp fee of the service"), default=0)
    honorary_fee = models.FloatField(_("Honorary fee of the service"), default=0)
    excavation_fee = models.FloatField(_("Excavation fee of the service"), default=500)

    additional_cr_fee = models.FloatField(_("Default additional criminal record fee of the service"), default=0)
    currency_code = models.CharField(max_length=5, default='XAF',
                                     help_text=_("Code of your currency. Eg: <strong>USD, GBP, EUR, XAF,</strong> ..."))

    def __str__(self):
        return self.type_of_document

    class Meta:
        unique_together = (
            ('format', 'ror_code', 'rob_code', 'cor_code'),
        )


class Agent(BaseUUIDModel, AbstractUser):
    """
    Agent will play the role of User model.
    """
    created_on = models.DateTimeField(auto_now_add=True, null=True, editable=False)
    updated_on = models.DateTimeField(auto_now_add=True, null=True, editable=False)
    gender = models.CharField(max_length=1, choices=GENDERS)
    verify = models.BooleanField(default=False, help_text=_("Ensure email or phone is verified"))
    phone = models.TextField(help_text=_("Phone"), editable=True)
    dob = models.DateField(blank=True, null=True, db_index=True, help_text=_("Date of birth"), editable=True)
    logo = models.FileField(_("Agent profile picture"), blank=True, null=True, upload_to="Agents")
    court = models.ForeignKey(Court, db_index=True, on_delete=models.PROTECT, null=True, blank=True)
    region_code = models.CharField(max_length=2, db_index=True, null=True, blank=True)
    is_csa = models.BooleanField(default=False)
    pending_task_count = models.IntegerField(default=0)
    lang = models.CharField(max_length=2, help_text=_("Agent language"), blank=True, null=True,
                            db_index=True, default='en')

    def __str__(self):
        return f'{self.first_name}, {self.last_name}'

    @property
    def full_name(self):
        return self.__str__()

    objects = UserManager()

    class Meta:
        permissions = [
            ("view_user_birthday_certificate", "Can view and download birthday certificate"),
            ("view_user_passport", "Can view user passport"),
            ("view_proof_of_stay", "Can view proof of stay"),
            ("view_id_card", "Can view ID card"),
            ("view_wedding_certificate", "Can view wedding certificate"),
            ("view_destination_address", "Can view destination address"),
            ("view_destination_location", "Can view destination location"),
            ("change_request_status", "Can change status of a request"),
        ]
        ordering = ['first_name', 'last_name']


class Request(models.Model):
    code = models.CharField(max_length=20, unique=True, db_index=True)
    created_on = models.DateTimeField(auto_now_add=True, null=True, editable=False)
    updated_on = models.DateTimeField(auto_now_add=True, null=True, editable=False)
    status = models.CharField(max_length=15, choices=REQUEST_STATUS, default=STARTED, db_index=True)

    user_full_name = models.CharField(max_length=150, help_text=_("Full name of the client requesting the service"),
                                      db_index=True)
    user_first_name = models.CharField(max_length=150, help_text=_("First name of the client requesting the service"),
                                       db_index=True)

    user_last_name = models.CharField(max_length=150, help_text=_("Last name of the client requesting the service"),
                                      db_index=True, null=True, blank=True)
    user_middle_name = models.CharField(max_length=150, help_text=_("Middle name of client requesting the service"),
                                        db_index=True, null=True, blank=True)
    user_gender = models.CharField(max_length=6, choices=GENDERS, help_text=_("Gender of client requesting "
                                                                              "the service"), db_index=True)
    user_civility = models.CharField(_("Civility"), max_length=15, choices=CIVILITIES,
                                     help_text=_("Civility of the client requesting the service"), db_index=True,
                                     default='')
    user_id_scan_1 = models.FileField(upload_to="SCANS", help_text=_("ID card scan of client requesting the service"),
                                    db_index=True, null=True, blank=True)
    user_id_scan_2 = models.FileField(upload_to="SCANS", help_text=_("ID card scan of client requesting the service"),
                                    db_index=True, null=True, blank=True)
    user_passport_1 = models.FileField(upload_to="SCANS", help_text=_("Passport of client requesting the service"),
                                     db_index=True, null=True, blank=True)
    user_passport_2 = models.FileField(upload_to="SCANS", help_text=_("Passport of client requesting the service"),
                                       db_index=True, null=True, blank=True)
    proof_of_stay = models.FileField(upload_to="SCANS", help_text=_("Proof of stay in Cameroon"),
                                     db_index=True, null=True, blank=True)
    user_birthday_certificate = models.FileField(upload_to="SCANS", help_text=_("Birthday certificate of client "
                                                                                "requesting the service"),
                                                 db_index=True, null=True, blank=True)
    user_phone_number_1 = models.CharField(max_length=15, help_text=_("1st phone number of the client requesting "
                                                                      "the service"), db_index=True)
    user_phone_number_2 = models.CharField(max_length=15, help_text=_("2nd phone number of the client  of client "
                                                                      "requesting the service"), db_index=True, null=True, blank=True)
    user_close_friend_number = models.CharField(max_length=15, help_text=_("Close friend phone's number"), db_index=True,
                                           null=True, blank=True)

    user_whatsapp_number = models.CharField(max_length=15, help_text=_("Whatsapp phone number of client requesting the service"),
                                            db_index=True)
    user_email = models.EmailField(max_length=150, help_text=_("Email of client requesting the service"),
                                   db_index=True, null=True, blank=True)
    user_dob = models.DateField(_("Date of birth"), blank=True, null=True, db_index=True)
    user_dpb = models.ForeignKey(Department, help_text=_("Department of birth"), blank=True, null=True,
                                 db_index=True, on_delete=models.SET_NULL)
    user_cob_code = models.CharField(max_length=2, help_text=_("Country of birth"), blank=True, null=True,
                                 db_index=True, default=None)
    user_lang = models.CharField(max_length=2, help_text=_("User language"), blank=True, null=True,
                                 db_index=True, default='en')
    user_residency_hood = models.CharField(_("Residency's hood"), max_length=150, blank=True, null=True, db_index=True)
    user_residency_state = models.CharField(_("State where the user stays"), max_length=150, blank=True, null=True, db_index=True)
    user_residency_city = models.CharField(_("City where the user stays"), max_length=150, blank=True, null=True, db_index=True)
    user_residency_town = models.ForeignKey(Town, help_text=_("Town of residency"), blank=True,
                                            null=True, on_delete=models.SET_NULL, db_index=True)

    user_residency_country_code = models.CharField(max_length=2, help_text=_("Country of residency"), db_index=True, null=True, blank=True)
    user_residency_municipality = models.ForeignKey(Municipality, help_text=_("Municipality of residency"),
                                                    on_delete=models.SET_NULL, blank=True, null=True, db_index=True,
                                                    related_name="user_residency_municipality")

    user_nationality_code = models.CharField(max_length=2, help_text=_("Nationality of client requesting the service"), null=True,
                                         blank=True, db_index=True)
    user_occupation = models.CharField(_("Occupation of the client requesting the service"), max_length=150,
                                       blank=True, null=True, db_index=True)
    user_marital_status = models.CharField(_("Marital status of the client requesting the service"), max_length=150, blank=True,
                                           null=True, db_index=True, choices=MARITAL_STATUS)

    user_address = models.CharField(max_length=255, null=True, blank=True,
                                    help_text=_("Address line where the user stays"))

    user_postal_code = models.CharField(_("Postal code"), max_length=150, null=True, blank=True,
                                        help_text=_("Postal address of the client, it's going to be use to ship request"))

    user_birthday_certificate_url = models.URLField(max_length=250, blank=True, null=True)
    user_passport_1_url = models.URLField(max_length=250, blank=True, null=True)
    user_passport_2_url = models.URLField(max_length=250, blank=True, null=True)
    user_proof_of_stay_url = models.URLField(max_length=250, blank=True, null=True)
    user_id_card_1 = models.FileField(upload_to='card-uploads', blank=True, null=True)
    user_id_card_1_url = models.URLField(max_length=250, blank=True, null=True)
    user_id_card_2 = models.FileField(upload_to='passport-uploads', blank=True, null=True)
    user_id_card_2_url = models.URLField(max_length=250, blank=True, null=True)
    user_wedding_certificate = models.FileField(upload_to='passport-uploads', blank=True, null=True)
    user_wedding_certificate_url = models.URLField(max_length=250, blank=True, null=True)
    destination_address = models.CharField(max_length=150, db_index=True, blank=True)
    destination_location = models.CharField(max_length=150, db_index=True, blank=True)

    # This parameter mostly relevant for non-Cameroonian but who has stayed in Cameroon during a period
    has_stayed_in_cameroon = models.BooleanField(default=True)
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True)
    copy_count = models.PositiveIntegerField(default=1)
    purpose = models.TextField(_("Describe the purpose of your request"),  blank=True, null=True, db_index=True)
    amount = models.IntegerField(_("Amount of the request"),  blank=True, null=True, db_index=True)
    court = models.ForeignKey(Court, on_delete=models.PROTECT, null=True, blank=True)
    agent = models.ForeignKey(Agent, on_delete=models.PROTECT, null=True, blank=True)


class Shipment(models.Model):
    created_on = models.DateTimeField(auto_now_add=True, null=True, editable=False)
    updated_on = models.DateTimeField(auto_now_add=True, null=True, editable=False)
    agent = models.ForeignKey(Agent, db_index=True, on_delete=models.SET_NULL, blank=True, null=True)
    destination_municipality = models.ForeignKey(Municipality, db_index=True, help_text=_("Municipality where a requested document will be "
                                                                     "shipped"), on_delete=models.SET_NULL, blank=True, null=True)
    destination_town = models.ForeignKey(Town, db_index=True,
                                                 help_text=_("Town where a requested document will be "
                                                             "shipped"), on_delete=models.SET_NULL, blank=True, null=True)
    destination_hood = models.CharField(max_length=250, db_index=True, help_text=_("Hood where a requested document will be "
                                                             "shipped"), blank=True, null=True)

    destination_country_code = models.CharField(max_length=3, db_index=True)
    destination_address = models.CharField(max_length=150, db_index=True, blank=True)
    destination_location = models.CharField(max_length=150, db_index=True, blank=True)
    request = models.ForeignKey(Request, db_index=True, on_delete=models.PROTECT)
    transport_company = models.CharField(max_length=150, db_index=True, blank=True)
    status = models.CharField(max_length=150, choices=DELIVERY_STATUSES, db_index=True, default=STARTED)


class Payment(BaseUUIDModel):
    created_on = models.DateTimeField(auto_now_add=True, null=True, editable=False)
    updated_on = models.DateTimeField(auto_now_add=True, null=True, editable=False)
    request_code = models.CharField(max_length=24, db_index=True, null=True)
    request_codes = models.CharField(max_length=24, db_index=True, null=True, blank=True)
    label = models.CharField(max_length=150, db_index=True, null=True, default="")
    amount = models.FloatField(db_index=True)
    pay_token = models.CharField(max_length=36, null=True, db_index=True)
    mean = models.CharField(_('Payment Methods'), max_length=15, null=True, db_index=True)
    user_lang = models.CharField(_('User Language'), max_length=2, null=True, db_index=True, default=settings.LANGUAGE_CODE)
    operator_tx_id = models.CharField(max_length=50, null=True, db_index=True)
    operator_user_id = models.CharField(max_length=50, null=True, db_index=True)

    status = models.CharField(max_length=36, default=PENDING, db_index=True)
    currency_code = models.CharField(max_length=5, default='XAF',
                                     help_text=_("Code of your currency. Eg: <strong>USD, GBP, EUR, XAF,</strong> ..."))
    message = models.CharField(max_length=255, default='',
                               help_text=_("Message rendered by the gateway for initiated payment transaction ..."))

    class Meta:
        unique_together = (
            ('request_code', 'status'),
        )


class Company(models.Model):
    name = models.CharField(max_length=255, help_text=_("Name of the company ..."))
    percentage = models.PositiveIntegerField(default=0, help_text=_("Percentage the company earns for disbursement"
                                                                    " on each transaction. Eg: 5, 3, 25 etc..."))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Companies"


class Income(BaseModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    amount = models.FloatField(default=0)

    def get_total_amount(self):
        return


class ExpenseReport(models.Model):
    request = models.OneToOneField(Request, db_index=True, on_delete=models.CASCADE, unique=True)
    stamp_fee = models.FloatField(db_index=True)
    stamp_quantity = models.IntegerField(db_index=True)
    honorary_fee = models.FloatField(db_index=True)
    honorary_quantity = models.IntegerField(db_index=True)
    disbursement_fee = models.FloatField(db_index=True)
    disbursement_quantity = models.CharField(max_length=150, default="Forfait")

    def __get_total_stamp_fee(self):
        return self.stamp_quantity * self.stamp_fee

    total_stamp_fee = property(__get_total_stamp_fee)

    def __get_total_honorary_fee(self):
        return self.honorary_quantity * self.honorary_fee

    total_honorary_fee = property(__get_total_honorary_fee)

    def __get_total_disbursement_fee(self):
        return self.disbursement_fee

    total_disbursement_fee = property(__get_total_disbursement_fee)

    def __get_total_amount(self):
        return self.total_stamp_fee + self.total_honorary_fee + self.total_disbursement_fee

