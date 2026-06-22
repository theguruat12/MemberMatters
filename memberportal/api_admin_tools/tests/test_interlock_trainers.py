import pytest

from access.models import InterlockAccessGrant

from .factories import AdminFactory, InterlockFactory, MemberFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin():
    return AdminFactory.create(email="roleadmin@test.com")


@pytest.fixture
def trainer():
    return MemberFactory.create(email="trainer@test.com")


@pytest.fixture
def regular():
    return MemberFactory.create(email="regular@test.com")


@pytest.fixture
def interlock():
    return InterlockFactory.create(name="Role Test Mill")


def _url(interlock_id, action, user_id):
    return f"/api/access/interlocks/{interlock_id}/{action}/{user_id}/"


def test_admin_can_assign_trainer(api_client, admin, trainer, interlock):
    api_client.force_authenticate(user=admin)
    response = api_client.put(_url(interlock.id, "assign-trainer", trainer.id))
    assert response.status_code == 200
    assert (
        InterlockAccessGrant.objects.get(
            profile=trainer.profile, interlock=interlock
        ).role
        == InterlockAccessGrant.ROLE_TRAINER
    )


def test_non_admin_cannot_assign_trainer(api_client, regular, trainer, interlock):
    api_client.force_authenticate(user=regular)
    response = api_client.put(_url(interlock.id, "assign-trainer", trainer.id))
    assert response.status_code == 403


def test_assign_trainer_to_existing_user_upgrades_role(
    api_client, admin, trainer, interlock
):
    InterlockAccessGrant.objects.create(
        profile=trainer.profile,
        interlock=interlock,
        role=InterlockAccessGrant.ROLE_USER,
    )
    api_client.force_authenticate(user=admin)
    api_client.put(_url(interlock.id, "assign-trainer", trainer.id))
    assert (
        InterlockAccessGrant.objects.get(
            profile=trainer.profile, interlock=interlock
        ).role
        == InterlockAccessGrant.ROLE_TRAINER
    )


def test_revoke_trainer_downgrades_to_user(api_client, admin, trainer, interlock):
    InterlockAccessGrant.objects.create(
        profile=trainer.profile,
        interlock=interlock,
        role=InterlockAccessGrant.ROLE_TRAINER,
    )
    api_client.force_authenticate(user=admin)
    response = api_client.put(_url(interlock.id, "revoke-trainer", trainer.id))
    assert response.status_code == 200
    assert (
        InterlockAccessGrant.objects.get(
            profile=trainer.profile, interlock=interlock
        ).role
        == InterlockAccessGrant.ROLE_USER
    )


def test_trainer_can_grant_user_access(api_client, trainer, regular, interlock):
    InterlockAccessGrant.objects.create(
        profile=trainer.profile,
        interlock=interlock,
        role=InterlockAccessGrant.ROLE_TRAINER,
    )
    api_client.force_authenticate(user=trainer)
    response = api_client.put(_url(interlock.id, "authorise", regular.id))
    assert response.status_code == 200
    assert InterlockAccessGrant.objects.filter(
        profile=regular.profile,
        interlock=interlock,
        role=InterlockAccessGrant.ROLE_USER,
    ).exists()


def test_non_trainer_cannot_grant_user_access(api_client, regular, trainer, interlock):
    api_client.force_authenticate(user=regular)
    response = api_client.put(_url(interlock.id, "authorise", trainer.id))
    assert response.status_code == 403


def test_trainer_can_revoke_user_access(api_client, trainer, regular, interlock):
    InterlockAccessGrant.objects.create(
        profile=trainer.profile,
        interlock=interlock,
        role=InterlockAccessGrant.ROLE_TRAINER,
    )
    InterlockAccessGrant.objects.create(
        profile=regular.profile,
        interlock=interlock,
        role=InterlockAccessGrant.ROLE_USER,
    )
    api_client.force_authenticate(user=trainer)
    response = api_client.put(_url(interlock.id, "revoke", regular.id))
    assert response.status_code == 200
    assert not InterlockAccessGrant.objects.filter(
        profile=regular.profile, interlock=interlock
    ).exists()


def test_trainer_cannot_revoke_another_trainer(api_client, trainer, interlock):
    trainer2 = MemberFactory.create(email="trainer2@test.com")
    InterlockAccessGrant.objects.create(
        profile=trainer.profile,
        interlock=interlock,
        role=InterlockAccessGrant.ROLE_TRAINER,
    )
    InterlockAccessGrant.objects.create(
        profile=trainer2.profile,
        interlock=interlock,
        role=InterlockAccessGrant.ROLE_TRAINER,
    )
    api_client.force_authenticate(user=trainer)
    response = api_client.put(_url(interlock.id, "revoke", trainer2.id))
    assert response.status_code == 403


def test_managed_interlocks_returns_trainer_interlocks(api_client, trainer, interlock):
    InterlockAccessGrant.objects.create(
        profile=trainer.profile,
        interlock=interlock,
        role=InterlockAccessGrant.ROLE_TRAINER,
    )
    api_client.force_authenticate(user=trainer)
    response = api_client.get("/api/access/interlocks/managed/")
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["id"] == interlock.id


def test_managed_interlocks_empty_for_non_trainer(api_client, regular):
    api_client.force_authenticate(user=regular)
    response = api_client.get("/api/access/interlocks/managed/")
    assert response.status_code == 200
    assert len(response.data) == 0


def test_member_search_accessible_to_trainer(api_client, trainer, interlock):
    InterlockAccessGrant.objects.create(
        profile=trainer.profile,
        interlock=interlock,
        role=InterlockAccessGrant.ROLE_TRAINER,
    )
    api_client.force_authenticate(user=trainer)
    response = api_client.get("/api/access/members/search/?q=Test")
    assert response.status_code == 200


def test_member_search_blocked_for_non_trainer(api_client, regular):
    api_client.force_authenticate(user=regular)
    response = api_client.get("/api/access/members/search/?q=Test")
    assert response.status_code == 403


def test_admin_interlock_list_includes_role_on_grant(
    api_client, admin, trainer, interlock
):
    InterlockAccessGrant.objects.create(
        profile=trainer.profile,
        interlock=interlock,
        role=InterlockAccessGrant.ROLE_TRAINER,
    )
    api_client.force_authenticate(user=admin)
    response = api_client.get("/api/admin/interlocks/")
    interlock_data = next(i for i in response.json() if i["id"] == interlock.id)
    member_entry = interlock_data["authorisedMembers"][0]
    assert member_entry["role"] == InterlockAccessGrant.ROLE_TRAINER


def test_revoke_no_op_when_grant_does_not_exist(api_client, admin, regular, interlock):
    api_client.force_authenticate(user=admin)
    response = api_client.put(
        f"/api/access/interlocks/{interlock.id}/revoke/{regular.id}/"
    )
    assert response.status_code == 200


def test_assign_interlock_trainer_rejects_unauthenticated(
    api_client, trainer, interlock
):
    response = api_client.put(_url(interlock.id, "assign-trainer", trainer.id))
    assert response.status_code == 401


def test_member_search_rejects_unauthenticated(api_client):
    r = api_client.get("/api/access/members/search/?q=Test")
    assert r.status_code == 401


def test_member_search_returns_empty_for_short_query(api_client, trainer, interlock):
    InterlockAccessGrant.objects.create(
        profile=trainer.profile,
        interlock=interlock,
        role=InterlockAccessGrant.ROLE_TRAINER,
    )
    api_client.force_authenticate(user=trainer)
    r = api_client.get("/api/access/members/search/?q=T")
    assert r.status_code == 200
    assert r.data == []
