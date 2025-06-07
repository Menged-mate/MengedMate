#!/usr/bin/env python3

import os
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mengedmate.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from ai_recommendations.serializers import NearbyStationSearchSerializer
from ai_recommendations.services import AIRecommendationService

User = get_user_model()

def test_ai_recommendations():
    print("🧪 Testing AI Recommendations...")
    
    # Get or create test user
    user, created = User.objects.get_or_create(
        email='test@example.com',
        defaults={
            'first_name': 'Test',
            'last_name': 'User',
            'is_verified': True,
            'ev_battery_capacity_kwh': 75.0,
            'ev_connector_type': 'type2'
        }
    )
    
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"✅ Created test user: {user.email}")
    else:
        print(f"✅ Using existing user: {user.email}")
    
    # Test serializer validation
    print("\n📝 Testing serializer validation...")
    
    test_data = {
        'latitude': 9.0222,
        'longitude': 38.7468,
        'radius_km': 10.0,
        'connector_type': 'type2',
        'charging_speed': 'any',
        'amenities': [],
        'min_rating': None,
        'availability_only': False,
        'sort_by': 'recommendation',
        'limit': 20
    }
    
    serializer = NearbyStationSearchSerializer(data=test_data)
    if serializer.is_valid():
        print("✅ Serializer validation passed")
        print(f"📊 Validated data: {serializer.validated_data}")
    else:
        print("❌ Serializer validation failed")
        print(f"🚨 Errors: {serializer.errors}")
        return
    
    # Test AI service
    print("\n🤖 Testing AI service...")
    
    try:
        ai_service = AIRecommendationService()
        recommendations = ai_service.get_personalized_recommendations(
            user=user,
            user_lat=9.0222,
            user_lng=38.7468,
            radius_km=10.0,
            limit=5
        )
        
        print(f"✅ AI service returned {len(recommendations)} recommendations")
        
        for i, rec in enumerate(recommendations[:3], 1):
            station = rec['station']
            print(f"  {i}. {station.name} - Score: {rec['score']:.1f}% - Distance: {rec['distance_km']:.1f}km")
            print(f"     Reason: {rec['recommendation_reason']}")
        
    except Exception as e:
        print(f"❌ AI service error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎯 Test completed!")

if __name__ == '__main__':
    test_ai_recommendations()
