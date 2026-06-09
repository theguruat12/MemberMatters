from unittest.mock import patch, MagicMock

import pytest
from rest_framework import status

from access.models import Interlock, InterlockAccessGrant

from .factories import AdminFactory, MemberFactory, InterlockFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin():
    return AdminFactory.create(email="admin2@test.com")


@pytest.fixture
def member():
    return MemberFactory.create(email="member2@test.com")


@pytest.fixture
def interlock():
    return InterlockFactory.create(name="Test Mill")


def _authorise_url(interlock_id, member_id):
    return f"/api/access/interlocks/{interlock_id}/authorise/{member_id}/"


def _revoke_url(interlock_id, member_id):
    return f"/api/access/interlocks/{interlock_id}/revoke/{member_id}/"


def test_authorise_creates_grant(api_client, admin, member, interlock):
    api_client.force_authenticate(user=admin)
    response = api_client.put(_authorise_url(interlock.id, member.id))
    assert response.status_code == status.HTTP_200_OK
    assert InterlockAccessGrant.objects.filter(
        profile=member.profile, interlock=interlock
    ).exists()


def test_authorise_records_granting_admin(api_client, admin, member, interlock):
    api_client.force_authenticate(user=admin)
    api_client.put(_authorise_url(interlock.id, member.id))
    grant = InterlockAccessGrant.objects.get(
        profile=member.profile, interlock=interlock
    )
    assert grant.granted_by == admin


def test_authorise_records_granted_date(api_client, admin, member, interlock):
    api_client.force_authenticate(user=admin)
    api_client.put(_authorise_url(interlock.id, member.id))
    grant = InterlockAccessGrant.objects.get(
        profile=member.profile, interlock=interlock
    )
    assert grant.granted_date is not None


def test_authorise_idempotent(api_client, admin, member, interlock):
    api_client.force_authenticate(user=admin)
    api_client.put(_authorise_url(interlock.id, member.id))
    api_client.put(_authorise_url(interlock.id, member.id))
    assert (
        InterlockAccessGrant.objects.filter(
            profile=member.profile, interlock=interlock
        ).count()
        == 1
    )


def test_revoke_removes_grant(api_client, admin, member, interlock):
    InterlockAccessGrant.objects.create(
        profile=member.profile,
        interlock=interlock,
        granted_by=admin,
    )
    api_client.force_authenticate(user=admin)
    response = api_client.put(_revoke_url(interlock.id, member.id))
    assert response.status_code == status.HTTP_200_OK
    assert not InterlockAccessGrant.objects.filter(
        profile=member.profile, interlock=interlock
    ).exists()


def test_access_permissions_include_grant_info(api_client, admin, member, interlock):
    InterlockAccessGrant.objects.create(
        profile=member.profile,
        interlock=interlock,
        granted_by=admin,
    )
    member.profile.state = "active"
    member.profile.save()
    perms = member.profile.get_access_permissions()
    interlock_perm = next(i for i in perms["interlocks"] if i["id"] == interlock.id)
    assert interlock_perm["access"]
    assert interlock_perm["grantedDate"] is not None
    assert interlock_perm["grantedBy"] is not None


def test_access_permissions_no_access_has_null_grant_fields(
    api_client, member, interlock
):
    member.profile.state = "active"
    member.profile.save()
    perms = member.profile.get_access_permissions()
    interlock_perm = next(
        (i for i in perms["interlocks"] if i["id"] == interlock.id), None
    )
    if interlock_perm:
        assert not interlock_perm["access"]
        assert interlock_perm["grantedBy"] is None
        assert interlock_perm["grantedDate"] is None


def test_admin_interlock_list_includes_authorised_members(
    api_client, admin, member, interlock
):
    InterlockAccessGrant.objects.create(
        profile=member.profile,
        interlock=interlock,
        granted_by=admin,
    )
    api_client.force_authenticate(user=admin)
    response = api_client.get("/api/admin/interlocks/")
    assert response.status_code == status.HTTP_200_OK
    interlock_data = next(i for i in response.json() if i["id"] == interlock.id)
    assert "authorisedMembers" in interlock_data
    assert len(interlock_data["authorisedMembers"]) == 1
    member_entry = interlock_data["authorisedMembers"][0]
    assert member_entry["userId"] == member.id
    assert member_entry["grantedDate"] is not None


def test_admin_interlock_list_grant_includes_granter_name(
    api_client, admin, member, interlock
):
    InterlockAccessGrant.objects.create(
        profile=member.profile,
        interlock=interlock,
        granted_by=admin,
    )
    api_client.force_authenticate(user=admin)
    response = api_client.get("/api/admin/interlocks/")
    interlock_data = next(i for i in response.json() if i["id"] == interlock.id)
    member_entry = interlock_data["authorisedMembers"][0]
    assert member_entry["grantedBy"] is not None


def test_default_access_true_creates_grants_for_all_members(
    api_client, admin, member, interlock
):
    api_client.force_authenticate(user=admin)
    with patch("api_admin_tools.views.async_to_sync") as mock_sync:
        mock_sync.return_value = MagicMock()
        response = api_client.put(
            f"/api/admin/interlocks/{interlock.id}/",
            {
                "name": interlock.name,
                "description": "",
                "ipAddress": None,
                "defaultAccess": True,
                "maintenanceLockout": False,
                "playThemeOnSwipe": False,
                "exemptFromSignin": False,
                "hiddenToMembers": False,
            },
            format="json",
        )
    assert response.status_code == 200
    assert InterlockAccessGrant.objects.filter(
        profile=member.profile, interlock=interlock
    ).exists()


def test_default_access_false_removes_grants_for_all_members(
    api_client, admin, member, interlock
):
    from access import models as access_models

    access_models.Interlock.objects.filter(pk=interlock.pk).update(all_members=True)
    InterlockAccessGrant.objects.create(profile=member.profile, interlock=interlock)
    api_client.force_authenticate(user=admin)
    with patch("api_admin_tools.views.async_to_sync") as mock_sync:
        mock_sync.return_value = MagicMock()
        response = api_client.put(
            f"/api/admin/interlocks/{interlock.id}/",
            {
                "name": interlock.name,
                "description": "",
                "ipAddress": None,
                "defaultAccess": False,
                "maintenanceLockout": False,
                "playThemeOnSwipe": False,
                "exemptFromSignin": False,
                "hiddenToMembers": False,
            },
            format="json",
        )
    assert response.status_code == 200
    assert not InterlockAccessGrant.objects.filter(
        profile=member.profile, interlock=interlock
    ).exists()


def test_interlock_access_grant_str(admin, member, interlock):
    grant = InterlockAccessGrant.objects.create(
        profile=member.profile,
        interlock=interlock,
        granted_by=admin,
    )
    assert interlock.name in str(grant)
    assert admin.email in str(grant)


def test_interlock_access_grant_str_no_granter(member, interlock):
    grant = InterlockAccessGrant.objects.create(
        profile=member.profile, interlock=interlock
    )
    assert "system" in str(grant)
