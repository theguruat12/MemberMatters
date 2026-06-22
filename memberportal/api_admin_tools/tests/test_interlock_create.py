import pytest
from rest_framework import status

from access.models import Interlock

from .factories import AdminFactory, MemberFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin():
    return AdminFactory.create(email="admin@test.com")


@pytest.fixture
def regular_user():
    return MemberFactory.create(email="member@test.com")


def test_create_interlock_succeeds(api_client, admin):
    api_client.force_authenticate(user=admin)
    response = api_client.post(
        "/api/admin/interlocks/",
        {
            "name": "Laser Cutter",
            "description": "Main workshop",
            "ipAddress": "192.168.1.10",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert "id" in response.data
    assert Interlock.objects.filter(name="Laser Cutter").exists()


def test_create_interlock_without_description_succeeds(api_client, admin):
    api_client.force_authenticate(user=admin)
    response = api_client.post(
        "/api/admin/interlocks/",
        {"name": "3D Printer"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    interlock = Interlock.objects.get(id=response.data["id"])
    assert interlock.description == ""


def test_create_interlock_without_ip_succeeds(api_client, admin):
    api_client.force_authenticate(user=admin)
    response = api_client.post(
        "/api/admin/interlocks/",
        {"name": "Welder", "description": "Welding bay"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    interlock = Interlock.objects.get(id=response.data["id"])
    assert interlock.ip_address is None


def test_create_interlock_missing_name_returns_400(api_client, admin):
    api_client.force_authenticate(user=admin)
    response = api_client.post(
        "/api/admin/interlocks/",
        {"description": "No name provided"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "error" in response.data


def test_create_interlock_blank_name_returns_400(api_client, admin):
    api_client.force_authenticate(user=admin)
    response = api_client.post(
        "/api/admin/interlocks/",
        {"name": "   "},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_create_interlock_unauthenticated_returns_401(api_client):
    response = api_client.post(
        "/api/admin/interlocks/",
        {"name": "Unauthorised"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_interlock_non_admin_returns_403(api_client, regular_user):
    api_client.force_authenticate(user=regular_user)
    response = api_client.post(
        "/api/admin/interlocks/",
        {"name": "Not allowed"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_admin_interlocks_list_includes_created_interlock(api_client, admin):
    Interlock.objects.create(name="Listed Tool", description="")
    api_client.force_authenticate(user=admin)
    response = api_client.get("/api/admin/interlocks/")
    assert response.status_code == status.HTTP_200_OK
    # Response is a generator rendered via map(); parse the rendered JSON instead
    names = [i["name"] for i in response.json()]
    assert "Listed Tool" in names
