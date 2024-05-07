"""
URL configuration for EasyPro237 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token

from request.views import RequestViewSet, CountryViewSet, MunicipalityViewSet, RegionViewSet, CourtViewSet, \
    DepartmentViewSet, ShipmentViewSet, Logout, ChangePasswordView, Login, AgentViewSet, change_password, Home

# from request.views import RequestViewSet

router = routers.DefaultRouter()

router.register(r'requests', RequestViewSet)
router.register(r'shipments', ShipmentViewSet)
router.register(r'countries', CountryViewSet)
router.register(r'municipalities', MunicipalityViewSet)
router.register(r'regions', RegionViewSet)
router.register(r'departments', DepartmentViewSet)
router.register(r'courts', CourtViewSet)
router.register(r'agents', AgentViewSet)

admin.autodiscover()

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('token', obtain_auth_token),
    path('api/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('api/change-password/<str:pk>', change_password, name='change_agent_password'),
    path('api/password-reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),

    path('logout/', Logout.as_view()),
    path('login/', Login.as_view()),
    path('api/payment/', include('request.urls')),
    path('api/visualization/', include('visualization.urls')),

    path('home/', Home.as_view(), name='home'),
    path('', include(router.urls)),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) \
              + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

