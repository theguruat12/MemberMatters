from django.db import migrations, models


def copy_interlock_access(apps, schema_editor):
    # Copy rows from the old auto-generated M2M table into the explicit
    # through model, then drop the old table. Uses database-agnostic
    # introspection + the ORM so it works on both SQLite (dev) and
    # PostgreSQL (production) -- the original hand-written SQL relied on
    # SQLite-only constructs (sqlite_master, "INSERT OR IGNORE").
    old_table = "profile_profile_interlocks"
    connection = schema_editor.connection
    if old_table not in connection.introspection.table_names():
        return

    InterlockAccessGrant = apps.get_model("access", "InterlockAccessGrant")
    with connection.cursor() as cursor:
        cursor.execute("SELECT profile_id, interlock_id FROM %s" % old_table)
        rows = cursor.fetchall()

    # granted_date (auto_now_add) and role (default) are populated by the ORM.
    InterlockAccessGrant.objects.bulk_create(
        [
            InterlockAccessGrant(profile_id=profile_id, interlock_id=interlock_id)
            for profile_id, interlock_id in rows
        ],
        ignore_conflicts=True,
    )
    schema_editor.execute("DROP TABLE %s" % old_table)


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
