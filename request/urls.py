from django.urls import path

from request.utils import checkout, confirm_payment

# from ikwen.core.api.views import upload_file
# from eska.commons.views import Upload, delete_single_media, delete_object_list, inspect_logs, Notification

app_name = 'request'



urlpatterns = [
    path('checkout/', checkout, name='checkout'),
    path('confirm_payment/', confirm_payment, name='confirm_payment'),
    # path('confirm_payment/<object_id>', confirm_payment, name='confirm_payment'),
    # path('upload/', Upload.as_view(), name='upload'),
    # path('upload_file/', upload_file, name='upload_file'),
    # path('upload_file/', upload_file, name='upload_file'),
    # path('delete_single_media/', delete_single_media, name='delete_single_media'),
    # path('delete_object_list/', delete_object_list, name='delete_object_list'),
    # path('check_payment_integrity', check_integrity),
    # path('confirm_payment/<slug:object_id>', confirm_payment, name='confirm_payment'),
    # path('confirm_payment_method/<slug:object_id>', confirm_payment_method, name='confirm_payment_method'),
    # path('confirm_payment_with_member_balance', confirm_payment_with_member_balance),
    # path('notify_teacher_after_cash_out/<slug:member_id>', notify_teacher_after_cash_out),
    # # path('inspect_logs', InspectLogs.as_view(), name='inspect_logs'),
    # path('inspect_logs', inspect_logs, name='inspect_logs'),
    # path('notification', Notification.as_view(), name='notification'),
    # path('run_batch_send_notifications/', run_batch_send_notifications, name='run_batch_send_notifications'),
]
