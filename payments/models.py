from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import uuid


class PaymentMethod(models.Model):
    class MethodType(models.TextChoices):
        CHAPA = 'chapa', _('Chapa')
        TELEBIRR = 'telebirr', _('TeleBirr')
        BANK_TRANSFER = 'bank_transfer', _('Bank Transfer')
        CREDIT_CARD = 'credit_card', _('Credit Card')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payment_methods')
    method_type = models.CharField(max_length=20, choices=MethodType.choices)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    account_name = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.get_method_type_display()}"


class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        PAYMENT = 'payment', _('Payment')
        REFUND = 'refund', _('Refund')
        WITHDRAWAL = 'withdrawal', _('Withdrawal')
        DEPOSIT = 'deposit', _('Deposit')

    class TransactionStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        PROCESSING = 'processing', _('Processing')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        CANCELLED = 'cancelled', _('Cancelled')
        REFUNDED = 'refunded', _('Refunded')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, blank=True)
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    status = models.CharField(max_length=20, choices=TransactionStatus.choices, default=TransactionStatus.PENDING)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='ETB')
    description = models.TextField(blank=True, null=True)
    reference_number = models.CharField(max_length=100, unique=True)
    external_reference = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    provider_response = models.JSONField(blank=True, null=True)
    callback_data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference_number} - {self.amount} {self.currency}"


class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, default='ETB')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.balance} {self.currency}"


class WalletTransaction(models.Model):
    class TransactionType(models.TextChoices):
        CREDIT = 'credit', _('Credit')
        DEBIT = 'debit', _('Debit')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='wallet_transactions')
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='wallet_transactions')
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance_before = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.wallet.user.email} - {self.transaction_type} {self.amount}"


class PaymentSession(models.Model):
    class SessionStatus(models.TextChoices):
        ACTIVE = 'active', _('Active')
        COMPLETED = 'completed', _('Completed')
        EXPIRED = 'expired', _('Expired')
        CANCELLED = 'cancelled', _('Cancelled')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payment_sessions')
    session_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='ETB')
    phone_number = models.CharField(max_length=15)
    status = models.CharField(max_length=20, choices=SessionStatus.choices, default=SessionStatus.ACTIVE)
    checkout_request_id = models.CharField(max_length=100, blank=True, null=True)
    merchant_request_id = models.CharField(max_length=100, blank=True, null=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.session_id} - {self.amount} {self.currency}"


class QRPaymentSession(models.Model):
    class PaymentType(models.TextChoices):
        AMOUNT = 'amount', _('Fixed Amount')
        KWH = 'kwh', _('Kilowatt Hours')

    class SessionStatus(models.TextChoices):
        PENDING = 'pending', _('Pending Payment')
        PAYMENT_INITIATED = 'payment_initiated', _('Payment Initiated')
        PAYMENT_COMPLETED = 'payment_completed', _('Payment Completed')
        CHARGING_STARTED = 'charging_started', _('Charging Started')
        CHARGING_COMPLETED = 'charging_completed', _('Charging Completed')
        FAILED = 'failed', _('Failed')
        EXPIRED = 'expired', _('Expired')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='qr_payment_sessions')
    connector = models.ForeignKey('charging_stations.ChargingConnector', on_delete=models.CASCADE, related_name='qr_sessions')

    payment_type = models.CharField(max_length=10, choices=PaymentType.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    kwh_requested = models.DecimalField(max_digits=8, decimal_places=3, blank=True, null=True)
    calculated_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    phone_number = models.CharField(max_length=15)
    status = models.CharField(max_length=20, choices=SessionStatus.choices, default=SessionStatus.PENDING)

    # Payment tracking
    payment_transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True)
    charging_session = models.OneToOneField('ocpp_integration.ChargingSession', on_delete=models.SET_NULL, null=True, blank=True)

    # Session metadata
    session_token = models.CharField(max_length=100, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.session_token:
            self.session_token = str(uuid.uuid4())

        if self.payment_type == 'kwh' and self.kwh_requested and self.connector.price_per_kwh:
            self.calculated_amount = self.kwh_requested * self.connector.price_per_kwh
        elif self.payment_type == 'amount' and self.amount:
            self.calculated_amount = self.amount

        super().save(*args, **kwargs)

    def get_payment_amount(self):
        """Get the amount to be charged"""
        return self.calculated_amount or self.amount or 0

    def __str__(self):
        return f"QR Session {self.session_token} - {self.connector}"
