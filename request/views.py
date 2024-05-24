# Create your views here.
import json
import os
import uuid
from datetime import datetime, timedelta
from threading import Thread

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, F, Sum
from django.dispatch import receiver
from django.views.generic import TemplateView
from rest_framework.generics import UpdateAPIView
from slugify import slugify
from xhtml2pdf import pisa
from num2words import num2words

from django.conf import settings
from django.contrib.staticfiles import finders
from django.contrib.auth.models import Permission
from django.contrib.auth.models import Group
from django.shortcuts import render, get_object_or_404
from django.contrib.humanize.templatetags.humanize import intcomma
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _
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
# from rest_framework.decorators import detail_route

from request.constants import PENDING, STARTED, COMPLETED, SHIPPED, RECEIVED, DELIVERED, REQUEST_STATUS, \
    DELIVERY_STATUSES
from request.models import Request, Country, Court, Agent, Municipality, Region, Department, Shipment, Service, \
    Disbursement
from request.permissions import HasGroupPermission, IsAnonymous, HasCourierAgentPermission, HasRegionalAgentPermission, \
    IsSudo, HasCourierDeliveryPermission
from request.serializers import RequestSerializer, CountrySerializer, CourtSerializer, AgentSerializer, \
    DepartmentSerializer, MunicipalitySerializer, RegionSerializer, RequestListSerializer, ShipmentSerializer, \
    ChangePasswordSerializer, GroupSerializer, \
    AgentListSerializer, AgentDetailSerializer, \
    RequestCollectionDeliveryDetailSerializer, RequestCourierDetailSerializer
from request.utils import generate_code, send_notification_email, dispatch_new_task, process_data, BearerAuthentication, \
    compute_expense_report, compute_receipt_expense_report


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
        region_name = self.request.GET.get('region_name', '')
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
            queryset = queryset.exclude(status=STARTED)

            # If it's a regional agent
            if Agent.objects.filter(id=self.request.user.id, region_id__isnull=False).count():
                agent = Agent.objects.filter(id=self.request.user.id, region_id__isnull=False).get()
                if agent.region_id == Region.objects.get(name__icontains='central').id:
                    queryset = queryset.filter(court__slug__contains='minjustice')
                else:

                    queryset = queryset.filter(court__department__region_id__exact=agent.region.id).exclude(court__slug__contains='minjustice')

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
        if region_name:
            queryset = queryset.filter(user_dpb__region__slug=slugify(region_name))
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
        data = process_data(self.request.data)
        data['code'] = generate_code()
        cameroon = Country.objects.get(name__iexact='cameroun')
        min_justice_yaounde = Court.objects.get(slug='minjustice-yaounde')
        user_cob = data.get('user_cob', None)

        if user_cob != cameroon.id and data['court'].id != min_justice_yaounde.id:
            return Response({"error": True, 'message': "Invalid court for this user born abroad"},
                            status=status.HTTP_400_BAD_REQUEST)

        department_in_red_area = Department.objects.filter(region__code__in=['NW', 'SW'])
        court_in_red_area = []
        for department in department_in_red_area:
            for court in department.court_set.all():
                court_in_red_area.append(court.id)
        try:
            # For users born locally in Cameroon
            birth_department = Department.objects.get(id=data['user_dpb'])
            birth_court_list = [court.id for court in birth_department.court_set.all()]

            if data['court'].id not in birth_court_list:
                if birth_department.id in department_in_red_area and data['court'].id != min_justice_yaounde.id:
                    return Response({"error": True, 'message': f"{birth_department} is in red area department, "
                                                               f"selected court {data['court']} is not eligible "
                                                               f"(not in central file))"},
                                    status=status.HTTP_400_BAD_REQUEST)
                elif birth_department.id not in [dp.id for dp in department_in_red_area]:
                    return Response({"error": True, 'message': f"Fichier Central des Casiers Judiciaires - Minjustice - "
                                                               f"Yaoundé does not handle {birth_department}"},
                                    status=status.HTTP_400_BAD_REQUEST)
        except:
            # For users living abroad
            cor = Country.objects.get(id=data['user_residency_country'])
            if cor:
                if cor.id != cameroon.id and data['court'].id != min_justice_yaounde.id:
                    return Response({"error": True, 'message': f"Selected court {data['court']} is not eligible "
                                                               f"(not the central file)) to handle your request"},
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
        expense_report = compute_receipt_expense_report(request, service)
        request.amount = int(expense_report['total'])
        request.save()
        headers = self.get_success_headers(serializer.data)
        return Response({"request": RequestListSerializer(request).data, "expense_report": expense_report},
                        status=status.HTTP_201_CREATED, headers=headers)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        request_status = request.data.get('status', None)

        if request_status in ["STARTED", "PENDING"]:
            return Response({"error": "Impossible to update the status of this request"}, status=status.HTTP_401_UNAUTHORIZED)

        if request_status == COMPLETED and instance.status not in ['COMMITTED', 'INCORRECT', 'REJECTED']:
            return Response({"error": f"The request {instance.code} must be committed or incorrect or rejected"},
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
                                                   request=instance, destination_country=instance.user_residency_country)
                delivery_agent.pending_task_count += 1

                subject = _(f"Nouvelle livraison a effectué")
                message = _(
                    f"M. {delivery_agent.username}, <p>La demande d'Extrait de Casier Judiciaire N°"
                    f" <strong>{instance.code}</strong> a été effectué avec succès."
                    f"</p><p>Veuillez vous connecter pour récupérer les contacts téléphoniques du client</p>"
                    f"<p>Merci et excellente journée</p>"
                    f"<br>L'équipe EasyPro237.")
                send_notification_email(instance, subject, message, delivery_agent.email)
                if instance.user_residency_hood:
                    shipment.destination_hood = instance.user_residency_hood
                if instance.user_residency_town:
                    shipment.destination_town = instance.user_residency_town
                shipment.save()
            elif request_status == 'SHIPPED':
                if Shipment.objects.filter(request=instance, status=STARTED).count() == 0:
                    return Response({"error": f"The request {instance.code} is not yet completed"}, status=status.HTTP_400_BAD_REQUEST)
                Shipment.objects.filter(request=instance).update(status=SHIPPED)
            elif request_status == 'RECEIVED':
                if Shipment.objects.filter(request=instance, status=SHIPPED).count() == 0:
                    return Response({"error": f"The package of request {instance.code} has not yet been shipped"}, status=status.HTTP_400_BAD_REQUEST)
                Shipment.objects.filter(request=instance).update(status=RECEIVED)
            elif request_status == 'DELIVERED':
                if Shipment.objects.filter(request=instance, status=RECEIVED).count() == 0:
                    return Response({"error": f"The package of request {instance.code} has not yet received"}, status=status.HTTP_400_BAD_REQUEST)
                Shipment.objects.filter(request=instance).update(status=DELIVERED)
                delivery_agent.pending_task_count -= 1
                Agent.objects.filter(region=instance.region).update(pending_task_count=F("pending_task_count") - 1)
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
                # raise ValidationError({"authorize": _("You dont have permission to change status of this request")})
                return Response({"error": True, "message": "You dont have permission to change status of "
                                                           "this request"}, status=status.HTTP_401_UNAUTHORIZED)

            if request_status == 'PENDING':
                request_status = 'Soumis'
            if request_status == 'COMMITTED':
                request_status = 'Initié'
            if request_status == 'REJECTED':
                request_status = 'Rejeté'
            if request_status == 'INCORRECT':
                request_status = 'Erroné'
            if request_status == 'COMPLETED':
                request_status = 'Etabli'
            if request_status == 'SHIPPED':
                request_status = 'Expédié'
            if request_status == 'RECEIVED':
                request_status = 'Réceptionné'
            if request_status == 'DELIVERED':
                request_status = 'Livré'
            if request_status:
                # Notify customer that the status of his request changed
                subject = _(f"Le status de la demande {instance.code} a changé")
                message = _(
                    f"{instance.user_civility} <strong>{instance.user_full_name}</strong>,"
                    f"<p>Le statut de votre demande de service numéro <strong>{instance.code}</strong>"
                    f" est passée à <strong>{request_status}</strong></p> "
                    f"<p>En cas de souci veuillez nous contacter au <strong>650 229 950</strong></p><p>Merci et excellente"
                    f" journée.</p><br>L'équipe EasyPro237.")
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
    queryset = Agent.objects.all().order_by('-region', '-court')
    authentication_classes = [BearerAuthentication]

    def get_queryset(self):
        region_name = self.request.GET.get('region_name', '')
        queryset = Agent.objects.all()
        if region_name:
            region_slug = slugify(region_name)
            region = get_object_or_404(Region, slug=region_slug)
            queryset = self.queryset.filter(region=region)
        return queryset.order_by('-region', '-court')

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
        return Response({"success": True, 'message': f'{agent.get_full_name()} successfully added '
                                                     f'to group {group.name}'}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            instance = serializer.instance
            court_id = request.data.get('court_id', None)
            region_id = request.data.get('region_id', None)
            if court_id:
                court = get_object_or_404(Court, id=court_id)
                instance.court = court
            if region_id:
                region = get_object_or_404(Region, id=region_id)
                instance.region = region
            instance.set_password(serializer.validated_data["password"])
            now = datetime.now()
            instance.last_login = now
            instance.save()
            data = {"agent": AgentListSerializer(instance).data, "token": Token.objects.create(user=instance).key}
            headers = self.get_success_headers(serializer.validated_data)
            return Response(data, status=status.HTTP_201_CREATED, headers=headers)
        # return Response({"error"}, status=status.HTTP_201_CREATED, headers=headers)

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
        # Obtenir l'ID utilisateur depuis les données de la requête
        id = request.data.get('id')
        # Obtenir le nom de la permission depuis les données de la requête
        permission_name = request.data.get('permission_name')
        # Obtenir le code de permission depuis les données de la requête
        permission_code = request.data.get('permission_code')

        try:
            # Récupérer l'objet utilisateur à partir de l'ID
            agent = Agent.objects.get(id=id)
            # Récupérer l'objet permission à partir du copermission_code
            permission = Permission.objects.get(codename=permission_code)

            # Ajouter la permission à l'utilisateur
            agent.user_permissions.add(permission)

            # # Set Admin user's token to no expiring date
            # if user.user_permissions == [perm for perm in Permission.objects.all()] or TokenUser.is_superuser:
            #     exp = datetime.now() + timedelta(days=365)
            #     OutstandingToken.objects.filter(user=TokenUser.id).update(expires_at=exp)

            if agent.has_perm(permission):
                return Response({"message": "Permission already exist"}, status=status.HTTP_404_NOT_FOUND)
            # Code de succès avec un message de réussite
            return Response(
                {'message': f"La permission {permission_name} a été attribuée à l'utilisateur {agent.username}."})

        except Agent.DoesNotExist:
            # Gérer l'erreur si l'utilisateur n'existe pas
            return Response({'message': 'L\'utilisateur spécifié n\'existe pas.'}, status=404)

        except Permission.DoesNotExist:
            # Gérer l'erreur si la permission n'existe pas
            return Response({'message': 'La permission spécifiée n\'existe pas.'}, status=404)


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
    expense_report = compute_receipt_expense_report(_request, _request.service)
    context = {'company_name': "EASYPRO",
               'request': _request,
               'expense_report_stamp_fee': expense_report['stamp']['fee'],
               'expense_report_stamp_quantity': expense_report['stamp']['quantity'],
               'expense_report_stamp_total': expense_report['stamp']['total'],
               'expense_report_honorary_fee': expense_report['honorary']['fee'],
               'expense_report_honorary_quantity': expense_report['honorary']['quantity'],
               'expense_report_honorary_total': expense_report['honorary']['total'],
               'expense_report_disbursement_fee': expense_report['disbursement']['fee'],
               'expense_report_disbursement_quantity': expense_report['disbursement']['quantity'],
               'expense_report_disbursement_total': expense_report['disbursement']['total'],
               'expense_report_total': expense_report['total'],
               'total_amount_in_words': num2words(expense_report['total'], lang='fr')}
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
        # Obtenir le nom de la permission depuis les données de la requête
        permission_name = request.data.get('permission_name')
        # Obtenir le code de permission depuis les données de la requête
        permission_code = request.data.get('permission_code')
        group = self.get_object()

        try:
            # Récupérer l'objet permission à partir du copermission_code
            permission = Permission.objects.get(codename=permission_code)

            # Ajouter la permission à un groupe
            group.permissions.add(permission)

            if group.has_perm(permission):
                return Response({"message": "Group already has that permission"}, status=status.HTTP_404_NOT_FOUND)
            # Code de succès avec un message de réussite
            return Response({'message': f"La permission {permission_name} a été attribuée au groupe {group.name}."})

        except Group.DoesNotExist:
            # Gérer l'erreur si l'utilisateur n'existe pas
            return Response({'message': 'L\'utilisateur spécifié n\'existe pas.'}, status=status.HTTP_404_NOT_FOUND)

        except Permission.DoesNotExist:
            # Gérer l'erreur si la permission n'existe pas
            return Response({'message': 'La permission spécifiée n\'existe pas.'}, status=status.HTTP_404_NOT_FOUND)


class Login(APIView):
    def post(self, request, format=None):
        try:
            serializer = AuthTokenSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']
            try:
                # Delete user token if it hasn't been deleted when he logged out
                Token.objects.get(user=user).delete()
            except:
                pass
            token = Token.objects.create(user=user)
            return Response({"success": True, "message": f"{user.get_full_name()} logged in successfully",
                             "user": AgentSerializer(user).data, "token": token.key}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response("Authentication failed", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
    # domain = getattr(settings, "DOMAIN", "easyproonline.com")
    domain = getattr(settings, "DOMAIN", "easyproonline.com")
    # sender = getattr(settings, "EMAIL_HOST_USER", '%s <no-reply@%s>' % (project_name, domain))
    sender = 'contact@africadigitalxperts.com'
    # send an e-mail to the user
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
        return Response({"error": True, "message": "Agent %s not found." % pk}, status=status.HTTP_404_NOT_FOUND)
    new_password = Agent.objects.make_random_password(length=16, allowed_chars="abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQR"
                                                                               "STUVWXYZ123456789!#$&'*.:=@_|")
    user.set_password(new_password)
    return Response({"user": user.username, "new_password": new_password}, status=status.HTTP_200_OK)


class Home(TemplateView):
    template_name = 'request/out/index.html'


class PrivacyPolicy(TemplateView):
    template_name = 'request/out/privacy-policy/index.html'

