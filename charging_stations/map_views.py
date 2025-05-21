from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.conf import settings
from .models import ChargingStation, FavoriteStation
from .serializers import (
    MapStationSerializer,
    StationDetailSerializer,
    FavoriteStationSerializer
)
from authentication.authentication import AnonymousAuthentication, TokenAuthentication
from rest_framework.authentication import SessionAuthentication
import math

User = get_user_model()

class PublicStationListView(generics.ListAPIView):
    """
    API view for listing public charging stations for the map.
    """
    serializer_class = MapStationSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = [AnonymousAuthentication, TokenAuthentication, SessionAuthentication]
    
    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = ChargingStation.objects.filter(
            is_active=True,
            is_public=True,
            latitude__isnull=False,
            longitude__isnull=False
        )
        
        # Filter by bounds if provided
        north = self.request.query_params.get('north')
        south = self.request.query_params.get('south')
        east = self.request.query_params.get('east')
        west = self.request.query_params.get('west')
        
        if all([north, south, east, west]):
            try:
                queryset = queryset.filter(
                    latitude__lte=float(north),
                    latitude__gte=float(south),
                    longitude__lte=float(east),
                    longitude__gte=float(west)
                )
            except ValueError:
                pass
        
        # Filter by connector type
        connector_type = self.request.query_params.get('connector_type')
        if connector_type:
            queryset = queryset.filter(connectors__connector_type=connector_type).distinct()
        
        # Filter by minimum power
        min_power = self.request.query_params.get('min_power')
        if min_power:
            try:
                queryset = queryset.filter(connectors__power_kw__gte=float(min_power)).distinct()
            except ValueError:
                pass
        
        # Filter by availability
        available_only = self.request.query_params.get('available_only') == 'true'
        if available_only:
            queryset = queryset.filter(available_connectors__gt=0)
        
        return queryset

class NearbyStationsView(generics.ListAPIView):
    """
    API view for listing nearby charging stations.
    """
    serializer_class = MapStationSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = [AnonymousAuthentication, TokenAuthentication, SessionAuthentication]
    
    def get_queryset(self):
        # Get latitude and longitude from query parameters
        lat = self.request.query_params.get('lat')
        lng = self.request.query_params.get('lng')
        radius = self.request.query_params.get('radius', 5)  # Default radius: 5km
        
        if not lat or not lng:
            return ChargingStation.objects.none()
        
        try:
            lat = float(lat)
            lng = float(lng)
            radius = float(radius)
        except ValueError:
            return ChargingStation.objects.none()
        
        # Calculate bounding box for initial filtering (optimization)
        # 1 degree of latitude is approximately 111 km
        # 1 degree of longitude varies with latitude, approximately 111 * cos(lat) km
        lat_range = radius / 111.0
        lng_range = radius / (111.0 * math.cos(math.radians(lat)))
        
        # Get stations within the bounding box
        queryset = ChargingStation.objects.filter(
            is_active=True,
            is_public=True,
            latitude__range=(lat - lat_range, lat + lat_range),
            longitude__range=(lng - lng_range, lng + lng_range)
        )
        
        # Filter stations by exact distance (Haversine formula)
        result = []
        for station in queryset:
            # Calculate distance using Haversine formula
            station_lat = float(station.latitude)
            station_lng = float(station.longitude)
            
            dlat = math.radians(station_lat - lat)
            dlng = math.radians(station_lng - lng)
            a = (math.sin(dlat/2)**2 + 
                 math.cos(math.radians(lat)) * math.cos(math.radians(station_lat)) * 
                 math.sin(dlng/2)**2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            distance = 6371 * c  # Earth radius in km
            
            if distance <= radius:
                station.distance = distance
                result.append(station)
        
        # Sort by distance
        return sorted(result, key=lambda x: x.distance)

class StationSearchView(generics.ListAPIView):
    """
    API view for searching charging stations.
    """
    serializer_class = MapStationSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = [AnonymousAuthentication, TokenAuthentication, SessionAuthentication]
    
    def get_queryset(self):
        query = self.request.query_params.get('q', '')
        if not query or len(query) < 2:
            return ChargingStation.objects.none()
        
        return ChargingStation.objects.filter(
            Q(name__icontains=query) | 
            Q(address__icontains=query) | 
            Q(city__icontains=query) | 
            Q(state__icontains=query) |
            Q(zip_code__icontains=query)
        ).filter(is_active=True, is_public=True)

class PublicStationDetailView(generics.RetrieveAPIView):
    """
    API view for retrieving a public charging station.
    """
    serializer_class = StationDetailSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = [AnonymousAuthentication, TokenAuthentication, SessionAuthentication]
    lookup_field = 'id'
    queryset = ChargingStation.objects.filter(is_active=True, is_public=True)

class FavoriteStationListView(generics.ListAPIView):
    """
    API view for listing user's favorite charging stations.
    """
    serializer_class = FavoriteStationSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    
    def get_queryset(self):
        return FavoriteStation.objects.filter(user=self.request.user)

class FavoriteStationToggleView(APIView):
    """
    API view for toggling a station as favorite.
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    
    def post(self, request, station_id):
        try:
            station = ChargingStation.objects.get(id=station_id, is_active=True, is_public=True)
        except ChargingStation.DoesNotExist:
            return Response({"detail": "Station not found."}, status=status.HTTP_404_NOT_FOUND)
        
        favorite, created = FavoriteStation.objects.get_or_create(
            user=request.user,
            station=station
        )
        
        if not created:
            # If it already existed, remove it
            favorite.delete()
            return Response({"detail": "Station removed from favorites."}, status=status.HTTP_200_OK)
        
        return Response({"detail": "Station added to favorites."}, status=status.HTTP_201_CREATED)
