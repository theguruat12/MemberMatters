import pytest
from rest_framework import status

from access.models import InterlockAccessGrant

from .factories import AdminFactory, InterlockFactory, MemberFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin():
    return AdminFactory.create(email="csvadmin@test.com")


@pytest.fixture
def trainer():
    return MemberFactory.create(email="csvtrainer@test.com")


@pytest.fixture
def user():
    return MemberFactory.create(email="csvuser@test.com")


@pytest.fixture
def interlock():
    return InterlockFactory.create(name="CSV Test Mill")


def test_csv_export_requires_admin(api_client, user, interlock):
    api_client.force_authenticate(user=user)
    response = api_client.get("/api/admin/interlocks/export-csv/")
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_csv_export_unauthenticated_returns_401(api_client, interlock):
    response = api_client.get("/api/admin/interlocks/export-csv/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_csv_export_returns_csv_content_type(api_client, admin):
    api_client.force_authenticate(user=admin)
    response = api_client.get("/api/admin/interlocks/export-csv/")
    assert response.status_code == status.HTTP_200_OK
    assert "text/csv" in response["Content-Type"]
    assert "interlock_access.csv" in response["Content-Disposition"]


def test_csv_export_contains_header_row(api_client, admin):
    api_client.force_authenticate(user=admin)
    response = api_client.get("/api/admin/interlocks/export-csv/")
    content = response.content.decode("utf-8")
    assert "Interlock" in content
    assert "Member Name" in content
    assert "Role" in content
    assert "Granted By" in content


def test_csv_export_includes_grant_rows(api_client, admin, trainer, user, interlock):
    InterlockAccessGrant.objects.create(
        profile=trainer.profile,
        interlock=interlock,
        role=InterlockAccessGrant.ROLE_TRAINER,
        granted_by=admin,
    )
    InterlockAccessGrant.objects.create(
        profile=user.profile,
        interlock=interlock,
        role=InterlockAccessGrant.ROLE_USER,
        granted_by=trainer,
    )
    api_client.force_authenticate(user=admin)
    response = api_client.get("/api/admin/interlocks/export-csv/")
    content = response.content.decode("utf-8")
    assert "CSV Test Mill" in content
    assert "trainer" in content
    assert "user" in content
    assert trainer.profile.get_full_name() in content
    assert user.profile.get_full_name() in content


def test_csv_export_empty_when_no_grants(api_client, admin):
    api_client.force_authenticate(user=admin)
    response = api_client.get("/api/admin/interlocks/export-csv/")
    assert response.status_code == status.HTTP_200_OK
    lines = response.content.decode("utf-8").strip().splitlines()
    assert len(lines) == 1
