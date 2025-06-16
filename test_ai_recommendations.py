#!/usr/bin/env python3
import os
import django
import json
from datetime import datetime, timedelta
import random
from decimal import Decimal

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mengedmate.settings')
django.setup()

from django.contrib.auth import get_user_model
from authentication.models import CustomUser, Vehicle
from charging_stations.models import ChargingStation, ChargingConnector, StationOwner
from ocpp_integration.models import ChargingSession, OCPPStation, OCPPConnector
from ai_recommendations.models import UserSearchPreferences, StationRecommendationScore, UserRecommendationHistory
from ai_recommendations.services import AIRecommendationService
from django.utils import timezone

User = get_user_model()

def create_test_user():
    """Create a test user"""
    user, created = User.objects.get_or_create(
        email="test@example.com",
        defaults={
            'first_name': 'Test',
            'last_name': 'User',
            'is_verified': True,
            'password': 'testpass123'  # This will be hashed by Django
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
    return user

def create_test_vehicle(user):
    """Create a test vehicle for the user"""
    vehicle, created = Vehicle.objects.get_or_create(
        user=user,
        defaults={
            'name': 'Test Tesla',
            'make': 'Tesla',
            'model': 'Model 3',
            'year': 2023,
            'battery_capacity_kwh': Decimal('75.00'),
            'connector_type': 'tesla',
            'max_charging_speed_kw': Decimal('250.00'),
            'estimated_range_km': 500,
            'is_primary': True,
            'is_active': True,
        }
    )
    return vehicle

def create_test_stations():
    """Create test charging stations with different characteristics"""
    stations = []
    
    # Create stations with different characteristics
    station_data = [
        {
            'name': 'Downtown Station',
            'address': '123 Main St',
            'latitude': 9.0320,
            'longitude': 38.7489,
            'rating': 4.5,
            'connectors': [
                {'type': 'tesla', 'power_kw': Decimal('250.00')},
                {'type': 'ccs2', 'power_kw': Decimal('150.00')},
            ]
        },
        {
            'name': 'Airport Station',
            'address': '456 Airport Rd',
            'latitude': 8.9779,
            'longitude': 38.7993,
            'rating': 4.2,
            'connectors': [
                {'type': 'tesla', 'power_kw': Decimal('150.00')},
                {'type': 'type2', 'power_kw': Decimal('22.00')},
            ]
        },
        {
            'name': 'Shopping Mall Station',
            'address': '789 Mall Ave',
            'latitude': 9.0123,
            'longitude': 38.7567,
            'rating': 4.0,
            'connectors': [
                {'type': 'type2', 'power_kw': Decimal('11.00')},
                {'type': 'ccs2', 'power_kw': Decimal('50.00')},
            ]
        }
    ]
    
    # Get or create a station owner
    owner_user, _ = User.objects.get_or_create(
        email="station_owner@example.com",
        defaults={
            'first_name': 'Station',
            'last_name': 'Owner',
            'is_verified': True,
            'password': 'testpass123'
        }
    )
    if not owner_user.has_usable_password():
        owner_user.set_password('testpass123')
        owner_user.save()
    
    # Create StationOwner instance
    owner, _ = StationOwner.objects.get_or_create(
        user=owner_user,
        defaults={
            'company_name': 'Test Charging Network',
            'business_registration_number': 'BRN123456',
            'verification_status': 'verified',
            'contact_phone': '+251912345678',
            'contact_email': 'contact@testcharging.com',
            'website': 'https://testcharging.com',
            'description': 'Test charging network for development',
            'is_profile_completed': True
        }
    )
    
    for data in station_data:
        station, created = ChargingStation.objects.get_or_create(
            name=data['name'],
            defaults={
                'owner': owner,
                'address': data['address'],
                'latitude': data['latitude'],
                'longitude': data['longitude'],
                'rating': data['rating'],
                'rating_count': random.randint(10, 100),
                'is_active': True,
                'city': 'Addis Ababa',
                'state': 'Addis Ababa',
                'zip_code': '1000',
                'country': 'Ethiopia',
                'status': 'operational'
            }
        )
        
        # Create connectors for the station
        for connector_data in data['connectors']:
            ChargingConnector.objects.get_or_create(
                station=station,
                connector_type=connector_data['type'],
                defaults={
                    'power_kw': connector_data['power_kw'],
                    'status': 'available',
                    'price_per_kwh': Decimal(str(random.uniform(0.3, 0.5))),
                    'quantity': 1,
                    'available_quantity': 1,
                    'is_available': True
                }
            )
        
        stations.append(station)
    
    return stations

def create_test_charging_sessions(user, vehicle, stations):
    """Create test charging sessions to generate usage patterns"""
    sessions = []
    
    # Create sessions over the last 30 days
    for i in range(10):
        start_time = timezone.now() - timedelta(days=random.randint(1, 30))
        duration = random.randint(30, 180)  # 30 minutes to 3 hours
        stop_time = start_time + timedelta(minutes=duration)
        
        station = random.choice(stations)
        connector = random.choice(station.connectors.all())
        
        # Create OCPP station and connector if they don't exist
        ocpp_station, _ = OCPPStation.objects.get_or_create(
            station_id=f"TEST_STATION_{station.id}",
            defaults={
                'charging_station': station,
                'status': 'available',
                'is_online': True
            }
        )
        
        ocpp_connector, _ = OCPPConnector.objects.get_or_create(
            ocpp_station=ocpp_station,
            connector_id=1,
            defaults={
                'charging_connector': connector,
                'status': 'available'
            }
        )
        
        session = ChargingSession.objects.create(
            transaction_id=random.randint(1000, 9999),
            user=user,
            ocpp_station=ocpp_station,
            ocpp_connector=ocpp_connector,
            id_tag=f"TEST_TAG_{user.id}",
            status='completed',
            payment_status='completed',
            start_time=start_time,
            stop_time=stop_time,
            duration_seconds=int((stop_time - start_time).total_seconds()),
            energy_consumed_kwh=Decimal(str(random.uniform(10.0, 50.0))),
            current_power_kw=Decimal(str(random.uniform(10.0, 50.0))),
            max_power_kw=Decimal(str(random.uniform(50.0, 250.0))),
            estimated_cost=Decimal(str(random.uniform(5.0, 25.0))),
            final_cost=Decimal(str(random.uniform(5.0, 25.0))),
            meter_start=random.randint(1000, 9999),
            meter_stop=random.randint(10000, 99999)
        )
        sessions.append(session)
    
    return sessions

def create_test_user_preferences(user):
    """Create test user preferences"""
    preferences = {
        'preferred_connector_types': ['tesla', 'ccs2'],
        'preferred_charging_speeds': ['ultra_rapid', 'rapid'],
        'preferred_price_range': {'min': 0.3, 'max': 0.5},
        'preferred_amenities': ['restroom', 'coffee_shop'],
        'preferred_charging_times': ['morning', 'evening'],
        'preferred_station_types': ['public', 'commercial'],
    }
    
    UserSearchPreferences.objects.update_or_create(
        user=user,
        defaults={
            'preferred_charging_speed': 'ultra_rapid',
            'preferred_amenities': json.dumps(['restroom', 'coffee_shop']),
            'price_sensitivity': 'medium',
            'preferred_charging_times': json.dumps({
                'morning': True,
                'evening': True
            })
        }
    )

def create_test_station_ratings(user, stations):
    """Create test station ratings"""
    for station in stations:
        StationRecommendationScore.objects.update_or_create(
            user=user,
            station=station,
            defaults={
                'overall_score': Decimal(str(random.uniform(70.0, 95.0))),
                'compatibility_score': Decimal(str(random.uniform(70.0, 95.0))),
                'distance_score': Decimal(str(random.uniform(70.0, 95.0))),
                'availability_score': Decimal(str(random.uniform(70.0, 95.0))),
                'review_sentiment_score': Decimal(str(random.uniform(70.0, 95.0))),
                'amenities_score': Decimal(str(random.uniform(70.0, 95.0))),
                'price_score': Decimal(str(random.uniform(70.0, 95.0))),
                'reliability_score': Decimal(str(random.uniform(70.0, 95.0))),
                'recommendation_reason': "Great station with fast charging and good amenities!"
            }
        )

def create_test_recommendation_history(user, stations):
    """Create test recommendation history"""
    for i, station in enumerate(stations):
        UserRecommendationHistory.objects.create(
            user=user,
            station=station,
            recommendation_score=Decimal(str(random.uniform(70.0, 95.0))),
            recommendation_rank=i+1,
            was_clicked=random.choice([True, False]),
            was_visited=random.choice([True, False]),
            was_used_for_charging=random.choice([True, False])
        )

def test_ai_recommendations():
    """Main test function"""
    print("Starting AI recommendations test...")
    
    # Create test data
    user = create_test_user()
    print(f"Created test user: {user.email}")
    
    vehicle = create_test_vehicle(user)
    print(f"Created test vehicle: {vehicle.name}")
    
    stations = create_test_stations()
    print(f"Created {len(stations)} test stations")
    
    sessions = create_test_charging_sessions(user, vehicle, stations)
    print(f"Created {len(sessions)} test charging sessions")
    
    create_test_user_preferences(user)
    print("Created user preferences")
    
    create_test_station_ratings(user, stations)
    print("Created station ratings")
    
    create_test_recommendation_history(user, stations)
    print("Created recommendation history")
    
    # Test AI recommendations
    print("\nTesting AI recommendations...")
    
    # Get user's current location (using a sample location in Addis Ababa)
    current_location = {
        'latitude': 9.0320,
        'longitude': 38.7489
    }
    
    # Initialize AI recommendation service
    ai_service = AIRecommendationService()
    
    # Get recommendations
    try:
        recommendations = ai_service.get_personalized_recommendations(
            user=user,
            user_lat=current_location['latitude'],
            user_lng=current_location['longitude'],
            radius_km=10
        )
        
        print("\nAI Recommendations:")
        for i, rec in enumerate(recommendations, 1):
            station = rec['station']
            print(f"\n{i}. {station.name}")
            print(f"   Address: {station.address}")
            print(f"   Distance: {rec['distance_km']:.1f} km")
            print(f"   Rating: {station.rating:.1f} ⭐")
            print(f"   Available Connectors: {station.available_connectors}/{station.total_connectors}")
            print(f"   AI Score: {rec['score']:.2f}")
            print(f"   AI Reason: {rec['recommendation_reason']}")
            
    except Exception as e:
        print(f"Error testing recommendations: {str(e)}")
    
    print("\nTest completed!")

if __name__ == '__main__':
    test_ai_recommendations() 