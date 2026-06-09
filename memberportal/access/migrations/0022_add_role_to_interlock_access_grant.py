from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("access", "0021_interlock_access_grant"),
    ]

    operations = [
        migrations.AddField(
            model_name="interlockaccessgrant",
            name="role",
            field=models.CharField(
                max_length=20,
                choices=[("user", "User"), ("trainer", "Trainer")],
                default="user",
            ),
        ),
    ]
