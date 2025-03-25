from django.conf import settings
from django.core.files.uploadhandler import FileUploadHandler
from django.core.cache import cache
import time

from django import forms


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
