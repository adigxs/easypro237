from datetime import timedelta

from django.contrib.admin.sites import AlreadyRegistered
from django.contrib.auth.models import Permission, Group
from django.utils import timezone
from django.contrib import admin

from import_export.admin import ImportExportModelAdmin
from import_export import resources

from request.models import Agent, Region, Department, Municipality, Request, Court, Service, Country, Town, Shipment, \
    Payment, Revenues, Company, ExpenseReport


# Register your models here.

class CountryResource(resources.ModelResource):
    class Meta:
        model = Country
        fields = ('id', 'name', 'iso2', 'iso3', 'is_active')
        export_order = ('name', 'iso2', 'iso3', 'is_active')  # remove is_active


class CountryAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    list_display = ('name', 'slug', 'iso2', 'iso3', 'is_active')
    fields = ('name', 'iso2', 'iso3', 'is_active')
    search_fields = ('name',)
    resource_class = CountryResource

    class Meta:
        model = Country
        fields = '__all__'


class AgentResource(resources.ModelResource):
    class Meta:
        model = Agent
        fields = ('username', 'email', 'full_name', 'court', 'region', 'is_csa')
        export_order = ('username', 'email', 'full_name', 'court', 'region', 'is_csa')  # remove is_active


class AgentAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    list_display = ('full_name', 'email', 'pending_task_count', 'court', 'region', 'is_csa')
    class Meta:
        model = Agent
        fields = '__all__'
        # readonly_fields = ('email', 'password',)


class RegionAdmin(admin.ModelAdmin):
    # prepopulated_fields = {'slug': ('name',), }
    list_display = ('name', 'slug', 'code')

    class Meta:
        model = Region
        fields = '__all__'

        # readonly_fields = ('email', 'password',)
        # search_fields = ('first_name', 'last_name')


class MunicipalityResource(resources.ModelResource):
    class Meta:
        model = Municipality
        fields = ('name', 'department')
        export_order = ('name', 'department')


class MunicipalityAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',), }
    list_display = ('name', 'department', 'region')
    fields = ('name', 'department', 'slug')
    readonly_fields = ('region',)
    list_filter = ('department',)

    class Meta:
        model = Municipality
        fields = '__all__'
        # readonly_fields = ('email', 'password',)
        # search_fields = ('first_name', 'last_name')


class DepartmentResource(resources.ModelResource):
    class Meta:
        model = Department
        fields = ('name', 'region')
        export_order = ('name', 'region')


class DepartmentAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',), }
    list_display = ('name', 'region',)
    fields = ('name', 'region', 'slug',)

    class Meta:
        model = Department
        fields = '__all__'
        # readonly_fields = ('email', 'password',)
        # search_fields = ('first_name', 'last_name')


class TownResource(resources.ModelResource):
    class Meta:
        model = Town
        fields = ('name', 'municipality')
        export_order = ('name', 'region')


class TownAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',), }
    list_display = ('name', 'municipality',)
    fields = ('name', 'municipality', 'slug')

    class Meta:
        model = Town
        fields = '__all__'


class RequestResource(resources.ModelResource):
    class Meta:
        model = Request
        fields = ('code', 'user_civility', 'user_gender', 'user_full_name', 'user_phone_number_1', 'user_dpb',
                  'user_residency_country', 'user_residency_country', 'user_residency_municipality', 'user_nationality',
                  'user_address', 'destination_address', 'destination_location', 'court', 'agent', 'amount')
        export_order = ('code', 'user_civility', 'user_gender', 'user_full_name', 'user_phone_number_1', 'user_dpb',
                        'user_residency_country', 'user_residency_country', 'user_residency_municipality',
                        'user_nationality', 'user_address', 'destination_address', 'destination_location', 'court',
                        'agent', 'amount')


class RequestAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    list_display = ('code', 'user_full_name', 'user_phone_number_1', 'user_gender', 'user_dpb',
                    'user_residency_country', 'court', 'agent', 'amount')
    list_filter = ('status',)

    class Meta:
        model = Request
        fields = '__all__'


class ShipmentAdmin(admin.ModelAdmin):
    list_display = ('agent', 'destination_country', 'destination_municipality', 'request', 'transport_company', 'status')
    # fields = ('name', 'region', 'slug',)

    class Meta:
        model = Shipment
        fields = '__all__'
        # readonly_fields = ('email', 'password',)
        # search_fields = ('first_name', 'last_name')


class CourtResource(resources.ModelResource):
    prepopulated_fields = {'slug': ('name',), }

    class Meta:
        model = Court
        fields = ('id', 'name', 'type', 'description')
        export_order = ('name', 'type', 'description')  # remove is_active


class CourtAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',), }
    list_display = ('name', 'type',  'department', 'region')
    fields = ('name', 'slug', 'type', 'department')
    list_filter = ('type', 'department')

    class Meta:
        model = Court
        fields = '__all__'


class ServiceResource(admin.ModelAdmin):
    def dehydrate(self, service):
        return service.rob.name

    def dehydrate(self, service):
        return service.ror.name

    def dehydrate(self, service):
        return service.cor.name

    class Meta:
        model = Service
        fields = ('type_of_document', 'format', 'rob', 'ror', 'cor', 'cost', 'currency_code')
        export_order = ('type_of_document', 'format', 'rob', 'ror', 'cor', 'cost', 'currency_code')


class ServiceAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    fields = ('type_of_document', 'format', 'rob', 'ror', 'cor', 'cost', 'stamp_fee', 'Revenues', 'honorary_fee',
              'excavation_fee', 'additional_cr_fee', 'currency_code')
    list_display = ('type_of_document', 'format', 'rob', 'ror', 'cor', 'cost', 'stamp_fee', 'Revenues',
                    'honorary_fee', 'excavation_fee', 'additional_cr_fee', 'currency_code')
    list_filter = ('type_of_document', 'format', 'rob', 'ror', 'cor')

    class Meta:
        model = Service
        fields = '__all__'
        # readonly_fields = ('email', 'password',)
        # search_fields = ('first_name', 'last_name')


class PaymentResource(admin.ModelAdmin):
    class Meta:
        model = Payment
        fields = ('request_code', 'label', 'amount', 'pay_token', 'operator_tx_id', 'operator_user_id', 'currency_code',
                  'status')
        export_order = ('request_code', 'label', 'amount', 'pay_token', 'operator_tx_id', 'operator_user_id',
                        'currency_code', 'status')


class PaymentAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    fields = ('request_code', 'label', 'amount', 'pay_token', 'operator_tx_id', 'operator_user_id', 'currency_code',
              'message', 'status')
    list_display = ('request_code', 'label', 'amount', 'pay_token', 'operator_tx_id', 'operator_user_id',
                    'currency_code', 'status')
    list_filter = ('currency_code', 'status', 'created_on')

    class Meta:
        model = Payment
        fields = '__all__'


class RevenuesResource(admin.ModelAdmin):
    class Meta:
        model = Revenues
        fields = ('company', 'payment', 'amount')
        export_order = ('created_on', 'company', 'payment', 'amount')


class RevenuesAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    fields = ('company', 'payment', 'amount')
    list_display = ('company', 'payment', 'amount')
    list_filter = ('company', 'payment',)

    class Meta:
        model = Revenues
        fields = '__all__'


class ExpenseReportResource(admin.ModelAdmin):
    class Meta:
        model = ExpenseReport
        fields = ('request', 'stamp_fee', 'stamp_quantity', 'honorary_fee', 'honorary_quantity', 'Revenues_fee',
                  'Revenues_quantity',)
        export_order = ('request', 'stamp_fee', 'stamp_quantity', 'honorary_fee', 'honorary_quantity',
                        'Revenues_fee', 'Revenues_quantity',)


class ExpenseReportAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    fields = ('request', 'stamp_fee', 'stamp_quantity', 'honorary_fee', 'honorary_quantity', 'Revenues_fee',
              'Revenues_quantity',)
    list_display = ('request', 'stamp_fee', 'stamp_quantity', 'honorary_fee', 'honorary_quantity', 'Revenues_fee',
                    'Revenues_quantity',)
    list_filter = ('request',)

    class Meta:
        model = ExpenseReport
        fields = '__all__'


class CompanyResource(admin.ModelAdmin):
    class Meta:
        model = Company
        fields = ('name', 'percentage',)
        export_order = ('created_on', 'name', 'percentage')


class CompanyAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    fields = ('name', 'percentage',)
    list_display = ('name', 'percentage',)
    list_filter = ('name', 'percentage',)

    class Meta:
        model = Revenues
        fields = '__all__'


class GroupResource(resources.ModelResource):
    class Meta:
        model = Group
        fields = ('id', 'name', 'permissions')
        export_order = ('id', 'name', 'permissions')  # remove is_active


class GroupAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',), }
    list_display = ('id', 'name', 'permissions')
    fields = ('id', 'name', 'permissions')
    list_filter = ('id', 'name', 'permissions')

    class Meta:
        model = Group
        fields = '__all__'


class PermissionResource(resources.ModelResource):
    class Meta:
        model = Permission
        fields = ('id', 'name', 'content_type')
        export_order = ('id', 'name', 'content_type')  # remove is_active


class PermissionAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    list_display = ('name', 'content_type')
    fields = ('id', 'name', 'content_type')
    list_filter = ('id', 'name', 'content_type')

    class Meta:
        model = Permission
        fields = '__all__'


admin.site.register(Country, CountryAdmin)
admin.site.register(Region, RegionAdmin)
admin.site.register(Department, DepartmentAdmin)
admin.site.register(Municipality, MunicipalityAdmin)
admin.site.register(Town, TownAdmin)
admin.site.register(Service, ServiceAdmin)
admin.site.register(Agent, AgentAdmin)
admin.site.register(Permission, PermissionAdmin)
admin.site.register(Request, RequestAdmin)
admin.site.register(Shipment, ShipmentAdmin)
admin.site.register(Court, CourtAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(Company, CompanyAdmin)
admin.site.register(Revenues, RevenuesAdmin)
admin.site.register(ExpenseReport, ExpenseReportAdmin)
