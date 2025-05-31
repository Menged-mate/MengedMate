from django.contrib import admin
from .models import OCPPStation, OCPPConnector, ChargingSession, SessionMeterValue, OCPPLog


@admin.register(OCPPStation)
class OCPPStationAdmin(admin.ModelAdmin):
    list_display = ['station_id', 'charging_station', 'vendor', 'model', 'status', 'is_online', 'last_heartbeat', 'created_at']
    list_filter = ['status', 'is_online', 'vendor', 'created_at']
    search_fields = ['station_id', 'charging_station__name', 'vendor', 'model']
    readonly_fields = ['id', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('station_id', 'charging_station', 'vendor', 'model', 'firmware_version')
        }),
        ('Status', {
            'fields': ('status', 'is_online', 'last_heartbeat')
        }),
        ('OCPP Configuration', {
            'fields': ('ocpp_websocket_url',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(OCPPConnector)
class OCPPConnectorAdmin(admin.ModelAdmin):
    list_display = ['connector_id', 'ocpp_station', 'charging_connector', 'status', 'error_code', 'created_at']
    list_filter = ['status', 'ocpp_station__status', 'created_at']
    search_fields = ['ocpp_station__station_id', 'connector_id', 'error_code']
    readonly_fields = ['id', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('ocpp_station', 'connector_id', 'charging_connector')
        }),
        ('Status', {
            'fields': ('status', 'error_code', 'info')
        }),
        ('Vendor Information', {
            'fields': ('vendor_id', 'vendor_error_code'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(ChargingSession)
class ChargingSessionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'user', 'ocpp_station', 'status', 'payment_status', 'energy_consumed_kwh', 'estimated_cost', 'start_time']
    list_filter = ['status', 'payment_status', 'payment_method', 'created_at']
    search_fields = ['transaction_id', 'user__email', 'ocpp_station__station_id', 'payment_transaction_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'start_time'

    fieldsets = (
        ('Session Information', {
            'fields': ('transaction_id', 'user', 'ocpp_station', 'ocpp_connector', 'id_tag')
        }),
        ('Payment', {
            'fields': ('payment_transaction_id', 'payment_method', 'payment_status')
        }),
        ('Status & Timing', {
            'fields': ('status', 'start_time', 'stop_time', 'duration_seconds', 'stop_reason')
        }),
        ('Energy & Power', {
            'fields': ('energy_consumed_kwh', 'current_power_kw', 'max_power_kw')
        }),
        ('Costs', {
            'fields': ('estimated_cost', 'final_cost')
        }),
        ('Meter Readings', {
            'fields': ('meter_start', 'meter_stop'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(SessionMeterValue)
class SessionMeterValueAdmin(admin.ModelAdmin):
    list_display = ['charging_session', 'measurand', 'value', 'unit', 'timestamp']
    list_filter = ['measurand', 'unit', 'context', 'location', 'timestamp']
    search_fields = ['charging_session__transaction_id', 'measurand']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'timestamp'

    fieldsets = (
        ('Session', {
            'fields': ('charging_session',)
        }),
        ('Measurement', {
            'fields': ('timestamp', 'measurand', 'value', 'unit')
        }),
        ('Context', {
            'fields': ('context', 'location'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )


@admin.register(OCPPLog)
class OCPPLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'level', 'ocpp_station', 'charging_session', 'action', 'message_type', 'message']
    list_filter = ['level', 'message_type', 'timestamp']
    search_fields = ['ocpp_station__station_id', 'charging_session__transaction_id', 'action', 'message']
    readonly_fields = ['id', 'timestamp']
    date_hierarchy = 'timestamp'

    fieldsets = (
        ('Log Information', {
            'fields': ('level', 'message_type', 'action', 'message')
        }),
        ('Related Objects', {
            'fields': ('ocpp_station', 'charging_session')
        }),
        ('Raw Data', {
            'fields': ('raw_data',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        })
    )
