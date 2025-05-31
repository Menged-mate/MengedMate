import requests
import json
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from .models import OCPPStation, OCPPConnector, ChargingSession, SessionMeterValue, OCPPLog
from charging_stations.models import ChargingStation, ChargingConnector
from authentication.models import CustomUser

logger = logging.getLogger(__name__)


class OCPPIntegrationService:
    def __init__(self):
        self.config = settings.OCPP_SETTINGS
        self.base_url = self.config['BASE_URL']
        self.api_key = self.config.get('API_KEY')
        self.timeout = self.config.get('TIMEOUT', 30)
        self.retry_attempts = self.config.get('RETRY_ATTEMPTS', 3)

    def get_headers(self):
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers

    def make_request(self, method, endpoint, data=None, retries=None):
        if retries is None:
            retries = self.retry_attempts
        
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = self.get_headers()
        
        for attempt in range(retries + 1):
            try:
                if method.upper() == 'GET':
                    response = requests.get(url, headers=headers, timeout=self.timeout)
                elif method.upper() == 'POST':
                    response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
                elif method.upper() == 'PUT':
                    response = requests.put(url, json=data, headers=headers, timeout=self.timeout)
                elif method.upper() == 'DELETE':
                    response = requests.delete(url, headers=headers, timeout=self.timeout)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                return {'success': True, 'data': response.json()}
                
            except requests.exceptions.RequestException as e:
                logger.error(f"OCPP API request failed (attempt {attempt + 1}): {e}")
                if attempt == retries:
                    return {'success': False, 'error': str(e)}
                
        return {'success': False, 'error': 'Max retries exceeded'}

    def sync_station_to_ocpp(self, charging_station):
        try:
            with transaction.atomic():
                station_data = {
                    "station_id": f"STATION_{charging_station.id}",
                    "name": charging_station.name,
                    "latitude": float(charging_station.latitude) if charging_station.latitude else 0.0,
                    "longitude": float(charging_station.longitude) if charging_station.longitude else 0.0,
                    "address": charging_station.address,
                    "vendor": "Generic",
                    "model": "EV Charger",
                    "connectors": []
                }
                
                for connector in charging_station.connectors.all():
                    connector_data = {
                        "connector_id": connector.id,
                        "connector_type": connector.connector_type,
                        "max_power": float(connector.power_kw)
                    }
                    station_data["connectors"].append(connector_data)
                
                result = self.make_request('POST', '/api/locator/sync-station/', station_data)
                
                if result['success']:
                    response_data = result['data']
                    
                    ocpp_station, created = OCPPStation.objects.get_or_create(
                        charging_station=charging_station,
                        defaults={
                            'station_id': station_data["station_id"],
                            'vendor': station_data.get("vendor"),
                            'model': station_data.get("model"),
                            'ocpp_websocket_url': response_data.get('ocpp_websocket'),
                            'is_online': True
                        }
                    )
                    
                    if not created:
                        ocpp_station.station_id = station_data["station_id"]
                        ocpp_station.ocpp_websocket_url = response_data.get('ocpp_websocket')
                        ocpp_station.is_online = True
                        ocpp_station.save()
                    
                    for connector in charging_station.connectors.all():
                        ocpp_connector, created = OCPPConnector.objects.get_or_create(
                            ocpp_station=ocpp_station,
                            connector_id=connector.id,
                            defaults={
                                'charging_connector': connector,
                                'status': OCPPConnector.ConnectorStatus.AVAILABLE
                            }
                        )
                    
                    self.log_event(
                        ocpp_station=ocpp_station,
                        level=OCPPLog.LogLevel.INFO,
                        message=f"Station {ocpp_station.station_id} synced successfully",
                        raw_data=response_data
                    )
                    
                    return {
                        'success': True,
                        'ocpp_station': ocpp_station,
                        'data': response_data
                    }
                else:
                    self.log_event(
                        level=OCPPLog.LogLevel.ERROR,
                        message=f"Failed to sync station {charging_station.name}: {result['error']}"
                    )
                    return result
                    
        except Exception as e:
            logger.error(f"Error syncing station to OCPP: {e}")
            return {'success': False, 'error': str(e)}

    def initiate_charging(self, station_id, connector_id, user, payment_transaction_id, owner_info=None):
        try:
            ocpp_station = OCPPStation.objects.get(station_id=station_id)
            ocpp_connector = OCPPConnector.objects.get(
                ocpp_station=ocpp_station,
                connector_id=connector_id
            )
            
            id_tag = f"USER_{user.id}_{payment_transaction_id}"
            
            request_data = {
                "station_id": station_id,
                "connector_id": connector_id,
                "user_id": str(user.id),
                "payment_transaction_id": payment_transaction_id,
                "payment_method": "qr_code"
            }
            
            if owner_info:
                request_data.update({
                    "owner_id": owner_info.get('owner_id'),
                    "owner_name": owner_info.get('owner_name')
                })
            
            result = self.make_request('POST', '/api/locator/initiate-charging/', request_data)
            
            if result['success']:
                response_data = result['data']
                transaction_data = response_data.get('transaction', {})
                
                charging_session = ChargingSession.objects.create(
                    transaction_id=transaction_data.get('transaction_id'),
                    user=user,
                    ocpp_station=ocpp_station,
                    ocpp_connector=ocpp_connector,
                    payment_transaction_id=payment_transaction_id,
                    id_tag=id_tag,
                    status=ChargingSession.SessionStatus.STARTED,
                    payment_status=ChargingSession.PaymentStatus.AUTHORIZED,
                    start_time=timezone.now(),
                    max_power_kw=ocpp_connector.charging_connector.power_kw if ocpp_connector.charging_connector else 0
                )
                
                ocpp_connector.status = OCPPConnector.ConnectorStatus.PREPARING
                ocpp_connector.save()
                
                self.log_event(
                    ocpp_station=ocpp_station,
                    charging_session=charging_session,
                    level=OCPPLog.LogLevel.INFO,
                    message=f"Charging session {charging_session.transaction_id} initiated",
                    raw_data=response_data
                )
                
                return {
                    'success': True,
                    'charging_session': charging_session,
                    'data': response_data
                }
            else:
                self.log_event(
                    ocpp_station=ocpp_station,
                    level=OCPPLog.LogLevel.ERROR,
                    message=f"Failed to initiate charging: {result['error']}"
                )
                return result
                
        except (OCPPStation.DoesNotExist, OCPPConnector.DoesNotExist) as e:
            error_msg = f"Station or connector not found: {e}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        except Exception as e:
            logger.error(f"Error initiating charging: {e}")
            return {'success': False, 'error': str(e)}

    def get_session_data(self, transaction_id):
        try:
            result = self.make_request('GET', f'/api/locator/session/{transaction_id}/')
            
            if result['success']:
                response_data = result['data']
                
                try:
                    charging_session = ChargingSession.objects.get(transaction_id=transaction_id)
                    
                    session_data = response_data.get('session_data', {})
                    charging_session.duration_seconds = session_data.get('duration_seconds', 0)
                    charging_session.energy_consumed_kwh = session_data.get('energy_consumed_kwh', 0)
                    charging_session.current_power_kw = session_data.get('current_power_kw', 0)
                    charging_session.estimated_cost = session_data.get('estimated_cost', 0)
                    
                    status_mapping = {
                        'Started': ChargingSession.SessionStatus.STARTED,
                        'Charging': ChargingSession.SessionStatus.CHARGING,
                        'Suspended': ChargingSession.SessionStatus.SUSPENDED,
                        'Stopping': ChargingSession.SessionStatus.STOPPING,
                        'Stopped': ChargingSession.SessionStatus.STOPPED,
                    }
                    
                    ocpp_status = session_data.get('status', 'Started')
                    charging_session.status = status_mapping.get(ocpp_status, ChargingSession.SessionStatus.STARTED)
                    charging_session.save()
                    
                    return {
                        'success': True,
                        'charging_session': charging_session,
                        'data': response_data
                    }
                    
                except ChargingSession.DoesNotExist:
                    return {
                        'success': True,
                        'data': response_data
                    }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error getting session data: {e}")
            return {'success': False, 'error': str(e)}

    def stop_charging(self, transaction_id, user_id=None):
        try:
            request_data = {
                "transaction_id": transaction_id
            }
            
            if user_id:
                request_data["user_id"] = str(user_id)
            
            result = self.make_request('POST', '/api/locator/stop-charging/', request_data)
            
            if result['success']:
                response_data = result['data']
                
                try:
                    charging_session = ChargingSession.objects.get(transaction_id=transaction_id)
                    charging_session.status = ChargingSession.SessionStatus.STOPPING
                    charging_session.stop_time = timezone.now()
                    charging_session.save()
                    
                    charging_session.ocpp_connector.status = OCPPConnector.ConnectorStatus.FINISHING
                    charging_session.ocpp_connector.save()
                    
                    self.log_event(
                        ocpp_station=charging_session.ocpp_station,
                        charging_session=charging_session,
                        level=OCPPLog.LogLevel.INFO,
                        message=f"Stop command sent for session {transaction_id}",
                        raw_data=response_data
                    )
                    
                    return {
                        'success': True,
                        'charging_session': charging_session,
                        'data': response_data
                    }
                    
                except ChargingSession.DoesNotExist:
                    return {
                        'success': True,
                        'data': response_data
                    }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error stopping charging: {e}")
            return {'success': False, 'error': str(e)}

    def log_event(self, ocpp_station=None, charging_session=None, level=OCPPLog.LogLevel.INFO, 
                  message_type=None, action=None, message="", raw_data=None):
        try:
            OCPPLog.objects.create(
                ocpp_station=ocpp_station,
                charging_session=charging_session,
                level=level,
                message_type=message_type,
                action=action,
                message=message,
                raw_data=raw_data
            )
        except Exception as e:
            logger.error(f"Error logging OCPP event: {e}")
