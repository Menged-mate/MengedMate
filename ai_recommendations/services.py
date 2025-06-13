import math
import json
import re
from decimal import Decimal
from typing import List, Dict, Tuple, Optional
from django.db.models import Q, Avg, Count, F
from django.contrib.gis.measure import Distance
from django.contrib.gis.geos import Point
from django.utils import timezone
from datetime import timedelta

from .models import (
    UserSearchPreferences, 
    StationRecommendationScore, 
    ReviewSentimentAnalysis,
    UserRecommendationHistory
)
from charging_stations.models import ChargingStation, StationReview
from authentication.models import CustomUser


class AIRecommendationService:
    """AI-powered station recommendation service"""
    
    def __init__(self):
        """AI-powered station recommendation service"""
        # Adjust weights to prioritize compatibility and distance
        self.weights = {
            'compatibility': 0.40,  # Increased from 0.25
            'distance': 0.35,      # Increased from 0.20
            'availability': 0.10,  # Reduced from 0.15
            'review_sentiment': 0.05,  # Reduced from 0.15
            'amenities': 0.05,     # Reduced from 0.10
            'price': 0.03,         # Reduced from 0.10
            'reliability': 0.02    # Reduced from 0.05
        }
    
    def get_personalized_recommendations(
        self, 
        user: CustomUser, 
        user_lat: float, 
        user_lng: float,
        radius_km: float = 10.0,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get AI-powered personalized station recommendations
        """
        # Get user preferences
        preferences = self._get_user_preferences(user)
        
        # Get nearby stations
        nearby_stations = self._get_nearby_stations(user_lat, user_lng, radius_km)
        
        # Calculate scores for each station
        recommendations = []
        for station in nearby_stations:
            score_data = self._calculate_station_score(
                user, station, user_lat, user_lng, preferences
            )
            
            if score_data['overall_score'] > 0:
                recommendations.append({
                    'station': station,
                    'score': score_data['overall_score'],
                    'distance_km': score_data['distance_km'],
                    'recommendation_reason': score_data['recommendation_reason'],
                    'score_breakdown': score_data['score_breakdown']
                })
        
        # Sort by score and limit results
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        recommendations = recommendations[:limit]
        
        # Save recommendation history
        self._save_recommendation_history(user, recommendations)
        
        return recommendations
    
    def _get_user_preferences(self, user: CustomUser) -> Dict:
        """Get user preferences with defaults"""
        try:
            prefs = user.search_preferences
        except (UserSearchPreferences.DoesNotExist, AttributeError):
            prefs = UserSearchPreferences.objects.get_or_create(user=user)[0]
        
        return {
            'battery_capacity': user.ev_battery_capacity_kwh or Decimal('50.0'),
            'connector_type': user.ev_connector_type,
            'search_radius': prefs.default_search_radius_km,
            'charging_speed': prefs.preferred_charging_speed,
            'amenities': prefs.get_preferred_amenities(),
            'price_sensitivity': prefs.price_sensitivity,
            'active_vehicle': user.active_vehicle
        }
    
    def _get_nearby_stations(self, lat: float, lng: float, radius_km: float) -> List[ChargingStation]:
        """Get stations within radius"""
        # Simple distance calculation (can be improved with PostGIS)
        stations = ChargingStation.objects.filter(
            status='operational',
            latitude__isnull=False,
            longitude__isnull=False
        ).select_related().prefetch_related('connectors', 'reviews')
        
        nearby_stations = []
        for station in stations:
            distance = self._calculate_distance(
                lat, lng, 
                float(station.latitude), float(station.longitude)
            )
            if distance <= radius_km:
                station.distance_km = distance
                nearby_stations.append(station)
        
        return nearby_stations
    
    def _calculate_station_score(
        self, 
        user: CustomUser, 
        station: ChargingStation, 
        user_lat: float, 
        user_lng: float,
        preferences: Dict
    ) -> Dict:
        """Calculate comprehensive station score"""
        
        # Calculate core scores (compatibility and distance)
        compatibility_score = self._calculate_compatibility_score(station, preferences)
        distance_score = self._calculate_distance_score(station.distance_km, preferences['search_radius'])
        
        # If compatibility score is 0, return immediately with 0 overall score
        if compatibility_score == 0:
            return {
                'overall_score': 0,
                'distance_km': station.distance_km,
                'recommendation_reason': "This station is not compatible with your vehicle's connector type.",
                'score_breakdown': {
                    'compatibility': 0,
                    'distance': float(distance_score),
                    'availability': 0,
                    'review_sentiment': 0,
                    'amenities': 0,
                    'price': 0,
                    'reliability': 0
                }
            }
        
        # Calculate secondary scores
        availability_score = self._calculate_availability_score(station)
        review_sentiment_score = self._calculate_review_sentiment_score(station)
        amenities_score = self._calculate_amenities_score(station, preferences)
        price_score = self._calculate_price_score(station, preferences)
        reliability_score = self._calculate_reliability_score(station)
        
        # Convert weights to Decimal
        weights = {k: Decimal(str(v)) for k, v in self.weights.items()}
        
        # Calculate weighted overall score
        overall_score = (
            compatibility_score * weights['compatibility'] +
            distance_score * weights['distance'] +
            availability_score * weights['availability'] +
            review_sentiment_score * weights['review_sentiment'] +
            amenities_score * weights['amenities'] +
            price_score * weights['price'] +
            reliability_score * weights['reliability']
        )
        
        # Generate recommendation reason based primarily on compatibility and distance
        reason = self._generate_recommendation_reason(
            station, compatibility_score, distance_score, 
            review_sentiment_score, amenities_score
        )
        
        # Save/update score in database
        score_obj, created = StationRecommendationScore.objects.update_or_create(
            user=user,
            station=station,
            defaults={
                'overall_score': overall_score,
                'compatibility_score': compatibility_score,
                'distance_score': distance_score,
                'availability_score': availability_score,
                'review_sentiment_score': review_sentiment_score,
                'amenities_score': amenities_score,
                'price_score': price_score,
                'reliability_score': reliability_score,
                'user_location_lat': Decimal(str(user_lat)),
                'user_location_lng': Decimal(str(user_lng)),
                'recommendation_reason': reason
            }
        )
        
        return {
            'overall_score': float(overall_score),
            'distance_km': station.distance_km,
            'recommendation_reason': reason,
            'score_breakdown': {
                'compatibility': float(compatibility_score),
                'distance': float(distance_score),
                'availability': float(availability_score),
                'review_sentiment': float(review_sentiment_score),
                'amenities': float(amenities_score),
                'price': float(price_score),
                'reliability': float(reliability_score)
            }
        }
    
    def _calculate_compatibility_score(self, station: ChargingStation, preferences: Dict) -> Decimal:
        """Calculate connector and vehicle compatibility score"""
        if not preferences['connector_type'] or preferences['connector_type'] == 'none':
            return Decimal('50.0')  # Neutral score if no preference
        
        compatible_connectors = station.connectors.filter(
            connector_type=preferences['connector_type'],
            status='available'
        )
        
        if compatible_connectors.exists():
            # Check charging speed compatibility
            if preferences['charging_speed'] != 'any':
                speed_ranges = {
                    'slow': (0, 7),
                    'fast': (7, 22),
                    'rapid': (22, 50),
                    'ultra_rapid': (50, 1000)
                }
                min_power, max_power = speed_ranges.get(preferences['charging_speed'], (0, 1000))
                
                suitable_connectors = compatible_connectors.filter(
                    power_kw__gte=min_power,
                    power_kw__lt=max_power
                )
                
                if suitable_connectors.exists():
                    return Decimal('100.0')
                else:
                    return Decimal('70.0')  # Compatible connector but not ideal speed
            else:
                return Decimal('100.0')  # Perfect compatibility
        else:
            return Decimal('0.0')  # No compatible connectors
    
    def _calculate_distance_score(self, distance_km: float, max_radius: Decimal) -> Decimal:
        """Calculate distance-based score (closer = better)"""
        if distance_km <= 1.0:
            return Decimal('100.0')
        elif distance_km <= float(max_radius) * 0.5:
            return Decimal('80.0')
        elif distance_km <= float(max_radius):
            return Decimal(str(100 - (distance_km / float(max_radius)) * 50))
        else:
            return Decimal('0.0')
    
    def _calculate_availability_score(self, station: ChargingStation) -> Decimal:
        """Calculate availability score based on current status"""
        available_connectors = station.connectors.filter(status='available').count()
        total_connectors = station.connectors.count()
        
        if total_connectors == 0:
            return Decimal('0.0')
        
        availability_ratio = available_connectors / total_connectors
        return Decimal(str(availability_ratio * 100))
    
    def _calculate_review_sentiment_score(self, station: ChargingStation) -> Decimal:
        """Calculate score based on AI-analyzed review sentiment"""
        recent_reviews = station.reviews.filter(
            created_at__gte=timezone.now() - timedelta(days=90),
            is_active=True
        )
        
        if not recent_reviews.exists():
            return Decimal('50.0')  # Neutral score for no reviews
        
        # Get sentiment analysis for recent reviews
        sentiment_analyses = ReviewSentimentAnalysis.objects.filter(
            review__in=recent_reviews
        )
        
        if sentiment_analyses.exists():
            avg_sentiment = sentiment_analyses.aggregate(
                avg_sentiment=Avg('overall_sentiment')
            )['avg_sentiment']
            return Decimal(str(float(avg_sentiment) * 100))
        else:
            # Fallback to traditional rating
            avg_rating = recent_reviews.aggregate(avg_rating=Avg('rating'))['avg_rating']
            if avg_rating:
                return Decimal(str((float(avg_rating) / 5.0) * 100))
            return Decimal('50.0')
    
    def _calculate_amenities_score(self, station: ChargingStation, preferences: Dict) -> Decimal:
        """Calculate amenities score based on available facilities"""
        score = Decimal('0.0')
        total_amenities = 0
        
        # Check each amenity
        if station.has_restroom:
            score += Decimal('1.0')
            total_amenities += 1
        if station.has_wifi:
            score += Decimal('1.0')
            total_amenities += 1
        if station.has_restaurant:
            score += Decimal('1.0')
            total_amenities += 1
        if station.has_shopping:
            score += Decimal('1.0')
            total_amenities += 1
        
        # Calculate final score
        if total_amenities > 0:
            score = (score / Decimal(str(total_amenities))) * Decimal('100.0')
        
        return score
    
    def _calculate_price_score(self, station: ChargingStation, preferences: Dict) -> Decimal:
        """Calculate price competitiveness score"""
        # This would need pricing data in the station model
        # For now, return neutral score
        return Decimal('50.0')
    
    def _calculate_reliability_score(self, station: ChargingStation) -> Decimal:
        """Calculate reliability based on historical data"""
        # This would analyze historical uptime, maintenance records, etc.
        # For now, use rating as proxy
        if station.rating_count > 0:
            return Decimal(str((float(station.rating) / 5.0) * 100))
        return Decimal('50.0')
    
    def _generate_recommendation_reason(
        self, 
        station: ChargingStation, 
        compatibility: Decimal, 
        distance: Decimal,
        sentiment: Decimal, 
        amenities: Decimal
    ) -> str:
        """Generate a human-readable recommendation reason"""
        reasons = []
        
        # Always include compatibility and distance information
        if float(compatibility) == 100:
            reasons.append(f"Compatible with your vehicle")
        elif float(compatibility) > 0:
            reasons.append(f"Partially compatible with your vehicle")
            
        if float(distance) >= 80:
            reasons.append(f"Very close to your location ({station.distance_km:.1f} km)")
        elif float(distance) >= 50:
            reasons.append(f"Within reasonable distance ({station.distance_km:.1f} km)")
        else:
            reasons.append(f"{station.distance_km:.1f} km away")
            
        # Add additional information only if scores are significant
        if float(sentiment) > 75:
            reasons.append("Highly rated by users")
        if float(amenities) > 75:
            reasons.append("Good amenities available")
            
        return " • ".join(reasons)
    
    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c

    def _save_recommendation_history(self, user: CustomUser, recommendations: List[Dict]):
        """Save recommendation history for learning"""
        for i, rec in enumerate(recommendations):
            UserRecommendationHistory.objects.create(
                user=user,
                station=rec['station'],
                recommendation_score=Decimal(str(rec['score'])),
                recommendation_rank=i + 1
            )


class SentimentAnalysisService:
    """AI-powered review sentiment analysis service"""

    def __init__(self):
        # Positive and negative keywords for basic sentiment analysis
        self.positive_keywords = [
            'excellent', 'great', 'good', 'fast', 'reliable', 'convenient',
            'clean', 'easy', 'helpful', 'quick', 'efficient', 'perfect',
            'amazing', 'wonderful', 'fantastic', 'smooth', 'working',
            'available', 'accessible', 'friendly', 'professional'
        ]

        self.negative_keywords = [
            'terrible', 'bad', 'slow', 'broken', 'dirty', 'expensive',
            'difficult', 'confusing', 'unreliable', 'unavailable', 'poor',
            'awful', 'horrible', 'useless', 'failed', 'error', 'problem',
            'issue', 'fault', 'maintenance', 'out of order', 'not working'
        ]

        self.aspect_keywords = {
            'charging_speed': ['fast', 'slow', 'quick', 'speed', 'rapid', 'charging time'],
            'reliability': ['reliable', 'working', 'broken', 'maintenance', 'fault', 'error'],
            'location': ['location', 'convenient', 'accessible', 'parking', 'easy to find'],
            'amenities': ['clean', 'facilities', 'restroom', 'cafe', 'shop', 'wifi'],
            'price': ['expensive', 'cheap', 'cost', 'price', 'affordable', 'value']
        }

    def analyze_review(self, review: StationReview) -> Dict:
        """Analyze sentiment of a single review"""
        # Combine review text with any additional rating-specific comments
        text = review.review_text or ""
        
        # Add context from specific ratings if available
        if review.charging_speed_rating:
            text += f" Charging speed: {review.charging_speed_rating}/5."
        if review.location_rating:
            text += f" Location: {review.location_rating}/5."
        if review.amenities_rating:
            text += f" Amenities: {review.amenities_rating}/5."

        # If no text but has rating, create basic sentiment text
        if not text and review.rating:
            rating_sentiments = {
                1: "very poor",
                2: "poor",
                3: "average",
                4: "good",
                5: "excellent"
            }
            text = f"Overall experience was {rating_sentiments.get(review.rating, 'neutral')}"
        elif not text:
            text = "neutral"  # Fallback for completely empty reviews

        # Overall sentiment analysis
        overall_sentiment = self._calculate_overall_sentiment(text)

        # Aspect-based sentiment analysis
        aspect_sentiments = {}
        for aspect, keywords in self.aspect_keywords.items():
            aspect_sentiments[f"{aspect}_sentiment"] = self._calculate_aspect_sentiment(text, keywords)

        # Extract keywords
        positive_keywords = self._extract_keywords(text.lower(), self.positive_keywords)
        negative_keywords = self._extract_keywords(text.lower(), self.negative_keywords)

        # Calculate confidence based on text length and keyword matches
        confidence = self._calculate_confidence(text, positive_keywords, negative_keywords)

        # Adjust overall sentiment based on actual rating if available
        if review.rating:
            rating_sentiment = (review.rating - 1) / 4  # Convert 1-5 to 0-1
            overall_sentiment = (overall_sentiment + rating_sentiment) / 2

        return {
            'overall_sentiment': overall_sentiment,
            'confidence_score': confidence,
            'positive_keywords': positive_keywords,
            'negative_keywords': negative_keywords,
            **aspect_sentiments
        }

    def _calculate_overall_sentiment(self, text: str) -> float:
        """Calculate overall sentiment score (0-1)"""
        positive_count = sum(1 for keyword in self.positive_keywords if keyword in text)
        negative_count = sum(1 for keyword in self.negative_keywords if keyword in text)

        total_sentiment_words = positive_count + negative_count

        if total_sentiment_words == 0:
            return 0.5  # Neutral

        # Calculate sentiment ratio
        sentiment_score = positive_count / total_sentiment_words

        # Adjust based on rating if available
        # This creates a more nuanced score
        return max(0.0, min(1.0, sentiment_score))

    def _calculate_aspect_sentiment(self, text: str, aspect_keywords: List[str]) -> Optional[float]:
        """Calculate sentiment for specific aspect"""
        # Check if aspect is mentioned
        aspect_mentioned = any(keyword in text for keyword in aspect_keywords)

        if not aspect_mentioned:
            return None

        # Find sentences containing aspect keywords
        sentences = text.split('.')
        relevant_sentences = []

        for sentence in sentences:
            if any(keyword in sentence for keyword in aspect_keywords):
                relevant_sentences.append(sentence)

        if not relevant_sentences:
            return None

        # Analyze sentiment in relevant sentences
        relevant_text = ' '.join(relevant_sentences)
        return self._calculate_overall_sentiment(relevant_text)

    def _extract_keywords(self, text: str, keyword_list: List[str]) -> List[str]:
        """Extract keywords found in text"""
        found_keywords = []
        for keyword in keyword_list:
            if keyword in text:
                found_keywords.append(keyword)
        return found_keywords

    def _calculate_confidence(self, text: str, positive_keywords: List[str], negative_keywords: List[str]) -> float:
        """Calculate confidence in sentiment analysis"""
        text_length = len(text.split())
        keyword_count = len(positive_keywords) + len(negative_keywords)

        # Base confidence on text length and keyword density
        length_factor = min(1.0, text_length / 20)  # More confident with longer text
        keyword_factor = min(1.0, keyword_count / 5)  # More confident with more sentiment words

        return (length_factor + keyword_factor) / 2

    def analyze_station_reviews(self, station: ChargingStation) -> Dict:
        """Analyze all reviews for a station"""
        reviews = station.reviews.filter(is_active=True)

        if not reviews.exists():
            return {
                'overall_sentiment': 0.5,
                'review_count': 0,
                'sentiment_distribution': {'positive': 0, 'neutral': 0, 'negative': 0}
            }

        sentiments = []
        for review in reviews:
            analysis = self.analyze_review(review)
            sentiments.append(analysis['overall_sentiment'])

            # Save analysis to database
            ReviewSentimentAnalysis.objects.update_or_create(
                review=review,
                defaults={
                    'overall_sentiment': Decimal(str(analysis['overall_sentiment'])),
                    'charging_speed_sentiment': Decimal(str(analysis.get('charging_speed_sentiment') or 0.5)),
                    'reliability_sentiment': Decimal(str(analysis.get('reliability_sentiment') or 0.5)),
                    'location_sentiment': Decimal(str(analysis.get('location_sentiment') or 0.5)),
                    'amenities_sentiment': Decimal(str(analysis.get('amenities_sentiment') or 0.5)),
                    'price_sentiment': Decimal(str(analysis.get('price_sentiment') or 0.5)),
                    'positive_keywords': json.dumps(analysis['positive_keywords']),
                    'negative_keywords': json.dumps(analysis['negative_keywords']),
                    'confidence_score': Decimal(str(analysis['confidence_score']))
                }
            )

        # Calculate overall statistics
        avg_sentiment = sum(sentiments) / len(sentiments)

        # Sentiment distribution
        positive = sum(1 for s in sentiments if s > 0.6)
        negative = sum(1 for s in sentiments if s < 0.4)
        neutral = len(sentiments) - positive - negative

        return {
            'overall_sentiment': avg_sentiment,
            'review_count': len(sentiments),
            'sentiment_distribution': {
                'positive': positive,
                'neutral': neutral,
                'negative': negative
            }
        }
