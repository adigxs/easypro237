from datetime import timedelta

from django.contrib.admin.sites import AlreadyRegistered
from django.contrib.auth.models import Permission
from django.utils import timezone
from django.contrib import admin

from import_export.admin import ImportExportModelAdmin
from import_export import resources

from request.models import Agent, Region, Department, District, Request, OfficeDistrict, Service


# Register your models here.

class AgentAdmin(admin.ModelAdmin):
    class Meta:
        model = Agent
        fields = '__all__'
        # readonly_fields = ('email', 'password',)


class Region(admin.ModelAdmin):
    class Meta:
        model = Region
        fields = '__all__'
        # readonly_fields = ('email', 'password',)
        # search_fields = ('first_name', 'last_name')


class DepartmentAdmin(admin.ModelAdmin):
    class Meta:
        model = Department
        fields = '__all__'
        # readonly_fields = ('email', 'password',)
        # search_fields = ('first_name', 'last_name')


class RequestAdmin(admin.ModelAdmin):
    class Meta:
        model = Request
        fields = '__all__'
        # readonly_fields = ('email', 'password',)
        # search_fields = ('first_name', 'last_name')


class OfficeDistrictAdmin(admin.ModelAdmin):
    class Meta:
        model = OfficeDistrict
        fields = '__all__'


class ServiceAdmin(admin.ModelAdmin):
    class Meta:
        model = Service
        fields = '__all__'
        # readonly_fields = ('email', 'password',)
        # search_fields = ('first_name', 'last_name')
