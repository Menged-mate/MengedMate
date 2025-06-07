from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import json

User = get_user_model()


class UserSearchPreferences(models.Model):
    """Store user's search and recommendation preferences"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='search_preferences')
    
    # Search radius preferences
    default_search_radius_km = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('10.00'),
        validators=[MinValueValidator(Decimal('1.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Default search radius in kilometers"
    )
    
    # Charging preferences
    preferred_charging_speed = models.CharField(
        max_length=20,
        choices=[
            ('slow', 'Slow (3-7 kW)'),
            ('fast', 'Fast (7-22 kW)'),
            ('rapid', 'Rapid (22-50 kW)'),
            ('ultra_rapid', 'Ultra Rapid (50+ kW)'),
            ('any', 'Any Speed')
        ],
        default='any'
    )
    
    # Amenity preferences (stored as JSON)
    preferred_amenities = models.TextField(
        blank=True, null=True,
        help_text="JSON array of preferred amenity IDs"
    )
    
    # Price sensitivity
    price_sensitivity = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Price is not important'),
            ('medium', 'Moderate price sensitivity'),
            ('high', 'Very price sensitive')
        ],
        default='medium'
    )
    
    # Time preferences
    preferred_charging_times = models.TextField(
        blank=True, null=True,
        help_text="JSON object with preferred charging time slots"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_preferred_amenities(self):
        if self.preferred_amenities:
            try:
                return json.loads(self.preferred_amenities)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_preferred_amenities(self, amenities_list):
        self.preferred_amenities = json.dumps(amenities_list)
    
    def __str__(self):
        return f"Search Preferences for {self.user.email}"


class StationRecommendationScore(models.Model):
    """AI-calculated recommendation scores for stations"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    station = models.ForeignKey('charging_stations.ChargingStation', on_delete=models.CASCADE)
    
    # Overall recommendation score (0-100)
    overall_score = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))]
    )
    
    # Individual scoring components
    compatibility_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    distance_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    availability_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    review_sentiment_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    amenities_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    price_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    reliability_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Metadata
    calculation_timestamp = models.DateTimeField(auto_now=True)
    user_location_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    user_location_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Recommendation reason (AI-generated explanation)
    recommendation_reason = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ('user', 'station')
        ordering = ['-overall_score', '-calculation_timestamp']
        indexes = [
            models.Index(fields=['user', '-overall_score']),
            models.Index(fields=['station', '-overall_score']),
            models.Index(fields=['-calculation_timestamp']),
        ]
    
    def __str__(self):
        return f"Score {self.overall_score} for {self.station.name} (User: {self.user.email})"


class ReviewSentimentAnalysis(models.Model):
    """AI analysis of station reviews"""
    review = models.OneToOneField('charging_stations.StationReview', on_delete=models.CASCADE)
    
    # Sentiment scores (0-1)
    overall_sentiment = models.DecimalField(
        max_digits=4, decimal_places=3,
        validators=[MinValueValidator(Decimal('0.000')), MaxValueValidator(Decimal('1.000'))],
        help_text="Overall sentiment score (0=negative, 1=positive)"
    )
    
    # Aspect-based sentiment analysis
    charging_speed_sentiment = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    reliability_sentiment = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    location_sentiment = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    amenities_sentiment = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    price_sentiment = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    
    # Extracted keywords and topics
    positive_keywords = models.TextField(blank=True, null=True, help_text="JSON array of positive keywords")
    negative_keywords = models.TextField(blank=True, null=True, help_text="JSON array of negative keywords")
    
    # Confidence score
    confidence_score = models.DecimalField(
        max_digits=4, decimal_places=3, default=Decimal('0.500'),
        help_text="AI confidence in the analysis (0-1)"
    )
    
    # Analysis metadata
    analysis_model_version = models.CharField(max_length=50, default="v1.0")
    analyzed_at = models.DateTimeField(auto_now_add=True)
    
    def get_positive_keywords(self):
        if self.positive_keywords:
            try:
                return json.loads(self.positive_keywords)
            except json.JSONDecodeError:
                return []
        return []
    
    def get_negative_keywords(self):
        if self.negative_keywords:
            try:
                return json.loads(self.negative_keywords)
            except json.JSONDecodeError:
                return []
        return []
    
    def __str__(self):
        return f"Sentiment Analysis for Review {self.review.id} (Score: {self.overall_sentiment})"


class UserRecommendationHistory(models.Model):
    """Track user's recommendation interactions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    station = models.ForeignKey('charging_stations.ChargingStation', on_delete=models.CASCADE)
    
    # Recommendation details
    recommended_at = models.DateTimeField(auto_now_add=True)
    recommendation_score = models.DecimalField(max_digits=5, decimal_places=2)
    recommendation_rank = models.PositiveIntegerField(help_text="Position in recommendation list")
    
    # User interaction
    was_clicked = models.BooleanField(default=False)
    was_visited = models.BooleanField(default=False)
    was_used_for_charging = models.BooleanField(default=False)
    
    # Feedback
    user_rating = models.PositiveIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="User's rating of the recommendation (1-5)"
    )
    
    feedback_text = models.TextField(blank=True, null=True)
    
    # Timestamps
    clicked_at = models.DateTimeField(null=True, blank=True)
    visited_at = models.DateTimeField(null=True, blank=True)
    charged_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-recommended_at']
        indexes = [
            models.Index(fields=['user', '-recommended_at']),
            models.Index(fields=['station', '-recommended_at']),
        ]
    
    def __str__(self):
        return f"Recommendation: {self.station.name} to {self.user.email} (Score: {self.recommendation_score})"
