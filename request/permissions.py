from django.contrib.auth.models import Group
from rest_framework import permissions
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import BasePermission

from request.models import Agent


class IsAdminAuth(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsSudo(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_superuser


class IsAnonymous(BasePermission):
    def has_permission(self, request, view):
        return not request.user.is_authenticated


class CanReadMandateFiles(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


def is_in_group(user, group_name):
    """
    Takes a user and a group name, and returns `True` if the user is in that group.
    """
    try:
        return Group.objects.get(name=group_name).user_set.filter(id=user.id).exists()
    except Group.DoesNotExist:
        return None


class HasGroupPermission(permissions.BasePermission):
    """
    Ensure user is in required groups.
    """

    def has_permission(self, request, view):
        # Get a mapping of methods -> required group.
        required_groups_mapping = getattr(view, "required_groups", {})

        # Determine the required groups for this particular request method.
        required_groups = required_groups_mapping.get(request.method, [])

        # Return True if the user has all the required groups or is staff.
        return all([is_in_group(request.user, group_name) if group_name != "__all__" else True for group_name in required_groups]) or (request.user and request.user.is_staff)


class HasCourierAgentPermission(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return bool(Agent.objects.filter(id=request.user.id, court_id__isnull=False, is_csa=False).count())
        return False


class HasRegionalAgentPermission(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return bool(Agent.objects.filter(id=request.user.id, region_code__isnull=False).count())
        return False


class HasCourierDeliveryPermission(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return bool(Agent.objects.filter(id=request.user.id, court_id__isnull=False, is_csa=True).count())
        return False


