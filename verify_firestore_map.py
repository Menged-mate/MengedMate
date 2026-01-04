
import sys
from utils.firestore_repo import firestore_repo
from charging_stations.serializers import FirestoreMapStationSerializer

print("--- Verifying Firestore Repo & Serializer ---")

try:
    stations = firestore_repo.list_stations(filters={'is_public': True, 'is_active': True})
    print(f"Fetched {len(stations)} stations from Firestore.")
    
    if stations:
        station = stations[0]
        print(f"First Station: {station.get('name')} (ID: {station.get('id')})")
        
        # Test Serializer
        serializer = FirestoreMapStationSerializer(station)
        data = serializer.data
        print("Serialized Data:")
        print(data)
        
        # Check computed fields
        print(f"Marker Color: {data.get('marker_color')}")
        print(f"Availability: {data.get('availability_status')}")
    else:
        print("No stations found. Cannot verify serializer.")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("--- Verification Complete ---")
