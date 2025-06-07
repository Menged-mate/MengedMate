from django.apps import AppConfig


class AiRecommendationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai_recommendations'
    verbose_name = 'AI Recommendations'
    
    def ready(self):
        import ai_recommendations.signals
