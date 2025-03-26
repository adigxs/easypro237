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


from request.constants import PENDING, STARTED, CRIMINAL_RECORD, PHYSICAL_COPY, SUCCESS, ACCEPTED
from request.decorator import payment_gateway_callback
from request.models import Court, Shipment, Request, Agent, Country, Municipality, Region, Department, Service, Payment, \
    Company, Income, ExpenseReport
from request.serializers import ServiceSerializer


logger = logging.getLogger('easypro237')


class BearerAuthentication(TokenAuthentication):
    keyword = 'Bearer'


def parse_number(s:str):
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return None


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



def compute_receipt_expense_report(request: Request, service: Service, is_receipt=False) -> dict:
    """
    Compute expense report of a request with details of each entry.
    :param request:
    :param service:
    :return: dict
    """
    stamp_fee = service.stamp_fee

    expense_report = {"stamp": {"fee": intcomma(round(stamp_fee)), "quantity": 2 * request.copy_count,
                                "total":  2 * stamp_fee * request.copy_count}}
    total_honorary = (service.honorary_fee + (request.copy_count - 1) * service.additional_cr_fee)
    honorary = service.honorary_fee
    disbursement = service.disbursement + ((request.copy_count - 1) * service.additional_cr_fee)

    expense_report['total'] = expense_report['stamp']['total'] + total_honorary + disbursement + (request.copy_count * service.excavation_fee)
    expense_report['honorary'] = {'fee': intcomma(round(honorary)), 'quantity': request.copy_count,
                                  'total': intcomma(round(total_honorary))}
    expense_report['disbursement'] = {"fee": intcomma(round(disbursement)),
                                      "quantity": _("Package"),
                                      "total": intcomma(round(disbursement))}
    expense_report["stamp"]["fee"] = intcomma(round(expense_report["stamp"]["total"]))
    expense_report['total_humanized'] = intcomma(round(expense_report['total']))
    expense_report['currency_code'] = service.currency_code
    if is_receipt:
        try:
            ExpenseReport.objects.create(request=request, stamp_fee=round(stamp_fee),
                                         stamp_quantity=2 * request.copy_count, honorary_fee=service.honorary_fee,
                                         honorary_quantity=request.copy_count, disbursement_fee=round(disbursement))
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
    bcc_recipient_list = ['silatchomsiaka@gmail.com', 'contact@africadigitalxperts.com', 'dex@easyproonline.com']
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

    _request = get_object_or_404(Request, code=payment.request_code)
    lang = _request.user_lang
    activate(lang)
    if payment.status.casefold() == SUCCESS.casefold():
        Request.objects.filter(code=_request.code).update(status=PENDING)
        for company in Company.objects.all():
            try:
                expense_report = compute_receipt_expense_report(_request, _request.service)
                amount = company.percentage * 0.01 * expense_report.disbursement_fee
                if company.name == "SOPAC":
                    amount += 1260
                if company.name == "ADIGXS":
                    amount += 1000 - (0.03 * amount)
                if company.name == "SOPAC PARTNERS":
                    amount = 240

                Income.objects.create(company=company, payment=payment, amount=round(amount))
            except:
                continue

        instance = _request
        if instance.user_email:
            # Notify customer who created the request
            subject = _("Assistance in obtaining your criminal record")
            message = _(
                f"Dear <strong>{instance.user_full_name}</strong>,<p>Congratulations on your payment, <br>"
                f"Your payment of %(currency_code)s <strong>%(amount)s</strong> for your criminal record N°"
                f"<strong>{instance.code}</strong> has been received. Please find attached your payment receipt."
                f"EASYPRO Cameroon sincerely thanks you for your confidence.</p>"
                f"<p>By paying, you have accepted our “Terms and Conditions” which stipulate that:</p> "
                f"<p>EASYPRO Cameroon delivers or ships the deliverable between three (3) and seven (7) working days, "
                f"from the working day following your payment, depending on the distance between the place of birth and"
                f" the declared place of delivery. Users residing abroad must take into account an additional delay"
                f" related to shipping.</p><p>EASYPRO Cameroon is not a public service. EASYPRO Cameroon is an "
                f"application developed and operated by a private entity, which provides an intermediation service "
                f"between public administrations and you, to make your life easier.</p>"
                f"<p>Our intermediation service consists of obtaining your authentic criminal record from "
                f"the court of your birth, or from the Criminal Record Central Index Card in Yaoundé (if applicable), "
                f"without you or a relative having to travel physically.</p> "
                f"<p>Our teams will work to submit your request to your court of birth or to the Criminal Record Central"
                f" Index Card in Yaoundé (if applicable), as soon as possible, so that you can quickly receive your"
                f" authentic criminal record.</p>"
                f"<p>Please remain contactable at all times, for any communication regarding your service order, until "
                f"your original document has been delivered (or dispatched).</p>."
                f"<p>Once again, EASYPRO Cameroon sincerely thanks you for your understanding,</p>"
                f"<p>EASY PROCÉDURES Economic Interest Group (EASYPRO GIE), <br>Rodrigue ONGOLO ONAMBELE"
                f"<br>Chairman and Managing Director <br>Tel: <a href='tel:+237 650 22 99 50'>(+237) 650 22 99 50</strong></a><strong>"
                f"<a href='mailto:easypro@easyproonline.com'>e"
                f"asypro@easyproonline.com</a></p>") % {'amount': intcomma(payment.amount),
                                                        'currency_code': payment.currency_code,
                                                        'request_code': payment.request_code}
            expense_report = compute_receipt_expense_report(instance, instance.service)
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
                    activate(instance.lang)
                    urls = "<br>"
                    for url in url_list:
                        if url:
                            urls += url
                        urls += "<br>"
                    subject = _("New request for criminal record extract")
                    message = _(
                        f"Dear {selected_agent.first_name}, <p>The request for criminal record extract N°"
                        f" <strong>{instance.code}</strong> was assigned to you. </p><p>Click below links to download "
                        f"the client's birthday certificate, and his ID card</p><p>Thanks and have a great day "
                        f"</p>{urls}<br>The EasyPro237 team.")
                    send_notification_email(instance, subject, message, selected_agent.email, selected_agent)

                    # Notify regional agent.
                    regional_agent = Agent.objects.get(region=selected_agent.court.department.region)
                    regional_agent.pending_task_count += 1
                    regional_agent.save()
                    subject = _(f"New request of criminal record extract in the "
                                f"{selected_agent.court.department.region} region")
                    region = regional_agent.region
                    if instance.user_lang == "fr":
                        if region.name[0] in ['E', 'O', 'A']:
                            region = f"de l'{region}"
                        else:
                            region = f"du {region}"
                    message = _(
                        f"Dear Regional of {region}, <p> The request of Criminal Record N°"
                        f" <strong>{instance.code}</strong> has been assigned to your agent of the "
                        f"{selected_agent.court.name} court."
                        f"</p><p>Please supervise this operation</p><p>Thank you and Happy day</p>"
                        f"<br>The Team EasyPro237.")
                    send_notification_email(instance, subject, message, selected_agent.email, regional_agent)
    else:
        # Payment failed
        # We're trying to find the reason why payment failed and we're notifying the user of this failure.
        try:
            api_payment_url = getattr(settings, "API_PAYMENT_URL")
            api_payment_token = getattr(settings, "API_PAYMENT_TOKEN")
            url = api_payment_url + "/v2/payment/" + payment.pay_token
            headers = {'Authorization': "Bearer %s" % api_payment_token}

            response = requests.get(url, headers=headers)
            json_string = response.content
            json_response = json.loads(json_string)
            message = json_response.get('message', payment.message)
            title = _("Payment failed")
            body = _(
                "Your payment transaction of %(currency_code)s <strong>%(amount)s</strong> for the establishment of "
                "your Criminal Record N°<strong>%(request_code)s</strong> has failed with the response "
                "<strong>%(message)s</strong>.<p>Please try again.</p>"
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
    payer_phone = request.GET['phone']

    if operator_tx_id:
        try:
            payment = Payment.objects.exclude(status=PENDING).get(operator_tx_id=operator_tx_id)
            api_payment_url = getattr(settings, "API_PAYMENT_URL")
            api_payment_token = getattr(settings, "API_PAYMENT_TOKEN")
            url = api_payment_url + "/v2/payment/check_operator_tx_id"
            headers = {'Authorization': "Bearer %s" % api_payment_token}
            response = requests.get(url, params={"operator_tx_id": operator_tx_id, "amount": payment.amount, "phone":
                payer_phone}, headers=headers)
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


@api_view(['POST'])
def checkout_foreign_payment(request, *args, **kwargs):
    """
    This view intends to handle foreign payments.
    :param request:
    :param args:
    :param kwargs:
    :return:
    """
    request_code = request.data.get('request_code', None)
    receipt_url = request.data['receipt_url']
    _request = get_object_or_404(Request, code=request_code)
    if _request.service.ror:
        return Response({'error': True,
                         'message': _("Actually!! You can only pay with mobile payments in Cameroon")},
                        status=status.HTTP_400_BAD_REQUEST)
    elif _request.service.cor:
        return Response({'error': True,
                         'message': _("Foreign payment is not handled now")}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({'error': True,
                         'message': _("Unknown error")}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
