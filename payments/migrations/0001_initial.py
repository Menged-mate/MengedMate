# Generated by Django 4.2.21 on 2025-05-29 03:36

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentMethod',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('method_type', models.CharField(choices=[('mpesa', 'M-Pesa'), ('telebirr', 'TeleBirr'), ('bank_transfer', 'Bank Transfer'), ('credit_card', 'Credit Card')], max_length=20)),
                ('phone_number', models.CharField(blank=True, max_length=15, null=True)),
                ('account_name', models.CharField(blank=True, max_length=100, null=True)),
                ('account_number', models.CharField(blank=True, max_length=50, null=True)),
                ('is_default', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_methods', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('transaction_type', models.CharField(choices=[('payment', 'Payment'), ('refund', 'Refund'), ('withdrawal', 'Withdrawal'), ('deposit', 'Deposit')], max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed'), ('cancelled', 'Cancelled'), ('refunded', 'Refunded')], default='pending', max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('currency', models.CharField(default='ETB', max_length=3)),
                ('description', models.TextField(blank=True, null=True)),
                ('reference_number', models.CharField(max_length=100, unique=True)),
                ('external_reference', models.CharField(blank=True, max_length=100, null=True)),
                ('phone_number', models.CharField(blank=True, max_length=15, null=True)),
                ('provider_response', models.JSONField(blank=True, null=True)),
                ('callback_data', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('payment_method', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='payments.paymentmethod')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Wallet',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('balance', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('currency', models.CharField(default='ETB', max_length=3)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='wallet', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='WalletTransaction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('transaction_type', models.CharField(choices=[('credit', 'Credit'), ('debit', 'Debit')], max_length=10)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('balance_before', models.DecimalField(decimal_places=2, max_digits=10)),
                ('balance_after', models.DecimalField(decimal_places=2, max_digits=10)),
                ('description', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('transaction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wallet_transactions', to='payments.transaction')),
                ('wallet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wallet_transactions', to='payments.wallet')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PaymentSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('session_id', models.CharField(max_length=100, unique=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('currency', models.CharField(default='ETB', max_length=3)),
                ('phone_number', models.CharField(max_length=15)),
                ('status', models.CharField(choices=[('active', 'Active'), ('completed', 'Completed'), ('expired', 'Expired'), ('cancelled', 'Cancelled')], default='active', max_length=20)),
                ('checkout_request_id', models.CharField(blank=True, max_length=100, null=True)),
                ('merchant_request_id', models.CharField(blank=True, max_length=100, null=True)),
                ('expires_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_sessions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
