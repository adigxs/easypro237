from datetime import timedelta

from django.contrib.admin.sites import AlreadyRegistered
from django.contrib.auth.models import Permission
from django.utils import timezone
from django.contrib import admin

from import_export.admin import ImportExportModelAdmin
from import_export import resources

from request.models import Agent, Region, Department, Municipality, Request, Court, Service


# Register your models here.

class AgentAdmin(admin.ModelAdmin):

    class Meta:
        model = Agent
        fields = '__all__'
        # readonly_fields = ('email', 'password',)


class RegionAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',), }

    class Meta:
        model = Region
        fields = '__all__'

        # readonly_fields = ('email', 'password',)
        # search_fields = ('first_name', 'last_name')


class MunicipalityAdmin(admin.ModelAdmin):
    # prepopulated_fields = {'slug': ('name',), }

    class Meta:
        model = Municipality
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


class CourtAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',), }

    class Meta:
        model = Court
        fields = '__all__'


class ServiceAdmin(admin.ModelAdmin):
    class Meta:
        model = Service
        fields = '__all__'
        # readonly_fields = ('email', 'password',)
        # search_fields = ('first_name', 'last_name')


admin.site.register(Service, ServiceAdmin)
admin.site.register(Agent, AgentAdmin)
admin.site.register(Request, RequestAdmin)
admin.site.register(Court, CourtAdmin)
admin.site.register(Region, RegionAdmin)
admin.site.register(Municipality, MunicipalityAdmin)