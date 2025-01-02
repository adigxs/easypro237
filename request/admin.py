from datetime import timedelta

from django.contrib.admin.sites import AlreadyRegistered
from django.contrib.auth.models import Permission, Group
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib import admin

from import_export.admin import ImportExportModelAdmin
from import_export import resources, fields
from import_export.admin import ImportExportMixin

from request.models import Agent, Region, Department, Municipality, Request, Court, Service, Country, Town, Shipment, \
    Payment, Income, Company, ExpenseReport


# Register your models here.

class CountryResource(resources.ModelResource):
    class Meta:
        model = Country
        fields = ('id', 'name', 'iso2', 'iso3', 'is_active')
        export_order = ('name', 'iso2', 'iso3', 'is_active')  # remove is_active


class CountryAdmin(ImportExportMixin, admin.ModelAdmin):
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


class AgentAdmin(ImportExportMixin, admin.ModelAdmin):
    list_display = ('full_name', 'email', 'pending_task_count', 'court', 'region', 'is_csa')
    class Meta:
        model = Agent
        fields = '__all__'
        # readonly_fields = ('email', 'password',)


class RegionResource(resources.ModelResource):
    class Meta:
        model = Region
        fields = ('name', 'slug', 'code',)
        export_order = ('name', 'slug', 'code',)  # remove is_active


class RegionAdmin(ImportExportMixin, admin.ModelAdmin):
    # prepopulated_fields = {'slug': ('name',), }
    list_display = ('name', 'slug', 'code')
    resource_class = RegionResource

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


class MunicipalityAdmin(ImportExportMixin, admin.ModelAdmin):
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


class DepartmentAdmin(ImportExportMixin, admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',), }
    list_display = ('name', 'region',)
    fields = ('name', 'region', 'slug',)
    resource_class = DepartmentResource

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


class TownAdmin(ImportExportMixin, admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',), }
    list_display = ('name', 'municipality',)
    fields = ('name', 'municipality', 'slug')

    class Meta:
        model = Town
        fields = '__all__'


class RequestResource(resources.ModelResource):
    created_on = fields.Field(column_name='Created On')
    copy_count = fields.Field(column_name='Copy count')
    user_full_name = fields.Field(column_name='Full name')
    user_occupation = fields.Field(column_name='Occupation')
    user_residency_country = fields.Field(column_name='Country of residency')
    user_residency_municipality = fields.Field(column_name='Municipality of residency')
    user_nationality = fields.Field(column_name='Nationality')
    user_cob = fields.Field(column_name='Country of birth')
    user_address = fields.Field(column_name='Address')
    user_email = fields.Field(column_name='Email')
    destination_address = fields.Field(column_name='Delivery Address')
    destination_location = fields.Field(column_name='Delivery Location')
    court = fields.Field(column_name='Court')
    user_dpb = fields.Field(column_name='Department of birth')
    user_postal_code = fields.Field(column_name='Postal code')
    has_stayed_in_cameroon = fields.Field(column_name='Stayed in Cameroon')
    agent = fields.Field(column_name='Agent')

    class Meta:
        model = Request
        fields = ('created_on', 'code', 'status', 'copy_count', 'user_civility', 'user_gender', 'user_full_name',
                        'user_email', 'user_occupation', 'user_marital_status', 'user_phone_number_1', 'user_cob',
                        'user_residency_country', 'user_nationality', 'user_dpb', 'user_residency_municipality',
                        'court', 'user_address', 'user_postal_code', 'destination_address', 'destination_location',
                        'agent', 'amount', 'user_birthday_certificate_url', 'user_passport_1_url', 'user_passport_2_url',
                        'user_proof_of_stay_url', 'user_id_card_1_url', 'user_id_card_2_url',
                        'user_wedding_certificate_url', 'has_stayed_in_cameroon',)
        export_order = ('created_on', 'code', 'status', 'copy_count', 'user_civility', 'user_gender', 'user_full_name',
                        'user_email', 'user_occupation', 'user_marital_status', 'user_phone_number_1', 'user_cob',
                        'user_residency_country', 'user_nationality', 'user_dpb', 'user_residency_municipality',
                        'court', 'user_address', 'user_postal_code', 'destination_address', 'destination_location',
                        'agent', 'amount', 'user_birthday_certificate_url', 'user_passport_1_url', 'user_passport_2_url',
                        'user_proof_of_stay_url', 'user_id_card_1_url', 'user_id_card_2_url',
                        'user_wedding_certificate_url', 'has_stayed_in_cameroon',)


    def dehydrate_created_on(self, request):
        return request.created_on.strftime('%y-%m-%d %H:%M')

    def dehydrate_user_full_name(self, request):
        return request.user_full_name

    def dehydrate_copy_count(self, request):
        return request.copy_count

    def dehydrate_user_occupation(self, request):
        if request.user_occupation:
            return request.user_occupation
        else:
            return ""

    def dehydrate_user_full_name(self, request):
        return request.user_full_name

    def dehydrate_user_residency_country(self, request):
        return request.user_residency_country.name

    def dehydrate_user_residency_municipality(self, request):
        if request.user_residency_municipality:
            return request.user_residency_municipality.name
        else:
            return ""

    def dehydrate_user_cob(self, request):
        if request.user_cob:
            return request.user_cob.name
        else:
            return ""

    def dehydrate_destination_address(self, request):
        if request.destination_address:
            return request.destination_address
        else:
            return ""

    def dehydrate_destination_location(self, request):
        if request.destination_location:
            return request.destination_location
        else:
            return ""

    def dehydrate_user_address(self, request):
        if request.user_address:
            return request.user_address
        else:
            return ""

    def dehydrate_user_email(self, request):
        if request.user_email:
            return request.user_email
        else:
            return ""

    def dehydrate_user_postal_code(self, request):
        if request.user_postal_code:
            return request.user_postal_code
        else:
            return ""

    def dehydrate_court(self, request):
        if request.court:
            return request.court.name
        else:
            return ""

    def dehydrate_user_dpb(self, request):
        if request.user_dpb:
            return request.user_dpb.name
        else:
            return ""

    def dehydrate_user_nationality(self, request):
        if request.user_nationality:
            return request.user_nationality.name
        else:
            return ""

    def dehydrate_has_stayed_in_cameroon(self, request):
        if request.has_stayed_in_cameroon:
            return "True"
        else:
            return "False"

    def dehydrate_agent(self, request):
        if request.agent:
            if request.agent.region:
                return f"Regional de la region du/de l'{request.agent.name}"
            elif not request.agent.is_csa:
                return f"Agent d'établissement du tribunal de {request.agent.court.name}"
            else:
                return f"Agent de collecte et de distribution du la commune de {request.agent.court.municipality.name}"
        else:
            return ""


class RequestAdmin(ImportExportMixin, admin.ModelAdmin):
    list_display = ('code', 'user_full_name', 'user_phone_number_1', 'user_gender', 'user_dpb',
                    'user_residency_country', 'court', 'agent', 'amount')
    list_filter = ('status',)
    resource_class = RequestResource

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
    department = fields.Field(column_name='Department')
    region = fields.Field(column_name='Region')

    prepopulated_fields = {'slug': ('name',), }

    class Meta:
        model = Court
        fields = ('id', 'name', 'type', 'description')
        export_order = ('name', 'type', 'description')  # remove is_active

    def dehydrate_department(self, court):
        return court.department.name

    def dehydrate_region(self, court):
        return court.region.name


class CourtAdmin(ImportExportMixin, admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',), }
    list_display = ('name', 'type',  'department', 'region')
    fields = ('name', 'slug', 'type', 'department')
    list_filter = ('type', 'department')
    resource_class = CourtResource

    class Meta:
        model = Court
        fields = '__all__'


class ServiceResource(resources.ModelResource):

    rob = fields.Field(column_name='Region of Birth')
    ror = fields.Field(column_name='Region of residency')
    cor = fields.Field(column_name='Country of residency')
    stamp_fee = fields.Field(column_name='Stamp fee')
    disbursement = fields.Field(column_name='Disbursement')
    honorary_fee = fields.Field(column_name='Honorary fee')
    excavation_fee = fields.Field(column_name='Excavation fee')
    additional_cr_fee = fields.Field(column_name='Additional Criminal Record fee')


    def dehydrate_rob(self, service):
        if service.rob:
            return service.rob.name
        else:
            return ""

    def dehydrate_ror(self, service):
        if service.ror:
            return service.ror.name
        else:
            return ""

    def dehydrate_cor(self, service):
        if service.cor:
            return service.cor.name
        else:
            return ""

    class Meta:
        model = Service
        fields = ('type_of_document', 'format', 'rob', 'ror', 'cor', 'cost', 'stamp_fee', 'disbursement', 'honorary_fee',
              'excavation_fee', 'additional_cr_fee', 'currency_code')
        export_order = ('type_of_document', 'format', 'rob', 'ror', 'cor', 'cost', 'stamp_fee', 'disbursement', 'honorary_fee',
              'excavation_fee', 'additional_cr_fee', 'currency_code')


class ServiceAdmin(ImportExportMixin, admin.ModelAdmin):
    fields = ('type_of_document', 'format', 'rob', 'ror', 'cor', 'cost', 'stamp_fee', 'disbursement', 'honorary_fee',
              'excavation_fee', 'additional_cr_fee', 'currency_code')
    list_display = ('type_of_document', 'format', 'rob', 'ror', 'cor', 'cost', 'stamp_fee', 'disbursement',
                    'honorary_fee', 'excavation_fee', 'additional_cr_fee', 'currency_code')
    list_filter = ('type_of_document', 'format', 'rob', 'ror', 'cor', 'currency_code')

    resource_class = ServiceResource

    class Meta:
        model = Service
        fields = '__all__'
        # readonly_fields = ('email', 'password',)
        # search_fields = ('first_name', 'last_name')


class PaymentResource(resources.ModelResource):
    class Meta:
        model = Payment
        fields = ('request_code', 'label', 'amount', 'pay_token', 'operator_tx_id', 'operator_user_id', 'currency_code',
                  'status')
        export_order = ('request_code', 'label', 'amount', 'pay_token', 'operator_tx_id', 'operator_user_id',
                        'currency_code', 'status')


class PaymentAdmin(ImportExportMixin, admin.ModelAdmin):
    fields = ('request_code', 'label', 'amount', 'pay_token', 'operator_tx_id', 'operator_user_id', 'currency_code',
              'message', 'status')
    list_display = ('request_code', 'label', 'amount', 'pay_token', 'operator_tx_id', 'operator_user_id',
                    'currency_code', 'status')
    list_filter = ('currency_code', 'status', 'created_on')

    class Meta:
        model = Payment
        fields = '__all__'


class IncomeResource(resources.ModelResource):
    class Meta:
        model = Income
        fields = ('company', 'payment', 'amount')
        export_order = ('created_on', 'company', 'payment', 'amount')


class IncomeAdmin(ImportExportMixin, admin.ModelAdmin):
    fields = ('company', 'payment', 'amount')
    list_display = ('company', 'payment', 'amount')
    list_filter = ('company', 'payment',)

    class Meta:
        model = Income
        fields = '__all__'


class ExpenseReportResource(resources.ModelResource):
    class Meta:
        model = ExpenseReport
        fields = ('request', 'stamp_fee', 'stamp_quantity', 'honorary_fee', 'honorary_quantity', 'disbursement_fee',
                  'disbursement_quantity',)
        export_order = ('request', 'stamp_fee', 'stamp_quantity', 'honorary_fee', 'honorary_quantity',
                        'disbursement_fee', 'disbursement_quantity',)


class ExpenseReportAdmin(ImportExportMixin, admin.ModelAdmin):
    fields = ('request', 'stamp_fee', 'stamp_quantity', 'honorary_fee', 'honorary_quantity', 'disbursement_fee',
              'disbursement_quantity',)
    list_display = ('request', 'stamp_fee', 'stamp_quantity', 'honorary_fee', 'honorary_quantity', 'disbursement_fee',
                    'disbursement_quantity',)
    list_filter = ('request',)

    class Meta:
        model = ExpenseReport
        fields = '__all__'


class CompanyResource(resources.ModelResource):
    class Meta:
        model = Company
        fields = ('name', 'percentage',)
        export_order = ('created_on', 'name', 'percentage')


class CompanyAdmin(ImportExportMixin, admin.ModelAdmin):
    fields = ('name', 'percentage',)
    list_display = ('name', 'percentage',)
    list_filter = ('name', 'percentage',)

    class Meta:
        model = Company
        fields = '__all__'


class GroupResource(resources.ModelResource):
    class Meta:
        model = Group
        fields = ('id', 'name', 'permissions')
        export_order = ('id', 'name', 'permissions')  # remove is_active


class GroupAdmin(ImportExportMixin, admin.ModelAdmin):
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


class PermissionAdmin(ImportExportMixin, admin.ModelAdmin):
    list_display = ('name', 'content_type')
    fields = ('name', 'content_type')
    list_filter = ('name', 'content_type')

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
admin.site.register(Income, IncomeAdmin)
admin.site.register(ExpenseReport, ExpenseReportAdmin)
