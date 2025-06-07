from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from charging_stations.models import ChargingStation, StationReview
from authentication.models import Vehicle
from .models import UserSearchPreferences, ReviewSentimentAnalysis
from .services import AIRecommendationService, SentimentAnalysisService

User = get_user_model()


class AIRecommendationServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            ev_battery_capacity_kwh=Decimal('75.0'),
            ev_connector_type='type2'
        )
        
        self.station = ChargingStation.objects.create(
            name='Test Station',
            address='123 Test St',
            latitude=Decimal('9.0222'),
            longitude=Decimal('38.7468'),
            status='active',
            owner=self.user
        )
        
        self.ai_service = AIRecommendationService()
    
    def test_get_user_preferences(self):
        """Test getting user preferences with defaults"""
        preferences = self.ai_service._get_user_preferences(self.user)
        
        self.assertEqual(preferences['battery_capacity'], Decimal('75.0'))
        self.assertEqual(preferences['connector_type'], 'type2')
        self.assertIsInstance(preferences['search_radius'], Decimal)
    
    def test_calculate_distance(self):
        """Test distance calculation"""
        # Distance between Addis Ababa coordinates
        lat1, lng1 = 9.0222, 38.7468
        lat2, lng2 = 9.0322, 38.7568
        
        distance = self.ai_service._calculate_distance(lat1, lng1, lat2, lng2)
        
        self.assertIsInstance(distance, float)
        self.assertGreater(distance, 0)
        self.assertLess(distance, 2)  # Should be less than 2km
    
    def test_compatibility_score(self):
        """Test connector compatibility scoring"""
        preferences = {
            'connector_type': 'type2',
            'charging_speed': 'fast'
        }
        
        score = self.ai_service._calculate_compatibility_score(self.station, preferences)
        
        self.assertIsInstance(score, Decimal)
        self.assertGreaterEqual(score, Decimal('0.0'))
        self.assertLessEqual(score, Decimal('100.0'))


class SentimentAnalysisServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.station = ChargingStation.objects.create(
            name='Test Station',
            address='123 Test St',
            latitude=Decimal('9.0222'),
            longitude=Decimal('38.7468'),
            status='active',
            owner=self.user
        )
        
        self.sentiment_service = SentimentAnalysisService()
    
    def test_positive_sentiment_analysis(self):
        """Test analysis of positive review"""
        review = StationReview.objects.create(
            user=self.user,
            station=self.station,
            rating=5,
            title="Excellent charging station",
            comment="This station is excellent! Fast charging, clean facilities, and very reliable. Great location too!"
        )
        
        analysis = self.sentiment_service.analyze_review(review)
        
        self.assertGreater(analysis['overall_sentiment'], 0.6)
        self.assertIn('excellent', analysis['positive_keywords'])
        self.assertIn('fast', analysis['positive_keywords'])
        self.assertGreater(analysis['confidence_score'], 0.5)
    
    def test_negative_sentiment_analysis(self):
        """Test analysis of negative review"""
        review = StationReview.objects.create(
            user=self.user,
            station=self.station,
            rating=2,
            title="Terrible experience",
            comment="This station is terrible. Slow charging, broken connectors, and dirty facilities. Very unreliable!"
        )
        
        analysis = self.sentiment_service.analyze_review(review)
        
        self.assertLess(analysis['overall_sentiment'], 0.4)
        self.assertIn('terrible', analysis['negative_keywords'])
        self.assertIn('broken', analysis['negative_keywords'])
        self.assertGreater(analysis['confidence_score'], 0.5)
    
    def test_neutral_sentiment_analysis(self):
        """Test analysis of neutral review"""
        review = StationReview.objects.create(
            user=self.user,
            station=self.station,
            rating=3,
            title="Average station",
            comment="The station works fine. Nothing special but gets the job done."
        )
        
        analysis = self.sentiment_service.analyze_review(review)
        
        self.assertGreaterEqual(analysis['overall_sentiment'], 0.4)
        self.assertLessEqual(analysis['overall_sentiment'], 0.6)
    
    def test_aspect_sentiment_analysis(self):
        """Test aspect-based sentiment analysis"""
        review = StationReview.objects.create(
            user=self.user,
            station=self.station,
            rating=4,
            title="Good station with fast charging",
            comment="The charging speed is excellent and very fast. Location is convenient but the facilities are dirty."
        )
        
        analysis = self.sentiment_service.analyze_review(review)
        
        # Should detect positive sentiment for charging speed
        self.assertIsNotNone(analysis.get('charging_speed_sentiment'))
        if analysis.get('charging_speed_sentiment'):
            self.assertGreater(analysis['charging_speed_sentiment'], 0.6)
        
        # Should detect negative sentiment for amenities (dirty facilities)
        self.assertIsNotNone(analysis.get('amenities_sentiment'))


class UserSearchPreferencesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_preferences(self):
        """Test creating user search preferences"""
        preferences = UserSearchPreferences.objects.create(
            user=self.user,
            default_search_radius_km=Decimal('15.0'),
            preferred_charging_speed='fast',
            price_sensitivity='medium'
        )
        
        self.assertEqual(preferences.user, self.user)
        self.assertEqual(preferences.default_search_radius_km, Decimal('15.0'))
        self.assertEqual(preferences.preferred_charging_speed, 'fast')
    
    def test_amenities_json_handling(self):
        """Test JSON handling for preferred amenities"""
        preferences = UserSearchPreferences.objects.create(
            user=self.user
        )
        
        amenities = [1, 2, 3, 4]
        preferences.set_preferred_amenities(amenities)
        preferences.save()
        
        retrieved_amenities = preferences.get_preferred_amenities()
        self.assertEqual(retrieved_amenities, amenities)


class VehicleModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_vehicle(self):
        """Test creating a vehicle"""
        vehicle = Vehicle.objects.create(
            user=self.user,
            name='My Tesla',
            make='Tesla',
            model='Model 3',
            year=2023,
            battery_capacity_kwh=Decimal('75.0'),
            efficiency_kwh_per_100km=Decimal('15.0'),
            range_km=500,
            is_primary=True
        )
        
        self.assertEqual(vehicle.user, self.user)
        self.assertEqual(vehicle.name, 'My Tesla')
        self.assertTrue(vehicle.is_primary)
    
    def test_efficiency_rating(self):
        """Test efficiency rating calculation"""
        vehicle = Vehicle.objects.create(
            user=self.user,
            name='Efficient Car',
            efficiency_kwh_per_100km=Decimal('12.0')
        )
        
        rating = vehicle.get_efficiency_rating()
        self.assertEqual(rating, 'Excellent')
        
        vehicle.efficiency_kwh_per_100km = Decimal('18.0')
        rating = vehicle.get_efficiency_rating()
        self.assertEqual(rating, 'Good')
        
        vehicle.efficiency_kwh_per_100km = Decimal('30.0')
        rating = vehicle.get_efficiency_rating()
        self.assertEqual(rating, 'Poor')
