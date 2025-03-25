import json
import requests
import logging

from django.db import transaction

from datetime import datetime
from threading import Thread
from slugify import slugify

from django.contrib.humanize.templatetags.humanize import intcomma
from django.template import Context
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _
from django.core.mail import EmailMessage, send_mail
from django.conf import settings
from django.http import HttpResponse, Http404
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.utils.translation import gettext as _, activate

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.generics import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token



def process_data(request):
    """
    This function intends to process data received from user.
    """
    data = dict()
    data["user_gender"] = "M" if request['civility'] == 'Monsieur' else "F"
    data["user_full_name"] = request['fullName']
    data["user_civility"] = request['civility']
    data["user_phone_number_1"] = request['phoneNumber']
    data["user_whatsapp_number"] = request['whatsappContact']
    data["user_email"] = request.get('email', None)
    data["user_address"] = request.get('address', None)
    data["user_postal_code"] = request.get('postalCode', None)
    data["user_residency_country"] = request['residence']
    data["user_birthday_certificate_url"] = request.get('birthCertificateUrl', None)
    data["user_passport_1_url"] = request.get('passportUrl', None)
    data["user_passport_2_url"] = request.get('passportVisaPageUrl', None)
    data["user_proof_of_stay_url"] = request.get('proofStayCameroonUrl', None)
    data["user_id_card_1_url"] = request.get('cniFrontUrl', None)
    data["user_id_card_2_url"] = request.get('cniBackUrl', None)
    data["user_wedding_certificate_url"] = request.get('weddingCertificateUrl', None)
    cameroon = Country.objects.get(name__iexact="Cameroun")
    data['user_marital_status'] = request.get('user_marital_status', None)
    data['destination_address'] = request.get('destination_address', None)
    data['destination_location'] = request.get('destination_location', None)
    data['user_occupation'] = request.get('user_occupation', None)
    data['user_dob'] = request.get('user_dob', None)
    try:
        data["user_close_friend_number"] = request['contactPersonName']
    except:
        data["user_close_friend_number"] = request.get('contactPerson', None)

    try:
        department = Department.objects.get(slug=slugify(request['regionOfBirth'].split()[1]))
        data['user_dpb'] = department.id
        data['user_cob'] = cameroon.id
    except:
        data['user_dpb'] = None

    if 'central' in slugify(request['court']):
        # We check whether the user in the court
        court = Court.objects.get(slug='minjustice-yaounde')
        data['court'] = court

    else:
        try:
            court = Court.objects.get(slug__iexact='-'.join(slugify(request['court']).split('-')[1:]))
            data['court'] = court
        except:
            data['court'] = None

    if "Camerounais" in request['typeUser'] or "CAMEROUNAIS" in request['typeUser']:
        country = cameroon
        data['user_nationality'] = country.id
    else:
        data['user_nationality'] = None

    try:
        country = Country.objects.get(name__iexact=slugify(request['typeUser']).lower().split('ne')[1].strip('-').split('-')[1])
        data['user_cob'] = country.id
    except:
        pass
    # if "Cameroun" in request['typeUser'] or "CAMEROUN" in request['typeUser']:
    #     country = Country.objects.get(name__iexact="Cameroun")
    #     data['user_cob'] = country.id
    # else:
    #     data['user_cob'] = None
    try:
        country = Country.objects.get(slug__iexact=slugify(request['residence']))
        data['user_residency_country'] = country.id
    except:
        data['user_residency_country'] = cameroon.id
    try:
        data["user_last_name"] = request['fullName'].split()[0]
    except:
        return Response({"error": True, "message": "Full name should be at least 2 words"},
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        data["user_first_name"] = request['fullName'].split()[1]
        data["user_last_name"] = request['fullName'].split()[0]
    except:
        data["user_first_name"] = request['fullName'].split()[0]
        data["user_last_name"] = ''


    try:
        data['user_middle_name'] = ' '.join(request['fullName'].split()[2:])
    except:
        pass

    try:
        municipality = Municipality.objects.get(slug__iexact=slugify(f"{request['residence'].split()[0]} {request['residence'].split()[1]}"))
        data["user_residency_municipality"] = municipality.id
    except:
        try:
            municipality = Municipality.objects.get(slug__iexact=slugify(f"{request['residence'].split()[0]}"))
            data["user_residency_municipality"] = municipality.id
        except:
            data["user_residency_municipality"] = None

    data["copy_count"] = request['criminalRecordNumber']

    return data


def complete_missing_service():
    """
    Set default amount of 150 euros to service that has not yet a Service object
    :return:
    """
    country_list, existing_service_list = [], []
    for country in Country.objects.all():
        if Service.objects.filter(cor=country).count() in range(0, 9):
            print(country.name)
            country_list.append(country.name)
            for region in Region.objects.all():
                try:
                    Service.objects.create(type_of_document=CRIMINAL_RECORD, format=PHYSICAL_COPY, rob=region,
                                           cor=country, cost=150, currency_code='EUR')
                except:
                    service = Service.objects.get(type_of_document=CRIMINAL_RECORD, format=PHYSICAL_COPY, rob=region,
                                                  cor=country)
                    existing_service_list.append(ServiceSerializer(service).data)
    return country_list, existing_service_list


def create_agents():
    """
    This function intends to generate emails of different agents of each court
    :return:
    """
    admin_user_token = "c3174148dd7d54665cb40030486db5c4f4eece00"
    agent_list = []
    for department in Department.objects.all():
        for court in department.court_set.all():
            agent_email = f"{court.slug}.{department.slug}.{department.region.slug}@easyproonline.com"
            data = dict()
            data["email"] = agent_email
            data["username"] = f"{court.slug}"
            data["first_name"] = f"{court.slug}.{department.slug}"
            data["last_name"] = f"{department.region.slug}"
            data["court_id"] = court.id
            data["password"] = "password"
            headers = {'Authorization': "Bearer %s" % admin_user_token}
            try:
                requests.post("https://easyproonline.com/agents/", data=data, headers=headers)
                agent_list.append(agent_email)
            except:
                continue
    for department in Department.objects.all():
        for court in department.court_set.all():
            agent_email = f"{court.slug}.{department.slug}.{department.region.slug}.acd@easyproonline.com"
            data = dict()
            data["email"] = agent_email
            data["username"] = f"{court.slug}.acd"
            data["first_name"] = f"{court.slug}.{department.slug}"
            data["last_name"] = f"{department.region.slug}"
            data["court_id"] = court.id
            data["is_csa"] = 1
            data["password"] = "password"
            headers = {'Authorization': "Bearer %s" % admin_user_token}
            try:
                requests.post("https://easyproonline.com/agents/", data=data, headers=headers)
                agent_list.append(agent_email)
            except:
                continue
    for region in Region.objects.all():
        agent_email = f"{region.slug}@easyproonline.com"
        data = dict()
        data["email"] = agent_email
        data["username"] = f"{region.name}"
        data["first_name"] = f"{region.name}"
        data["last_name"] = f"{region.name}"
        data["region_id"] = region.id
        data["password"] = "password"
        headers = {'Authorization': "Bearer %s" % admin_user_token}
        try:
            requests.post("https://easyproonline.com/agents/", data=data, headers=headers)
            agent_list.append(agent_email)
        except:
            continue
    return agent_list


def render_coordinates(region_code: str) -> tuple:
    """
    Render coordinates of a region in landmark
    :return:
    """
    if region_code == "EN":
        return 0, 3
    if region_code == "NO":
        return 0, 2
    if region_code == "AD":
        return 0, 1
    if region_code == "CE":
        return 0, 0
    if region_code == "ES":
        return 1, 0
    if region_code == "NW":
        return -2, 0
    if region_code == "OU":
        return -1, 0
    if region_code == "SW":
        return -2, -1
    if region_code == "LT":
        return -1, -1
    if region_code == "SU":
        return 0, -1


def update_service_cost():
    """
    This function intends to update the cost of service
    :return:
    """
    for rob in Region.objects.all():
        for ror in Region.objects.all():
            if rob.code == ror.code:
                Service.objects.filter(ror=ror, rob=rob).update(cost=9600, disbursement=4100)
                continue
            x1, y1 = render_coordinates(rob.code)
            x2, y2 = render_coordinates(ror.code)
            d = round((((x2-x1) ** 2) + ((y2-y1) ** 2)) ** 0.5)

            if d == 1:
                Service.objects.filter(ror=ror, rob=rob).update(cost=10600, disbursement=5100)
            if d == 2:
                Service.objects.filter(ror=ror, rob=rob).update(cost=11600, disbursement=6100)
            if d == 3:
                Service.objects.filter(ror=ror, rob=rob).update(cost=12600, disbursement=7100)
            if d == 4:
                Service.objects.filter(ror=ror, rob=rob).update(cost=13600, disbursement=8100)