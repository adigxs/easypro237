# -*- coding: utf-8 -*-
import json
import logging

from django.conf import settings
from django.http import Http404, HttpResponse

from request.constants import SUCCESS, ACCEPTED
from request.models import Payment

# from eska.commons.models import Payment
# from ikwen.billing.models import MoMoTransaction
# from ikwen.core.constants import ACCEPTED

logger = logging.getLogger('easypro237')


def payment_gateway_callback(fn):
    """
    Decorator that does necessary checks upon the call of the
    function that runs behind the URL hit by ikwen's payment Gateway.
    """
    def wrapper(*args, **kwargs):
        request = args[0]
        data = json.loads(request.body)
        amount = float(data['amount'])
        status = data['status']
        object_id = kwargs['object_id']
        try:
            payment = Payment.objects.exclude(status=SUCCESS).get(pk=object_id)

            if status == SUCCESS:
                payment.operator_code = data['operator_code']
                payment.operator_tx_id = data['operator_tx_id']
                payment.operator_user_id = data['operator_user_id']
            payment.status = status
            payment.save()
        except:
            raise Http404("Transaction with object_id %s not found" % object_id)

        if status == ACCEPTED:
            return HttpResponse(f'Status of payment {object_id} successfully updated to {ACCEPTED}')

        if amount < payment.amount:
            return HttpResponse('Invalid amount, %s expected' % amount)

        kwargs['payment'] = payment
        try:
            return fn(*args, **kwargs)
        except:
            logger.error(f"Error running callback for payment {payment.id}", exc_info=True)
            return HttpResponse('Warning: Failed to run callback')
    return wrapper
