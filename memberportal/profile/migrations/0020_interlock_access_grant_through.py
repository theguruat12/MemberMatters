from django.db import migrations, models


def copy_interlock_access(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='profile_profile_interlocks'"
        )
        if cursor.fetchone():
            cursor.execute(
                "INSERT OR IGNORE INTO access_interlockaccessgrant (profile_id, interlock_id)"
                " SELECT profile_id, interlock_id FROM profile_profile_interlocks"
            )
            cursor.execute("DROP TABLE profile_profile_interlocks")


class Migration(migrations.Migration):

    dependencies = [
        ("profile", "0019_merge_0018_discord_handle_0018_emergency_contact"),
        ("access", "0021_interlock_access_grant"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="profile",
                    name="interlocks",
                    field=models.ManyToManyField(
                        blank=True,
                        through="access.InterlockAccessGrant",
                        to="access.Interlock",
                    ),
                ),
            ],
            database_operations=[
                migrations.RunPython(copy_interlock_access, migrations.RunPython.noop),
            ],
        ),
    ]
