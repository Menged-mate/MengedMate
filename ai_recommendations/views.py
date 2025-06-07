from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.db.models import Q, Avg, Count
from django.utils import timezone
from datetime import timedelta

from .models import (
    UserSearchPreferences, 
    StationRecommendationScore, 
    ReviewSentimentAnalysis,
    UserRecommendationHistory
)
from .serializers import (
    UserSearchPreferencesSerializer,
    StationRecommendationSerializer,
    NearbyStationSearchSerializer,
    RecommendationResponseSerializer,
    UserRecommendationHistorySerializer,
    RecommendationFeedbackSerializer,
    StationSentimentSummarySerializer,
    UserVehicleProfileSerializer,
    VehicleSerializer
)
from .services import AIRecommendationService, SentimentAnalysisService
from charging_stations.models import ChargingStation, StationReview
from authentication.models import Vehicle

User = get_user_model()


class AIRecommendationsView(APIView):
    """Get AI-powered personalized station recommendations"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = NearbyStationSearchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        user = request.user
        
        # Get AI recommendations
        ai_service = AIRecommendationService()
        recommendations = ai_service.get_personalized_recommendations(
            user=user,
            user_lat=float(data['latitude']),
            user_lng=float(data['longitude']),
            radius_km=float(data.get('radius_km', 10.0)),
            limit=data.get('limit', 20)
        )
        
        # Enhance recommendations with additional data
        enhanced_recommendations = []
        for rec in recommendations:
            station = rec['station']
            
            # Calculate estimated charging time
            estimated_time = self._calculate_charging_time(user, station)
            
            # Get compatibility status
            compatibility_status = self._get_compatibility_status(user, station)
            
            # Get availability status
            availability_status = self._get_availability_status(station)
            
            enhanced_rec = {
                **rec,
                'estimated_charging_time': estimated_time,
                'compatibility_status': compatibility_status,
                'availability_status': availability_status
            }
            enhanced_recommendations.append(enhanced_rec)
        
        return Response({
            'recommendations': enhanced_recommendations,
            'total_found': len(enhanced_recommendations),
            'search_params': data,
            'user_location': {
                'latitude': data['latitude'],
                'longitude': data['longitude']
            }
        })
    
    def _calculate_charging_time(self, user, station):
        """Calculate estimated charging time"""
        if not user.ev_battery_capacity_kwh:
            return "Unknown"
        
        # Get the most powerful compatible connector
        compatible_connectors = station.connectors.filter(
            connector_type=user.ev_connector_type,
            status='available'
        ).order_by('-power_kw')
        
        if not compatible_connectors.exists():
            return "Incompatible"
        
        max_power = float(compatible_connectors.first().power_kw)
        battery_capacity = float(user.ev_battery_capacity_kwh)
        
        # Assume charging from 20% to 80% (60% of capacity)
        charging_needed = battery_capacity * 0.6
        
        # Estimate time (accounting for charging curve - slower at higher percentages)
        estimated_hours = charging_needed / (max_power * 0.8)  # 80% efficiency
        
        if estimated_hours < 1:
            return f"{int(estimated_hours * 60)} minutes"
        else:
            return f"{estimated_hours:.1f} hours"
    
    def _get_compatibility_status(self, user, station):
        """Get connector compatibility status"""
        if not user.ev_connector_type or user.ev_connector_type == 'none':
            return "Unknown"
        
        compatible_connectors = station.connectors.filter(
            connector_type=user.ev_connector_type
        )
        
        if not compatible_connectors.exists():
            return "Incompatible"
        
        available_compatible = compatible_connectors.filter(status='available')
        if available_compatible.exists():
            return "Compatible & Available"
        else:
            return "Compatible (Currently Busy)"
    
    def _get_availability_status(self, station):
        """Get overall station availability status"""
        total_connectors = station.connectors.count()
        available_connectors = station.connectors.filter(status='available').count()
        
        if total_connectors == 0:
            return "Unknown"
        
        availability_ratio = available_connectors / total_connectors
        
        if availability_ratio >= 0.8:
            return "Highly Available"
        elif availability_ratio >= 0.5:
            return "Moderately Available"
        elif availability_ratio > 0:
            return "Limited Availability"
        else:
            return "Currently Full"


class UserSearchPreferencesView(generics.RetrieveUpdateAPIView):
    """Manage user search preferences"""
    serializer_class = UserSearchPreferencesSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        preferences, created = UserSearchPreferences.objects.get_or_create(
            user=self.request.user
        )
        return preferences


class UserVehicleProfileView(generics.RetrieveUpdateAPIView):
    """Manage user vehicle profile"""
    serializer_class = UserVehicleProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class UserVehiclesView(generics.ListCreateAPIView):
    """Manage user vehicles"""
    serializer_class = VehicleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Vehicle.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        vehicle = serializer.save(user=self.request.user)
        
        # If this is the first vehicle or marked as primary, set as active
        if not self.request.user.active_vehicle or vehicle.is_primary:
            self.request.user.active_vehicle = vehicle
            self.request.user.save()


class UserVehicleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Manage individual vehicle"""
    serializer_class = VehicleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Vehicle.objects.filter(user=self.request.user)
    
    def perform_update(self, serializer):
        vehicle = serializer.save()
        
        # If marked as primary, set as active vehicle
        if vehicle.is_primary:
            self.request.user.active_vehicle = vehicle
            self.request.user.save()


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def set_active_vehicle(request):
    """Set active vehicle for recommendations"""
    vehicle_id = request.data.get('vehicle_id')
    
    try:
        vehicle = Vehicle.objects.get(id=vehicle_id, user=request.user)
        request.user.active_vehicle = vehicle
        request.user.save()
        
        return Response({
            'message': 'Active vehicle updated successfully',
            'active_vehicle': VehicleSerializer(vehicle).data
        })
    except Vehicle.DoesNotExist:
        return Response(
            {'error': 'Vehicle not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )


class StationSentimentAnalysisView(APIView):
    """Get AI sentiment analysis for a station"""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, station_id):
        try:
            station = ChargingStation.objects.get(id=station_id)
        except ChargingStation.DoesNotExist:
            return Response(
                {'error': 'Station not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Run sentiment analysis
        sentiment_service = SentimentAnalysisService()
        analysis = sentiment_service.analyze_station_reviews(station)
        
        # Get top keywords
        recent_analyses = ReviewSentimentAnalysis.objects.filter(
            review__station=station,
            analyzed_at__gte=timezone.now() - timedelta(days=90)
        )
        
        all_positive_keywords = []
        all_negative_keywords = []
        
        for analysis_obj in recent_analyses:
            all_positive_keywords.extend(analysis_obj.get_positive_keywords())
            all_negative_keywords.extend(analysis_obj.get_negative_keywords())
        
        # Count keyword frequency
        from collections import Counter
        positive_counter = Counter(all_positive_keywords)
        negative_counter = Counter(all_negative_keywords)
        
        # Get aspect sentiments
        aspect_sentiments = {}
        if recent_analyses.exists():
            aspect_sentiments = {
                'charging_speed': recent_analyses.aggregate(
                    avg=Avg('charging_speed_sentiment')
                )['avg'],
                'reliability': recent_analyses.aggregate(
                    avg=Avg('reliability_sentiment')
                )['avg'],
                'location': recent_analyses.aggregate(
                    avg=Avg('location_sentiment')
                )['avg'],
                'amenities': recent_analyses.aggregate(
                    avg=Avg('amenities_sentiment')
                )['avg'],
                'price': recent_analyses.aggregate(
                    avg=Avg('price_sentiment')
                )['avg']
            }
        
        response_data = {
            **analysis,
            'top_positive_keywords': [word for word, count in positive_counter.most_common(5)],
            'top_negative_keywords': [word for word, count in negative_counter.most_common(5)],
            'aspect_sentiments': aspect_sentiments
        }
        
        return Response(response_data)


class RecommendationHistoryView(generics.ListAPIView):
    """Get user's recommendation history"""
    serializer_class = UserRecommendationHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserRecommendationHistory.objects.filter(
            user=self.request.user
        ).order_by('-recommended_at')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def recommendation_feedback(request):
    """Record user feedback on recommendations"""
    serializer = RecommendationFeedbackSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    try:
        recommendation = UserRecommendationHistory.objects.get(
            id=data['recommendation_id'],
            user=request.user
        )
        
        action = data['action']
        now = timezone.now()
        
        if action == 'clicked':
            recommendation.was_clicked = True
            recommendation.clicked_at = now
        elif action == 'visited':
            recommendation.was_visited = True
            recommendation.visited_at = now
        elif action == 'charged':
            recommendation.was_used_for_charging = True
            recommendation.charged_at = now
        
        if 'rating' in data:
            recommendation.user_rating = data['rating']
        
        if 'feedback' in data:
            recommendation.feedback_text = data['feedback']
        
        recommendation.save()
        
        return Response({'message': 'Feedback recorded successfully'})
        
    except UserRecommendationHistory.DoesNotExist:
        return Response(
            {'error': 'Recommendation not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
