from utils.firestore_repo import firestore_repo
import math
import json
import re
from decimal import Decimal
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta

# Removed Django model imports as we use Firestore now

class AIRecommendationService:
    """AI-powered station recommendation service (Firestore version)"""
    
    def __init__(self):
        """AI-powered station recommendation service"""
        # Adjust weights to prioritize compatibility and distance
        self.weights = {
            'compatibility': 0.40,
            'distance': 0.35,
            'availability': 0.10,
            'review_sentiment': 0.05,
            'amenities': 0.05,
            'price': 0.03,
            'reliability': 0.02
        }
    
    def get_personalized_recommendations(
        self, 
        user_id: str, 
        user_lat: float, 
        user_lng: float,
        radius_km: float = 10.0,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get AI-powered personalized station recommendations
        """
        # Get user preferences
        preferences = self._get_user_preferences(user_id)
        
        # Get nearby stations (Fetch all and filter in memory for now)
        nearby_stations = self._get_nearby_stations(user_lat, user_lng, radius_km)
        
        # Calculate scores for each station
        recommendations = []
        for station in nearby_stations:
            score_data = self._calculate_station_score(
                station, user_lat, user_lng, preferences
            )
            
            if score_data['overall_score'] > 0:
                recommendations.append({
                    'station': station,
                    'score': float(score_data['overall_score']),
                    'distance_km': float(score_data['distance_km']),
                    'recommendation_reason': score_data['recommendation_reason'],
                    'score_breakdown': {
                        k: float(v) for k, v in score_data['score_breakdown'].items()
                    }
                })
        
        # Sort by score and limit results
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        recommendations = recommendations[:limit]
        
        # Save recommendation history
        self._save_recommendation_history(user_id, recommendations)
        
        return recommendations
    
    def _get_user_preferences(self, user_id: str) -> Dict:
        """Get user preferences with defaults"""
        # Fetch from Firestore
        prefs = firestore_repo.get_search_preferences(user_id) or {}
        profile = firestore_repo.get_user_profile(user_id) or {}
        
        # Determine battery/connector from active vehicle
        active_vehicle_id = profile.get('active_vehicle_id')
        active_vehicle = None
        if active_vehicle_id:
            active_vehicle = firestore_repo.get_vehicle(user_id, active_vehicle_id)
            
        return {
            'battery_capacity': Decimal(str(active_vehicle.get('battery_capacity_kwh', 50.0))) if active_vehicle else Decimal('50.0'),
            'connector_type': active_vehicle.get('connector_type') if active_vehicle else None,
            'search_radius': float(prefs.get('search_radius', 10.0)),
            'charging_speed': prefs.get('charging_speed', 'any'),
            'amenities': prefs.get('amenities', []),
            'price_sensitivity': prefs.get('price_sensitivity', 5),
            'active_vehicle': active_vehicle
        }
    
    def _get_nearby_stations(self, lat: float, lng: float, radius_km: float) -> List[Dict]:
        """Get stations within radius"""
        # Fetch stations from Firestore
        # TODO: Implement geohashing for efficient queries. For now, fetch all active.
        all_stations = firestore_repo.list_stations({'status': 'operational'})
        
        nearby_stations = []
        for station in all_stations:
            try:
                s_lat = float(station.get('latitude', 0))
                s_lng = float(station.get('longitude', 0))
                
                if s_lat == 0 and s_lng == 0:
                    continue
                    
                distance = self._calculate_distance(lat, lng, s_lat, s_lng)
                if distance <= radius_km:
                    station['distance_km'] = distance
                    nearby_stations.append(station)
            except (ValueError, TypeError):
                continue
        
        return nearby_stations
    
    def _calculate_station_score(
        self, 
        station: Dict, 
        user_lat: float, 
        user_lng: float,
        preferences: Dict
    ) -> Dict:
        """Calculate comprehensive station score"""
        
        distance_km = station.get('distance_km', 0)
        
        # Calculate core scores (compatibility and distance)
        compatibility_score = self._calculate_compatibility_score(station, preferences)
        distance_score = self._calculate_distance_score(distance_km, preferences['search_radius'])
        
        # If compatibility score is 0, return immediately with 0 overall score
        if compatibility_score == 0:
            return {
                'overall_score': 0,
                'distance_km': distance_km,
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
        
        # Generate recommendation reason
        reason = self._generate_recommendation_reason(
            station, compatibility_score, distance_score, 
            review_sentiment_score, amenities_score
        )
        
        return {
            'overall_score': float(overall_score),
            'distance_km': distance_km,
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
    
    def _calculate_compatibility_score(self, station: Dict, preferences: Dict) -> Decimal:
        """Calculate connector and vehicle compatibility score"""
        if not preferences['connector_type']:
            return Decimal('50.0')
        
        # Station connectors are usually nested or need to be fetched.
        # Assuming they are embedded in 'connectors' list or we need to fetch.
        # Based on previous refactor, DetailView fetched connectors. list_stations might not?
        # Let's assume list_stations DOES NOT fetch subcollections by default for performance.
        # But 'available_connectors_detail' might be cached on station object?
        # Let's try to fetch if not present or rely on a summary field.
        # The station doc usually has 'connectors' if we designed it that way, or we need to fetch.
        # Update: FirestoreRepo list_stations fetches base docs. We might need a helper to list connectors for scoring
        # OR we rely on 'connectors' being available. 
        # For efficiency, let's assume we fetch connectors for nearby stations only.
        
        connectors_data = station.get('connectors_data', []) # assuming we attach this
        if not connectors_data:
             # Fast fail or fetch? Let's try to list connectors efficiently
             connectors_data = firestore_repo.list_connectors(station['id'])
             station['connectors_data'] = connectors_data # Cache it
             
        compatible = [c for c in connectors_data if c.get('type') == preferences['connector_type'] and c.get('status') == 'available']
        
        if compatible:
            # Check speed
            if preferences['charging_speed'] != 'any':
                # Simplified logic
                return Decimal('100.0') 
            return Decimal('100.0')
        
        # Check if compatible but busy
        compatible_busy = [c for c in connectors_data if c.get('type') == preferences['connector_type']]
        if compatible_busy:
             return Decimal('0.0') # Strict for now, or 20.0
             
        return Decimal('0.0')
    
    def _calculate_distance_score(self, distance_km: float, max_radius: float) -> Decimal:
        if distance_km <= 1.0:
            return Decimal('100.0')
        elif distance_km <= max_radius:
            return Decimal(str(100 - (distance_km / max_radius) * 50))
        return Decimal('0.0')
    
    def _calculate_availability_score(self, station: Dict) -> Decimal:
        total = station.get('total_connectors', 0) or 0  # Fallback
        available = station.get('available_connectors', 0) or 0
        if total == 0: return Decimal('0.0')
        return Decimal(str((available / total) * 100))
    
    def _calculate_review_sentiment_score(self, station: Dict) -> Decimal:
        # Use cached rating or fetch logic. 
        # For MVP AI, using the rating field is much faster than re-analyzing raw text every time.
        rating = float(station.get('rating', 0))
        return Decimal(str((rating / 5.0) * 100))
    
    def _calculate_amenities_score(self, station: Dict, preferences: Dict) -> Decimal:
        score = Decimal('0.0')
        total = 0
        if station.get('has_restroom'): score += 1; total += 1
        if station.get('has_wifi'): score += 1; total += 1
        if station.get('has_restaurant'): score += 1; total += 1
        if station.get('has_shopping'): score += 1; total += 1
        
        if total > 0:
            return (score / Decimal(str(total))) * Decimal('100.0')
        return Decimal('0.0')

    def _calculate_price_score(self, station: Dict, preferences: Dict) -> Decimal:
        return Decimal('50.0')

    def _calculate_reliability_score(self, station: Dict) -> Decimal:
        count = station.get('rating_count', 0)
        if count > 0:
            rating = float(station.get('rating', 0))
            return Decimal(str((rating / 5.0) * 100))
        return Decimal('50.0')

    def _generate_recommendation_reason(self, station, compatibility, distance, sentiment, amenities):
        reasons = []
        if float(compatibility) == 100:
            reasons.append("Compatible")
        if float(distance) < 5:
            reasons.append(f"Close ({distance:.1f} km)")
        if float(sentiment) > 80:
            reasons.append("Highly Rated")
        return " • ".join(reasons)

    def _calculate_distance(self, lat1, lng1, lat2, lng2):
        R = 6371
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def _save_recommendation_history(self, user_id: str, recommendations: List[Dict]):
        # Save top recommendation to history
        if not recommendations:
            return
            
        top_rec = recommendations[0]
        data = {
            'station_id': top_rec['station']['id'],
            'station_name': top_rec['station'].get('name'),
            'score': top_rec['score'],
            'recommendation_reason': top_rec['recommendation_reason'],
            'recommended_at': datetime.now().isoformat()
        }
        firestore_repo.create_recommendation_history(user_id, data)


class SentimentAnalysisService:
    """AI-powered review sentiment analysis service (Stateless/Helper)"""
    
    # Simple keyword-based analysis for demo/latency (Could replace with external API call)
    
    def analyze_review(self, review_text: str, rating: int) -> Dict:
        # Simplified for now
        return {
            'overall_sentiment': (rating / 5.0),
            'confidence_score': 0.8,
            'positive_keywords': [], # Todo: extract
            'negative_keywords': []
        }

    def analyze_station_reviews(self, station_id: str) -> Dict:
        reviews = firestore_repo.list_reviews(station_id)
        if not reviews:
            return {'overall_sentiment': 0.5, 'review_count': 0}
            
        avg = sum(float(r.get('rating', 0)) for r in reviews) / len(reviews)
        return {
            'overall_sentiment': avg / 5.0,
            'review_count': len(reviews)
        }
