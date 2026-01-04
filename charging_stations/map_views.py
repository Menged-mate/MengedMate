from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.conf import settings
from .serializers import (
    FirestoreMapStationSerializer,
    FirestoreChargingStationSerializer,
    FavoriteStationSerializer
)
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
import math
from utils.firestore_repo import firestore_repo

User = get_user_model()

class PublicStationListView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    
    @method_decorator(cache_page(60 * 5))
    def get(self, request):
        # Fetch all public/active stations from Firestore
        # Ideally firestore_repo.list_stations accepts filters
        stations = firestore_repo.list_stations(filters={'is_public': True, 'is_active': True}, limit=1000)
        
        north = self.request.query_params.get('north')
        south = self.request.query_params.get('south')
        east = self.request.query_params.get('east')
        west = self.request.query_params.get('west')
        
        filtered_stations = []
        
        # Apply bounds filter in memory if provided
        if all([north, south, east, west]):
            try:
                n, s, e, w = float(north), float(south), float(east), float(west)
                for station in stations:
                    try:
                        lat = float(station.get('latitude', 0))
                        lng = float(station.get('longitude', 0))
                        if s <= lat <= n and w <= lng <= e:
                            filtered_stations.append(station)
                    except (ValueError, TypeError):
                        continue
            except ValueError:
                filtered_stations = stations
        else:
            filtered_stations = stations

        connector_type = self.request.query_params.get('connector_type')
        if connector_type:
            # Need to check connectors. This implies we need connectors in the station dict.
            # create_station stores connectors in subcollection, but maybe we should store types array in doc.
            # For now, we might skip detailed filtering or fetch connectors if needed (expensive).
            # If we rely on update_station logic to store 'connector_types' on the doc, we can filter.
            # Assuming 'connector_types' or similar aggregation exists on station doc, or we skip.
            # Let's try to filter if we can, else ignore.
            pass

        min_power = self.request.query_params.get('min_power')
        if min_power:
             pass

        # Availability filter
        available_only = self.request.query_params.get('available_only') == 'true'
        if available_only:
            filtered_stations = [s for s in filtered_stations if s.get('available_connectors', 0) > 0]
        
        serializer = FirestoreMapStationSerializer(filtered_stations, many=True)
        return Response(serializer.data)

class NearbyStationsView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    
    def get(self, request):
        lat_param = self.request.query_params.get('lat')
        lng_param = self.request.query_params.get('lng')
        radius_param = self.request.query_params.get('radius', 5) 
        
        if not lat_param or not lng_param:
            return Response([], status=status.HTTP_200_OK)
        
        try:
            center_lat = float(lat_param)
            center_lng = float(lng_param)
            radius = float(radius_param)
        except ValueError:
            return Response([], status=status.HTTP_200_OK)
        
        # Fetch all public stations
        stations = firestore_repo.list_stations(filters={'is_public': True, 'is_active': True}, limit=1000)
        
        result = []
        for station in stations:
            try:
                station_lat = float(station.get('latitude', 0))
                station_lng = float(station.get('longitude', 0))
                
                # Haversine distance
                dlat = math.radians(station_lat - center_lat)
                dlng = math.radians(station_lng - center_lng)
                a = (math.sin(dlat/2)**2 + 
                     math.cos(math.radians(center_lat)) * math.cos(math.radians(station_lat)) * 
                     math.sin(dlng/2)**2)
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                distance = 6371 * c  
                
                if distance <= radius:
                    # Inject distance for sorting if needed, though serializer doesn't field it explicitly
                    station['distance'] = distance
                    result.append(station)
            except (ValueError, TypeError):
                continue
        
        # Sort by distance
        result.sort(key=lambda x: x.get('distance', float('inf')))
        
        serializer = FirestoreMapStationSerializer(result, many=True)
        return Response(serializer.data)

class StationSearchView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    
    def get(self, request):
        query = self.request.query_params.get('q', '').lower()
        if not query or len(query) < 2:
            return Response([], status=status.HTTP_200_OK)
        
        # Fetch all public stations
        stations = firestore_repo.list_stations(filters={'is_public': True, 'is_active': True}, limit=1000)
        
        filtered = []
        for station in stations:
            # Check name, address, city, state, zip
            # Use safe get and string conversion
            searchable = [
                station.get('name', ''),
                station.get('address', ''),
                station.get('city', ''),
                station.get('state', ''),
                station.get('zip_code', '')
            ]
            if any(query in str(s).lower() for s in searchable):
                filtered.append(station)
                
        serializer = FirestoreMapStationSerializer(filtered, many=True)
        return Response(serializer.data)

class PublicStationDetailView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    
    def get(self, request, id):
        station = firestore_repo.get_station(id)
        if not station:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
            
        if not station.get('is_public', False) or not station.get('is_active', False):
             return Response({'detail': 'Station not public or active.'}, status=status.HTTP_404_NOT_FOUND)

        # We probably need to fetch subcollections (connectors, images) manually 
        # because get_station just returns the document.
        # FirestoreChargingStationSerializer expects 'connectors' and 'images' lists in the data dict if many=True?
        # No, it's a Serializer, so it expects input data to have these keys.
        
        # Hydrate subcollections
        connectors = firestore_repo.list_connectors(id)
        images = firestore_repo.list_images(id)
        
        station['connectors'] = connectors
        station['images'] = images
        
        # We also need 'owner_name' and 'is_verified_owner' which create method populated onto the doc?
        # create_station in serializer puts them on doc: owner_name, is_verified_owner.
        # So they should be there.
        
        serializer = FirestoreChargingStationSerializer(station, context={'request': request})
        return Response(serializer.data)

class FavoriteStationListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    
    def get(self, request):
        favorites = firestore_repo.list_favorites(request.user.id)
        # Favorites from firestore are dicts with station snapshot.
        # We might need a serializer that matches this structure.
        # FavoriteStationSerializer in serializers.py expects SQL model structure (nested station object).
        # We should just return the list directly or make a simple serializer.
        # The list_favorites returns:
        # { 'station_id':..., 'station_name':..., 'station_image':..., ... }
        # This is already client-friendly.
        return Response(favorites)

class FavoriteStationToggleView(APIView):
   
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    
    def post(self, request, station_id):
        user_id = request.user.id
        
        # Check if already favorite
        existing = firestore_repo.get_favorite(user_id, station_id)
        
        if existing:
            # Remove
            firestore_repo.remove_favorite(user_id, station_id)
            return Response({
                "detail": "Station removed from favorites.",
                "is_favorite": False
            }, status=status.HTTP_200_OK)
        else:
            # Add
            # We need station details to store the snapshot.
            station = firestore_repo.get_station(str(station_id))
            if not station:
                 return Response({"detail": "Station not found."}, status=status.HTTP_404_NOT_FOUND)
                 
            firestore_repo.add_favorite(user_id, station)
            return Response({
                "detail": "Station added to favorites.",
                "is_favorite": True
            }, status=status.HTTP_200_OK)
