from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import OCPPStation, OCPPConnector, ChargingSession, SessionMeterValue, OCPPLog
from charging_stations.models import ChargingStation, ChargingConnector

User = get_user_model()


class OCPPStationSerializer(serializers.ModelSerializer):
    charging_station_name = serializers.CharField(source='charging_station.name', read_only=True)
    charging_station_address = serializers.CharField(source='charging_station.address', read_only=True)
    owner_name = serializers.CharField(source='charging_station.owner.company_name', read_only=True)
    
    class Meta:
        model = OCPPStation
        fields = [
            'id', 'station_id', 'charging_station', 'charging_station_name', 
            'charging_station_address', 'owner_name', 'vendor', 'model', 
            'firmware_version', 'status', 'ocpp_websocket_url', 'last_heartbeat', 
            'is_online', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class OCPPConnectorSerializer(serializers.ModelSerializer):
    charging_connector_type = serializers.CharField(source='charging_connector.connector_type', read_only=True)
    charging_connector_power = serializers.DecimalField(source='charging_connector.power_kw', max_digits=6, decimal_places=2, read_only=True)
    
    class Meta:
        model = OCPPConnector
        fields = [
            'id', 'connector_id', 'charging_connector', 'charging_connector_type',
            'charging_connector_power', 'status', 'error_code', 'info', 
            'vendor_id', 'vendor_error_code', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SessionMeterValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionMeterValue
        fields = [
            'id', 'timestamp', 'measurand', 'value', 'unit', 
            'context', 'location', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ChargingSessionSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    station_name = serializers.CharField(source='ocpp_station.charging_station.name', read_only=True)
    station_address = serializers.CharField(source='ocpp_station.charging_station.address', read_only=True)
    connector_type = serializers.CharField(source='ocpp_connector.charging_connector.connector_type', read_only=True)
    meter_values = SessionMeterValueSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChargingSession
        fields = [
            'id', 'transaction_id', 'user', 'user_email', 'user_name',
            'ocpp_station', 'ocpp_connector', 'station_name', 'station_address',
            'connector_type', 'payment_transaction_id', 'payment_method',
            'id_tag', 'status', 'payment_status', 'start_time', 'stop_time',
            'duration_seconds', 'energy_consumed_kwh', 'current_power_kw',
            'max_power_kw', 'estimated_cost', 'final_cost', 'stop_reason',
            'meter_start', 'meter_stop', 'meter_values', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email


class ChargingSessionDetailSerializer(ChargingSessionSerializer):
    ocpp_station = OCPPStationSerializer(read_only=True)
    ocpp_connector = OCPPConnectorSerializer(read_only=True)


class OCPPLogSerializer(serializers.ModelSerializer):
    station_id = serializers.CharField(source='ocpp_station.station_id', read_only=True)
    session_transaction_id = serializers.IntegerField(source='charging_session.transaction_id', read_only=True)
    
    class Meta:
        model = OCPPLog
        fields = [
            'id', 'station_id', 'session_transaction_id', 'level', 
            'message_type', 'action', 'message', 'raw_data', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class SyncStationSerializer(serializers.Serializer):
    charging_station_id = serializers.UUIDField()
    vendor = serializers.CharField(max_length=100, required=False, default="Generic")
    model = serializers.CharField(max_length=100, required=False, default="EV Charger")
    
    def validate_charging_station_id(self, value):
        try:
            charging_station = ChargingStation.objects.get(id=value)
            if not charging_station.is_active:
                raise serializers.ValidationError("Charging station is not active")
            return value
        except ChargingStation.DoesNotExist:
            raise serializers.ValidationError("Charging station not found")


class InitiateChargingSerializer(serializers.Serializer):
    station_id = serializers.CharField(max_length=100)
    connector_id = serializers.IntegerField()
    user_id = serializers.UUIDField()
    payment_transaction_id = serializers.CharField(max_length=255)
    payment_method = serializers.CharField(max_length=50, default='qr_code')
    owner_id = serializers.CharField(max_length=100, required=False)
    owner_name = serializers.CharField(max_length=255, required=False)
    
    def validate_station_id(self, value):
        try:
            OCPPStation.objects.get(station_id=value)
            return value
        except OCPPStation.DoesNotExist:
            raise serializers.ValidationError("OCPP station not found")
    
    def validate_user_id(self, value):
        try:
            User.objects.get(id=value)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")
    
    def validate(self, attrs):
        try:
            ocpp_station = OCPPStation.objects.get(station_id=attrs['station_id'])
            ocpp_connector = OCPPConnector.objects.get(
                ocpp_station=ocpp_station,
                connector_id=attrs['connector_id']
            )
            
            if ocpp_connector.status != OCPPConnector.ConnectorStatus.AVAILABLE:
                raise serializers.ValidationError(
                    f"Connector {attrs['connector_id']} is not available. Current status: {ocpp_connector.status}"
                )
                
        except OCPPConnector.DoesNotExist:
            raise serializers.ValidationError("Connector not found")
        
        return attrs


class StopChargingSerializer(serializers.Serializer):
    transaction_id = serializers.IntegerField()
    user_id = serializers.UUIDField(required=False)
    
    def validate_transaction_id(self, value):
        try:
            session = ChargingSession.objects.get(transaction_id=value)
            if session.status in [ChargingSession.SessionStatus.STOPPED, ChargingSession.SessionStatus.COMPLETED]:
                raise serializers.ValidationError("Charging session is already stopped")
            return value
        except ChargingSession.DoesNotExist:
            raise serializers.ValidationError("Charging session not found")


class SessionStatusSerializer(serializers.Serializer):
    transaction_id = serializers.IntegerField()
    
    def validate_transaction_id(self, value):
        try:
            ChargingSession.objects.get(transaction_id=value)
            return value
        except ChargingSession.DoesNotExist:
            raise serializers.ValidationError("Charging session not found")


class WebhookDataSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=50)
    station_id = serializers.CharField(max_length=100, required=False)
    transaction_id = serializers.IntegerField(required=False)
    data = serializers.JSONField()
    timestamp = serializers.DateTimeField(required=False)


class StationStatusUpdateSerializer(serializers.Serializer):
    station_id = serializers.CharField(max_length=100)
    status = serializers.ChoiceField(choices=OCPPStation.StationStatus.choices)
    is_online = serializers.BooleanField(required=False)
    last_heartbeat = serializers.DateTimeField(required=False)


class ConnectorStatusUpdateSerializer(serializers.Serializer):
    station_id = serializers.CharField(max_length=100)
    connector_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=OCPPConnector.ConnectorStatus.choices)
    error_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    info = serializers.CharField(required=False, allow_blank=True)
    vendor_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    vendor_error_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
