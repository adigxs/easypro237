from django.urls import path

from request.utils import checkout, confirm_payment, check_transaction_status, check_succeeded_transaction_status, \
    checkout_foreign_payment
from request.views import render_pdf_view, ViewPdf

app_name = 'request'

urlpatterns = [
    path('checkout/', checkout, name='checkout'),
    path('checkout_foreign_payment/', checkout_foreign_payment, name='checkout_foreign_payment'),
    path('confirm_payment/<object_id>', confirm_payment, name='confirm_payment'),
    path('check_succeeded_transaction_status', check_succeeded_transaction_status,
         name='check_succeeded_transaction_status'),
    path('check_transaction_status', check_transaction_status, name='check_transaction_status'),
    path('render_pdf_view/<object_id>', render_pdf_view, name='render_pdf_view'),
    path('view_pdf', ViewPdf.as_view(), name='view_pdf'),
]
