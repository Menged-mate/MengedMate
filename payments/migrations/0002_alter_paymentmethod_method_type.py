# Generated by Django 4.2.21 on 2025-05-30 14:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentmethod',
            name='method_type',
            field=models.CharField(choices=[('chapa', 'Chapa'), ('telebirr', 'TeleBirr'), ('bank_transfer', 'Bank Transfer'), ('credit_card', 'Credit Card')], max_length=20),
        ),
    ]
