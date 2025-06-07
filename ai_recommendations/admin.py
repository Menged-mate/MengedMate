from django.contrib import admin
from .models import (
    UserSearchPreferences,
    StationRecommendationScore,
    ReviewSentimentAnalysis,
    UserRecommendationHistory
)


@admin.register(UserSearchPreferences)
class UserSearchPreferencesAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'default_search_radius_km', 'preferred_charging_speed',
        'price_sensitivity', 'created_at', 'updated_at'
    ]
    list_filter = ['preferred_charging_speed', 'price_sensitivity', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Search Preferences', {
            'fields': (
                'default_search_radius_km',
                'preferred_charging_speed',
                'preferred_amenities',
                'price_sensitivity'
            )
        }),
        ('Time Preferences', {
            'fields': ('preferred_charging_times',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(StationRecommendationScore)
class StationRecommendationScoreAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'station', 'overall_score', 'compatibility_score',
        'distance_score', 'calculation_timestamp'
    ]
    list_filter = [
        'calculation_timestamp', 'overall_score', 'compatibility_score'
    ]
    search_fields = [
        'user__email', 'station__name', 'station__address'
    ]
    readonly_fields = ['calculation_timestamp']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'station', 'overall_score')
        }),
        ('Score Breakdown', {
            'fields': (
                'compatibility_score', 'distance_score', 'availability_score',
                'review_sentiment_score', 'amenities_score', 'price_score',
                'reliability_score'
            )
        }),
        ('Location Data', {
            'fields': ('user_location_lat', 'user_location_lng'),
            'classes': ('collapse',)
        }),
        ('AI Analysis', {
            'fields': ('recommendation_reason',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('calculation_timestamp',),
            'classes': ('collapse',)
        })
    )


@admin.register(ReviewSentimentAnalysis)
class ReviewSentimentAnalysisAdmin(admin.ModelAdmin):
    list_display = [
        'review', 'overall_sentiment', 'confidence_score',
        'analysis_model_version', 'analyzed_at'
    ]
    list_filter = [
        'overall_sentiment', 'confidence_score', 'analysis_model_version',
        'analyzed_at'
    ]
    search_fields = [
        'review__station__name', 'review__user__email',
        'review__comment', 'review__title'
    ]
    readonly_fields = ['analyzed_at']
    
    fieldsets = (
        ('Review Info', {
            'fields': ('review',)
        }),
        ('Overall Sentiment', {
            'fields': ('overall_sentiment', 'confidence_score')
        }),
        ('Aspect Sentiments', {
            'fields': (
                'charging_speed_sentiment', 'reliability_sentiment',
                'location_sentiment', 'amenities_sentiment', 'price_sentiment'
            ),
            'classes': ('collapse',)
        }),
        ('Keywords', {
            'fields': ('positive_keywords', 'negative_keywords'),
            'classes': ('collapse',)
        }),
        ('Analysis Metadata', {
            'fields': ('analysis_model_version', 'analyzed_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(UserRecommendationHistory)
class UserRecommendationHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'station', 'recommendation_score', 'recommendation_rank',
        'was_clicked', 'was_visited', 'was_used_for_charging',
        'user_rating', 'recommended_at'
    ]
    list_filter = [
        'was_clicked', 'was_visited', 'was_used_for_charging',
        'user_rating', 'recommended_at'
    ]
    search_fields = [
        'user__email', 'station__name', 'feedback_text'
    ]
    readonly_fields = ['recommended_at']
    
    fieldsets = (
        ('Recommendation Info', {
            'fields': (
                'user', 'station', 'recommendation_score',
                'recommendation_rank', 'recommended_at'
            )
        }),
        ('User Interactions', {
            'fields': (
                'was_clicked', 'clicked_at',
                'was_visited', 'visited_at',
                'was_used_for_charging', 'charged_at'
            )
        }),
        ('User Feedback', {
            'fields': ('user_rating', 'feedback_text'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'station'
        )
