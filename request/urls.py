from django.urls import path

from request.utils import checkout, confirm_payment, check_transaction_status, check_succeeded_transaction_status

app_name = 'request'

urlpatterns = [
    path('checkout/', checkout, name='checkout'),
    path('confirm_payment/<object_id>', confirm_payment, name='confirm_payment'),
    path('check_succeeded_transaction_status', check_succeeded_transaction_status,
         name='check_succeeded_transaction_status'),
    path('check_transaction_status', check_transaction_status, name='check_transaction_status'),
    # path('upload/', Upload.as_view(), name='upload'),
    # path('upload_file/', upload_file, name='upload_file'),
    # path('upload_file/', upload_file, name='upload_file'),
    # path('delete_single_media/', delete_single_media, name='delete_single_media'),
]
