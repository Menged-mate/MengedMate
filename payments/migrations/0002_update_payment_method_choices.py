# Generated manually to update payment method choices from M-Pesa to Chapa

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentmethod',
            name='method_type',
            field=models.CharField(
                choices=[
                    ('chapa', 'Chapa'),
                    ('telebirr', 'TeleBirr'),
                    ('bank_transfer', 'Bank Transfer'),
                    ('credit_card', 'Credit Card')
                ],
                max_length=20
            ),
        ),
    ]
