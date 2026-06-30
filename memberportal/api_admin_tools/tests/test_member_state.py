from unittest.mock import patch

import pytest
from rest_framework import status

from profile.models import UserEventLog

from .factories import AdminFactory, MemberFactory

pytestmark = pytest.mark.django_db

STATE_URL = "/api/admin/members/{member_id}/state/{state}/"


@pytest.fixture
def admin():
    return AdminFactory.create()


@pytest.fixture
def member():
    return MemberFactory.create()


def _url(member_id, state):
    return STATE_URL.format(member_id=member_id, state=state)


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------


def test_unauthenticated_cannot_change_state(api_client, member):
    response = api_client.post(
        _url(member.id, "inactive"), {"justification": "test"}, format="json"
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_non_admin_cannot_change_state(api_client, member):
    other = MemberFactory.create()
    api_client.force_authenticate(user=other)
    response = api_client.post(
        _url(member.id, "inactive"), {"justification": "test"}, format="json"
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _suppress_side_effects():
    """Suppress email, SMS, and access-sync calls for all tests in this module."""
    with (
        patch("profile.models.sms.SMS"),
        patch("profile.models.Profile.sync_access"),
        patch("profile.models.User.email_disable_member"),
        patch("profile.models.User.email_enable_member"),
    ):
        yield


def test_deactivate_sets_state_inactive(api_client, admin, member):
    member.profile.state = "active"
    member.profile.save()

    api_client.force_authenticate(user=admin)
    response = api_client.post(
        _url(member.id, "inactive"), {"justification": "Non-payment"}, format="json"
    )

    assert response.status_code == status.HTTP_200_OK
    member.profile.refresh_from_db()
    assert member.profile.state == "inactive"


def test_activate_sets_state_active(api_client, admin, member):
    member.profile.state = "inactive"
    member.profile.save()

    api_client.force_authenticate(user=admin)
    response = api_client.post(
        _url(member.id, "active"), {"justification": "Dues paid"}, format="json"
    )

    assert response.status_code == status.HTTP_200_OK
    member.profile.refresh_from_db()
    assert member.profile.state == "active"


def test_invalid_state_returns_400(api_client, admin, member):
    api_client.force_authenticate(user=admin)
    response = api_client.post(
        _url(member.id, "bogus"), {"justification": "test"}, format="json"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# Justification stored in logs
# ---------------------------------------------------------------------------


def test_deactivate_stores_justification_in_logs(api_client, admin, member):
    member.profile.state = "active"
    member.profile.save()

    api_client.force_authenticate(user=admin)
    api_client.post(
        _url(member.id, "inactive"),
        {"justification": "Membership lapsed"},
        format="json",
    )

    # Both the admin's log and the member's log should carry the justification.
    admin_log = UserEventLog.objects.filter(user=admin, logtype="admin").latest("date")
    member_log = UserEventLog.objects.filter(user=member, logtype="admin").latest(
        "date"
    )

    assert "Membership lapsed" in admin_log.description
    assert "Membership lapsed" in member_log.description


def test_activate_stores_justification_in_logs(api_client, admin, member):
    member.profile.state = "inactive"
    member.profile.save()

    api_client.force_authenticate(user=admin)
    api_client.post(
        _url(member.id, "active"), {"justification": "Dues now settled"}, format="json"
    )

    admin_log = UserEventLog.objects.filter(user=admin, logtype="admin").latest("date")
    member_log = UserEventLog.objects.filter(user=member, logtype="admin").latest(
        "date"
    )

    assert "Dues now settled" in admin_log.description
    assert "Dues now settled" in member_log.description


def test_no_justification_omits_suffix(api_client, admin, member):
    member.profile.state = "active"
    member.profile.save()

    api_client.force_authenticate(user=admin)
    api_client.post(_url(member.id, "inactive"), {}, format="json")

    member_log = UserEventLog.objects.filter(user=member, logtype="admin").latest(
        "date"
    )
    assert "Justification" not in member_log.description


# ---------------------------------------------------------------------------
# Notification failures must not block state changes
# ---------------------------------------------------------------------------


def test_deactivate_succeeds_when_email_raises(api_client, admin, member):
    """State change must complete even if the notification email throws."""
    member.profile.state = "active"
    member.profile.save()

    with patch(
        "profile.models.User.email_disable_member", side_effect=Exception("SMTP down")
    ):
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            _url(member.id, "inactive"), {"justification": "Test"}, format="json"
        )

    assert response.status_code == status.HTTP_200_OK
    member.profile.refresh_from_db()
    assert member.profile.state == "inactive"


def test_activate_succeeds_when_email_raises(api_client, admin, member):
    """State change must complete even if the notification email throws."""
    member.profile.state = "inactive"
    member.profile.save()

    with patch(
        "profile.models.User.email_enable_member", side_effect=Exception("SMTP down")
    ):
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            _url(member.id, "active"), {"justification": "Test"}, format="json"
        )

    assert response.status_code == status.HTTP_200_OK
    member.profile.refresh_from_db()
    assert member.profile.state == "active"
