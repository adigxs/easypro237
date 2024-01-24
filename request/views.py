# Create your views here.
import json
from datetime import datetime

from django.shortcuts import render
# from django.core.files.uploadedfile import


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


class RequestViewSet(viewsets.ModelViewSet):
    """
    This viewset intends to manage all operations against Requests
    """
    queryset = Request.objects.all()
    serializer_class = RequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        request = serializer.instance
        request.code = generate_code()
        service_cost = Service.objects.get(rob=request.user_mob.region,
                                           ror=request.user_residency_municipality.region)
        request.amount = service_cost * request.copy_count
        request.save()
        headers = self.get_success_headers(serializer.data)
        return Response(RequestListSerializer(request).data, status=status.HTTP_201_CREATED, headers=headers)

    # def partial_update(self, request, *args, **kwargs):
    #     instance = self.get_object()
    #     serializer = self.get_serializer(instance, data=request.data, partial=True)
    #     serializer.is_valid(raise_exception=True)
    #     instance = serializer.save()


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


def dispatch_new_task(request: Request) -> tuple:
    """
    This function intends to assign a new request to the first available agent resides in the court where
    of the municipality where the requested user is born.

    The first most available agent is the first person from a list of people who has less pending shipments
    """
    agent_court = Court.objects.get(municipality=request.user_mob)
    most_available_agent_list = sorted([agent.pending_task_count for agent in Agent.objects.filter(court=agent_court)], key=lambda agent: agent.pending_task_count)
    selected_agent = most_available_agent_list.pop(0)

    selected_agent.pending_task_count += 1
    selected_agent.save()
    shipment = Shipment.objects.create(agent=selected_agent, destination_municipality=selected_agent.court.municipality,
                                       request=request, destination_country=request.user_residency_country)

    if request.user_residency_hood:
        shipment.destination_hood = request.user_residency_hood
    if request.user_residency_town:
        shipment.destination_town = request.user_residency_town
    shipment.save()
    request.status = PENDING
    request.save()

    return selected_agent, shipment


def generate_code() -> str:
    prefix = "DCJ"
    now = f'{datetime.now():%Y%m%d}'
    request_count = Request.objects.all().count()
    leading_zero_count = 5 - len(str(request_count))
    leading_zero = leading_zero_count * "0"

    return prefix + now + leading_zero + str(request_count)


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
