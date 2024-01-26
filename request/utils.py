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

from request.constants import PENDING
from request.models import Court, Shipment, Request, Agent, Country, Municipality, Region, Department


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


def dispatch_new_task(request: Request, agent_court: Court) -> tuple:
    """
    This function intends to assign a new request to the first available agent resides in the court where
    of the municipality where the requested user is born.

    The first most available agent is the first person from a list of people who has less pending shipments
    """
    most_available_agent_list = sorted([agent for agent in Agent.objects.filter(court=agent_court)], key=lambda agent: agent.pending_task_count)
    selected_agent, shipment = None, None
    if most_available_agent_list:
        selected_agent = most_available_agent_list.pop(0)
        selected_agent.pending_task_count += 1
        selected_agent.save()
        shipment = Shipment.objects.create(agent=selected_agent, destination_municipality=request.user_residency_municipality,
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
    """
    This function generate unique code for a request
    """
    prefix = "DCJ"
    now = f'{datetime.now():%Y%m%d}'
    request_count = Request.objects.all().count()
    leading_zero_count = 5 - len(str(request_count))
    leading_zero = leading_zero_count * "0"

    return f"{prefix}{now}{leading_zero}{str(request_count)}"


def send_notification_email(request: Request):
    """
    This function will send notification email to the available agent for process the request.
    """
    email = request.user_email
    project_name = 'easypro237'
    domain = 'easypro237.com'
    # try:
    subject = _("Support pour l'établissement de votre Extrait de Casier Judiciaire")
    # request_url = f"http://164.68.126.211:7000/requests/{request.id}/"
    photo_url = ''
    html_content = get_mail_content(subject, template_name='request/mails/new_request.html',
                                    extra_context={'photo_url': photo_url,
                                                   'request_code': request.code})
                                                   # 'agent': agent,
                                                   # 'request_url': request_url})
    # sender = '%s <no-reply@%s>' % (project_name, domain)
    sender = 'contact@africadigitalxpert.com'
    msg = EmailMessage(subject, html_content, sender, [email], ['axel.deffo@gmail.com',
                                                                'alexis.k.abosson@hotmail.com',
                                                                'silatchomsiaka@gmail.com',
                                                                'sergemballa@yahoo.fr '])
    msg.content_subtype = "html"
    msg.send()
    message = _("Nous vous remercions de nous faire confiance pour vous accompagner dans l'établissement de votre"
                " Extrait de Casier Judiciaire. Votre demande de service numéro [Identifiant de la demande] est bien "
                "reçue par nos équipes et nous vous informerons de l'évolution dans son traitement. Vous vous joignons"
                " également une copie de votre reçu pour toutes fins utiles. Merci et excellente journée. "
                "L'équipe EasyPro237.")

    recipient_list = [email] + ['axel.deffo@gmail.com', 'alexis.k.abosson@hotmail.com', 'silatchomsiaka@gmail.com',
                                'sergemballa@yahoo.fr ']
    return send_mail(subject, message, sender, recipient_list)
    #     Thread(target=lambda m: m.send(), args=(msg,)).start()
    # except:
    #     pass


def process_data(request):
    """
    This function intends to process data received from user.
    """
    data = dict()
    data["user_gender"] = "M" if request['civility'] == 'Monsieur' else "F"
    data["user_phone_number_1"] = request['phoneNumber']
    data["user_whatsapp_number"] = request['whatsappContact']
    data["user_email"] = request['email']
    try:
        department = Department.objects.get(slug=slugify(request['regionOfBirth'].split()[1]))
        data['user_dpb'] = department.id
    except:
        data['user_dpb'] = None
    try:
        court = Court.objects.get(name__iexact=request['court'].split()[1])
        data['court'] = court
    except:
        data['court'] = None
    if "Camerounais" in request['typeUser'] or "CAMEROUNAIS" in request['typeUser']:
        country = Country.objects.get(name__iexact="Cameroun")
        data['user_nationality'] = country.id
    else:
        data['user_nationality'] = None
    try:
        country = Country.objects.get(name__iexact=slugify(request['typeUser']).lower().split('ne')[1].strip('-').split('-')[1])
        data['user_residency_country'] = country.id
    except:
        data['user_residency_country'] = None
    try:
        data["user_first_name"] = request['fullName'].split()[0]
    except:
        return Response({"error": True, "message": "Full name should be at least 2 words"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        data["user_last_name"] = request['fullName'].split()[1]
    except:
        data["user_last_name"] = ''


    try:
        municipality = Municipality.objects.get(slug__iexact=slugify(f"{request['location'].split()[0]} {request['location'].split()[1]}"))
        data["user_residency_municipality"] = municipality.id
    except:
        data["user_residency_municipality"] = None
    data["copy_count"] = request['criminalRecordNumber']

    return data







