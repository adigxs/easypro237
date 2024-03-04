# Create your views here.
import json
import os
from datetime import datetime

from django.views.generic import TemplateView
from slugify import slugify
from xhtml2pdf import pisa
from num2words import num2words

from django.conf import settings
from django.contrib.staticfiles import finders
from django.shortcuts import render
from django.contrib.humanize.templatetags.humanize import intcomma
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _
from django.core.mail import EmailMessage
from django.http import HttpResponseBadRequest, HttpResponse, Http404, QueryDict
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

from request.constants import PENDING, STARTED, COMPLETED, SHIPPED, RECEIVED, DELIVERED
from request.models import Request, Country, Court, Agent, Municipality, Region, Department, Shipment, Service
from request.serializers import RequestSerializer, CountrySerializer, CourtSerializer, AgentSerializer, \
    DepartmentSerializer, MunicipalitySerializer, RegionSerializer, RequestListSerializer, ShipmentSerializer, \
    RequestPatchSerializer
from request.utils import generate_code, send_notification_email, dispatch_new_task, process_data, BearerAuthentication, \
    compute_expense_report, compute_receipt_expense_report


class RequestViewSet(viewsets.ModelViewSet):
    """
    This viewSet intends to manage all operations against Requests
    """
    queryset = Request.objects.all()
    serializer_class = RequestListSerializer
    authentication_classes = [BearerAuthentication]

    # def get_serializer_class(self):
    #     if self.action == 'list':
    #         return RequestListSerializer
    #     else:
    #         return RequestSerializer

    def get_queryset(self):
        queryset = self.queryset
        code = self.request.GET.get('code', '')
        region_name = self.request.GET.get('region_name', '')
        status = self.request.GET.get('status', '')
        municipality_name = self.request.GET.get('municipality_name', '')
        department_name = self.request.GET.get('department_name', '')
        court_name = self.request.GET.get('court_name', '')
        agent_email = self.request.GET.get('agent_email', '')
        created_on = self.request.GET.get('created_on', '')
        start_date = self.request.GET.get('start_date', '')
        end_date = self.request.GET.get('end_date', '')
        pk = self.kwargs.get('pk', None)

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
        if status:
            if status == 'SHIPPED':
                id_list = [shipment.request.id for shipment in Shipment.objects.filter(status__iexact=SHIPPED)]
                queryset = queryset.filter(id__in=id_list)
            if status == 'RECEIVED':
                id_list = [shipment.request.id for shipment in Shipment.objects.filter(status__iexact=RECEIVED)]
                queryset = queryset.filter(id__in=id_list)
            if status == 'DELIVERED':
                id_list = [shipment.request.id for shipment in Shipment.objects.filter(status__iexact=DELIVERED)]
                queryset = queryset.filter(id__in=id_list)
            else:
                queryset = queryset.filter(status__iexact=status)
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
        minjustice_yaounde = Court.objects.get(slug='minjustice-yaounde')
        user_cob = data.get('user_cob', None)

        if user_cob != cameroon.id and data['court'].id != minjustice_yaounde.id:
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
                if birth_department.id in department_in_red_area and data['court'].id != minjustice_yaounde.id:
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
                if cor.id != cameroon.id and data['court'].id != minjustice_yaounde.id:
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
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        request_status = request.data.get('status', None)
        url_list = [request.data.get('user_birthday_certificate_url', None),
                    request.data.get('user_passport_1_url', None),
                    request.data.get('user_passport_2_url', None),
                    request.data.get('user_proof_of_stay_url', None),
                    request.data.get('user_id_card_1_url', None),
                    request.data.get('user_id_card_2_url', None),
                    request.data.get('user_wedding_certificate_url', None)]
        if request_status not in ['INCORRECT', 'REJECTED', 'COMPLETED']:
            if isinstance(request.data, QueryDict):  # optional
                request.data._mutable = True
            request.data.update({'status': instance.status})
        if request_status == 'COMPLETED':
            shipment = Shipment.objects.create(agent=instance.agent,
                                               destination_municipality=instance.user_residency_municipality,
                                               request=instance, destination_country=instance.user_residency_country)
            if instance.user_residency_hood:
                shipment.destination_hood = instance.user_residency_hood
            if instance.user_residency_town:
                shipment.destination_town = instance.user_residency_town
            shipment.save()
        if request_status == 'SHIPPED':
            Shipment.objects.filter(request=instance).update(status=SHIPPED)
        if request_status == 'RECEIVED':
            Shipment.objects.filter(request=instance).update(status=RECEIVED)
        if request_status == 'DELIVERED':
            Shipment.objects.filter(request=instance).update(status=DELIVERED)

        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if request_status:
            # Notify customer that the status of his request changed
            subject = _("Le status de la demande à changer")
            message = _(
                f"{instance.user_civility} <strong>{instance.user_full_name}</strong>,"
                f"<p>Le statut de votre demande de service numéro <strong>{instance.code}</strong>"
                f" est passée à <strong>{request_status}</strong></p> "
                f"<p>En cas de souci veuillez nous contacter au <strong>675 296 018</strong></p><p>Merci et excellente"
                f" journée.</p><br>L'équipe EasyPro237.")
            send_notification_email(instance, subject, message, instance.user_email)

        if instance.user_email and not request_status:
            # Notify customer who created the request
            subject = _("Support pour l'établissement de votre Extrait de Casier Judiciaire")
            message = _(
                f"{instance.user_civility} <strong>{instance.user_full_name}</strong>,<p>Nous vous remercions de nous "
                f"faire confiance pour vous accompagner dans l'établissement de votre Extrait de Casier Judiciaire. </p>"
                f"<p>Votre demande de service numéro <strong>{instance.code}</strong> est bien "
                f"reçue par nos équipes et nous vous informerons de l'évolution dans son traitement. Nous vous joignons"
                f" également une copie de votre reçu pour toutes fins utiles.</p> "
                f"<p>En cas de souci veuillez nous contacter au <strong>675 296 018</strong></p><p>Merci et excellente"
                f" journée.</p><br>L'équipe EasyPro237.")
            expense_report = compute_expense_report(instance, instance.service)
            send_notification_email(instance, subject, message, instance.user_email, expense_report)

        # ToDo:
        #  Selecting the right agent for your territory

        if any(url_list):
            selected_agent = dispatch_new_task(instance)

            if selected_agent:
                # Notify selected agent a request has been assigned to him.
                instance.agent = selected_agent
                instance.save()
                url_list = [instance.user_birthday_certificate_url, instance.user_passport_1_url,
                            instance.user_passport_2_url, instance.user_proof_of_stay_url, instance.user_id_card_1_url,
                            instance.user_id_card_2_url, instance.user_wedding_certificate_url]
                urls = "<br>"
                for url in url_list:
                    if url:
                        urls += url
                    urls += "<br>"
                subject = _("Nouvelle demande d'Extrait de Casier Judiciaire")
                message = _(
                    f"Cher {selected_agent.first_name}, <p>La demande d'Extrait de Casier Judiciaire N°"
                    f" <strong>{instance.code}</strong> vous a été assignée. </p><p>Cliquez sur les liens ci-dessous "
                    f"pour obtenir l'acte de naissance, la pièce d'idendité du client</p><p>Merci et excellente journée."
                    f"</p>{urls}<br>L'équipe EasyPro237.")
                send_notification_email(instance, subject, message, selected_agent.email, selected_agent)

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
               'expense_report_dispursement_fee': expense_report['dispursement']['fee'],
               'expense_report_dispursement_quantity': expense_report['dispursement']['quantity'],
               'expense_report_dispursement_total': expense_report['dispursement']['total'],
               'expense_report_total': expense_report['total'],
               'total_amount_in_words': num2words(expense_report['total'], lang='fr')}
    # Create a Django response object, and specify content_type as pdf
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_N_{_request.code}.pdf"'
    # find the template and render it.
    template = get_template(template_path)
    html = template.render(context)

    # create a pdf
    pisa_status = pisa.CreatePDF(
       html, dest=response, link_callback=link_callback)
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


class Logout(APIView):
    authentication_classes = [BearerAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        # simply delete the token to force a login
        request.user.auth_token.delete()
        # Profile.objects.filter(member_id=self.request.user.id).delete()
        return Response(status=status.HTTP_200_OK)


