from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from charging_stations.models import StationReview
from .models import ReviewSentimentAnalysis
from .services import SentimentAnalysisService


@receiver(post_save, sender=StationReview)
def analyze_review_sentiment(sender, instance, created, **kwargs):
    """Automatically analyze sentiment when a new review is created"""
    if created and instance.is_active:
        # Run sentiment analysis in background (could be moved to Celery task)
        sentiment_service = SentimentAnalysisService()
        analysis_data = sentiment_service.analyze_review(instance)
        
        # Save sentiment analysis
        ReviewSentimentAnalysis.objects.create(
            review=instance,
            overall_sentiment=analysis_data['overall_sentiment'],
            charging_speed_sentiment=analysis_data.get('charging_speed_sentiment'),
            reliability_sentiment=analysis_data.get('reliability_sentiment'),
            location_sentiment=analysis_data.get('location_sentiment'),
            amenities_sentiment=analysis_data.get('amenities_sentiment'),
            price_sentiment=analysis_data.get('price_sentiment'),
            positive_keywords=analysis_data['positive_keywords'],
            negative_keywords=analysis_data['negative_keywords'],
            confidence_score=analysis_data['confidence_score']
        )


@receiver(post_delete, sender=StationReview)
def cleanup_sentiment_analysis(sender, instance, **kwargs):
    """Clean up sentiment analysis when review is deleted"""
    try:
        sentiment_analysis = ReviewSentimentAnalysis.objects.get(review=instance)
        sentiment_analysis.delete()
    except ReviewSentimentAnalysis.DoesNotExist:
        pass
