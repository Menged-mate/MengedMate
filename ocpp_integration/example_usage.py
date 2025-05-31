#!/usr/bin/env python3
"""
Example usage of the OCPP Integration App

This script demonstrates how to use the OCPP integration in your application.
"""

import os
import sys
import django

# Setup Django environment
sys.path.append('/home/haile/Desktop/MengedMate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mengedmate.settings')
django.setup()

from django.contrib.auth import get_user_model
from charging_stations.models import ChargingStation, StationOwner
from ocpp_integration.services import OCPPIntegrationService
from ocpp_integration.client import OCPPIntegrationClient
import uuid

User = get_user_model()


def example_sync_station():
    """Example: Sync a charging station to OCPP simulation"""
    print("=== Example: Sync Station to OCPP ===")
    
    try:
        # Get a test station
        station = ChargingStation.objects.get(name='Test OCPP Station')
        print(f"Found station: {station.name}")
        
        # Initialize OCPP service
        ocpp_service = OCPPIntegrationService()
        
        # Sync station to OCPP
        result = ocpp_service.sync_station_to_ocpp(station)
        
        if result['success']:
            print("✅ Station synced successfully!")
            print(f"OCPP Station ID: {result['ocpp_station'].station_id}")
            print(f"WebSocket URL: {result['ocpp_station'].ocpp_websocket_url}")
        else:
            print(f"❌ Failed to sync station: {result['error']}")
            
    except ChargingStation.DoesNotExist:
        print("❌ Test station not found. Run: python manage.py test_ocpp_integration --create-sample-data")


def example_initiate_charging():
    """Example: Initiate a charging session"""
    print("\n=== Example: Initiate Charging Session ===")
    
    try:
        # Get test data
        user = User.objects.get(email='testuser@example.com')
        station = ChargingStation.objects.get(name='Test OCPP Station')
        
        if not hasattr(station, 'ocpp_station'):
            print("❌ Station not synced to OCPP. Please sync first.")
            return
        
        ocpp_station = station.ocpp_station
        connector = ocpp_station.ocpp_connectors.first()
        
        if not connector:
            print("❌ No OCPP connectors found.")
            return
        
        # Initialize OCPP service
        ocpp_service = OCPPIntegrationService()
        
        # Generate test payment ID
        payment_id = f'test_payment_{uuid.uuid4().hex[:8]}'
        
        print(f"Initiating charging for user: {user.email}")
        print(f"Station: {ocpp_station.station_id}")
        print(f"Connector: {connector.connector_id}")
        print(f"Payment ID: {payment_id}")
        
        # Initiate charging
        result = ocpp_service.initiate_charging(
            station_id=ocpp_station.station_id,
            connector_id=connector.connector_id,
            user=user,
            payment_transaction_id=payment_id,
            owner_info={
                'owner_id': str(station.owner.id),
                'owner_name': station.owner.company_name
            }
        )
        
        if result['success']:
            session = result['charging_session']
            print("✅ Charging session initiated successfully!")
            print(f"Transaction ID: {session.transaction_id}")
            print(f"Session Status: {session.status}")
            print(f"Payment Status: {session.payment_status}")
            return session.transaction_id
        else:
            print(f"❌ Failed to initiate charging: {result['error']}")
            
    except (User.DoesNotExist, ChargingStation.DoesNotExist) as e:
        print(f"❌ Required data not found: {e}")
        print("Run: python manage.py test_ocpp_integration --create-sample-data")


def example_monitor_session(transaction_id):
    """Example: Monitor a charging session"""
    print(f"\n=== Example: Monitor Charging Session {transaction_id} ===")
    
    ocpp_service = OCPPIntegrationService()
    
    # Get session status
    result = ocpp_service.get_session_data(transaction_id)
    
    if result['success']:
        if 'charging_session' in result:
            session = result['charging_session']
            print("✅ Session data retrieved successfully!")
            print(f"Status: {session.status}")
            print(f"Duration: {session.duration_seconds} seconds")
            print(f"Energy Consumed: {session.energy_consumed_kwh} kWh")
            print(f"Current Power: {session.current_power_kw} kW")
            print(f"Estimated Cost: ${session.estimated_cost}")
        else:
            print("✅ Session data retrieved from OCPP simulation")
            print(f"Data: {result['data']}")
    else:
        print(f"❌ Failed to get session data: {result['error']}")


def example_stop_charging(transaction_id):
    """Example: Stop a charging session"""
    print(f"\n=== Example: Stop Charging Session {transaction_id} ===")
    
    try:
        user = User.objects.get(email='testuser@example.com')
        ocpp_service = OCPPIntegrationService()
        
        # Stop charging
        result = ocpp_service.stop_charging(
            transaction_id=transaction_id,
            user_id=user.id
        )
        
        if result['success']:
            print("✅ Stop command sent successfully!")
            if 'charging_session' in result:
                session = result['charging_session']
                print(f"Session Status: {session.status}")
                print(f"Stop Time: {session.stop_time}")
        else:
            print(f"❌ Failed to stop charging: {result['error']}")
            
    except User.DoesNotExist:
        print("❌ Test user not found.")


def example_using_client():
    """Example: Using the OCPP Integration Client"""
    print("\n=== Example: Using OCPP Integration Client ===")
    
    # Initialize client (no auth token for this example)
    client = OCPPIntegrationClient(base_url="http://localhost:8001")
    
    # Test webhook
    print("Testing webhook...")
    webhook_result = client.send_webhook(
        webhook_type="session_progress",
        data={
            "energy_consumed_kwh": 10.5,
            "current_power_kw": 22.0,
            "duration_seconds": 1800,
            "estimated_cost": 52.50
        },
        transaction_id=1001
    )
    
    print(f"Webhook Status: {webhook_result['status_code']}")
    print(f"Webhook Response: {webhook_result['data']}")


def example_webhook_simulation():
    """Example: Simulate OCPP webhooks"""
    print("\n=== Example: Simulate OCPP Webhooks ===")
    
    from ocpp_integration.views import ocpp_webhook
    from django.test import RequestFactory
    import json
    
    factory = RequestFactory()
    
    # Simulate session started webhook
    webhook_data = {
        "type": "session_started",
        "transaction_id": 1001,
        "data": {
            "status": "started",
            "start_time": "2024-05-31T10:30:00Z"
        }
    }
    
    request = factory.post(
        '/api/ocpp/webhook/',
        data=json.dumps(webhook_data),
        content_type='application/json'
    )
    
    response = ocpp_webhook(request)
    print(f"Webhook Response Status: {response.status_code}")
    print(f"Webhook Response Data: {response.data}")


def main():
    """Run all examples"""
    print("🔌 OCPP Integration Examples")
    print("=" * 50)
    
    # 1. Sync station
    example_sync_station()
    
    # 2. Initiate charging
    transaction_id = example_initiate_charging()
    
    # 3. Monitor session (if we have a transaction ID)
    if transaction_id:
        example_monitor_session(transaction_id)
        example_stop_charging(transaction_id)
    
    # 4. Client usage
    example_using_client()
    
    # 5. Webhook simulation
    example_webhook_simulation()
    
    print("\n✅ All examples completed!")
    print("\nNote: Some operations may fail if the OCPP simulation backend is not running.")
    print("This is expected behavior - the integration will retry and log errors appropriately.")


if __name__ == "__main__":
    main()
