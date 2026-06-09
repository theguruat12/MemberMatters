from rest_framework.permissions import BasePermission

from access.models import InterlockAccessGrant


class IsInterlockTrainer(BasePermission):
    """Allow if the caller holds the 'trainer' role on the requested interlock."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        interlock_id = view.kwargs.get("interlock_id")
        try:
            return InterlockAccessGrant.objects.filter(
                profile=request.user.profile,
                interlock_id=interlock_id,
                role=InterlockAccessGrant.ROLE_TRAINER,
            ).exists()
        except Exception:
            return False


class IsAnyInterlockTrainer(BasePermission):
    """Allow if the caller is a trainer on at least one interlock."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        try:
            return InterlockAccessGrant.objects.filter(
                profile=request.user.profile,
                role=InterlockAccessGrant.ROLE_TRAINER,
            ).exists()
        except Exception:
            return False
