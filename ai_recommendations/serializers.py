from rest_framework import serializers
from django.contrib.auth import get_user_model
from decimal import Decimal
from .models import (
    UserSearchPreferences, 
    StationRecommendationScore, 
    ReviewSentimentAnalysis,
    UserRecommendationHistory
)
from charging_stations.serializers import ChargingStationSerializer
from authentication.models import Vehicle

User = get_user_model()


class UserSearchPreferencesSerializer(serializers.ModelSerializer):
    preferred_amenities = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = UserSearchPreferences
        fields = [
            'default_search_radius_km',
            'preferred_charging_speed',
            'preferred_amenities',
            'price_sensitivity',
            'preferred_charging_times'
        ]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['preferred_amenities'] = instance.get_preferred_amenities()
        return data
    
    def to_internal_value(self, data):
        if 'preferred_amenities' in data:
            # Convert list to JSON string for storage
            amenities = data.get('preferred_amenities', [])
            data = data.copy()
            data['preferred_amenities'] = amenities
        return super().to_internal_value(data)
    
    def update(self, instance, validated_data):
        if 'preferred_amenities' in validated_data:
            amenities = validated_data.pop('preferred_amenities')
            instance.set_preferred_amenities(amenities)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class VehicleSerializer(serializers.ModelSerializer):
    efficiency_rating = serializers.CharField(source='get_efficiency_rating', read_only=True)
    connector_types = serializers.SerializerMethodField()
    range_km = serializers.IntegerField(source='estimated_range_km', required=False, allow_null=True)

    class Meta:
        model = Vehicle
        fields = [
            'id', 'name', 'make', 'model', 'year', 'battery_capacity_kwh',
            'connector_type', 'connector_types', 'efficiency_kwh_per_100km', 'range_km',
            'is_primary', 'efficiency_rating', 'total_charging_sessions',
            'total_energy_charged_kwh', 'last_used_at'
        ]
        read_only_fields = ['total_charging_sessions', 'total_energy_charged_kwh', 'last_used_at', 'connector_types']
        extra_kwargs = {
            'name': {'required': True},
            'make': {'required': True},
            'model': {'required': True},
            'year': {'required': True},
            'battery_capacity_kwh': {'required': True},
            'connector_type': {'required': True},
            'efficiency_kwh_per_100km': {'required': False, 'allow_null': True},
            'is_primary': {'required': False, 'default': False}
        }

    def get_connector_types(self, obj):
        """Return connector_type as a list for compatibility with mobile app"""
        if obj.connector_type:
            return [obj.connector_type]
        return []

    def to_internal_value(self, data):
        """Handle connector_types list from mobile app"""
        if 'connector_types' in data and isinstance(data['connector_types'], list):
            # Take the first connector type from the list
            data = data.copy()
            if data['connector_types']:
                data['connector_type'] = data['connector_types'][0]
            data.pop('connector_types', None)
        return super().to_internal_value(data)


class StationRecommendationSerializer(serializers.ModelSerializer):
    station = ChargingStationSerializer(read_only=True)
    distance_km = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    
    class Meta:
        model = StationRecommendationScore
        fields = [
            'station', 'overall_score', 'distance_km',
            'compatibility_score', 'distance_score', 'availability_score',
            'review_sentiment_score', 'amenities_score', 'price_score',
            'reliability_score', 'recommendation_reason', 'calculation_timestamp'
        ]


class ReviewSentimentAnalysisSerializer(serializers.ModelSerializer):
    positive_keywords = serializers.ListField(
        child=serializers.CharField(),
        source='get_positive_keywords',
        read_only=True
    )
    negative_keywords = serializers.ListField(
        child=serializers.CharField(),
        source='get_negative_keywords',
        read_only=True
    )
    
    class Meta:
        model = ReviewSentimentAnalysis
        fields = [
            'overall_sentiment', 'charging_speed_sentiment',
            'reliability_sentiment', 'location_sentiment',
            'amenities_sentiment', 'price_sentiment',
            'positive_keywords', 'negative_keywords',
            'confidence_score', 'analyzed_at'
        ]


class NearbyStationSearchSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=12, decimal_places=8)
    longitude = serializers.DecimalField(max_digits=12, decimal_places=8)
    radius_km = serializers.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('10.00'),
        min_value=Decimal('1.00'),
        max_value=Decimal('100.00'),
        required=False
    )
    connector_type = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True
    )
    charging_speed = serializers.ChoiceField(
        choices=[
            ('slow', 'Slow (3-7 kW)'),
            ('fast', 'Fast (7-22 kW)'),
            ('rapid', 'Rapid (22-50 kW)'),
            ('ultra_rapid', 'Ultra Rapid (50+ kW)'),
            ('any', 'Any Speed')
        ],
        default='any',
        required=False
    )
    amenities = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        allow_null=True
    )
    min_rating = serializers.DecimalField(
        max_digits=3, decimal_places=2,
        min_value=Decimal('0.00'), max_value=Decimal('5.00'),
        required=False,
        allow_null=True
    )
    availability_only = serializers.BooleanField(default=False, required=False)
    sort_by = serializers.ChoiceField(
        choices=[
            ('distance', 'Distance'),
            ('rating', 'Rating'),
            ('recommendation', 'AI Recommendation'),
            ('availability', 'Availability')
        ],
        default='recommendation',
        required=False
    )
    limit = serializers.IntegerField(default=20, min_value=1, max_value=50, required=False)


class RecommendationResponseSerializer(serializers.Serializer):
    station = serializers.DictField(
        child=serializers.CharField(),
        allow_empty=True
    )
    score = serializers.FloatField()
    distance_km = serializers.FloatField()
    recommendation_reason = serializers.CharField()
    score_breakdown = serializers.DictField(
        child=serializers.FloatField(),
        allow_empty=True
    )
    
    # Additional computed fields
    estimated_charging_time = serializers.CharField(read_only=True)
    compatibility_status = serializers.CharField(read_only=True)
    availability_status = serializers.CharField(read_only=True)


class UserRecommendationHistorySerializer(serializers.ModelSerializer):
    station_name = serializers.CharField(source='station.name', read_only=True)
    station_address = serializers.CharField(source='station.address', read_only=True)
    
    class Meta:
        model = UserRecommendationHistory
        fields = [
            'id', 'station_name', 'station_address', 'recommended_at',
            'recommendation_score', 'recommendation_rank', 'was_clicked',
            'was_visited', 'was_used_for_charging', 'user_rating',
            'feedback_text', 'clicked_at', 'visited_at', 'charged_at'
        ]
        read_only_fields = [
            'recommended_at', 'recommendation_score', 'recommendation_rank'
        ]


class RecommendationFeedbackSerializer(serializers.Serializer):
    recommendation_id = serializers.IntegerField()
    action = serializers.ChoiceField(
        choices=['clicked', 'visited', 'charged']
    )
    rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    feedback = serializers.CharField(max_length=500, required=False, allow_blank=True)


class StationSentimentSummarySerializer(serializers.Serializer):
    overall_sentiment = serializers.DecimalField(max_digits=4, decimal_places=3)
    review_count = serializers.IntegerField()
    sentiment_distribution = serializers.DictField()
    top_positive_keywords = serializers.ListField(child=serializers.CharField())
    top_negative_keywords = serializers.ListField(child=serializers.CharField())
    aspect_sentiments = serializers.DictField()


class UserVehicleProfileSerializer(serializers.ModelSerializer):
    vehicles = VehicleSerializer(many=True, read_only=True)
    search_preferences = UserSearchPreferencesSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'ev_battery_capacity_kwh', 'ev_connector_type',
            'active_vehicle', 'vehicles', 'search_preferences'
        ]
        read_only_fields = ['id', 'email']
