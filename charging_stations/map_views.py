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
    serializer_class = MapStationSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = [AnonymousAuthentication, TokenAuthentication, SessionAuthentication]
    
    @method_decorator(cache_page(60 * 5))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = ChargingStation.objects.filter(
            is_active=True,
            is_public=True,
            latitude__isnull=False,
            longitude__isnull=False
        )
        
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
        
        connector_type = self.request.query_params.get('connector_type')
        if connector_type:
            queryset = queryset.filter(connectors__connector_type=connector_type).distinct()
        
        min_power = self.request.query_params.get('min_power')
        if min_power:
            try:
                queryset = queryset.filter(connectors__power_kw__gte=float(min_power)).distinct()
            except ValueError:
                pass
        
        available_only = self.request.query_params.get('available_only') == 'true'
        if available_only:
            queryset = queryset.filter(available_connectors__gt=0)
        
        return queryset

class NearbyStationsView(generics.ListAPIView):
  
    serializer_class = MapStationSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = [AnonymousAuthentication, TokenAuthentication, SessionAuthentication]
    
    def get_queryset(self):
        lat = self.request.query_params.get('lat')
        lng = self.request.query_params.get('lng')
        radius = self.request.query_params.get('radius', 5) 
        
        if not lat or not lng:
            return ChargingStation.objects.none()
        
        try:
            lat = float(lat)
            lng = float(lng)
            radius = float(radius)
        except ValueError:
            return ChargingStation.objects.none()
        
        lat_range = radius / 111.0
        lng_range = radius / (111.0 * math.cos(math.radians(lat)))
        
        queryset = ChargingStation.objects.filter(
            is_active=True,
            is_public=True,
            latitude__range=(lat - lat_range, lat + lat_range),
            longitude__range=(lng - lng_range, lng + lng_range)
        )
        
        result = []
        for station in queryset:
            station_lat = float(station.latitude)
            station_lng = float(station.longitude)
            
            dlat = math.radians(station_lat - lat)
            dlng = math.radians(station_lng - lng)
            a = (math.sin(dlat/2)**2 + 
                 math.cos(math.radians(lat)) * math.cos(math.radians(station_lat)) * 
                 math.sin(dlng/2)**2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            distance = 6371 * c  
            
            if distance <= radius:
                station.distance = distance
                result.append(station)
        
        return sorted(result, key=lambda x: x.distance)

class StationSearchView(generics.ListAPIView):
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
   
    serializer_class = StationDetailSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = [AnonymousAuthentication, TokenAuthentication, SessionAuthentication]
    lookup_field = 'id'
    queryset = ChargingStation.objects.filter(is_active=True, is_public=True)

class FavoriteStationListView(generics.ListAPIView):
    
    serializer_class = FavoriteStationSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    
    def get_queryset(self):
        return FavoriteStation.objects.filter(user=self.request.user)

class FavoriteStationToggleView(APIView):
   
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
            favorite.delete()
            return Response({
                "detail": "Station removed from favorites.",
                "is_favorite": False
            }, status=status.HTTP_200_OK)

        return Response({
            "detail": "Station added to favorites.",
            "is_favorite": True
        }, status=status.HTTP_200_OK)
