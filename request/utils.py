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


from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.generics import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token


from request.constants import PENDING, STARTED, CRIMINAL_RECORD, PHYSICAL_COPY, SUCCESS, ACCEPTED
from request.decorator import payment_gateway_callback
from request.models import Court, Shipment, Request, Agent, Country, Municipality, Region, Department, Service, Payment, \
    Company, Disbursement, ExpenseReport
from request.serializers import ServiceSerializer


logger = logging.getLogger('easypro237')


class BearerAuthentication(TokenAuthentication):
    keyword = 'Bearer'


def get_mail_content(subject, message=None, template_name='core/mails/notice.html', extra_context=None, service=None):
    """
    Generates the HTML content of an email based on its template.
    Some useful context variables are injected to the template; those are:
        - subject -> subject of the email
        - message -> actual message of the email
        - service -> weblet from which the email is sent
        - config -> config of the weblet
        - project_name -> weblet.project_name
        - company_name -> config.company_name
        - logo -> config.logo; the square logo of the weblet uploaded in the config
        - year -> current year
        - IKWEN_MEDIA_URL
    extra_context is a dictionary of whatever additional context variable
    one may need to add to its email template.
    """
    # if not service:
    #     service = get_service_instance()
    # config = service.basic_config
    html_template = get_template(template_name)
    context = {
        'subject': subject,
        'message': message,
        'service': service,
        # 'config': config,
        'project_name': 'EASYPRO237',
        'company_name': "ADIGXS SARL",
        # 'logo': config.logo,
        'year': datetime.now().year,
        # 'IKWEN_MEDIA_URL': getattr(settings, 'IKWEN_MEDIA_URL', '')
    }
    if extra_context:
        context.update(extra_context)
    return html_template.render(context)


def dispatch_new_task(request: Request) -> Agent:
    """
    This function intends to assign a new request to the first available agent resides in the court where
    of the municipality where the requested user is born.

    The first most available agent is the first person from a list of people who has less pending shipments
    """
    most_available_agent_list = sorted([agent for agent in Agent.objects.filter(court=request.court, is_csa=False)],
                                       key=lambda agent: agent.pending_task_count)
    selected_agent = None
    if most_available_agent_list:
        selected_agent = most_available_agent_list.pop(0)
        selected_agent.pending_task_count += 1
        selected_agent.save()
        request.status = STARTED
        request.save()

    return selected_agent


def compute_expense_report(request: Request, service: Service) -> dict:

    stamp_fee = service.stamp_fee
    disbursement = service.disbursement
    if service.currency_code == 'XAF':
        stamp_fee /= 200
        disbursement /= 200

    expense_report = {"stamp": {"fee": intcomma(round(stamp_fee)), "quantity": 2 * request.copy_count},
                      "disbursement": {"fee": intcomma(round(disbursement)), "quantity": request.copy_count}}
    subtotal = stamp_fee * expense_report["stamp"]["quantity"] + disbursement * expense_report["disbursement"][
        "quantity"]
    expense_report['honorary'] = intcomma(round(request.amount - subtotal))
    expense_report['total'] = intcomma(round(request.amount))
    expense_report['currency_code'] = service.currency_code

    return expense_report


def compute_receipt_expense_report(request: Request, service: Service) -> dict:
    """
    Compute expense report of a request with details of each entry.
    :param request:
    :param service:
    :return: dict
    """
    stamp_fee = service.stamp_fee
    if service.currency_code == "XAF":
        stamp_fee /= 200

    expense_report = {"stamp": {"fee": intcomma(round(stamp_fee)), "quantity": 2 * request.copy_count,
                                "total": stamp_fee * request.copy_count}}
    if service.currency_code == "XAF":
        total_honorary = (service.honorary_fee + (request.copy_count - 1) * service.additional_cr_fee) / 200
        honorary = service.honorary_fee / 200
        disbursement = service.disbursement / 200
    else:
        total_honorary = (service.honorary_fee + (request.copy_count - 1) * service.additional_cr_fee)
        honorary = service.honorary_fee
        disbursement = service.disbursement

    total = expense_report['stamp']['total'] + total_honorary + disbursement
    expense_report['honorary'] = {'fee': honorary, 'quantity': request.copy_count,
                                  'total': total_honorary}
    expense_report['disbursement'] = {"fee": intcomma(round(disbursement)),
                                      "quantity": "Forfait",
                                      "total": intcomma(round(disbursement))}
    expense_report['total'] = intcomma(round(total))
    expense_report['currency_code'] = service.currency_code
    try:

        ExpenseReport.objects.create(request=request, stamp_fee=intcomma(round(stamp_fee)),
                                     stamp_quantity=2 * request.copy_count, honorary_fee=service.honorary_fee,
                                     honorary_quantity=request.copy_count, disbursement_fee=intcomma(round(disbursement)))
    except:
        logger.error("Failed to store ExpenseReport")

    return expense_report


def generate_code() -> str:
    """
    This function generate unique code for a request
    """
    prefix = "DCJ"
    now = f'{datetime.now():%Y%m%d}'
    request_count = Request.objects.filter(created_on__date=datetime.now().date()).count()
    leading_zero_count = 5 - len(str(request_count))
    leading_zero = leading_zero_count * "0"

    return f"{prefix}{now}{leading_zero}{str(request_count)}"


def send_notification_email(request: Request, subject: str, message: str, to: str, agent=None, data=None, is_notification_payment=False):
    """
    This function will send notification email to the available agent for process the request.
    """
    sender = getattr(settings, "EMAIL_HOST_USER", "support@easyproonline.com")
    bcc_recipient_list = ['axel.deffo@gmail.com', 'alexis.k.abosson@hotmail.com', 'silatchomsiaka@gmail.com',
                          'sergemballa@yahoo.fr', 'imveng@yahoo.fr', 'dex@easyproonline.com']
    project_name = 'easypro237'
    domain = 'easypro237.com'
    # request_url = f"https://easyproonline.com/requests/{request.id}/"
    photo_url = ''
    if agent:
        html_content = get_mail_content(subject, template_name='request/mails/new_request.html',
                                        extra_context={'photo_url': photo_url,
                                                       'request_code': request.code})

    msg = EmailMessage(subject, message, sender, [to], bcc_recipient_list)
    if is_notification_payment:
        response = requests.get("https://easyproonline.com" + reverse('request:render_pdf_view', args=(request.id,)), params=data)
        content = response.content
        filename = response.headers['Content-Disposition'].split(';')[1].split('"')[1]
        msg.attach(filename, content, 'application/pdf')
    msg.content_subtype = "html"
    Thread(target=lambda m: m.send(), args=(msg,)).start()


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


@api_view(['POST'])
# @authentication_classes([BearerAuthentication])
# @permission_classes([IsAuthenticated])
def checkout(request, *args, **kwargs):
    """

    :param request:
    :param args:
    :param kwargs:
    :return:
    """
    request_code = request.data.get('request_code', None)
    _request = get_object_or_404(Request, code=request_code)
    try:
        phone = request.data['phone']
        if len(phone) > 9:
            if phone[0:3] == "237":
                phone = phone.removeprefix("237")
            elif phone[0:4] == "+237":
                phone = phone.removeprefix("+237")
            else:
                return Response({'error': True, 'message': 'Invalid payment phone number'},
                                status=status.HTTP_400_BAD_REQUEST)
        payment_method = request.data['payment_method']
        if payment_method not in ['mtn-momo', 'orange-money']:
            return Response({'error': True, 'message': 'Invalid Payment method'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            payment = Payment.objects.get(request_code=_request.code, status=PENDING)
        except:
            payment = Payment.objects.create(request_code=_request.code, amount=_request.amount,
                                             label=_("Request of certificate of non conviction"))
    except:
        return Response({'error': True, 'message': 'Invalid parameters'}, status=status.HTTP_400_BAD_REQUEST)

    payment.mean = payment_method
    currency_code = request.data.get('currency_code', 'XAF')
    amount = _request.amount
    if currency_code == 'EUR':
        amount = amount * 655
        payment.currency_code = 'EUR'
    payment.save()
    try:
        data = {
            'phone': phone,
            'amount': amount,
            'client_id': _request.user_email,
        }

        api_payment_url = getattr(settings, "API_PAYMENT_URL")
        api_payment_token = getattr(settings, "API_PAYMENT_TOKEN")
        url = api_payment_url + "/v2/payment/init"
        headers = {'Authorization': "Bearer %s" % api_payment_token}
        headers['X-Payment-Provider'] = request.data['payment_method']
        headers['X-Reference-Id'] = str(payment.id)
        headers['X-Notification-Url'] = f"https://easyproonline.com/api/payment/confirm_payment/{payment.id}"
        headers['X-Target-Environment'] = 'production'
        headers['Accept-Language'] = 'en'
        headers['Content-Type'] = 'application/json'
        # Since Content-Type is 'application/json', the requests.post()
        # is called with argument 'json'
        response = requests.post(url, json=data, headers=headers)
        json_string = response.content
        json_response = json.loads(json_string)
        payment.status = str(json_response.get('status', payment.status))
        payment.pay_token = json_response.get('pay_token', '')
        payment.message = json_response.get('message', '')
        payment.save()
    except:
        logger.error(f"Init payment {payment.id} failed", exc_info=True)

    return HttpResponse(json.dumps({"message": "Payment successful."}))


@api_view(['PUT'])
# @payment_gateway_callback
def confirm_payment(request, *args, **kwargs):
    """
    This view is the call-back view that will be run after a successful payment
    :param request:
    :param args:
    :param kwargs:
    :return:
    """
    # request = args[0]
    data = json.loads(request.body)
    amount = float(data['amount'])
    payment_status = data['status']
    object_id = kwargs['object_id']
    try:
        payment = Payment.objects.exclude(status=SUCCESS).get(pk=object_id)

        if payment_status.casefold() == SUCCESS.casefold():
            payment.operator_code = data['operator_code']
            payment.operator_tx_id = data['operator_tx_id']
            payment.operator_user_id = data['operator_user_id']
        payment.status = str(payment_status)
        payment.save()
    except:
        raise Http404("Transaction with object_id %s not found" % object_id)

    if payment_status == ACCEPTED:
        return HttpResponse(f'Status of payment {object_id} successfully updated to {ACCEPTED}')

    if amount < payment.amount:
        return HttpResponse('Invalid amount, %s expected' % amount)

    # activate(teacher_member.language)
    _request = get_object_or_404(Request, code=payment.request_code)
    if payment.status.casefold() == SUCCESS.casefold():
        Request.objects.filter(id=_request.id).update(status=PENDING)
        for company in Company.objects.all():
            try:
                Disbursement.objects.create(company=company, payment=payment,
                                            amount=round(company.percentage * 0.01 * payment.amount))
            except:
                continue

        title = _("Paiement réussi")
        body = _("Votre paiement de <strong>%(amount)s</strong> %(currency_code)s pour l'établissement de votre Extrait"
                 " de Cassier Judiciaire N°<strong>%(request_code)s</strong> a été bien reçu."
                 "<p>Merci pour votre confiance.</p>") % {'amount': intcomma(payment.amount),
                                                          'currency_code': payment.currency_code,
                                                          'request_code': payment.request_code}
        try:
            send_notification_email(_request, title, body, _request.user_email, is_notification_payment=True)
        except:
            logger.error(f"Payment notification to {_request.user_first_name} failed", exc_info=True)

        instance = _request
        if instance.user_email:
            # Notify customer who created the request
            subject = _("Support pour l'établissement de votre Extrait de Casier Judiciaire")
            message = _(
                f"{instance.user_civility} <strong>{instance.user_full_name}</strong>,<p>Nous vous remercions de nous "
                f"faire confiance pour vous accompagner dans l'établissement de votre Extrait de Casier Judiciaire. </p>"
                f"<p>Votre demande de service numéro <strong>{instance.code}</strong> est bien "
                f"reçue par nos équipes et nous vous informerons de l'évolution dans son traitement. Nous vous joignons"
                f" également une copie de votre reçu pour toutes fins utiles.</p> "
                f"<p>En cas de souci veuillez nous contacter au <strong>650 229 950</strong></p><p>Merci et excellente"
                f" journée.</p><br>L'équipe EasyPro237.")
            expense_report = compute_expense_report(instance, instance.service)
            send_notification_email(instance, subject, message, instance.user_email, expense_report)

        # ToDo:
        #  Selecting the right agent for your territory
        url_list = [instance.user_birthday_certificate_url, instance.user_passport_1_url,
                    instance.user_passport_2_url, instance.user_proof_of_stay_url,
                    instance.user_id_card_1_url, instance.user_id_card_2_url,
                    instance.user_wedding_certificate_url]
        if any(url_list):
            with transaction.atomic():
                selected_agent = dispatch_new_task(instance)

                if selected_agent:
                    # Notify selected agent a request has been assigned to him.
                    instance.agent = selected_agent
                    instance.save()
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

                    # Notify regional agent.
                    regional_agent = Agent.objects.get(region=selected_agent.court.department.region)
                    regional_agent.pending_task_count += 1
                    regional_agent.save()
                    subject = _(f"Nouvelle demande d'Extrait de Casier Judiciaire dans "
                                f"la region {selected_agent.court.department.region}")
                    message = _(
                        f"M. le régional du {regional_agent.region}, <p>La demande d'Extrait de Casier Judiciaire N°"
                        f" <strong>{instance.code}</strong> a été assignée à votre agent du tribunal "
                        f"du {selected_agent.court.name}."
                        f"</p><p>Veuillez superviser cette opération</p><p>Merci et excellente journée</p>"
                        f"<br>L'équipe EasyPro237.")
                    send_notification_email(instance, subject, message, selected_agent.email, regional_agent)
    else:
        # Payment failed
        # We're trying find the reason why payment failed and we're notifying the user of this failure.
        try:
            api_payment_url = getattr(settings, "API_PAYMENT_URL")
            api_payment_token = getattr(settings, "API_PAYMENT_TOKEN")
            url = api_payment_url + "/v2/payment/" + payment.pay_token
            headers = {'Authorization': "Bearer %s" % api_payment_token}

            response = requests.get(url, headers=headers)
            json_string = response.content
            json_response = json.loads(json_string)
            message = json_response.get('message', payment.message)
            title = _("Paiement échoué")
            body = (_(
                "Votre transaction de paiement de <strong>%(amount)s</strong> %(currency_code)s pour "
                "l'établissement de votre Extrait de Cassier Judiciaire N°<strong>%(request_code)s</strong> a échoué"
                " avec la réponse <strong>%(message)s</strong>.<p>Veuillez réessayer</p>")
                    % {'amount': intcomma(payment.amount), 'currency_code': payment.currency_code,
                       'request_code': payment.request_code, 'message': message})
            try:
                send_notification_email(_request, title, body, _request.user_email)
            except:
                logger.error(f"Failed payment notification to {_request.user_first_name} failed", exc_info=True)

        except:
            logger.error(f"Failed to check encountered message on gateway", exc_info=True)
            return Response(f"Failed to check encountered message on gateway",
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            logger.error(f"Unknown Error encountered while contacting the gateway", exc_info=True)
            return Response(f"Unknown Error encountered while contacting the gateway")
    return Response(f"User {_request.user_first_name} notified")


@api_view(['GET'])
def check_transaction_status(request, *args, **kwargs):
    """
    This view intends to periodically check status of an initiated transaction
    :param request:
    :param args:
    :param kwargs:
    :return:
    """

    request_code = request.GET.get('request_code', None)
    if request_code:
        if Payment.objects.filter(request_code=request_code).count() == 0:
            return Response(f"No pending payment matches with this request code {request_code}",
                            status=status.HTTP_404_NOT_FOUND)
        payment_qs = Payment.objects.exclude(pay_token__isnull=True).filter(request_code=request_code)
        if payment_qs.count() > 0:
            payment = payment_qs.last()
            try:
                api_payment_url = getattr(settings, "API_PAYMENT_URL")
                api_payment_token = getattr(settings, "API_PAYMENT_TOKEN")
                url = api_payment_url + "/v2/payment/" + payment.pay_token
                headers = {'Authorization': "Bearer %s" % api_payment_token}
                response = requests.get(url, headers=headers)
                json_string = response.content
                json_response = json.loads(json_string)
                if response.status_code == 200 and json_response['status'].casefold() == SUCCESS.casefold():
                    response_data = {'success': True, 'status': json_response['status']}
                    message = json_response.get('message', None)
                    if message:
                        response_data['message'] = message
                    return Response(response_data, status=status.HTTP_200_OK)
                else:
                    return Response({'error': True, 'status': json_response['status'], 'message': json_response['message']},
                                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except:
                logger.error(f"Unknown Error encountered while contacting the gateway", exc_info=True)
                return Response(f"Unknown Error encountered while contacting the gateway")
        else:
            payment = Payment.objects.exclude(pay_token__isnull=False).get(request_code=request_code)
            return Response({'error': True, 'status': payment.status, 'message': payment.message},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(f"request_code is required for this request", status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def check_succeeded_transaction_status(request, *args, **kwargs):
    """
    This view intends to check initiated transaction that succeeded without
    notifying the user with a correct status.
    :param request:
    :param args:
    :param kwargs:
    :return:
    """
    operator_tx_id = request.GET.get('operator_tx_id', None)

    if operator_tx_id:
        try:
            payment = Payment.objects.exclude(status=PENDING).get(operator_tx_id=operator_tx_id)
            api_payment_url = getattr(settings, "API_PAYMENT_URL")
            api_payment_token = getattr(settings, "API_PAYMENT_TOKEN")
            url = api_payment_url + "/v2/payment/check_operator_tx_id"
            headers = {'Authorization': "Bearer %s" % api_payment_token}
            response = requests.get(url, params={"operator_tx_id": operator_tx_id}, headers=headers)
            json_string = response.content
            json_response = json.loads(json_string)
            if response.status_code == 200 and json_response['success']:
                return Response({'success': True, 'return_url': json_response['return_url']}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response(f"No pending payment matches with this operator transaction ID {operator_tx_id}",
                            status=status.HTTP_404_NOT_FOUND)
        # else:
        #     logger.error(f"Unknown Error encountered while contacting the gateway", exc_info=True)
        #     return Response(f"Unknown Error encountered while contacting the gateway")
    else:
        return Response(f"operator_tx_id is required for this request", status=status.HTTP_400_BAD_REQUEST)


