# Create your views here.
import json
import os
import uuid
from datetime import datetime, timedelta
from threading import Thread

from num2words import num2words
from decimal import Decimal
from slugify import slugify
from xhtml2pdf import pisa

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, F, Sum
from django.dispatch import receiver
from django.views.generic import TemplateView
from django.conf import settings
from django.contrib.staticfiles import finders
from django.contrib.auth.models import Permission
from django.contrib.auth.models import Group
from django.shortcuts import render, get_object_or_404
from django.contrib.humanize.templatetags.humanize import intcomma
from django.template.loader import get_template
from django.utils import translation
from django.utils.translation import gettext_lazy as _, activate
from django.core.mail import EmailMessage
from django.http import HttpResponseBadRequest, HttpResponse, Http404, QueryDict
from django.urls import reverse
from django_rest_passwordreset.signals import reset_password_token_created

from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.decorators import api_view, permission_classes, authentication_classes, action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.request import Request
from rest_framework import permissions
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import UpdateAPIView
# from rest_framework.decorators import detail_route

from request.constants import PENDING, STARTED, COMPLETED, SHIPPED, RECEIVED, DELIVERED, REQUEST_STATUS, \
    DELIVERY_STATUSES, SIR
from request.models import Request, Country, Court, Agent, Municipality, Region, Department, Shipment, Service
from request.permissions import HasGroupPermission, IsAnonymous, HasCourierAgentPermission, HasRegionalAgentPermission, \
    IsSudo, HasCourierDeliveryPermission
from request.serializers import RequestSerializer, CountrySerializer, CourtSerializer, AgentSerializer, \
    DepartmentSerializer, MunicipalitySerializer, RegionSerializer, RequestListSerializer, ShipmentSerializer, \
    ChangePasswordSerializer, GroupSerializer, \
    AgentListSerializer, AgentDetailSerializer, \
    RequestCollectionDeliveryDetailSerializer, RequestCourierDetailSerializer
from request.utils import generate_code, send_notification_email, dispatch_new_task, BearerAuthentication, \
    compute_receipt_expense_report, parse_number


class RequestViewSet(viewsets.ModelViewSet):
    """
    This viewSet intends to manage all operations against Requests
    """
    queryset = Request.objects.all().order_by('-created_on')
    serializer_class = RequestListSerializer
    authentication_classes = [BearerAuthentication]
    required_groups = {
        'GET': ['courierAgents', 'regionalAgents'],
        'PATCH': ['regionalAgents']
    }

    def get_serializer_class(self):
        if self.action == 'list':
            if self.request.user.is_authenticated and Agent.objects.filter(id=self.request.user.id, court_id__isnull=False, is_csa=False, is_superuser=False).count():
                return RequestCourierDetailSerializer
            if self.request.user.is_authenticated and Agent.objects.filter(id=self.request.user.id, court_id__isnull=False, is_csa=True).count():
                return RequestCollectionDeliveryDetailSerializer
            return RequestListSerializer
        else:
            return RequestSerializer

    def get_permissions(self):
        self.permission_classes = []
        if self.action == 'list':
            self.permission_classes = [HasCourierAgentPermission | HasRegionalAgentPermission
                                       | HasCourierDeliveryPermission | IsAdminUser]
        if self.action == 'partial_update':
            self. permission_classes = [HasRegionalAgentPermission | IsAdminUser | IsAnonymous]
        return super().get_permissions()

    # @action(detail=False, methods=['GET'])
    def get_queryset(self):
        queryset = self.queryset
        code = self.request.GET.get('code', '')
        region_code = self.request.GET.get('region_code', '')
        request_status = self.request.GET.get('status', '')
        municipality_name = self.request.GET.get('municipality_name', '')
        department_name = self.request.GET.get('department_name', '')
        court_name = self.request.GET.get('court_name', '')
        agent_email = self.request.GET.get('agent_email', '')
        created_on = self.request.GET.get('created_on', '')
        start_date = self.request.GET.get('start_date', '')
        end_date = self.request.GET.get('end_date', '')
        pk = self.kwargs.get('pk', None)

        if not self.request.user.is_superuser:
            if self.action == 'list' or self.action == 'retrieve':
                queryset = queryset.exclude(status=STARTED)

            # If it's a regional agent
            if Agent.objects.filter(id=self.request.user.id, region_code__isnull=False).count():
                agent = Agent.objects.filter(id=self.request.user.id, region_code__isnull=False).get()
                if agent.region_code == Region.objects.get(name__icontains='central').code:
                    queryset = queryset.filter(court__slug__contains='minjustice')
                else:
                    queryset = queryset.filter(court__department__region_code__exact=agent.region_code).exclude(court__slug__contains='minjustice')

            # If it's a criminal record clearance officer
            if Agent.objects.filter(id=self.request.user.id, court_id__isnull=False, is_csa=False, is_superuser=False).count():
                agent = Agent.objects.filter(id=self.request.user.id, court_id__isnull=False, is_csa=False, is_superuser=False).get()
                qs = agent.request_set.all()
                #TODO
                # This section added for display purpose but it should be removed.
                if not qs:
                    qs = queryset.filter(status__in=['COMMITTED', 'INCORRECT', 'REJECTED'], court=agent.court)
                queryset = qs

            # If it's a courier and delivery agent
            if Agent.objects.filter(id=self.request.user.id, court_id__isnull=False, is_csa=True).count():
                agent = Agent.objects.filter(id=self.request.user.id, court_id__isnull=False, is_csa=True).get()
                shipment_list = [shipment.request.id for shipment in agent.shipment_set.filter(status__in=['SHIPPED', 'RECEIVED', 'DELIVERED'])]
                qs = queryset.filter(id__in=shipment_list)
                #TODO
                # This section added for display purpose but it should be removed.
                if not qs:
                    qs = queryset.filter(court=agent.court).exclude(status__in=['COMMITTED', 'INCORRECT', 'REJECTED'])
                queryset = qs

        if pk:
            return queryset
        if code:
            # return Response(RequestListSerializer(queryset.filter(code=code), many=True).data)
            return queryset.filter(code=code)
        if agent_email:
            id_list = []
            try:
                agent = Agent.objects.get(email=agent_email)
                shipment_qs = Shipment.objects.filter(agent=agent)
                for shipment in shipment_qs:
                    id_list.append(shipment.request.id)
            except:
                pass
            # return Response(RequestListSerializer(queryset.filter(id__in=id_list), many=True).data)
            return queryset.filter(id__in=id_list)

        if court_name:
            id_list = []
            try:
                if 'central' in court_name:
                    court = Court.objects.get(slug='minjustice-yaounde')
                else:
                    court = Court.objects.get(slug='-'.join(slugify(court_name).split('-')[1:]))
                agent = Agent.objects.get(court__id=court.id)
                shipment_qs = Shipment.objects.filter(agent__id=agent.id)
                for shipment in shipment_qs:
                    id_list.append(shipment.request.id)
            except:
                pass
            # return Response(RequestListSerializer(queryset.filter(id__in=id_list), many=True).data)
            return queryset.filter(id__in=id_list)

        if municipality_name:
            department_list = []
            try:
                municipality = Municipality.objects.get(slug=slugify(municipality_name))
                department_list = [municipality.department.id]
            except:
                pass
            queryset = queryset.filter(user_dpb__id__in=department_list)
        if department_name:
            queryset = queryset.filter(user_dpb__slug=slugify(department_name))
        if region_code:
            queryset = queryset.filter(user_dpb__region_code=region_code)
        if request_status:
            if request_status == 'SHIPPED':
                id_list = [shipment.request.id for shipment in Shipment.objects.filter(status__iexact=SHIPPED)]
                queryset = queryset.filter(id__in=id_list)
            if request_status == 'RECEIVED':
                id_list = [shipment.request.id for shipment in Shipment.objects.filter(status__iexact=RECEIVED)]
                queryset = queryset.filter(id__in=id_list)
            if request_status == 'DELIVERED':
                id_list = [shipment.request.id for shipment in Shipment.objects.filter(status__iexact=DELIVERED)]
                queryset = queryset.filter(id__in=id_list)
            else:
                queryset = queryset.filter(status__iexact=request_status)
        if created_on:
            created_on = datetime.strptime(created_on, '%Y-%m-%d')
            queryset = queryset.filter(created_on=created_on)
        if start_date and end_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            if start_date > end_date or end_date > datetime.now():
                queryset = queryset.filter(id__in=[])
            queryset = queryset.filter(created_on__range=[start_date, end_date])
        return queryset

    def create(self, request, *args, **kwargs):
        if isinstance(self.request.data, QueryDict):  # optional
            self.request.data._mutable = True
        self.request.data.update({'code': generate_code()})
        min_justice_yaounde = Court.objects.get(slug='minjustice-yaounde')
        user_cob_code = self.request.data.get('user_cob_code', None)
        selected_court = get_object_or_404(Court, pk=self.request.data['court'])
        if user_cob_code != "CM" and self.request.data['court'] != min_justice_yaounde.id:
            print("Invalid court for this user born abroad")
            return Response({"error": True, 'message': _("Invalid court for this user born abroad")},
                            status=status.HTTP_400_BAD_REQUEST)

        department_in_red_area = Department.objects.filter(region_code__in=['NW', 'SW'])
        court_in_red_area = []
        # Collect all courts of departments in RED areas due to strike
        for department in department_in_red_area:
            for court in department.court_set.all():
                court_in_red_area.append(court.id)
        try:
            # For users born locally in Cameroon
            birth_department = Department.objects.get(id=self.request.data['user_dpb'])
            birth_court_list = [str(court.id) for court in birth_department.court_set.all()]
            if self.request.data['court'] not in birth_court_list:
                if birth_department.id in department_in_red_area and selected_court.id != min_justice_yaounde.id:
                    print(f"{birth_department} is in red area department, selected court {selected_court} is not eligible "
                          f"(not in Criminal Record Central Index Card))")
                    return Response({"error": True, 'message': _(f"{birth_department} is in red area department, "
                                                               f"selected court {selected_court} is not eligible "
                                                               f"(not in Criminal Record Central Index Card))")},
                                    status=status.HTTP_400_BAD_REQUEST)
                elif birth_department.id not in [dp.id for dp in department_in_red_area]:
                    print(f"Criminal Record Central Index Card - Minjustice - Yaounde does not handle {birth_department}")
                    return Response({"error": True, 'message': _(f"Criminal Record Central Index Card - Minjustice - "
                                                               f"Yaounde does not handle {birth_department}")},
                                    status=status.HTTP_400_BAD_REQUEST)
        except:
            # For users living abroad
            cor = get_object_or_404(Country, iso2=self.request.data['user_residency_country_code'], lang=self.request.data['user_lang'])
            if cor:
                if cor.iso2 != "CM" and selected_court.id != min_justice_yaounde.id:
                    print(f"Selected court {selected_court} is not eligible (It's not the Criminal Record Central "
                          f"Index Card - Minjustice) to handle your request")
                    return Response({"error": True, 'message': _(f"Selected court {selected_court} is not eligible "
                                                               f"(It's not the Criminal Record Central Index Card - "
                                                                 f"Minjustice) to handle your request")},
                                    status=status.HTTP_400_BAD_REQUEST)
        self.request.data["user_gender"] = "M" if self.request.data['user_civility'] == SIR else "F"
        if self.request.data.get('user_full_name'):
            try:
                self.request.data["user_last_name"] = self.request.data['user_full_name'].split()[0]
            except:
                print("Full name should be at least 2 words")
                return Response({"error": True, "message": "Full name should be at least 2 words"},
                                status=status.HTTP_400_BAD_REQUEST)
            try:
                self.request.data["user_first_name"] = self.request.data['user_full_name'].split()[1]
                self.request.data["user_last_name"] = self.request.data['user_full_name'].split()[0]
            except:
                self.request.data["user_first_name"] = self.request.data['user_full_name'].split()[0]
                self.request.data["user_last_name"] = ''
        else:
            self.request.data["user_full_name"] = f"{self.request.data['user_first_name']} {self.request.data['user_last_name']}"

        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        request = serializer.instance

        if not request.user_cob_code:
            if request.user_residency_country_code != "CM":
                # Born abroad and lives abroad
                service = Service.objects.get(rob_code=request.court.department.region_code,
                                              cor_code=request.user_residency_country_code)

            else:
                # Born abroad and lives in local country (Cameroon)
                service = Service.objects.get(rob_code=request.court.department.region_code,
                                              ror_code=request.user_residency_municipality.region)
        else:
            if request.user_residency_country_code != "CM":
                # Born in Cameroon and lives abroad
                service = Service.objects.get(rob_code=request.user_dpb.region_code,
                                              cor_code=request.user_residency_country_code)
            else:
                # Born in Cameroon and lives in Cameroon
                service = Service.objects.get(rob_code=request.user_dpb.region_code,
                                              ror_code=request.user_residency_municipality.department.region_code)
        request.service = service
        expense_report = compute_receipt_expense_report(request, service)
        try:
            request.amount = parse_number(expense_report['total'].replace(',', ''))
        except:
            request.amount = parse_number(expense_report['total'])
        request.save()
        headers = self.get_success_headers(serializer.data)
        return Response({"request": RequestListSerializer(request).data, "expense_report": expense_report},
                        status=status.HTTP_201_CREATED, headers=headers)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        request_status = request.data.get('status', None)
        activate(instance.user_lang)

        if request_status in ["STARTED", "PENDING"]:
            return Response({"error": _("You are not authorize to update the status of this request")}, status=status.HTTP_401_UNAUTHORIZED)

        if request_status == COMPLETED and instance.status not in ['COMMITTED', 'INCORRECT', 'REJECTED']:
            return Response({"error": _(f"The request {instance.code} must be committed or incorrect or rejected")},
                            status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if request_status not in ['COMMITTED', 'INCORRECT', 'REJECTED', 'COMPLETED']:
                if isinstance(request.data, QueryDict):  # optional
                    request.data._mutable = True
                request.data.update({'status': instance.status})

            delivery_agent = Agent.objects.get(court=instance.court, is_csa=True)

            if request_status == 'COMPLETED':
                shipment = Shipment.objects.create(agent=delivery_agent,
                                                   destination_municipality=instance.user_residency_municipality,
                                                   request=instance,
                                                   user_residency_country_code=instance.user_residency_country_code)
                delivery_agent.pending_task_count += 1

                subject = _(f"New pending delivery")
                message = _(f"Mr/Mrs. {delivery_agent.username}, <p>The request for criminal record N°"
                            f" <strong>{instance.code}</strong> has been successfully completed."
                            f"</p><p>Please log in to retrieve the customer's phone contacts</p>"
                            f"<p>Thank you and have a great day</p>"
                            f"<br>The EasyPro237 team.")
                send_notification_email(instance, subject, message, delivery_agent.email)
                if instance.user_residency_hood:
                    shipment.destination_hood = instance.user_residency_hood
                if instance.user_residency_town:
                    shipment.destination_town = instance.user_residency_town
                shipment.save()
            elif request_status == 'SHIPPED':
                if Shipment.objects.filter(request=instance, status=STARTED).count() == 0:
                    return Response({"error": _(f"The request {instance.code} is not yet completed")}, status=status.HTTP_400_BAD_REQUEST)
                Shipment.objects.filter(request=instance).update(status=SHIPPED)
            elif request_status == 'RECEIVED':
                if Shipment.objects.filter(request=instance, status=SHIPPED).count() == 0:
                    return Response({"error": _(f"The package of request {instance.code} has not yet been shipped")}, status=status.HTTP_400_BAD_REQUEST)
                Shipment.objects.filter(request=instance).update(status=RECEIVED)
            elif request_status == 'DELIVERED':
                if Shipment.objects.filter(request=instance, status=RECEIVED).count() == 0:
                    return Response({"error": _(f"The package of request {instance.code} has not yet received")}, status=status.HTTP_400_BAD_REQUEST)
                Shipment.objects.filter(request=instance).update(status=DELIVERED)
                delivery_agent.pending_task_count -= 1
                Agent.objects.filter(region=instance.user_residency_municipality.region).update(pending_task_count=F("pending_task_count") - 1)
                Agent.objects.filter(court=instance.court, is_csa=True).update(pending_task_count=F("pending_task_count") - 1)

            delivery_agent.save()

            try:
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                if request_status in ['COMMITTED', 'INCORRECT', 'REJECTED', 'COMPLETED']:
                    instance.status = request_status
                    instance.save()
            except:
                # raise ValidationError({"authorize": _("You don't have permission to change status of this request")})
                return Response({"error": True, "message": _("You don't have permission to change status of "
                                                           "this request")}, status=status.HTTP_401_UNAUTHORIZED)
            if request_status:
                # Notify customer that the status of his request changed
                subject = _(f"The status of the request {instance.code} has changed")
                message = _(
                    f"{instance.user_civility} <strong>{instance.user_full_name}</strong>,"
                    f"<p>The status of your service request number <strong>{instance.code}</strong>"
                    f" has changed to <strong>{request_status}</strong></p> "
                    f"<p>In case of concern please contact us at <strong>650 229 950</strong></p><p>Thank you and have a great day."
                    f"</p><br>The EasyPro237 team.")
                send_notification_email(instance, subject, message, instance.user_email)

            if request.data.get('destination_address', None):
                Shipment.objects.filter(request=instance).update(
                    destination_address=request.data.get('destination_address'))
            elif instance.destination_address:
                Shipment.objects.filter(request=instance).update(destination_address=instance.destination_address)

            if request.data.get('destination_location', None):
                Shipment.objects.filter(request=instance).update(
                    destination_location=request.data.get('destination_location'))
            elif instance.destination_location:
                Shipment.objects.filter(request=instance).update(destination_location=instance.destination_location)

        return Response(RequestListSerializer(instance).data, status=status.HTTP_200_OK)


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
        lang = self.request.GET.get('lang', 'en')

        queryset = queryset.filter(lang=lang)
        if name:
            queryset = queryset.filter(name__iexact=name)
        if iso2:
            queryset = queryset.filter(iso2__iexact=iso2)
        if iso3:
            queryset = queryset.filter(iso3__iexact=iso3)

        return queryset.order_by('name')


class CourtViewSet(viewsets.ModelViewSet):
    """
    This ViewSet intends to manage all operations against Court
    """
    queryset = Court.objects.all()
    serializer_class = CourtSerializer

    def get_queryset(self):
        queryset = self.queryset
        region_code = self.request.GET.get('region_code', '')
        municipality_name = self.request.GET.get('municipality_name', '')
        department_name = self.request.GET.get('department_name', '')
        department_id = self.request.GET.get('department_id', '')
        court_type = self.request.GET.get('court_type', '')
        name = self.request.GET.get('name', '')
        lang = self.request.GET.get('lang', 'en')
        if name:
            queryset = queryset.filter(name__iexact=name).values().update(name="")
            return queryset
        if court_type:
            queryset = queryset.objects.filter(type=court_type)
        if municipality_name:
            municipality = Municipality.objects.get(name=municipality_name)
            queryset = queryset.filter(department=municipality.department)
        try:
            queryset = queryset.filter(department__id=department_id)
        except:
            if department_name:
                queryset = queryset.filter(department__name__iexact=department_name)
            else:
                pass
        if region_code:
            queryset = queryset.filter(department__region_code=region_code)


        return queryset


class AgentViewSet(viewsets.ModelViewSet):
    """
    This viewSet intends to manage all operations against Agents
    """
    queryset = Agent.objects.all().order_by('-region_code', '-court')
    authentication_classes = [BearerAuthentication]

    def get_queryset(self):
        region_code = self.request.GET.get('region_code', '')
        queryset = Agent.objects.all()
        if region_code:
            queryset = self.queryset.filter(region_code=region_code)
        return queryset.order_by('-region_code', '-court')

    def get_serializer_class(self):
        if self.action == 'create':
            return AgentSerializer
        else:
            return AgentDetailSerializer

    def get_permissions(self):
        if self.action == 'create':
            self.permission_classes = [permissions.IsAdminUser]
        elif self.action in ['list', 'partial_update']:
            try:
                if self.request.user == self.get_object():
                    self.permission_classes = [permissions.IsAuthenticated]
                else:
                    self.permission_classes = [permissions.IsAdminUser]
            except:
                self.permission_classes = [permissions.IsAdminUser]
        else:
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()

    @permission_classes([IsAdminUser])
    @action(detail=False, methods=["POST"])
    def move_to_group(self, request):
        group_name = request.data.get['group_name']
        group = Group.objects.get(name=group_name)
        agent = self.get_object()
        agent.groups.add(group)
        return Response({"success": True, 'message': _(f'{agent.get_full_name()} has been successfully added '
                                                     f'to group {group.name}')}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            instance = serializer.instance
            court_id = request.data.get('court_id', None)
            region_code = request.data.get('region_code', None)
            if court_id:
                court = get_object_or_404(Court, id=court_id)
                instance.court = court
            if region_code:
                # Make sure the region really exists
                get_object_or_404(Region, code=region_code)
                instance.region_code = region_code
            instance.set_password(serializer.validated_data["password"])
            now = datetime.now()
            instance.last_login = now
            instance.save()
            data = {"agent": AgentListSerializer(instance).data, "token": Token.objects.create(user=instance).key}
            headers = self.get_success_headers(serializer.validated_data)
            return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    def partial_update(self, request, *args, **kwargs, ):
        kwargs['partial'] = True
        partial = kwargs.pop('partial', False)
        try:
            # This prevents to update user's password
            request.POST.pop('password')
        except:
            pass
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.POST, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}
        return Response(serializer.data)

    @action(detail=False, methods=['GET'])
    def account(self, request):
        return Response(AgentDetailSerializer(request.user).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['PATCH'])
    def grant_permission(self, request):
        # Get user's ID from request data
        id = request.data.get('id')
        # Get permission name from request data
        permission_name = request.data.get('permission_name')
        # Get permission code from request data
        permission_code = request.data.get('permission_code')

        try:
            # Get user object by ID
            agent = Agent.objects.get(id=id)
            # Get permission by permission_code
            permission = Permission.objects.get(codename=permission_code)

            # Add permission to a user
            agent.user_permissions.add(permission)

            # # Set Admin user's token to no expiring date
            # if user.user_permissions == [perm for perm in Permission.objects.all()] or TokenUser.is_superuser:
            #     exp = datetime.now() + timedelta(days=365)
            #     OutstandingToken.objects.filter(user=TokenUser.id).update(expires_at=exp)

            if agent.has_perm(permission):
                return Response({"message": _("Permission already exists")}, status=status.HTTP_404_NOT_FOUND)
            # Success code with a success message
            return Response(
                {'message': f"The permission {permission_name} has been successfully granted to {agent.username}."})

        except Agent.DoesNotExist:
            # Handle error whenever user does not exist
            return Response({'message': _('The specified user does not exist.')}, status=404)

        except Permission.DoesNotExist:
            # Handle error whenever permission does not exist
            return Response({'message': _('The specified permission does not exist.')}, status=404)


class MunicipalityViewSet(viewsets.ModelViewSet):
    """
    This ViewSet intends to manage all operations against Municipalities
    """
    queryset = Municipality.objects.all()
    serializer_class = MunicipalitySerializer

    def get_queryset(self):
        queryset = self.queryset
        region_code = self.request.GET.get('region_code', '')
        department_name = self.request.GET.get('department_name', '')
        department_id = self.request.GET.get('department_id', '')
        name = self.request.GET.get('name', '')
        if name:
            queryset = queryset.filter(name__iexact=name)
        department_list = []
        if department_name:
            department_list = [department for department in Department.objects.filter(name__iexact=department_name)]
        if department_id:
            department_list = [department for department in Department.objects.filter(id=department_id)]
        if region_code:
                if department_list:
                    department_list = list(set(department_list) & set([department for department in Department.objects.filter(region_code__iexact=region_code)]))
                else:
                    department_list = [department for department in Department.objects.filter(region_code__iexact=region_code)]
        return queryset.filter(department__in=department_list)

    def list(self, request, *args, **kwargs):
        output = []
        if not self.request.GET:
            for department in Department.objects.all():
                output.append({'department': department.id,
                               'municipality_list': MunicipalitySerializer(Municipality.objects.filter(department=department), many=True).data})
            return Response(output)
        else:
            return Response(MunicipalitySerializer(self.get_queryset(), many=True).data)


class RegionViewSet(viewsets.ModelViewSet):
    """
    This ViewSet intends to manage all operations against Regions
    """
    queryset = Region.objects.all()
    serializer_class = RegionSerializer

    def get_queryset(self):
        queryset = self.queryset
        code = self.request.GET.get('code', '')
        lang = self.request.GET.get('lang', 'en')
        if code:
            return queryset.filter(code__iexact=code, lang=lang)
        else:
            return queryset.filter(lang=lang)


class DepartmentViewSet(viewsets.ModelViewSet):
    """
    This ViewSet intends to manage all operations against Departments
    """
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer

    def get_queryset(self):
        queryset = self.queryset
        region_code = self.request.GET.get('region_code', '')
        if region_code:
            return queryset.filter(region_code=region_code)
        else:
            return queryset

    def list(self, request, *args, **kwargs):
        output = []
        if not self.request.GET:
            for region in Region.objects.all():
                output.append({'region_code': region.code,
                               'department_list': DepartmentSerializer(
                                   Department.objects.filter(region_code=region.code), many=True).data})
            return Response(output)
        else:
            return Response(DepartmentSerializer(self.get_queryset(), many=True).data)


class ShipmentViewSet(viewsets.ModelViewSet):
    """
    This ViewSet intends to manage all operations against Municipalities
    """
    queryset = Shipment.objects.all()
    serializer_class = ShipmentSerializer


def link_callback(uri, rel):
    """
    Convert HTML URIs to absolute system paths so xhtml2pdf can access those
    resources
    """
    result = finders.find(uri)
    if result:
        if not isinstance(result, (list, tuple)):
            result = [result]
        result = list(os.path.realpath(path) for path in result)
        path = result[0]
    else:
        sUrl = settings.STATIC_URL        # Typically /static/
        sRoot = settings.STATIC_ROOT      # Typically /home/userX/project_static/
        mUrl = settings.MEDIA_URL         # Typically /media/
        mRoot = settings.MEDIA_ROOT       # Typically /home/userX/project_static/media/

        if uri.startswith(mUrl):
            path = os.path.join(mRoot, uri.replace(mUrl, ""))
        elif uri.startswith(sUrl):
            path = os.path.join(sRoot, uri.replace(sUrl, ""))
        else:
            return uri

    # make sure that file exists
    if not os.path.isfile(path):
        raise RuntimeError(
                'media URI must start with %s or %s' % (sUrl, mUrl)
        )
    return path


@api_view(['GET'])
def render_pdf_view(request, *args, **kwargs):
    template_path = 'receipt.html'
    request_id = kwargs['object_id']
    _request = Request.objects.get(id=request_id)
    lang = _request.user_lang
    activate(lang)
    user_residency_country = get_object_or_404(Country, iso2=_request.user_residency_country_code, lang=lang)
    user_cob = get_object_or_404(Country, iso2=_request.user_cob_code, lang=lang)
    user_dpb_region = get_object_or_404(Region, code=_request.user_dpb.region_code, lang=lang)
    expense_report = compute_receipt_expense_report(_request, _request.service, is_receipt=True)
    expense_report_total = expense_report['total']
    context = {'company_name': "EASYPRO",
               'request': _request,
               'request_court': _request.court.name,
               'expense_report_stamp_fee': expense_report['stamp']['fee'],
               'expense_report_stamp_quantity': expense_report['stamp']['quantity'],
               'expense_report_stamp_total': expense_report['stamp']['total'],
               'expense_report_honorary_fee': expense_report['honorary']['fee'],
               'expense_report_honorary_quantity': expense_report['honorary']['quantity'],
               'expense_report_honorary_total': expense_report['honorary']['total'],
               'expense_report_disbursement_fee': expense_report['disbursement']['fee'],
               'expense_report_disbursement_quantity': expense_report['disbursement']['quantity'],
               'expense_report_disbursement_total': expense_report['disbursement']['total'],
               'currency_code': _request.service.currency_code,
               'user_residency_country': user_residency_country.name,
               'user_civility': _(_request.user_civility),
               'court_type': _(_request.court.type),
               'user_cob': _(user_cob),
               'user_dpb_region': _(user_dpb_region.name),
               'user_dpb': _request.user_dpb.name,
               'expense_report_total': expense_report['total_humanized'],
               'total_amount_in_words': num2words(expense_report_total, lang=lang),
               'data': lang}
    # Create a Django response object, and specify content_type as pdf
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_N_{_request.code}.pdf"'
    # find the template and render it.
    template = get_template(template_path)
    html = template.render(context)

    # create a pdf
    pisa_status = pisa.CreatePDF(html, dest=response, link_callback=link_callback)
    # if error then show some funny view
    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response


class ViewPdf(TemplateView):
    template_name = 'receipt.html'

    def get_context_data(self, **kwargs):

        context = super(ViewPdf, self).get_context_data(**kwargs)
        context['request'] = Request.objects.last()
        context['company_name'] = "EASYPRO"
        return context


class GroupViewSet(viewsets.ModelViewSet):
    """
        API endpoint that allows groups management.
    """
    queryset = Group.objects.all().order_by("-id")
    serializer_class = GroupSerializer
    authentication_classes = [BearerAuthentication]
    permission_classes = [permissions.IsAdminUser]

    @action(detail=False, methods=['PATCH'])
    def grant_permission(self, request):
        # Get permission name from request data
        permission_name = request.data.get('permission_name')
        # Get permission code from request data
        permission_code = request.data.get('permission_code')
        group = self.get_object()

        try:
            # Get permission object from permission_code
            permission = Permission.objects.get(codename=permission_code)

            # Grant permission to a group
            group.permissions.add(permission)

            if group.has_perm(permission):
                return Response({"message": _("Group already has that permission")}, status=status.HTTP_404_NOT_FOUND)
            # Success code with success message
            return Response({'message': _(f"The permission {permission_name} has been granted to the group {group.name}.")})

        except Group.DoesNotExist:
            # Manage error if user doest not exist
            return Response({'message': _("The specified user does not exist")}, status=status.HTTP_404_NOT_FOUND)

        except Permission.DoesNotExist:
            # Manage error if permission does not exist
            return Response({'message': _("The specified permission does not exist")}, status=status.HTTP_404_NOT_FOUND)


class Login(APIView):
    def post(self, request, format=None):
        #try:
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        try:
            # Delete user token if it hasn't been deleted when he logged out
            Token.objects.get(user=user).delete()
        except:
            pass
        token = Token.objects.create(user=user)
        return Response({"success": True, "message": _(f"{user.get_full_name()} logged in successfully"),
                         "user": AgentSerializer(user).data, "token": token.key}, status=status.HTTP_200_OK)
#        except Exception as e:
#            return Response("Authentication failed", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class Logout(APIView):
    authentication_classes = [BearerAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        try:
            # simply delete the token to force a login
            request.user.auth_token.delete()
            # Profile.objects.filter(member_id=self.request.user.id).delete()
            return Response("User Logged out successfully /205/ ", status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response("BAD REQUEST /400/ ", status=status.HTTP_400_BAD_REQUEST)


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    """
        Handles password reset tokens
        When a token is created, an e-mail needs to be sent to the user
        :param sender: View Class that sent the signal
        :param instance: View Instance that sent the signal
        :param reset_password_token: Token Model Object
        :param args:
        :param kwargs:
        :return:
    """
    subject = _("Reset your password")
    project_name = getattr(settings, "PROJECT_NAME", "EasyPro")
    domain = getattr(settings, "DOMAIN", "easyproonline.com")
    # sender = getattr(settings, "EMAIL_HOST_USER", '%s <no-reply@%s>' % (project_name, domain))
    sender = 'contact@africadigitalxperts.com'
    # Send an e-mail to the user
    context = {
        'company_name': "EASYPRO",
        'service_url': domain,
        # 'logo_url': "https://rh_support.dpws.bfc.cam/images/bfc_logo.png",
        'current_user': reset_password_token.user,
        'username': reset_password_token.user.username,
        'email': reset_password_token.user.email,
        'reset_password_url': "{}?token={}".format(
            instance.request.build_absolute_uri(reverse('password_reset:reset-password-confirm')),
            reset_password_token.key),
        'protocol': 'http',
        'domain': domain
    }
    template_name = "mails/password_reset_email.html"
    html_template = get_template(template_name)
    # render email text
    html_content = html_template.render(context)
    msg = EmailMessage(subject, html_content, sender, [reset_password_token.user.email],
                       bcc=['axel.deffo@gmail.com', 'alexis.k.abosson@hotmail.com', 'silatchomsiaka@gmail.com',
                            'sergemballa@yahoo.fr', 'imveng@yahoo.fr'])
    msg.content_subtype = "html"
    if getattr(settings, 'UNIT_TESTING', False):
        msg.send()
    else:
        Thread(target=lambda m: m.send(), args=(msg, )).start()


class ChangePasswordView(UpdateAPIView):
    """
    This endpoint intend to change user's password.
    """
    serializer_class = ChangePasswordSerializer
    model = Agent
    permission_classes = (IsAuthenticated, IsAdminUser)
    authentication_classes = [BearerAuthentication]

    def get_object(self, queryset=None):
        obj = self.request.user
        return obj

    @action(detail=True, methods=['PATCH'])
    def update(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(data=request.data)
        print(serializer)

        if serializer.is_valid():
            if serializer.data.get("new_password") != serializer.data.get("confirmed_password"):
                return Response({"new_password": _("Password mismatched")}, status=status.HTTP_409_CONFLICT)
            # Check old password
            if not self.object.check_password(serializer.data.get("old_password")):
                return Response({"old_password": ["Wrong password."]}, status=status.HTTP_400_BAD_REQUEST)
            # set_password also hashes the password that the user will get
            self.object.set_password(serializer.data.get("new_password"))
            self.object.save()
            response = {
                'status': 'success',
                'code': status.HTTP_200_OK,
                'message': 'Password updated successfully',
                'data': []
            }
            # # Set Admin user's token to no expiring date
            # if TokenUser.is_superuser:
            #     exp = datetime.now() + timedelta(days=365)
            #     OutstandingToken.objects.filter(user=TokenUser.id).update(expires_at=exp)

            return Response(response)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class Upload(TemplateView):
    template_name = 'request/upload.html'


@api_view(['POST'])
@authentication_classes([BearerAuthentication])
@permission_classes([IsAdminUser])
def change_password(request, *args, **kwargs):
    pk = kwargs['pk']
    try:
        user = Agent.objects.get(pk=pk)
    except:
        return Response({"error": True, "message": _("Agent %s not found.") % pk}, status=status.HTTP_404_NOT_FOUND)
    new_password = Agent.objects.make_random_password(length=16, allowed_chars="abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQR"
                                                                               "STUVWXYZ123456789!#$&'*.:=@_|")
    user.set_password(new_password)
    return Response({"user": user.username, "new_password": new_password}, status=status.HTTP_200_OK)


class Home(TemplateView):
    template_name = 'request/out/index.html'


class PrivacyPolicy(TemplateView):
    template_name = 'request/out/privacy-policy/index.html'


class TermsConditions(TemplateView):
    template_name = 'request/out/terms-conditions/index.html'

