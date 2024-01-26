# Create your views here.
import json
from datetime import datetime

from django.shortcuts import render
# from django.core.files.uploadedfile import
from django.utils.translation import gettext_lazy as _
from django.core.mail import EmailMessage
from django.http import HttpResponseBadRequest
from django.urls import reverse

from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework import permissions
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView

from request.constants import PENDING
from request.models import Request, Country, Court, Agent, Municipality, Region, Department, Shipment, Service
from request.serializers import RequestSerializer, CountrySerializer, CourtSerializer, AgentSerializer, \
    DepartmentSerializer, MunicipalitySerializer, RegionSerializer, RequestListSerializer, ShipmentSerializer
from request.utils import generate_code, send_notification_email, dispatch_new_task, process_data, BearerAuthentication


class RequestViewSet(viewsets.ModelViewSet):
    """
    This viewset intends to manage all operations against Requests
    """
    queryset = Request.objects.all()
    serializer_class = RequestSerializer
    authentication_classes = [BearerAuthentication]

    # def get_queryset(self):
    #     queryset = self.queryset
    #     region_name = self.request.GET.get('region_name', '')
    #     municipality_name = self.request.GET.get('municipality_name', '')
    #     department_name = self.request.GET.get('department_name', '')
    #     court_type = self.request.GET.get('court_type', '')
    #     name = self.request.GET.get('name', '')
    #     if name:
    #         queryset = queryset.filter(name__iexact=name)
    #         return queryset
    #     if court_type:
    #         queryset = queryset.objects.filter(type=court_type)
    #     if municipality_name:
    #         municipality = Municipality.objects.get(name=municipality_name)
    #         queryset = queryset.filter(department=municipality.department)
    #     if department_name:
    #         queryset = queryset.filter(department__name=municipality_name)
    #     if region_name:
    #         queryset = queryset.filter(department__region__name=region_name)
    #     return queryset

    def create(self, request, *args, **kwargs):
        data = process_data(self.request.data)
        data['code'] = generate_code()
        birth_department = Department.objects.get(id=data['user_dpb'])
        birth_court_list = [court.id for court in birth_department.court_set.all()]
        department_in_red_area = Department.objects.filter(region__code__in=['NW', 'SW'])
        court_in_red_area = []
        for department in department_in_red_area:
            for court in department.court_set.all():
                court_in_red_area.append(court.id)
        if data['court'].id in court_in_red_area:
            return Response({"error": True, 'message': f"{data['court']} is in red area"},
                            status=status.HTTP_400_BAD_REQUEST)
        if data['court'].id not in birth_court_list:
            return Response({"error": True, 'message': f"{data['court']} does not handle {department}"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        request = serializer.instance
        service = Service.objects.get(rob=request.user_dpb.region,
                                      ror=request.user_residency_municipality.region)

        request.service = service
        request.amount = service.cost * request.copy_count
        request.save()
        selected_agent, shipment = dispatch_new_task(request, data['court'])
        send_notification_email(request)
        request.agent = selected_agent
        request.court = data['court']
        request.save()
        headers = self.get_success_headers(serializer.data)
        expense_report = {"stamp": {"fee": 1500, "quantity": 2*request.copy_count},
                          "dispursement": {"fee": 3000, "quantity": request.copy_count}}
        subtotal = expense_report["stamp"]["fee"] * expense_report["stamp"]["quantity"] + expense_report["dispursement"]["fee"] * expense_report["dispursement"]["quantity"]
        expense_report['honorary'] = request.amount - subtotal
        return Response({"request": RequestListSerializer(request).data, "expense_report": expense_report},
                        status=status.HTTP_201_CREATED, headers=headers)


class CountryViewSet(viewsets.ModelViewSet):
    """
    This viewset intends to manage all operations against requests
    """
    queryset = Country.objects.all()
    serializer_class = CountrySerializer

    def get_queryset(self):
        queryset = self.queryset
        name = self.request.GET.get('name', '')
        iso2 = self.request.GET.get('iso2', '')
        iso3 = self.request.GET.get('iso3', '')

        if name:
            queryset = queryset.filter(name__iexact=name)
        if iso2:
            queryset = queryset.filter(iso2__iexact=iso2)
        if iso3:
            queryset = queryset.filter(iso3__iexact=iso3)

        return queryset.order_by('name')


class CourtViewSet(viewsets.ModelViewSet):
    """
    This viewset intends to manage all operations against Court
    """
    queryset = Court.objects.all()
    serializer_class = CourtSerializer

    def get_queryset(self):
        queryset = self.queryset
        region_name = self.request.GET.get('region_name', '')
        municipality_name = self.request.GET.get('municipality_name', '')
        department_name = self.request.GET.get('department_name', '')
        court_type = self.request.GET.get('court_type', '')
        name = self.request.GET.get('name', '')
        if name:
            queryset = queryset.filter(name__iexact=name)
            return queryset
        if court_type:
            queryset = queryset.objects.filter(type=court_type)
        if municipality_name:
            municipality = Municipality.objects.get(name=municipality_name)
            queryset = queryset.filter(department=municipality.department)
        if department_name:
            queryset = queryset.filter(department__name=municipality_name)
        if region_name:
            queryset = queryset.filter(department__region__name=region_name)
        return queryset


class AgentViewSet(viewsets.ModelViewSet):
    """
    This viewset intends to manage all operations against Agents
    """
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)


class MunicipalityViewSet(viewsets.ModelViewSet):
    """
    This viewset intends to manage all operations against Municipalities
    """
    queryset = Municipality.objects.all()
    serializer_class = MunicipalitySerializer

    def get_queryset(self):
        queryset = self.queryset
        region_name = self.request.GET.get('region_name', '')
        department_name = self.request.GET.get('department_name', '')
        name = self.request.GET.get('name', '')
        if name:
            queryset = queryset.filter(name__iexact=name)
            return queryset
        department_list = []
        if department_name:
            department_list = [department for department in Department.objects.filter(name__iexact=department_name)]
        if region_name:
            department_list = [department for department in Department.objects.filter(region__name__iexact=region_name)]
        return queryset.filter(department__in=department_list)


class RegionViewSet(viewsets.ModelViewSet):
    """
    This viewset intends to manage all operations against Regions
    """
    queryset = Region.objects.all()
    serializer_class = RegionSerializer

    def get_queryset(self):
        queryset = self.queryset
        code = self.request.GET.get('code', '')
        if code:
            return queryset.filter(code__iexact=code)
        else:
            return queryset


class DepartmentViewSet(viewsets.ModelViewSet):
    """
    This viewset intends to manage all operations against Departments
    """
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer

    def get_queryset(self):
        queryset = self.queryset
        region_name = self.request.GET.get('region_name', '')
        if region_name:
            return queryset.filter(region__name__iexact=region_name)
        else:
            return queryset


class ShipmentViewSet(viewsets.ModelViewSet):
    """
    This viewset intends to manage all operations against Municipalities
    """
    queryset = Shipment.objects.all()
    serializer_class = ShipmentSerializer

    # def get_queryset(self):
    #     queryset = self.queryset
    #     region_name = self.request.GET.get('region_name', '')
    #     department_name = self.request.GET.get('department_name', '')
    #     name = self.request.GET.get('name', '')
