from django.conf import settings

from rest_framework import serializers

from request.models import Request, Country, Court, Agent, Municipality, Region, Department, Shipment


class RequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = ['user_first_name', 'user_last_name', 'user_middle_name', 'user_gender', 'user_phone_number_1',
                  'user_phone_number_2', 'user_whatsapp_number', 'user_email', 'user_dob', 'user_mob', 'user_cob',
                  'user_residency_hood', 'user_residency_town', 'user_residency_country', 'user_residency_municipality',
                  'user_nationality', 'user_occupation', 'user_marital_status', 'purpose']


class RequestListSerializer(serializers.ModelSerializer):
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
    class Meta:
        model = Agent
        fields = "__all__"


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
