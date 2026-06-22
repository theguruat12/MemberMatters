import factory
from django.contrib.auth import get_user_model

from access.models import Interlock, InterlockAccessGrant
from profile.models import Profile

User = get_user_model()


class _UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@test.com")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "pw")
        user = model_class.objects.create_user(password=password, **kwargs)
        return user


class AdminFactory(_UserFactory):
    email = factory.Sequence(lambda n: f"admin{n}@test.com")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        user = super()._create(model_class, *args, **kwargs)
        user.staff = True
        user.save()
        Profile.objects.create(
            user=user,
            screen_name="Admin",
            first_name="Test",
            last_name="Admin",
        )
        return user


class MemberFactory(_UserFactory):
    email = factory.Sequence(lambda n: f"member{n}@test.com")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        user = super()._create(model_class, *args, **kwargs)
        Profile.objects.create(
            user=user,
            screen_name="Test",
            first_name="Test",
            last_name="Member",
        )
        return user


class InterlockFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Interlock

    name = "Laser Cutter"
    description = ""


class InterlockAccessGrantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InterlockAccessGrant

    role = factory.LazyAttribute(lambda _: InterlockAccessGrant.ROLE_USER)
