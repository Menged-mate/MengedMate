from django.urls import path
from . import views

app_name = 'ai_recommendations'

urlpatterns = [
    # AI Recommendations
    path('recommendations/', views.AIRecommendationsView.as_view(), name='ai-recommendations'),
    
    # User Preferences
    path('preferences/', views.UserSearchPreferencesView.as_view(), name='user-preferences'),
    
    # Vehicle Management
    path('profile/', views.UserVehicleProfileView.as_view(), name='user-vehicle-profile'),
    path('vehicles/', views.UserVehiclesView.as_view(), name='user-vehicles'),
    path('vehicles/<int:pk>/', views.UserVehicleDetailView.as_view(), name='vehicle-detail'),
    path('vehicles/set-active/', views.set_active_vehicle, name='set-active-vehicle'),
    
    # Sentiment Analysis
    path('stations/<int:station_id>/sentiment/', views.StationSentimentAnalysisView.as_view(), name='station-sentiment'),
    
    # Recommendation History & Feedback
    path('history/', views.RecommendationHistoryView.as_view(), name='recommendation-history'),
    path('feedback/', views.recommendation_feedback, name='recommendation-feedback'),
]
