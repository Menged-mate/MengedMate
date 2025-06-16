from django.contrib import admin
from .models import Transaction, Wallet, WalletTransaction, QRPaymentSession, SimpleChargingSession


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['reference_number', 'user', 'transaction_type', 'status', 'amount', 'currency', 'created_at']
    list_filter = ['transaction_type', 'status', 'currency', 'created_at']
    search_fields = ['reference_number', 'external_reference', 'user__email', 'phone_number']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance', 'currency', 'is_active', 'created_at']
    list_filter = ['currency', 'is_active', 'created_at']
    search_fields = ['user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ['wallet', 'transaction_type', 'amount', 'balance_before', 'balance_after', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['wallet__user__email', 'transaction__reference_number']
    readonly_fields = ['id', 'created_at']


@admin.register(QRPaymentSession)
class QRPaymentSessionAdmin(admin.ModelAdmin):
    list_display = ['session_token', 'user', 'connector', 'payment_type', 'calculated_amount', 'status', 'created_at']
    list_filter = ['payment_type', 'status', 'created_at']
    search_fields = ['session_token', 'user__email', 'phone_number', 'connector__name']
    readonly_fields = ['id', 'session_token', 'calculated_amount', 'created_at', 'updated_at']


@admin.register(SimpleChargingSession)
class SimpleChargingSessionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'user', 'connector', 'status', 'energy_delivered_kwh', 'start_time', 'stop_time']
    list_filter = ['status', 'created_at']
    search_fields = ['transaction_id', 'user__email', 'connector__name']
    readonly_fields = ['id', 'transaction_id', 'created_at', 'updated_at']
