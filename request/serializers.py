from django.conf import settings
from django.contrib.auth.decorators import permission_required

from django.contrib.auth.models import Permission, Group
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _, activate

from rest_framework import serializers

from request.models import Request, Service, Country, Court, Agent, Municipality, Region, Department, Shipment
from request.permissions import HasCourierAgentPermission


class RequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = ['id', 'code', 'user_full_name', 'user_civility', 'user_first_name', 'user_last_name',
                  'user_middle_name', 'user_gender', 'user_phone_number_1', 'user_postal_code', 'user_address',
                  'user_phone_number_2', 'user_whatsapp_number', 'user_email', 'user_dob', 'user_dpb', 'user_cob_code',
                  'user_residency_hood', 'user_residency_town', 'user_residency_country_code', 'user_residency_municipality',
                  'user_nationality_code', 'destination_address', 'destination_location', 'user_occupation',
                  'user_marital_status', 'user_close_friend_number', 'user_birthday_certificate_url',
                  'user_passport_1_url', 'user_passport_2_url', 'user_proof_of_stay_url',
                  'user_id_card_1_url', 'user_id_card_2_url', 'user_wedding_certificate_url', 'court',
                  'copy_count', 'purpose']


class RequestCourierDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = ['id', 'code', 'user_full_name', 'user_civility', 'user_first_name', 'user_last_name',
                  'user_middle_name', 'user_gender', 'user_phone_number_1', 'user_postal_code', 'user_address',
                  'user_email', 'user_dob', 'user_dpb', 'user_cob_code',
                  'user_residency_hood', 'user_residency_town', 'user_residency_country_code', 'user_residency_municipality',
                  'user_nationality_code', 'destination_address', 'destination_location', 'user_occupation',
                  'user_marital_status', 'user_birthday_certificate_url',
                  'user_passport_1_url', 'user_passport_2_url', 'user_proof_of_stay_url',
                  'user_id_card_1_url', 'user_id_card_2_url', 'user_wedding_certificate_url', 'court',
                  'copy_count', 'purpose']

    def to_representation(self, instance):
        output = super(RequestCourierDetailSerializer, self).to_representation(instance)
        output['user_full_name'] = instance.user_full_name
        output['user_id_card_2_url'] = instance.user_id_card_2_url
        output['user_id_card_1_url'] = instance.user_id_card_1_url
        output['user_passport_1_url'] = instance.user_passport_1_url
        output['user_passport_2_url'] = instance.user_passport_2_url
        output['user_proof_of_stay_url'] = instance.user_proof_of_stay_url
        output['user_birthday_certificate_url'] = instance.user_birthday_certificate_url
        if instance.court:
            output['court'] = f"{instance.court.name}"
        else:
            output['court'] = ''
        output['user_dpb'] = f"{instance.user_dpb.name}"
        if instance.user_residency_municipality:
            output['user_residency_municipality'] = f"{instance.user_residency_municipality.name}"
        if instance.user_residency_country_code:
            user_residency_country = get_object_or_404(Country, code=instance.user_residency_country_code,
                                                       lang=instance.user_lang)
            output['user_residency_country'] = f"{user_residency_country.name}"
        if instance.user_cob_code:
            user_cob = get_object_or_404(Country, code=instance.user_cob_code, lang=instance.user_lang)
            output['user_cob'] = f"{user_cob.name}"
        if instance.user_residency_hood:
            output['user_residency_hood'] = f"{instance.user_residency_hood}"
        if instance.user_residency_town:
            output['user_residency_town'] = f"{instance.user_residency_town.name}"
        output['user_wedding_certificate_url'] = instance.user_wedding_certificate_url
        return output


class RequestCollectionDeliveryDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = ['id', 'code', 'user_civility', 'user_full_name', 'user_phone_number_1', 'user_postal_code',
                  'user_address', 'user_phone_number_2',
                  'user_whatsapp_number', 'user_residency_hood', 'user_residency_town', 'user_residency_country_code',
                  'user_residency_municipality', 'destination_address', 'destination_location',
                  'user_close_friend_number']

    def to_representation(self, instance):
        output = super(RequestCollectionDeliveryDetailSerializer, self).to_representation(instance)
        output['civility'] = instance.user_civility
        output['user_full_name'] = instance.user_full_name
        if instance.user_residency_country_code:
            user_residency_country = get_object_or_404(Country, name=instance.user_residency_country_code)
            output['user_residency_country'] = f"{user_residency_country.name}"
        if instance.user_residency_hood:
            output['user_residency_hood'] = f"{instance.user_residency_hood}"
        if instance.user_residency_town:
            output['user_residency_town'] = f"{instance.user_residency_town.name}"
        if instance.user_residency_municipality:
            output['user_residency_municipality'] = f"{instance.user_residency_municipality.name}"

        if instance.court:
            output['court'] = f"{instance.court.name}"
        else:
            output['court'] = ''
        return output


class RequestListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = "__all__"

    def to_representation(self, instance):
        output = super(RequestListSerializer, self).to_representation(instance)
        # output['civility'] = instance.user_civility
        # output['phoneNumber'] = instance.user_phone_number_1
        # output['whatsappContact'] = instance.user_whatsapp_number
        # output['email'] = instance.user_email
        # if instance.user_nationality_code == "CM":
        #     output['location'] = "Je vis au Cameroun"
        #     if instance.user_cob_code == 'CM':
        #         type_user = 'Je suis Camerounais né au Cameroun'
        #     else:
        #         type_user = "Je suis Camerounais né à l'étranger"
        # else:
        #     type_user = "Je suis nationalité étrangère"
        #     output['location'] = "Je vis à l'étranger"
        # output['typeUser'] = type_user
        # output['fullName'] = instance.user_full_name
        # output['criminalRecordNumber'] = instance.copy_count
        # if instance.court:
        #     output['court'] = f"{instance.court.name}"
        # else:
        #     output['court'] = ''
        # if instance.user_dpb:
        #     region_birth = f"{instance.user_dpb.region.name} {instance.user_dpb.name}"
        # else:
        #     region_birth = ''
        # if instance.user_residency_municipality:
        #     residence = f"{instance.user_residency_municipality.name} ({instance.user_residency_municipality.department.name}-{instance.user_residency_municipality.department.region.name})"
        # else:
        #     residence = ''
        #
        # if instance.user_residency_municipality:
        #     output['user_residency_municipality'] = f"{instance.user_residency_municipality.name}"
        # if instance.user_residency_country_code:
        #     output['user_residency_country_code'] = f"{instance.user_residency_country_code.name}"
        # if instance.user_residency_hood:
        #     output['user_residency_hood'] = f"{instance.user_residency_hood}"
        # if instance.user_residency_town:
        #     output['user_residency_town'] = f"{instance.user_residency_town.name}"
        # output['residence'] = residence
        # output['regionOfBirth'] = region_birth
        # output['birthCertificateUrl'] = instance.user_birthday_certificate_url
        # output['passportUrl'] = instance.user_passport_1_url
        # output['passportVisaPageUrl'] = instance.user_passport_2_url
        # output['proofStayCameroonUrl'] = instance.user_proof_of_stay_url
        # output['cniFrontUrl'] = instance.user_id_card_1_url
        # output['cniBackUrl'] = instance.user_id_card_2_url
        # output['weddingCertificateUrl'] = instance.user_wedding_certificate_url
        return output


class RequestPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = "__all__"


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = '__all__'


class CourtSerializer(serializers.ModelSerializer):
    class Meta:
        model = Court
        fields = "__all__"

    def to_representation(self, instance):
        output = super(CourtSerializer, self).to_representation(instance)
        activate(self.context['request'].GET.get('lang', 'en'))
        output['full_name'] = f"{_(instance.type)} {instance.name}"
        output['type'] = f"{_(instance.type)}"

        return output


class ShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        fields = "__all__"


class AgentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=150, write_only=True)
    password = serializers.CharField(max_length=150, write_only=True)
    last_name = serializers.CharField(max_length=150, required=True)
    first_name = serializers.CharField(max_length=150, write_only=True)
    email = serializers.EmailField(max_length=150, required=False)

    class Meta:
        model = Agent
        fields = ['username', 'password', 'first_name', 'last_name', 'email', 'court', 'region_code', 'is_csa']


class AgentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = "__all__"


class AgentDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'phone', 'gender', 'court', 'region_code',
                  'pending_task_count']

    def to_representation(self, instance):
        output = super(AgentDetailSerializer, self).to_representation(instance)
        if instance.court:
            output['court'] = instance.court.name
        if instance.region:
            output['region_code'] = instance.region.name
        return output


class MunicipalitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Municipality
        fields = "__all__"


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = "__all__"


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = "__all__"


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["name", "permission"]


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['name', 'codename']


class PermissionUpdateSerializer(serializers.ModelSerializer):
    # member_id = MemberSerializer(many=False, write_only=True)

    class Meta:
        model = Agent
        fields = ["id", "codename"]


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change endpoint.
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirmed_password = serializers.CharField(required=True)

