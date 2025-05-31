import requests
import json
from datetime import datetime


class OCPPIntegrationClient:
    """
    Client for testing OCPP integration endpoints
    """
    
    def __init__(self, base_url="http://localhost:8000", auth_token=None):
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.session = requests.Session()
        
        if auth_token:
            self.session.headers.update({
                'Authorization': f'Token {auth_token}'
            })
        
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    def sync_station(self, charging_station_id, vendor="Generic", model="EV Charger"):
        """Sync a charging station to OCPP simulation"""
        url = f"{self.base_url}/api/ocpp/sync-station/"
        data = {
            "charging_station_id": charging_station_id,
            "vendor": vendor,
            "model": model
        }
        
        response = self.session.post(url, json=data)
        return self._handle_response(response)

    def initiate_charging(self, station_id, connector_id, user_id, payment_transaction_id, 
                         payment_method="qr_code", owner_id=None, owner_name=None):
        """Initiate a charging session"""
        url = f"{self.base_url}/api/ocpp/initiate-charging/"
        data = {
            "station_id": station_id,
            "connector_id": connector_id,
            "user_id": user_id,
            "payment_transaction_id": payment_transaction_id,
            "payment_method": payment_method
        }
        
        if owner_id:
            data["owner_id"] = owner_id
        if owner_name:
            data["owner_name"] = owner_name
        
        response = self.session.post(url, json=data)
        return self._handle_response(response)

    def stop_charging(self, transaction_id, user_id=None):
        """Stop a charging session"""
        url = f"{self.base_url}/api/ocpp/stop-charging/"
        data = {
            "transaction_id": transaction_id
        }
        
        if user_id:
            data["user_id"] = user_id
        
        response = self.session.post(url, json=data)
        return self._handle_response(response)

    def get_session_status(self, transaction_id):
        """Get charging session status"""
        url = f"{self.base_url}/api/ocpp/session-status/"
        params = {"transaction_id": transaction_id}
        
        response = self.session.get(url, params=params)
        return self._handle_response(response)

    def list_ocpp_stations(self):
        """List all OCPP stations"""
        url = f"{self.base_url}/api/ocpp/stations/"
        response = self.session.get(url)
        return self._handle_response(response)

    def get_ocpp_station(self, station_id):
        """Get specific OCPP station details"""
        url = f"{self.base_url}/api/ocpp/stations/{station_id}/"
        response = self.session.get(url)
        return self._handle_response(response)

    def list_charging_sessions(self, status=None):
        """List charging sessions"""
        url = f"{self.base_url}/api/ocpp/sessions/"
        params = {}
        if status:
            params["status"] = status
        
        response = self.session.get(url, params=params)
        return self._handle_response(response)

    def get_charging_session(self, transaction_id):
        """Get specific charging session details"""
        url = f"{self.base_url}/api/ocpp/sessions/{transaction_id}/"
        response = self.session.get(url)
        return self._handle_response(response)

    def list_logs(self, level=None, station_id=None):
        """List OCPP logs"""
        url = f"{self.base_url}/api/ocpp/logs/"
        params = {}
        if level:
            params["level"] = level
        if station_id:
            params["station_id"] = station_id
        
        response = self.session.get(url, params=params)
        return self._handle_response(response)

    def send_webhook(self, webhook_type, data, station_id=None, transaction_id=None):
        """Send a test webhook"""
        url = f"{self.base_url}/api/ocpp/webhook/"
        webhook_data = {
            "type": webhook_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        if station_id:
            webhook_data["station_id"] = station_id
        if transaction_id:
            webhook_data["transaction_id"] = transaction_id
        
        # Remove auth for webhook (it's public)
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        response = requests.post(url, json=webhook_data, headers=headers)
        return self._handle_response(response)

    def _handle_response(self, response):
        """Handle API response"""
        try:
            data = response.json()
        except json.JSONDecodeError:
            data = {"error": "Invalid JSON response", "text": response.text}
        
        return {
            "status_code": response.status_code,
            "success": response.status_code < 400,
            "data": data
        }

    def print_response(self, response):
        """Pretty print API response"""
        print(f"Status Code: {response['status_code']}")
        print(f"Success: {response['success']}")
        print("Response Data:")
        print(json.dumps(response['data'], indent=2))
        print("-" * 50)


# Example usage and testing functions
def test_complete_flow(client, charging_station_id, user_id):
    """Test the complete OCPP integration flow"""
    print("=== Testing Complete OCPP Integration Flow ===\n")
    
    # 1. Sync station
    print("1. Syncing station to OCPP...")
    sync_result = client.sync_station(charging_station_id)
    client.print_response(sync_result)
    
    if not sync_result['success']:
        print("Failed to sync station. Stopping test.")
        return
    
    # 2. List OCPP stations
    print("2. Listing OCPP stations...")
    stations_result = client.list_ocpp_stations()
    client.print_response(stations_result)
    
    if not stations_result['success'] or not stations_result['data']:
        print("No OCPP stations found. Stopping test.")
        return
    
    station_id = stations_result['data'][0]['station_id']
    
    # 3. Initiate charging
    print("3. Initiating charging session...")
    payment_id = f"test_payment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    charging_result = client.initiate_charging(
        station_id=station_id,
        connector_id=1,
        user_id=user_id,
        payment_transaction_id=payment_id,
        owner_id="test_owner",
        owner_name="Test Owner"
    )
    client.print_response(charging_result)
    
    if not charging_result['success']:
        print("Failed to initiate charging. Stopping test.")
        return
    
    transaction_id = charging_result['data']['charging_session']['transaction_id']
    
    # 4. Get session status
    print("4. Getting session status...")
    status_result = client.get_session_status(transaction_id)
    client.print_response(status_result)
    
    # 5. Send progress webhook
    print("5. Sending progress webhook...")
    webhook_result = client.send_webhook(
        webhook_type="session_progress",
        transaction_id=transaction_id,
        data={
            "energy_consumed_kwh": 5.5,
            "current_power_kw": 22.0,
            "duration_seconds": 900,
            "estimated_cost": 27.50
        }
    )
    client.print_response(webhook_result)
    
    # 6. Stop charging
    print("6. Stopping charging session...")
    stop_result = client.stop_charging(transaction_id, user_id)
    client.print_response(stop_result)
    
    # 7. Send stopped webhook
    print("7. Sending session stopped webhook...")
    stopped_webhook = client.send_webhook(
        webhook_type="session_stopped",
        transaction_id=transaction_id,
        data={
            "final_cost": 27.50,
            "stop_reason": "User requested",
            "meter_stop": 1055
        }
    )
    client.print_response(stopped_webhook)
    
    # 8. List sessions
    print("8. Listing charging sessions...")
    sessions_result = client.list_charging_sessions()
    client.print_response(sessions_result)
    
    print("=== Test Complete ===")


if __name__ == "__main__":
    # Example usage
    client = OCPPIntegrationClient()
    
    # You would need to provide actual IDs for testing
    # test_complete_flow(client, "your-charging-station-uuid", "your-user-uuid")
