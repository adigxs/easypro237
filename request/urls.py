from django.urls import path

from request.utils import checkout, confirm_payment

# from ikwen.core.api.views import upload_file
# from request.views import Upload, delete_single_media, delete_object_list, inspect_logs, Notification

app_name = 'request'



urlpatterns = [
    path('checkout/', checkout, name='checkout'),
    # path('confirm_payment/', confirm_payment, name='confirm_payment'),
    path('confirm_payment/<object_id>', confirm_payment, name='confirm_payment'),
    # path('upload/', Upload.as_view(), name='upload'),
    # path('upload_file/', upload_file, name='upload_file'),
    # path('upload_file/', upload_file, name='upload_file'),
    # path('delete_single_media/', delete_single_media, name='delete_single_media'),
]
