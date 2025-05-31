from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import uuid


class OCPPStation(models.Model):
    class StationStatus(models.TextChoices):
        AVAILABLE = 'available', _('Available')
        OCCUPIED = 'occupied', _('Occupied')
        UNAVAILABLE = 'unavailable', _('Unavailable')
        FAULTED = 'faulted', _('Faulted')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    station_id = models.CharField(max_length=100, unique=True)
    charging_station = models.OneToOneField(
        'charging_stations.ChargingStation',
        on_delete=models.CASCADE,
        related_name='ocpp_station'
    )

    vendor = models.CharField(max_length=100, blank=True, null=True)
    model = models.CharField(max_length=100, blank=True, null=True)
    firmware_version = models.CharField(max_length=50, blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=StationStatus.choices,
        default=StationStatus.AVAILABLE
    )

    ocpp_websocket_url = models.URLField(blank=True, null=True)
    last_heartbeat = models.DateTimeField(blank=True, null=True)
    is_online = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"OCPP Station {self.station_id}"

    class Meta:
        verbose_name = "OCPP Station"
        verbose_name_plural = "OCPP Stations"


class OCPPConnector(models.Model):
    class ConnectorStatus(models.TextChoices):
        AVAILABLE = 'available', _('Available')
        PREPARING = 'preparing', _('Preparing')
        CHARGING = 'charging', _('Charging')
        SUSPENDED_EVSE = 'suspended_evse', _('Suspended EVSE')
        SUSPENDED_EV = 'suspended_ev', _('Suspended EV')
        FINISHING = 'finishing', _('Finishing')
        RESERVED = 'reserved', _('Reserved')
        UNAVAILABLE = 'unavailable', _('Unavailable')
        FAULTED = 'faulted', _('Faulted')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ocpp_station = models.ForeignKey(OCPPStation, on_delete=models.CASCADE, related_name='ocpp_connectors')
    connector_id = models.PositiveIntegerField()
    charging_connector = models.OneToOneField(
        'charging_stations.ChargingConnector',
        on_delete=models.CASCADE,
        related_name='ocpp_connector',
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=ConnectorStatus.choices,
        default=ConnectorStatus.AVAILABLE
    )

    error_code = models.CharField(max_length=50, blank=True, null=True)
    info = models.TextField(blank=True, null=True)
    vendor_id = models.CharField(max_length=255, blank=True, null=True)
    vendor_error_code = models.CharField(max_length=50, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Connector {self.connector_id} - {self.ocpp_station.station_id}"

    class Meta:
        unique_together = ['ocpp_station', 'connector_id']
        verbose_name = "OCPP Connector"
        verbose_name_plural = "OCPP Connectors"


class ChargingSession(models.Model):
    class SessionStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        STARTED = 'started', _('Started')
        CHARGING = 'charging', _('Charging')
        SUSPENDED = 'suspended', _('Suspended')
        STOPPING = 'stopping', _('Stopping')
        STOPPED = 'stopped', _('Stopped')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')

    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        AUTHORIZED = 'authorized', _('Authorized')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        REFUNDED = 'refunded', _('Refunded')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction_id = models.PositiveIntegerField(unique=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='charging_sessions')
    ocpp_station = models.ForeignKey(OCPPStation, on_delete=models.CASCADE, related_name='charging_sessions')
    ocpp_connector = models.ForeignKey(OCPPConnector, on_delete=models.CASCADE, related_name='charging_sessions')

    payment_transaction_id = models.CharField(max_length=255, blank=True, null=True)
    payment_method = models.CharField(max_length=50, default='qr_code')

    id_tag = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=SessionStatus.choices,
        default=SessionStatus.PENDING
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )

    start_time = models.DateTimeField(blank=True, null=True)
    stop_time = models.DateTimeField(blank=True, null=True)
    duration_seconds = models.PositiveIntegerField(default=0)

    energy_consumed_kwh = models.DecimalField(max_digits=10, decimal_places=3, default=0.000)
    current_power_kw = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    max_power_kw = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)

    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    final_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    stop_reason = models.CharField(max_length=100, blank=True, null=True)
    meter_start = models.PositiveIntegerField(default=0)
    meter_stop = models.PositiveIntegerField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Session {self.transaction_id} - {self.user.email}"

    class Meta:
        verbose_name = "Charging Session"
        verbose_name_plural = "Charging Sessions"
        ordering = ['-created_at']


class SessionMeterValue(models.Model):
    class MeasurandType(models.TextChoices):
        ENERGY_ACTIVE_IMPORT_REGISTER = 'energy_active_import_register', _('Energy Active Import Register')
        ENERGY_REACTIVE_IMPORT_REGISTER = 'energy_reactive_import_register', _('Energy Reactive Import Register')
        POWER_ACTIVE_IMPORT = 'power_active_import', _('Power Active Import')
        CURRENT_IMPORT = 'current_import', _('Current Import')
        VOLTAGE = 'voltage', _('Voltage')
        TEMPERATURE = 'temperature', _('Temperature')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    charging_session = models.ForeignKey(ChargingSession, on_delete=models.CASCADE, related_name='meter_values')

    timestamp = models.DateTimeField()
    measurand = models.CharField(max_length=50, choices=MeasurandType.choices)
    value = models.DecimalField(max_digits=15, decimal_places=3)
    unit = models.CharField(max_length=20, blank=True, null=True)
    context = models.CharField(max_length=50, blank=True, null=True)
    location = models.CharField(max_length=50, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.measurand}: {self.value} {self.unit}"

    class Meta:
        verbose_name = "Session Meter Value"
        verbose_name_plural = "Session Meter Values"
        ordering = ['-timestamp']


class OCPPLog(models.Model):
    class LogLevel(models.TextChoices):
        DEBUG = 'debug', _('Debug')
        INFO = 'info', _('Info')
        WARNING = 'warning', _('Warning')
        ERROR = 'error', _('Error')

    class MessageType(models.TextChoices):
        CALL = 'call', _('Call')
        CALL_RESULT = 'call_result', _('Call Result')
        CALL_ERROR = 'call_error', _('Call Error')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ocpp_station = models.ForeignKey(OCPPStation, on_delete=models.CASCADE, related_name='logs', blank=True, null=True)
    charging_session = models.ForeignKey(ChargingSession, on_delete=models.CASCADE, related_name='logs', blank=True, null=True)

    level = models.CharField(max_length=10, choices=LogLevel.choices, default=LogLevel.INFO)
    message_type = models.CharField(max_length=20, choices=MessageType.choices, blank=True, null=True)
    action = models.CharField(max_length=100, blank=True, null=True)
    message = models.TextField()
    raw_data = models.JSONField(blank=True, null=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.level.upper()}: {self.action or 'General'} - {self.timestamp}"

    class Meta:
        verbose_name = "OCPP Log"
        verbose_name_plural = "OCPP Logs"
        ordering = ['-timestamp']
