from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_prometheus.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("profile", "0017_alter_log_logtype"),
        ("access", "0020_accesscontrolleddevice_post_to_slack"),
    ]

    operations = [
        migrations.CreateModel(
            name="InterlockAccessGrant",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("granted_date", models.DateTimeField(auto_now_add=True)),
                (
                    "granted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="interlock_grants_given",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "interlock",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="access_grants",
                        to="access.interlock",
                    ),
                ),
                (
                    "profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="interlock_grants",
                        to="profile.profile",
                    ),
                ),
            ],
            options={
                "unique_together": {("profile", "interlock")},
            },
            bases=(
                django_prometheus.models.ExportModelOperationsMixin(
                    "interlock-access-grant"
                ),
                models.Model,
            ),
        ),
    ]
