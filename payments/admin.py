from django.contrib import admin
from .models import PaymentMethod, Transaction, Wallet, WalletTransaction, PaymentSession


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['user', 'method_type', 'phone_number', 'is_default', 'is_active', 'created_at']
    list_filter = ['method_type', 'is_default', 'is_active', 'created_at']
    search_fields = ['user__email', 'phone_number', 'account_name']
    readonly_fields = ['id', 'created_at', 'updated_at']


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


@admin.register(PaymentSession)
class PaymentSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'user', 'amount', 'phone_number', 'status', 'created_at']
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['session_id', 'user__email', 'phone_number', 'checkout_request_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
