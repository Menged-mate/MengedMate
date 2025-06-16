# Generated manually to remove social authentication components

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0001_initial"),
    ]

    operations = [
        migrations.DeleteModel(
            name="TelegramAuth",
        ),
    ]
