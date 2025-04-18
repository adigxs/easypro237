# Create your views here.

from datetime import datetime, timedelta

from django.db.models import Q, F, Sum

from rest_framework.decorators import api_view, permission_classes, authentication_classes, action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import viewsets, status
from rest_framework.response import Response
from slugify import slugify

from request.constants import PENDING, STARTED, COMPLETED, SHIPPED, RECEIVED, DELIVERED, REQUEST_STATUS, \
    DELIVERY_STATUSES, SUCCESS
from request.models import Request, Country, Court, Agent, Municipality, Region, Department, Shipment, Service, \
    Income, Payment, Company
from request.permissions import HasGroupPermission, IsAnonymous, HasCourierAgentPermission, HasRegionalAgentPermission, \
    IsSudo, HasCourierDeliveryPermission
from request.serializers import RequestSerializer, CountrySerializer, CourtSerializer, AgentSerializer, \
    DepartmentSerializer, MunicipalitySerializer, RegionSerializer, RequestListSerializer, ShipmentSerializer, \
    ChangePasswordSerializer, GroupSerializer, \
    AgentListSerializer, AgentDetailSerializer, \
    RequestCollectionDeliveryDetailSerializer, RequestCourierDetailSerializer
from request.utils import generate_code, send_notification_email, dispatch_new_task, BearerAuthentication


@api_view(['POST'])
@authentication_classes([BearerAuthentication])
@permission_classes([IsAdminUser])
def report(request, *args, **kwargs):
    start_date = request.data.get('start_date')
    end_date = request.data.get('end_date')

    expense_report = dict()
    k = 0
    _date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    while _date <= end_date:
        for disbursement in Income.objects.filter(created_on=_date):
            total_fee = Income.objects.filter(created_on=_date,
                                                    company_id=disbursement.company_id).aggregate(Sum('amount'))
            expense_report[disbursement.company.name] = {"total_fee": total_fee,
                                                         str(k): _date,
                                                         str(k): _date,
                                                         }
        _date = _date + timedelta(days=1)
        k += 1


@api_view(['GET'])
@authentication_classes([BearerAuthentication])
@permission_classes([IsAdminUser])
def render_dashboard(request, *args, **kwargs):
    """

    :param request:
    :param args:
    :param kwargs:
    :return:
    """
    region_name = request.data.get('region_name', '')
    municipality_name = request.data.get('municipality_name', '')
    department_name = request.data.get('department_name', '')
    court_name = request.data.get('court_name', '')
    created_on = request.data.get('created_on', '')
    start_date = request.data.get('start_date', '')
    end_date = request.data.get('end_date', '')
    period = request.data.get("period", '')

    queryset = Request.objects.all()
    output = dict()
    if court_name:
        if 'central' in court_name:
            court = Court.objects.get(slug='minjustice-yaounde')
        else:
            court = Court.objects.get(slug='-'.join(slugify(court_name).split('-')[1:]))
        queryset = queryset.filter(court=court)
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
    if period:
        if period == "monthly":
            created_on = datetime.now() - timedelta(days=28)
        if period == "weekly":
            created_on = datetime.now() - timedelta(days=7)
        if period == "quarterly":
            created_on = datetime.now() - timedelta(days=90)
        if period == "semi-annually":
            created_on = datetime.now() - timedelta(days=180)
        if period == "annually":
            created_on = datetime.now() - timedelta(days=365)
        queryset = queryset.filter(created_on__gte=created_on)

    if created_on:
        created_on = datetime.strptime(created_on, '%Y-%m-%d')
        queryset = queryset.filter(created_on=created_on)
    if start_date and end_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        if start_date > end_date or end_date > datetime.now():
            queryset = queryset.filter(id__in=[])
        queryset = queryset.filter(created_on__range=[start_date, end_date])
    total_count = queryset.count()
    for request_status in REQUEST_STATUS:
        qs = queryset.filter(status=request_status[0])
        output[request_status[0]] = {"requests": RequestListSerializer(qs, many=True).data,
                                     "count": qs.filter(status=request_status[0]).count(),
                                     "percentage": f"{queryset.filter(status=request_status[0]).count()/total_count * 100}%"}
    for request_status in DELIVERY_STATUSES:
        if request_status[0] == "STARTED":
            continue
        id_list = [shipment.request.id for shipment in Shipment.objects.filter(status__iexact=request_status[0])]
        qs = queryset.filter(id__in=id_list)
        output[request_status[0]] = {"requests": RequestListSerializer(qs, many=True).data,
                                     "count": qs.count(),
                                     "percentage": f"{qs.count() / total_count * 100}%"}

    return Response(output, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([BearerAuthentication])
@permission_classes([IsAdminUser])
def render_financial_report(request, *args, **kwargs):
    """

    :param request:
    :param args:
    :param kwargs:
    :return:
    """

    start_date = RequestListSerializer(Request.objects.first()).data["created_on"].split("T")[0]
    end_date = RequestListSerializer(Request.objects.last()).data["created_on"].split("T")[0]
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')
    given_date = start_date
    request_list = []
    while given_date <= end_date:
        data1 = dict()
        payment_qs = Payment.objects.filter(created_on__day=given_date.day, status=SUCCESS)
        data1["date"] = given_date.strftime('%Y-%m-%d')
        data1["total_request_count"] = Request.objects.filter(created_on__day=given_date.day).count()
        total_amount = payment_qs.aggregate(Sum("amount"))["amount__sum"] if payment_qs else 0
        data1["total_amount"] = total_amount
        om_total_amount = payment_qs.filter(mean="orange-money").aggregate(Sum("amount"))["amount__sum"] if payment_qs.filter(mean="orange-money") else 0
        data1["orange-money"] = {"total_amount": om_total_amount, "percentage": (om_total_amount / total_amount) * 100 if total_amount else 0}
        mtn_total_amount = payment_qs.filter(mean="mtn-momo").aggregate(Sum("amount"))["amount__sum"] if payment_qs.filter(mean="mtn-momo") else 0
        data1["mtn-momo"] = {"total_amount": mtn_total_amount, "percentage": (mtn_total_amount / total_amount) * 100 if total_amount else 0}
        data1["regions"] = []
        for region in Region.objects.all():
            data2 = dict()
            data2["name"] = region.slug
            region_request_qs = Request.objects.filter(service__rob=region, created_on__day=given_date.day)
            region_payment_qs = payment_qs.filter(request_code__in=[request.code for request in region_request_qs])
            total_amount = 0
            if region_payment_qs:
                total_amount = region_payment_qs.aggregate(Sum("amount"))["amount__sum"]
            data2["total_amount"] = total_amount
            data2["total_request_count"] = region_request_qs.count()
            data1["regions"].append(data2)
        data1["companies"] = []
        for company in Company.objects.all():
            data2 = dict()
            data2["name"] = slugify(company.name)
            total_amount = 0
            if payment_qs:
                total_amount = payment_qs.aggregate(Sum("amount"))["amount__sum"] * company.percentage
            data2["total_amount"] = total_amount
            data1["companies"].append(data2)
        data1["agents"] = []
        for agent in Agent.objects.filter(is_csa=False, is_superuser=False):
            data2 = dict()
            agent_request_qs = agent.request_set.filter(created_on__day=given_date.day) 
            agent_payment_qs = payment_qs.filter(request_code__in=[request.code for request in agent_request_qs])
            total_amount = 0
            if agent_payment_qs:
                total_amount = agent_payment_qs.aggregate(Sum("amount"))["amount__sum"]
            data2["name"] = slugify(agent.username)
            data2["total_amount"] = total_amount
            data2["total_request_count"] = agent_request_qs.count()
            data1["agents"].append(data2)
        data1["courts"] = []
        for court in Court.objects.all():
            data2 = dict()
            court_request_qs = court.request_set.filter(created_on__day=given_date.day)
            court_payment_qs = payment_qs.filter(request_code__in=[request.code for request in court_request_qs])
            total_amount = 0
            if court_payment_qs:
                total_amount = court_payment_qs.aggregate(Sum("amount"))["amount__sum"]
            data2["total_amount"] = total_amount
            data2["total_request_count"] = court_payment_qs.count()
            data2["name"] = court.slug
            data1["courts"].append(data2)
        request_list.append(data1)
        given_date = given_date + timedelta(days=1)
    return Response(request_list, status=status.HTTP_200_OK)




@api_view(['GET'])
@authentication_classes([BearerAuthentication])
@permission_classes([IsAdminUser])
def render_agent_performances(request, *args, **kwargs):
    start_date = RequestListSerializer(Request.objects.first()).data["created_on"].split("T")[0]
    end_date = RequestListSerializer(Request.objects.last()).data["created_on"].split("T")[0]
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')
    given_date = start_date
    output = []
    while given_date <= end_date:
        output1 = dict()
        output1["date"] = given_date.strftime('%Y-%m-%d')
        output1["agent_list"] = []
        for agent in Agent.objects.filter(court__isnull=False, is_superuser=False):
            data = dict()
            total_count = agent.request_set.filter(created_on__day=given_date.day).count()
            data.update({"username": agent.username})
            data.update({"total_count": total_count})
            for request_status in REQUEST_STATUS:
                qs = agent.request_set.filter(status=request_status[0])
                data[request_status[0]] = {"count": qs.filter(created_on__day=given_date.day, status=request_status[0]).count(),
                                           "percentage": f"{(agent.request_set.filter(created_on__day=given_date.day, status=request_status[0]).count() / total_count) * 100 if total_count else 0}%"}
            for request_status in DELIVERY_STATUSES:
                if request_status[0] == "STARTED":
                    continue
                id_list = [shipment.request.id for shipment in Shipment.objects.filter(created_on__day=given_date.day, status__iexact=request_status[0])]
                qs = agent.request_set.filter(id__in=id_list)
                data[request_status[0]] = {"count": qs.count(), "percentage": f"{(qs.count() / total_count) * 100 if total_count else 0}%"}

            output1["agent_list"].append(data)
        output.append(output1)
        given_date = given_date + timedelta(days=1)
    return Response(output, status=status.HTTP_200_OK)

