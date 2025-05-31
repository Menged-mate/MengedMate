# OCPP Integration App

This Django app provides seamless integration between MengedMate EV charging station management platform and OCPP (Open Charge Point Protocol) simulation backends.

## Features

- **Station Synchronization**: Sync charging stations from MengedMate to OCPP simulation
- **Real-time Charging Sessions**: Initiate, monitor, and stop charging sessions
- **Webhook Support**: Receive real-time updates from OCPP simulation
- **Comprehensive Logging**: Track all OCPP communications and events
- **Admin Interface**: Manage OCPP stations, sessions, and logs through Django admin

## Models

### OCPPStation
Represents a charging station in the OCPP simulation system.

### OCPPConnector
Represents individual connectors within an OCPP station.

### ChargingSession
Tracks active and completed charging sessions with real-time data.

### SessionMeterValue
Stores meter readings and measurements during charging sessions.

### OCPPLog
Comprehensive logging of all OCPP communications and events.

## API Endpoints

### Station Management
- `GET /api/ocpp/stations/` - List OCPP stations
- `GET /api/ocpp/stations/{station_id}/` - Get station details
- `POST /api/ocpp/sync-station/` - Sync station to OCPP

### Charging Session Management
- `POST /api/ocpp/initiate-charging/` - Start charging session
- `POST /api/ocpp/stop-charging/` - Stop charging session
- `GET /api/ocpp/session-status/` - Get session status

### Session History
- `GET /api/ocpp/sessions/` - List charging sessions
- `GET /api/ocpp/sessions/{transaction_id}/` - Get session details

### Webhooks & Logs
- `POST /api/ocpp/webhook/` - Receive OCPP webhooks
- `GET /api/ocpp/logs/` - List OCPP logs

## Configuration

Add to your Django settings:

```python
OCPP_SETTINGS = {
    'BASE_URL': 'http://localhost:8000',
    'WEBSOCKET_URL': 'ws://localhost:8000/ws/ev-locator/',
    'WEBHOOK_URL': 'https://yourdomain.com/api/ocpp/webhook/',
    'API_KEY': 'your-ocpp-api-key',
    'TIMEOUT': 30,
    'RETRY_ATTEMPTS': 3,
}
```

## Usage Examples

### Sync a Station
```python
from ocpp_integration.services import OCPPIntegrationService
from charging_stations.models import ChargingStation

station = ChargingStation.objects.get(name='My Station')
ocpp_service = OCPPIntegrationService()
result = ocpp_service.sync_station_to_ocpp(station)
```

### Initiate Charging
```python
result = ocpp_service.initiate_charging(
    station_id='STATION_001',
    connector_id=1,
    user=user,
    payment_transaction_id='pay_123',
    owner_info={'owner_id': 'owner_1', 'owner_name': 'Station Owner'}
)
```

### Monitor Session
```python
result = ocpp_service.get_session_data(transaction_id=1001)
session = result['charging_session']
print(f"Energy consumed: {session.energy_consumed_kwh} kWh")
print(f"Current cost: ${session.estimated_cost}")
```

## Testing

### Management Command
```bash
# Create sample data
python manage.py test_ocpp_integration --create-sample-data

# Sync a station
python manage.py test_ocpp_integration --sync-station <station-id>

# Test complete flow
python manage.py test_ocpp_integration --test-charging
```

### Python Client
```python
from ocpp_integration.client import OCPPIntegrationClient

client = OCPPIntegrationClient(auth_token='your-token')
result = client.sync_station('station-uuid')
client.print_response(result)
```

## Webhook Events

The integration handles these webhook types:

- `session_started` - Charging session initiated
- `session_progress` - Real-time charging updates
- `session_stopped` - Charging session completed
- `availability_changed` - Connector availability changed
- `station_status` - Station status updated
- `connector_status` - Connector status updated

## Integration Flow

1. **Station Registration**: Station owner registers in MengedMate
2. **OCPP Sync**: Station data synced to OCPP simulation
3. **User Initiates Charging**: QR code scan triggers payment and charging
4. **Real-time Monitoring**: Live updates via webhooks or polling
5. **Session Completion**: Final billing and session summary

## Error Handling

The service includes comprehensive error handling:
- Automatic retries for failed requests
- Detailed logging of all operations
- Graceful degradation when OCPP simulation is unavailable
- Validation of all input parameters

## Security

- Token-based authentication for API endpoints
- Webhook signature validation (configurable)
- Rate limiting on sensitive endpoints
- Input validation and sanitization

## Monitoring

- Real-time logs in Django admin
- Session status tracking
- Station availability monitoring
- Performance metrics and error rates
