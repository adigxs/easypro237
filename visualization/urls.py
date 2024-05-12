from django.urls import path

from visualization.dashboard import render_dashboard, render_financial_report

app_name = 'visualization'

urlpatterns = [
    path('render_dashboard/', render_dashboard, name='render_dashboard'),
    path('render_financial_report/', render_financial_report, name='render_financial_report'),
]
