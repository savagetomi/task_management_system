from rest_framework import permissions

from .models import User


class IsAdmin(permissions.BasePermission):
    """Admin-only access. Used for user/department management (FR-2..FR-7)."""

    message = "Only an admin can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.ADMIN
        )


class IsManagerOrAdmin(permissions.BasePermission):
    """
    Gates task creation (FR-8/FR-9): only Managers and Admins may create
    tasks. Employees cannot create or assign tasks to anyone (FR-11).
    """

    message = "Only a manager or admin can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (User.Role.MANAGER, User.Role.ADMIN)
        )


class IsSelfOrAdmin(permissions.BasePermission):
    """
    Used where a user should be able to act on their own account (e.g.
    viewing their own profile) while Admins can act on anyone's.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        return user.role == User.Role.ADMIN or obj.id == user.id