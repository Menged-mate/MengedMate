from rest_framework import serializers
from decimal import Decimal
from .models import PaymentMethod, Transaction, Wallet, WalletTransaction, PaymentSession, QRPaymentSession, SimpleChargingSession
from charging_stations.models import ChargingConnector


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
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('1.00'))
    phone_number = serializers.CharField(max_length=15)
    description = serializers.CharField(max_length=255, required=False, default="MengedMate Payment")

    def validate_phone_number(self, value):
        cleaned_value = ''.join(filter(str.isdigit, value.replace('+', '')))

        if value.startswith('09') or value.startswith('+2519') or value.startswith('2519'):
            if value.startswith('09'):
                value = '+251' + value[1:]
            elif value.startswith('251'):
                value = '+' + value
            elif not value.startswith('+251'):
                value = '+251' + value[4:] if value.startswith('2519') else value
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
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('1.00'))
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


class QRConnectorInfoSerializer(serializers.ModelSerializer):
    station_name = serializers.CharField(source='station.name', read_only=True)
    station_address = serializers.CharField(source='station.address', read_only=True)
    connector_type_display = serializers.CharField(source='get_connector_type_display', read_only=True)
    qr_code_url = serializers.SerializerMethodField()

    class Meta:
        model = ChargingConnector
        fields = [
            'id', 'station_name', 'station_address', 'connector_type',
            'connector_type_display', 'power_kw', 'price_per_kwh',
            'available_quantity', 'qr_code_url'
        ]

    def get_qr_code_url(self, obj):
        return obj.get_qr_code_url()


class QRPaymentInitiateSerializer(serializers.Serializer):
    payment_type = serializers.ChoiceField(choices=QRPaymentSession.PaymentType.choices)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    kwh_requested = serializers.DecimalField(max_digits=8, decimal_places=3, required=False)
    phone_number = serializers.CharField(max_length=15)

    def validate(self, data):
        payment_type = data.get('payment_type')
        amount = data.get('amount')
        kwh_requested = data.get('kwh_requested')

        if payment_type == 'amount' and not amount:
            raise serializers.ValidationError("Amount is required for amount-based payment")

        if payment_type == 'kwh' and not kwh_requested:
            raise serializers.ValidationError("kWh is required for kWh-based payment")

        if payment_type == 'amount' and amount and amount <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")

        if payment_type == 'kwh' and kwh_requested and kwh_requested <= 0:
            raise serializers.ValidationError("kWh must be greater than 0")

        return data

    def validate_phone_number(self, value):
        # Remove any spaces or special characters
        cleaned_value = ''.join(filter(str.isdigit, value.replace('+', '')))

        # Check if it's a valid Ethiopian number
        if cleaned_value.startswith('251'):
            # Already has country code
            if len(cleaned_value) != 12:  # 251 + 9 digits
                raise serializers.ValidationError("Invalid Ethiopian phone number length")
            return '+' + cleaned_value
        elif cleaned_value.startswith('9') and len(cleaned_value) == 9:
            # Local format (9xxxxxxxx)
            return '+251' + cleaned_value
        elif cleaned_value.startswith('09') and len(cleaned_value) == 10:
            # Local format with leading 0 (09xxxxxxxx)
            return '+251' + cleaned_value[1:]
        else:
            raise serializers.ValidationError("Phone number must be a valid Ethiopian number (09xxxxxxxx or +251xxxxxxxxx)")


class QRPaymentSessionSerializer(serializers.ModelSerializer):
    connector_info = QRConnectorInfoSerializer(source='connector', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_amount = serializers.SerializerMethodField()

    class Meta:
        model = QRPaymentSession
        fields = [
            'id', 'session_token', 'payment_type', 'payment_type_display',
            'amount', 'kwh_requested', 'calculated_amount', 'payment_amount',
            'phone_number', 'status', 'status_display', 'connector_info',
            'expires_at', 'created_at', 'updated_at'
        ]

    def get_payment_amount(self, obj):
        return obj.get_payment_amount()


class SimpleChargingSessionSerializer(serializers.ModelSerializer):
    duration_minutes = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = SimpleChargingSession
        fields = [
            'id', 'transaction_id', 'status', 'status_display',
            'start_time', 'stop_time', 'duration_seconds', 'duration_minutes',
            'estimated_duration_minutes', 'energy_delivered_kwh', 'energy_consumed_kwh',
            'max_power_kw', 'cost_per_kwh', 'created_at', 'updated_at'
        ]

    def get_duration_minutes(self, obj):
        if obj.duration_seconds:
            return round(obj.duration_seconds / 60, 1)
        return 0


class QRPaymentSessionWithChargingSerializer(serializers.ModelSerializer):
    """Extended serializer that includes charging session data for history"""
    connector_info = QRConnectorInfoSerializer(source='connector', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_amount = serializers.SerializerMethodField()
    connector_station_name = serializers.CharField(read_only=True)
    charging_session_info = SimpleChargingSessionSerializer(source='simple_charging_session', read_only=True)

    class Meta:
        model = QRPaymentSession
        fields = [
            'id', 'session_token', 'payment_type', 'payment_type_display',
            'amount', 'kwh_requested', 'calculated_amount', 'payment_amount',
            'phone_number', 'status', 'status_display', 'connector_info',
            'connector_station_name', 'charging_session_info',
            'expires_at', 'created_at', 'updated_at'
        ]

    def get_payment_amount(self, obj):
        return obj.get_payment_amount()
