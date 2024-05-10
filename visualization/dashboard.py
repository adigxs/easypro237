# Create your views here.

from datetime import datetime, timedelta

from django.db.models import Q, F, Sum

from rest_framework.decorators import api_view, permission_classes, authentication_classes, action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import viewsets, status
from rest_framework.response import Response

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
        for disbursement in Disbursement.objects.filter(created_on=_date):
            total_fee = Disbursement.objects.filter(created_on=_date,
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
    region_name = request.GET.get('region_name', '')
    municipality_name = request.GET.get('municipality_name', '')
    department_name = request.GET.get('department_name', '')
    court_name = request.GET.get('court_name', '')
    created_on = request.GET.get('created_on', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    period = request.GET.get("period", '')

    queryset = Request.objects.all()
    total_count = queryset.count()
    output = dict()
    # if court_name:
    #     id_list = []
    #     try:
    #         if 'central' in court_name:
    #             court = Court.objects.get(slug='minjustice-yaounde')
    #         else:
    #             court = Court.objects.get(slug='-'.join(slugify(court_name).split('-')[1:]))
    #         agent = Agent.objects.get(court__id=court.id)
    #         shipment_qs = Shipment.objects.filter(agent__id=agent.id)
    #         for shipment in shipment_qs:
    #             id_list.append(shipment.request.id)
    #     except:
    #         pass
    #     queryset = queryset.filter(id__in=id_list)
    #
    # if municipality_name:
    #     department_list = []
    #     try:
    #         municipality = Municipality.objects.get(slug=slugify(municipality_name))
    #         department_list = [municipality.department.id]
    #     except:
    #         pass
    #     queryset = queryset.filter(user_dpb__id__in=department_list)
    # if department_name:
    #     queryset = queryset.filter(user_dpb__slug=slugify(department_name))
    # if region_name:
    #     queryset = queryset.filter(user_dpb__region__slug=slugify(region_name))
    # if period:
    #     if period == "monthly":
    #         created_on = datetime.now() - timedelta(days=28)
    #     if period == "weekly":
    #         created_on = datetime.now() - timedelta(days=7)
    #     if period == "quarterly":
    #         created_on = datetime.now() - timedelta(days=90)
    #     if period == "semi-annually":
    #         created_on = datetime.now() - timedelta(days=180)
    #     if period == "annually":
    #         created_on = datetime.now() - timedelta(days=365)
    #     queryset = queryset.filter(created_on__gte=created_on)
    #
    # if created_on:
    #     created_on = datetime.strptime(created_on, '%Y-%m-%d')
    #     queryset = queryset.filter(created_on=created_on)
    # if start_date and end_date:
    #     start_date = datetime.strptime(start_date, '%Y-%m-%d')
    #     end_date = datetime.strptime(end_date, '%Y-%m-%d')
    #     if start_date > end_date or end_date > datetime.now():
    #         queryset = queryset.filter(id__in=[])
    #     queryset = queryset.filter(created_on__range=[start_date, end_date])
    for request_status in REQUEST_STATUS:
        queryset = Request.objects.filter(status=request_status[0])
        output[request_status[0]] = {
                                    # "requests": RequestListSerializer(queryset, many=True).data,
                                  "count": Request.objects.filter(status=request_status[0]).count(),
                                  "status": request_status,
                                  "total_count": total_count,
                                  "percentage": f"{Request.objects.filter(status=request_status[0]).count() / total_count}%"}
    for request_status in DELIVERY_STATUSES:
        id_list = [shipment.request.id for shipment in Shipment.objects.filter(status__iexact=request_status[0])]
        queryset = Request.objects.filter(id__in=id_list)
        output[request_status[0]] = {
                                     # "requests": RequestListSerializer(queryset, many=True).data,
                                     "count": Request.objects.filter(id__in=id_list).count(),
                                     "status": request_status[0],
                                     "total_count": total_count,
                                     "percentage": f"{queryset.count() / total_count}%"}

    return Response(output, status=status.HTTP_200_OK)
