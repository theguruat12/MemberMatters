from access.models import (
    Doors,
    Interlock,
    InterlockAccessGrant,
    MemberbucksDevice,
    HasExternalAccessControlAPIKey,
)
from profile.models import User
import api_access.metrics as metrics

from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from constance import config

from api_access.permissions import IsInterlockTrainer, IsAnyInterlockTrainer


def _caller_role_level(request, interlock_id):
    """Return the numeric role level for the calling user on a given interlock (0 = no access)."""
    if request.user.is_staff:
        return InterlockAccessGrant.LEVEL_STAFF
    try:
        grant = InterlockAccessGrant.objects.get(
            profile=request.user.profile, interlock_id=interlock_id
        )
        return grant.role_level
    except InterlockAccessGrant.DoesNotExist:
        return InterlockAccessGrant.LEVEL_NONE


class AccessSystemStatus(APIView):
    """
    get: This method returns the current status of the access system.
    """

    permission_classes = (HasExternalAccessControlAPIKey | permissions.IsAdminUser,)

    def get(self, request):
        statusObject = {
            "doors": [],
            "interlocks": [],
            "memberbucksDevices": [],
        }

        error_if_offline = request.GET.get("errorIfOffline", False)
        a_device_is_offline = False
        total_count, offline_count, online_count, locked_out_count = 0, 0, 0, 0

        def reset_count():
            nonlocal total_count, offline_count, online_count, locked_out_count
            total_count, offline_count, online_count, locked_out_count = 0, 0, 0, 0

        def update_count(device_offline=False, device_locked_out=False):
            nonlocal total_count, offline_count, online_count, locked_out_count
            total_count += 1
            if device_offline:
                offline_count += 1
            else:
                online_count += 1
            if device_locked_out:
                locked_out_count += 1

        def report_count(device_type: str):
            nonlocal total_count, offline_count, online_count, locked_out_count
            metrics.devices_total.labels(type=device_type).set(total_count)
            metrics.devices_online_total.labels(type=device_type).set(online_count)
            metrics.devices_offline_total.labels(type=device_type).set(offline_count)
            metrics.devices_locked_out_total.labels(type=device_type).set(
                locked_out_count
            )

        for door in Doors.objects.all():
            offline = door.get_unavailable()
            update_count(offline, door.locked_out)

            statusObject["doors"].append(
                {
                    "id": door.id,
                    "name": door.name,
                    "lastSeen": door.last_seen,
                    "lockedOut": door.locked_out,
                    "offline": offline,
                }
            )
            if offline and door.report_online_status:
                a_device_is_offline = True

        # report door metrics
        report_count("door")
        reset_count()

        for interlock in Interlock.objects.all():
            offline = interlock.get_unavailable()
            update_count(offline, interlock.locked_out)

            statusObject["interlocks"].append(
                {
                    "id": interlock.id,
                    "name": interlock.name,
                    "lastSeen": interlock.last_seen,
                    "lockedOut": interlock.locked_out,
                    "offline": offline,
                }
            )
            if offline and interlock.report_online_status:
                a_device_is_offline = True

        # report interlock metrics
        report_count("interlock")
        reset_count()

        for memberbucksDevice in MemberbucksDevice.objects.all():
            offline = memberbucksDevice.get_unavailable()
            update_count(offline, memberbucksDevice.locked_out)

            statusObject["memberbucksDevices"].append(
                {
                    "id": memberbucksDevice.id,
                    "name": memberbucksDevice.name,
                    "lastSeen": memberbucksDevice.last_seen,
                    "lockedOut": memberbucksDevice.locked_out,
                    "offline": offline,
                }
            )
            if offline and memberbucksDevice.report_online_status:
                a_device_is_offline = True

        # report spacebucksDevices metrics
        report_count("spacebucksDevice")
        reset_count()

        if error_if_offline and a_device_is_offline:
            return Response(statusObject, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(statusObject)


class UserAccessPermissions(APIView):
    """
    get: This method returns the current user's access permissions.
    """

    def get(self, request):
        return Response(request.user.profile.get_access_permissions())


class AuthoriseDoor(APIView):
    """
    post: This method authorises a member to access a door.
    """

    permission_classes = (permissions.IsAdminUser,)

    def put(self, request, door_id, user_id):
        member = User.objects.get(pk=user_id)
        door = Doors.objects.get(pk=door_id)

        member.profile.doors.add(door)
        member.profile.save()
        door.sync()

        return Response()


class AuthoriseInterlock(APIView):
    """
    put: Grants a member user-level access to an interlock.
    Allowed by: admin, interlock trainer.
    """

    permission_classes = (permissions.IsAdminUser | IsInterlockTrainer,)

    def put(self, request, interlock_id, user_id):
        member = User.objects.get(pk=user_id)
        interlock = Interlock.objects.get(pk=interlock_id)

        grant, created = InterlockAccessGrant.objects.get_or_create(
            profile=member.profile,
            interlock=interlock,
            defaults={
                "granted_by": request.user,
                "role": InterlockAccessGrant.ROLE_USER,
            },
        )
        if not created and grant.role == InterlockAccessGrant.ROLE_USER:
            grant.granted_by = request.user
            grant.save(update_fields=["granted_by"])

        interlock.sync()
        return Response()


class RevokeDoor(APIView):
    """
    put: This method revokes a member's access to a door.
    """

    permission_classes = (permissions.IsAdminUser,)

    def put(self, request, door_id, user_id):
        member = User.objects.get(pk=user_id)
        door = Doors.objects.get(pk=door_id)

        member.profile.doors.remove(door)
        member.profile.save()
        door.sync()

        return Response()


class RevokeInterlock(APIView):
    """
    put: Removes a member's access to an interlock.
    Trainers may only revoke user-level grants; admins can revoke any grant.
    """

    permission_classes = (permissions.IsAdminUser | IsInterlockTrainer,)

    def put(self, request, interlock_id, user_id):
        member = User.objects.get(pk=user_id)
        interlock = Interlock.objects.get(pk=interlock_id)

        try:
            target_grant = InterlockAccessGrant.objects.get(
                profile=member.profile, interlock=interlock
            )
        except InterlockAccessGrant.DoesNotExist:
            return Response()

        caller_level = _caller_role_level(request, interlock_id)
        if caller_level <= target_grant.role_level:
            return Response(
                {"error": "You do not have permission to revoke this member's access."},
                status=status.HTTP_403_FORBIDDEN,
            )

        target_grant.delete()
        interlock.sync()
        return Response()


# ---------------------------------------------------------------------------
# Interlock trainer role assignment — admin only
# ---------------------------------------------------------------------------


class AssignInterlockTrainer(APIView):
    """
    put: Assigns trainer role to a member. Admin only.
    """

    permission_classes = (permissions.IsAdminUser,)

    def put(self, request, interlock_id, user_id):
        member = User.objects.get(pk=user_id)
        interlock = Interlock.objects.get(pk=interlock_id)

        grant, _ = InterlockAccessGrant.objects.get_or_create(
            profile=member.profile,
            interlock=interlock,
            defaults={
                "granted_by": request.user,
                "role": InterlockAccessGrant.ROLE_TRAINER,
            },
        )
        if grant.role != InterlockAccessGrant.ROLE_TRAINER:
            grant.role = InterlockAccessGrant.ROLE_TRAINER
            grant.granted_by = request.user
            grant.save(update_fields=["role", "granted_by"])

        interlock.sync()
        return Response()


class RevokeInterlockTrainer(APIView):
    """
    put: Revokes trainer role, downgrading to regular user access. Admin only.
    """

    permission_classes = (permissions.IsAdminUser,)

    def put(self, request, interlock_id, user_id):
        member = User.objects.get(pk=user_id)
        interlock = Interlock.objects.get(pk=interlock_id)

        InterlockAccessGrant.objects.filter(
            profile=member.profile,
            interlock=interlock,
            role=InterlockAccessGrant.ROLE_TRAINER,
        ).update(role=InterlockAccessGrant.ROLE_USER, granted_by=request.user)

        interlock.sync()
        return Response()


# ---------------------------------------------------------------------------
# Managed interlocks — for trainers to view and manage their interlocks
# ---------------------------------------------------------------------------


class ManagedInterlocks(APIView):
    """
    get: Returns interlocks where the caller is a trainer, with member lists.
    """

    def get(self, request):
        my_grants = InterlockAccessGrant.objects.filter(
            profile=request.user.profile,
            role=InterlockAccessGrant.ROLE_TRAINER,
        ).select_related("interlock")

        result = []
        for my_grant in my_grants:
            interlock = my_grant.interlock
            all_grants = (
                InterlockAccessGrant.objects.filter(interlock=interlock)
                .select_related("profile__user", "granted_by__profile")
                .order_by("role", "granted_date")
            )

            users = []
            trainers = []
            for g in all_grants:
                entry = {
                    "userId": g.profile.user.id,
                    "name": g.profile.get_full_name(),
                    "email": g.profile.user.email,
                    "role": g.role,
                    "grantedBy": (
                        g.granted_by.profile.get_full_name() if g.granted_by else None
                    ),
                    "grantedDate": g.granted_date,
                }
                if g.role == InterlockAccessGrant.ROLE_TRAINER:
                    trainers.append(entry)
                else:
                    users.append(entry)

            result.append(
                {
                    "id": interlock.id,
                    "name": interlock.name,
                    "myRole": my_grant.role,
                    "users": users,
                    "trainers": trainers,
                }
            )

        return Response(result)


class MemberSearch(APIView):
    """
    get: Returns basic member info matching the search query. Accessible to
    admins and any user who is a trainer on at least one interlock.
    """

    permission_classes = (permissions.IsAdminUser | IsAnyInterlockTrainer,)

    def get(self, request):
        from django.db.models import Q
        from profile.models import Profile

        q = request.GET.get("q", "").strip()
        if len(q) < 2:
            return Response([])

        profiles = (
            Profile.objects.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(user__email__icontains=q)
            )
            .select_related("user")
            .order_by("first_name", "last_name")[:20]
        )
        return Response(
            [
                {
                    "id": p.user.id,
                    "name": p.get_full_name(),
                    "email": p.user.email,
                }
                for p in profiles
            ]
        )


class RebootInterlock(APIView):
    """
    post: This method will reboot the specified interlock.
    """

    permission_classes = (permissions.IsAdminUser,)

    def post(self, request, interlock_id):
        interlock = Interlock.objects.get(pk=interlock_id)
        interlock.log_force_rebooted()

        return Response({"success": interlock.reboot()})


class SyncDoor(APIView):
    """
    post: This method will force sync the specified door.
    """

    permission_classes = (permissions.IsAdminUser,)

    def post(self, request, door_id):
        door = Doors.objects.get(pk=door_id)
        door.log_force_sync()

        return Response({"success": door.sync(request=request)})


class RebootDoor(APIView):
    """
    post: This method will reboot the specified door.
    """

    permission_classes = (permissions.IsAdminUser,)

    def post(self, request, door_id):
        door = Doors.objects.get(pk=door_id)
        door.log_force_rebooted()

        return Response({"success": door.reboot(request=request)})


class BumpDoor(APIView):
    """
    post: This method will 'bump' the specified door. Note this MAY be called externally with an API key.
    """

    permission_classes = (HasExternalAccessControlAPIKey | permissions.IsAdminUser,)

    def post(self, request, door_id):
        # at this point the credentials been authorised by the permissions classes above
        # BUT we still need to check if the API is enabled or it's a user making the request
        if config.ENABLE_DOOR_BUMP_API or request.user.is_authenticated:
            door = Doors.objects.get(pk=door_id)
            bumped = door.bump(request)
            door.log_force_bump()
            return Response({"success": bumped})
        else:
            return Response(
                {"success": False, "error": "This API is disabled in the config."},
                status=status.HTTP_403_FORBIDDEN,
            )


class LockDevice(APIView):
    """
    post: This method will 'lock' the specified device. Note this MAY be called externally with an API key.
    """

    permission_classes = (HasExternalAccessControlAPIKey | permissions.IsAdminUser,)

    def post(self, request, door_id=None, interlock_id=None):
        # at this point the credentials been authorised by the permissions classes above
        # BUT we still need to check if the API is enabled or it's a user making the request
        if config.ENABLE_DOOR_BUMP_API or request.user.is_authenticated:
            device = (
                Doors.objects.get(pk=door_id)
                if door_id
                else Interlock.objects.get(pk=interlock_id)
            )
            locked = device.lock(request)
            device.log_force_lock()
            return Response({"success": locked})
        else:
            return Response(
                {"success": False, "error": "This API is disabled in the config."},
                status=status.HTTP_403_FORBIDDEN,
            )


class UnlockDevice(APIView):
    """
    post: This method will 'unlock' the specified device. Note this MAY be called externally with an API key.
    """

    permission_classes = (HasExternalAccessControlAPIKey | permissions.IsAdminUser,)

    def post(self, request, door_id=None, interlock_id=None):
        # at this point the credentials been authorised by the permissions classes above
        # BUT we still need to check if the API is enabled or it's a user making the request
        if config.ENABLE_DOOR_BUMP_API or request.user.is_authenticated:
            device = (
                Doors.objects.get(pk=door_id)
                if door_id
                else Interlock.objects.get(pk=interlock_id)
            )
            unlocked = device.unlock(request)
            device.log_force_unlock()
            return Response({"success": unlocked})
        else:
            return Response(
                {"success": False, "error": "This API is disabled in the config."},
                status=status.HTTP_403_FORBIDDEN,
            )
