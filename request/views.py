# Create your views here.
import json
from datetime import datetime

from django.shortcuts import render
# from django.core.files.uploadedfile import
from django.utils.translation import gettext_lazy as _
from django.core.mail import EmailMessage
from django.http import HttpResponseBadRequest
from django.urls import reverse

from slugify import slugify

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
    DepartmentSerializer, MunicipalitySerializer, RegionSerializer, RequestListSerializer, ShipmentSerializer, \
    RequestPatchSerializer
from request.utils import generate_code, send_notification_email, dispatch_new_task, process_data, BearerAuthentication


class RequestViewSet(viewsets.ModelViewSet):
    """
    This viewset intends to manage all operations against Requests
    """
    queryset = Request.objects.all()
    serializer_class = RequestSerializer
    authentication_classes = [BearerAuthentication]

    def get_queryset(self):
        queryset = self.queryset
        code = self.request.GET.get('code', '')
        region_name = self.request.GET.get('region_name', '')
        municipality_name = self.request.GET.get('municipality_name', '')
        department_name = self.request.GET.get('department_name', '')
        court_name = self.request.GET.get('court_name', '')
        agent_email = self.request.GET.get('agent_email', '')
        pk = self.kwargs.get('pk', None)

        if pk:
            return queryset

        if code:
            return queryset.filter(code=code)
        try:
            court_name = court_name.split('%20')[0] if len(court_name) <= 1 else court_name.split('%20')[1]
            court = Court.objects.get(slug='-'.join(slugify(court_name).split('-')[1:]))
            agent = Agent.objects.get(court=court)
            shipment_qs = Shipment.objects.filter(agent=agent)
            request_list = []
            for shipment in shipment_qs:
                request_list.append(shipment.request)
            return request_list
        except:
            pass
        try:
            municipality = Municipality.objects.get(slug__iexact=slugify(municipality_name))
            queryset = queryset.filter(user_dpb=municipality.department)
        except:
            pass
        try:
            queryset = queryset.filter(user_dpb__slug=slugify(department_name))
        except:
            pass
        try:
            queryset = queryset.filter(user_dpb__region__slug=slugify(region_name))
        except:
            pass
        try:
            agent = Agent.objects.get(email=agent_email)
            shipment_qs = Shipment.objects.filter(agent=agent)
            request_list = []
            for shipment in shipment_qs:
                request_list.append(shipment.request)
            return request_list
        except:
            pass
        return queryset

    def create(self, request, *args, **kwargs):
        data = process_data(self.request.data)
        data['code'] = generate_code()
        cameroon = Country.objects.get(name__iexact='cameroun')
        yaounde_centre_administratif = Court.objects.get(slug='yaounde-centre-administratif')
        user_cob = data.get('user_cob', None)

        if user_cob != cameroon.id and data['court'].id != yaounde_centre_administratif.id:
            return Response({"error": True, 'message': "Invalid court for this user born abroad"},
                            status=status.HTTP_400_BAD_REQUEST)

        department_in_red_area = Department.objects.filter(region__code__in=['NW', 'SW'])
        court_in_red_area = []
        for department in department_in_red_area:
            for court in department.court_set.all():
                court_in_red_area.append(court.id)

        # if data['court'].id in court_in_red_area:
        #     return Response({"error": True, 'message': f"{data['court']} is in red area"},
        #                     status=status.HTTP_400_BAD_REQUEST)
         
        try:
            # For users born locally in Cameroon
            birth_department = Department.objects.get(id=data['user_dpb'])
            birth_court_list = [court.id for court in birth_department.court_set.all()]

            if data['court'].id not in birth_court_list:
                if birth_department in department_in_red_area and data['court'].id != yaounde_centre_administratif.id:
                    return Response({"error": True, 'message': f"{birth_department} is in red area department, "
                                                               f"selected court {data['court']} is not eligible "
                                                               f"(not in central file))"},
                                    status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({"error": True, 'message': f"{data['court']} does not handle {department}"},
                                    status=status.HTTP_400_BAD_REQUEST)
        except:
            # For users living abroad
            cor = Country.objects.filter(id=data['user_residency_country'])
            if cor and data['court'].id != yaounde_centre_administratif.id:
                return Response({"error": True, 'message': f"Selected court {data['court']} is not eligible "
                                                           f"(not in central file)) to handle your request"},
                                status=status.HTTP_400_BAD_REQUEST)

        data['court'] = data['court'].id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        request = serializer.instance

        if not request.user_cob:
            if request.user_residency_country.id != cameroon.id:
                # Born abroad and lives abroad
                service = Service.objects.get(rob=request.court.department.region,
                                              cor=request.user_residency_country)

            else:
                # Born abroad and lives in local country (Cameroon)
                service = Service.objects.get(rob=request.court.department.region,
                                              ror=request.user_residency_municipality.region)

        else:
            if request.user_residency_country.id != cameroon.id:
                # Born in Cameroon and lives abroad
                service = Service.objects.get(rob=request.user_dpb.region,
                                              cor=request.user_residency_country)
            else:
                # Born in Cameroon and lives in Cameroon
                service = Service.objects.get(rob=request.user_dpb.region,
                                              ror=request.user_residency_municipality.region)
        request.service = service
        request.amount = service.cost * request.copy_count
        request.save()
        #ToDo:
        # Selecting the right agent for your territory

        if request.user_email:
            # Notify customer who created the request
            subject = _("Support pour l'établissement de votre Extrait de Casier Judiciaire")
            message = _(
                f"{request.user_civility} {request.user_full_name},\n\nNous vous remercions de nous faire confiance pour vous "
                f"accompagner dans l'établissement de votre"
                f" Extrait de Casier Judiciaire. Votre demande de service numéro {request.code} est bien "
                f"reçue par nos équipes et nous vous informerons de l'évolution dans son traitement. Vous vous joignons"
                f" également une copie de votre reçu pour toutes fins utiles. \n\n En cas de souci veuillez nous contacter"
                f" au 675 296 018\n\nMerci et excellente journée. "
                f"\n\nL'équipe EasyPro237.")
            send_notification_email(request, subject, message, request.user_email)

        headers = self.get_success_headers(serializer.data)

        if service.currency_code == 'EUR':
            stamp_fee = 1500 / 655
            dispursement_fee = 3000 / 655
        if service.currency_code == 'XAF':
            stamp_fee = 1500
            dispursement_fee = 3000

        # Compute and return expense's report.
        expense_report = {"stamp": {"fee": round(stamp_fee), "quantity": 2*request.copy_count},
                          "dispursement": {"fee": round(dispursement_fee), "quantity": request.copy_count}}
        subtotal = expense_report["stamp"]["fee"] * expense_report["stamp"]["quantity"] + expense_report["dispursement"]["fee"] * expense_report["dispursement"]["quantity"]
        expense_report['honorary'] = round(request.amount - subtotal)
        expense_report['currency_code'] = service.currency_code

        return Response({"request": RequestListSerializer(request).data, "expense_report": expense_report},
                        status=status.HTTP_201_CREATED, headers=headers)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        selected_agent, shipment = dispatch_new_task(instance)

        if selected_agent:
            # Notify selected agent a request has been assigned to him.
            instance.agent = selected_agent
            url_list = [instance.user_birthday_certificate_url, instance.user_passport_1_url,
                        instance.user_passport_2_url, instance.user_proof_of_stay_url, instance.user_id_card_1_url,
                        instance.user_id_card_2_url, instance.user_wedding_certificate_url]
            urls = "\n\n"
            for url in url_list:
                if not url:
                    urls += url
                urls += "\n\n"
            subject = _("Nouvelle demande d'Extrait de Casier Judiciaire")
            message = _(
                f"Cher {selected_agent.first_name}, \n\n La demande d'Extrait de Casier Judiciaire N°"
                f" {instance.code} vous a été assignée. \nCliquez sur les liens ci-dessous pour obtenir "
                f"l'acte de naissance, la pièce d'idendité du client\nMerci et excellente journée. "
                f"{urls}"                 
                f"\n\nL'équipe EasyPro237.")
            send_notification_email(request, subject, message, selected_agent.email, selected_agent)
        return self.update(request, *args, **kwargs)


class CountryViewSet(viewsets.ModelViewSet):
    """
    This viewSet intends to manage all operations against requests
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
    This viewSet intends to manage all operations against Agents
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
