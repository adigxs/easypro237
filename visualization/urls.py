from django.urls import path

from visualization.dashboard import render_dashboard

app_name = 'visualization'

urlpatterns = [
    path('render_dashboard/', render_dashboard, name='render_dashboard'),
]
