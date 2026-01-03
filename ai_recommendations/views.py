from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from datetime import datetime
from utils import firestore_repo

from .services import AIRecommendationService, SentimentAnalysisService
from .serializers_firestore import (
    UserSearchPreferencesSerializer, 
    UserRecommendationHistorySerializer,
    RecommendationFeedbackSerializer
)

class StationRecommenderView(APIView):
    """
    Get AI-powered station recommendations based on user profile and location
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            # Get location from query params
            lat = float(request.query_params.get('latitude', 0))
            lng = float(request.query_params.get('longitude', 0))
            radius = float(request.query_params.get('radius', 10.0))
            
            if not lat or not lng:
                return Response(
                    {'error': 'Latitude and longitude are required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get recommendations using AI service
            service = AIRecommendationService()
            recommendations = service.get_personalized_recommendations(
                user_id=str(request.user.id),
                user_lat=lat,
                user_lng=lng,
                radius_km=radius
            )
            
            return Response(recommendations)
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserSearchPreferencesView(APIView):
    """Manage user search preferences"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        prefs = firestore_repo.get_search_preferences(request.user.id) or {}
        return Response(prefs)
        
    def put(self, request):
        serializer = UserSearchPreferencesSerializer(data=request.data)
        if serializer.is_valid():
            updated = firestore_repo.update_search_preferences(request.user.id, serializer.validated_data)
            return Response(updated)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StationSentimentAnalysisView(APIView):
    """Get AI sentiment analysis for a station"""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, station_id):
        # Run sentiment analysis
        sentiment_service = SentimentAnalysisService()
        analysis = sentiment_service.analyze_station_reviews(station_id)
        return Response(analysis)

class RecommendationHistoryView(APIView):
    """Get user's recommendation history"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        history = firestore_repo.list_recommendation_history(request.user.id)
        serializer = UserRecommendationHistorySerializer(history, many=True)
        return Response(serializer.data)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def recommendation_feedback(request):
    """Record user feedback on recommendations"""
    serializer = RecommendationFeedbackSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    # Update logic
    firestore_repo.update_recommendation_feedback(
        request.user.id, 
        data['recommendation_id'], 
        {
            f"was_{data['action']}": True,
            f"{data['action']}_at": datetime.now().isoformat(),
            'user_rating': data.get('rating'),
            'feedback_text': data.get('feedback')
        }
    )
    
    return Response({'message': 'Feedback recorded successfully'})
