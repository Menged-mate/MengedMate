from rest_framework import serializers
from .models import PaymentMethod, Transaction, Wallet, WalletTransaction, PaymentSession


class PaymentMethodSerializer(serializers.ModelSerializer):
    method_type_display = serializers.CharField(source='get_method_type_display', read_only=True)

    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'method_type', 'method_type_display', 'phone_number',
            'account_name', 'account_number', 'is_default', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user

        if validated_data.get('is_default'):
            PaymentMethod.objects.filter(user=user, is_default=True).update(is_default=False)

        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get('is_default'):
            PaymentMethod.objects.filter(
                user=instance.user,
                is_default=True
            ).exclude(id=instance.id).update(is_default=False)

        return super().update(instance, validated_data)


class TransactionSerializer(serializers.ModelSerializer):
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'user_email', 'transaction_type', 'transaction_type_display',
            'status', 'status_display', 'amount', 'currency', 'description',
            'reference_number', 'external_reference', 'phone_number',
            'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'user_email', 'reference_number', 'external_reference',
            'created_at', 'updated_at', 'completed_at'
        ]


class WalletSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Wallet
        fields = [
            'id', 'user_email', 'balance', 'currency', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user_email', 'balance', 'created_at', 'updated_at']


class WalletTransactionSerializer(serializers.ModelSerializer):
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    transaction_reference = serializers.CharField(source='transaction.reference_number', read_only=True)

    class Meta:
        model = WalletTransaction
        fields = [
            'id', 'transaction_type', 'transaction_type_display', 'amount',
            'balance_before', 'balance_after', 'description', 'transaction_reference',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PaymentSessionSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = PaymentSession
        fields = [
            'id', 'user_email', 'session_id', 'amount', 'currency',
            'phone_number', 'status', 'status_display', 'checkout_request_id',
            'merchant_request_id', 'expires_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user_email', 'session_id', 'checkout_request_id',
            'merchant_request_id', 'created_at', 'updated_at'
        ]


class InitiatePaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=1)
    phone_number = serializers.CharField(max_length=15)
    description = serializers.CharField(max_length=255, required=False, default="MengedMate Payment")

    def validate_phone_number(self, value):
        # Remove any spaces or special characters
        cleaned_value = ''.join(filter(str.isdigit, value.replace('+', '')))

        # Ethiopian number validation (primary)
        if value.startswith('09') or value.startswith('+2519') or value.startswith('2519'):
            if value.startswith('09'):
                value = '+251' + value[1:]
            elif value.startswith('251'):
                value = '+' + value
            elif not value.startswith('+251'):
                value = '+251' + value[4:] if value.startswith('2519') else value
        # Basic international format validation
        elif not value.startswith('+'):
            raise serializers.ValidationError("Phone number must be in international format (+country_code)")

        return value


class PaymentCallbackSerializer(serializers.Serializer):
    Body = serializers.DictField()

    def validate_Body(self, value):
        required_fields = ['stkCallback']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Missing required field: {field}")
        return value


class TransactionStatusSerializer(serializers.Serializer):
    tx_ref = serializers.CharField(max_length=100)


class WithdrawSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=1)
    phone_number = serializers.CharField(max_length=15)
    description = serializers.CharField(max_length=255, required=False, default="Withdrawal")

    def validate_phone_number(self, value):
        if not value.startswith('+251') and not value.startswith('251') and not value.startswith('09'):
            raise serializers.ValidationError("Phone number must be a valid Ethiopian number")

        if value.startswith('09'):
            value = '+251' + value[1:]
        elif value.startswith('251'):
            value = '+' + value
        elif not value.startswith('+251'):
            raise serializers.ValidationError("Invalid phone number format")

        return value

    def validate_amount(self, value):
        user = self.context['request'].user
        wallet = Wallet.objects.filter(user=user).first()

        if not wallet or wallet.balance < value:
            raise serializers.ValidationError("Insufficient wallet balance")

        return value
