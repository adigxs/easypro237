from datetime import datetime
from threading import Thread

from slugify import slugify

from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _
from django.core.mail import EmailMessage, send_mail

from rest_framework import viewsets, status
from rest_framework.response import Response

from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token

from request.constants import PENDING, STARTED, CRIMINAL_RECORD, PHYSICAL_COPY
from request.models import Court, Shipment, Request, Agent, Country, Municipality, Region, Department, Service
from request.serializers import ServiceSerializer


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


def dispatch_new_task(request: Request) -> tuple:
    """
    This function intends to assign a new request to the first available agent resides in the court where
    of the municipality where the requested user is born.

    The first most available agent is the first person from a list of people who has less pending shipments
    """
    most_available_agent_list = sorted([agent for agent in Agent.objects.filter(court=request.court)], key=lambda agent: agent.pending_task_count)
    selected_agent = None
    if most_available_agent_list:
        selected_agent = most_available_agent_list.pop(0)
        selected_agent.pending_task_count += 1
        selected_agent.save()
        request.status = STARTED
        request.save()

    return selected_agent


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


def send_notification_email(request: Request, subject: str, message: str, to: str, agent=None):
    """
    This function will send notification email to the available agent for process the request.
    """
    sender = 'contact@africadigitalxperts.com'
    bcc_recipient_list = ['axel.deffo@gmail.com', 'alexis.k.abosson@hotmail.com', 'silatchomsiaka@gmail.com', 'sergemballa@yahoo.fr']
    project_name = 'easypro237'
    domain = 'easypro237.com'
    # try:
    # request_url = f"http://164.68.126.211:7000/requests/{request.id}/"
    photo_url = ''
    if agent:
        html_content = get_mail_content(subject, template_name='request/mails/new_request.html',
                                        extra_context={'photo_url': photo_url,
                                                       'request_code': request.code})
                                                       # 'agent': agent,
                                                       # 'request_url': request_url})
    # sender = '%s <no-reply@%s>' % (project_name, domain)
    # msg = EmailMessage(subject, html_content, sender, [email], ['axel.deffo@gmail.com',
    #                                                             'alexis.k.abosson@hotmail.com',
    #                                                             'silatchomsiaka@gmail.com',
    #                                                             'sergemballa@yahoo.fr '])
    #
    # msg.send()

    msg = EmailMessage(subject, message, sender, [to], bcc_recipient_list)
    msg.content_subtype = "html"
    # msg.send()
    # send_mail(subject, message, sender, [to])
    Thread(target=lambda m: m.send(), args=(msg,)).start()
    # except:
    #     pass


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
        court = Court.objects.get(slug='yaounde-centre-administratif')
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
        country = Country.objects.get(name__iexact=slugify(request['residence']))
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


def generate_emails():
    """
    This function intends to generate emails of different agents of each court
    :return:
    """
    agent_list = []
    for municipality in Municipality.objects.all():
        for department in municipality.department_set.all():
            for court in department.court_set.all():
                agent_email = f"{court.slug}.{municipality.slug}.{department.slug}.{department.region.slug}@easypro.com"
                agent_list.append(agent_email)
    return agent_list








