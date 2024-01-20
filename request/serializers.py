from django.conf import settings

from rest_framework import serializers

from request.models import Request


class RequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = ['']

