from django.conf import settings

from django.contrib.auth.models import Permission
from django.contrib.auth.models import Group

from rest_framework import serializers

from request.models import Request, Service, Country, Court, Agent, Municipality, Region, Department, Shipment


class RequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = ['id', 'code', 'user_full_name', 'user_civility', 'user_first_name', 'user_last_name',
                  'user_middle_name', 'user_gender', 'user_phone_number_1', 'user_postal_code', 'user_address',
                  'user_phone_number_2', 'user_whatsapp_number', 'user_email', 'user_dob', 'user_dpb', 'user_cob',
                  'user_residency_hood', 'user_residency_town', 'user_residency_country', 'user_residency_municipality',
                  'user_nationality', 'destination_address', 'destination_location', 'user_occupation',
                  'user_marital_status', 'user_close_friend_number', 'user_birthday_certificate_url',
                  'user_passport_1_url', 'user_passport_2_url', 'user_proof_of_stay_url',
                  'user_id_card_1_url', 'user_id_card_2_url', 'user_wedding_certificate_url', 'court',
                  'copy_count', 'purpose']


class RequestAttachmentDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = ['id', 'code', 'user_occupation', 'user_marital_status', 'user_birthday_certificate_url',
                  'user_passport_1_url', 'user_passport_2_url', 'user_proof_of_stay_url', 'user_id_card_1_url',
                  'user_id_card_2_url', 'user_wedding_certificate_url', 'copy_count']


class RequestShippingDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = ['id', 'code', 'user_phone_number_1', 'user_postal_code', 'user_address', 'user_phone_number_2',
                  'user_whatsapp_number', 'user_residency_hood', 'user_residency_town', 'user_residency_country',
                  'user_residency_municipality', 'destination_address', 'destination_location',
                  'user_close_friend_number']


class RequestListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = "__all__"

    def to_representation(self, instance):
        output = super(RequestListSerializer, self).to_representation(instance)
        output['civility'] = instance.user_civility
        output['phoneNumber'] = instance.user_phone_number_1
        output['whatsappContact'] = instance.user_whatsapp_number
        output['email'] = instance.user_email
        cameroon = Country.objects.get(name__iexact='cameroun')
        if instance.user_nationality == cameroon:
            output['location'] = "Je vis au Cameroun"
            if instance.user_cob == cameroon:
                type_user = 'Je suis Camerounais né au Cameroun'
            else:
                type_user = "Je suis Camerounais né à l'étranger"
        else:
            type_user = "Je suis nationalité étrangère"
            output['location'] = "Je vis à l'étranger"
        output['typeUser'] = type_user
        output['fullName'] = instance.user_full_name
        output['criminalRecordNumber'] = instance.copy_count
        if instance.court:
            output['court'] = f"{instance.court.name}"
        else:
            output['court'] = ''
        if instance.user_dpb:
            region_birth = f"{instance.user_dpb.region.name} {instance.user_dpb.name}"
        else:
            region_birth = ''
        if instance.user_residency_municipality:
            residence = f"{instance.user_residency_municipality.name} ({instance.user_residency_municipality.department.name}-{instance.user_residency_municipality.department.region.name})"
        else:
            residence = ''
        output['residence'] = residence
        output['regionOfBirth'] = region_birth
        output['birthCertificateUrl'] = instance.user_birthday_certificate_url
        output['passportUrl'] = instance.user_passport_1_url
        output['passportVisaPageUrl'] = instance.user_passport_2_url
        output['proofStayCameroonUrl'] = instance.user_proof_of_stay_url
        output['cniFrontUrl'] = instance.user_id_card_1_url
        output['cniBackUrl'] = instance.user_id_card_2_url
        output['weddingCertificateUrl'] = instance.user_wedding_certificate_url
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


class ShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        fields = "__all__"


class AgentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=150, write_only=True)
    password = serializers.CharField(max_length=150, write_only=True)
    last_name = serializers.CharField(max_length=150, required=True)
    first_name = serializers.CharField(max_length=150, read_only=True)
    email = serializers.EmailField(max_length=150, required=False)

    class Meta:
        model = Agent
        fields = ['username', 'password', 'first_name', 'last_name', 'email']


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

