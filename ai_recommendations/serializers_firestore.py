from rest_framework import serializers

class UserSearchPreferencesSerializer(serializers.Serializer):
    preferred_connector_types = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    min_power_output_kw = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, allow_null=True
    )
    max_price_per_kwh = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, allow_null=True
    )
    preferred_networks = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    amenities = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    
class UserRecommendationHistorySerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    station_id = serializers.CharField()
    station_name = serializers.CharField(required=False)
    recommended_reason = serializers.CharField(required=False)
    score = serializers.FloatField(required=False)
    
    was_clicked = serializers.BooleanField(default=False)
    was_visited = serializers.BooleanField(default=False)
    was_used_for_charging = serializers.BooleanField(default=False)
    
    clicked_at = serializers.DateTimeField(required=False, allow_null=True)
    visited_at = serializers.DateTimeField(required=False, allow_null=True)
    charged_at = serializers.DateTimeField(required=False, allow_null=True)
    
    user_rating = serializers.IntegerField(required=False, allow_null=True)
    feedback_text = serializers.CharField(required=False, allow_blank=True)
    
    recommended_at = serializers.DateTimeField(read_only=True)
    
class RecommendationFeedbackSerializer(serializers.Serializer):
    recommendation_id = serializers.CharField()
    action = serializers.ChoiceField(choices=['clicked', 'visited', 'charged'])
    rating = serializers.IntegerField(required=False, min_value=1, max_value=5)
    feedback = serializers.CharField(required=False, allow_blank=True)
