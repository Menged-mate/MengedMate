#!/usr/bin/env python3
"""
Test script to debug review submission issue
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/home/haile/Desktop/MengedMate')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mengedmate.settings')
django.setup()

from django.contrib.auth import get_user_model
from charging_stations.models import ChargingStation, StationReview
from charging_stations.serializers import StationReviewSerializer
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory
from charging_stations.views import StationReviewListCreateView

User = get_user_model()

def test_review_submission():
    print("=== Testing Review Submission ===")
    
    try:
        # Get a test user
        user = User.objects.filter(is_active=True).first()
        if not user:
            print("No active users found")
            return
        
        print(f"Using user: {user.email}")
        
        # Get a test station
        station = ChargingStation.objects.first()
        if not station:
            print("No charging stations found")
            return
            
        print(f"Using station: {station.name}")
        
        # Test data
        review_data = {
            'rating': 5,
            'review_text': 'Test review from debug script'
        }
        
        print(f"Review data: {review_data}")
        
        # Test serializer validation
        print("\n--- Testing Serializer ---")
        serializer = StationReviewSerializer(data=review_data)
        if serializer.is_valid():
            print("Serializer validation: PASSED")
            print(f"Validated data: {serializer.validated_data}")
        else:
            print("Serializer validation: FAILED")
            print(f"Errors: {serializer.errors}")
            return
        
        # Test direct model creation
        print("\n--- Testing Direct Model Creation ---")
        try:
            # Check if review already exists
            existing_review = StationReview.objects.filter(
                user=user,
                station=station
            ).first()
            
            if existing_review:
                print(f"Existing review found: {existing_review.id}")
                # Update existing review
                existing_review.rating = review_data['rating']
                existing_review.review_text = review_data['review_text']
                existing_review.save()
                print("Existing review updated successfully")
            else:
                # Create new review
                review = StationReview.objects.create(
                    user=user,
                    station=station,
                    rating=review_data['rating'],
                    review_text=review_data['review_text']
                )
                print(f"New review created successfully: {review.id}")
                
        except Exception as e:
            print(f"Direct model creation failed: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return
        
        # Test view creation
        print("\n--- Testing View Creation ---")
        try:
            factory = APIRequestFactory()
            request = factory.post(
                f'/api/stations/{station.id}/reviews/',
                review_data,
                format='json'
            )
            request.user = user
            
            view = StationReviewListCreateView()
            view.kwargs = {'station_id': str(station.id)}
            
            response = view.create(request)
            print(f"View response status: {response.status_code}")
            print(f"View response data: {response.data}")
            
        except Exception as e:
            print(f"View creation failed: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
        
        print("\n=== Test Complete ===")
        
    except Exception as e:
        print(f"Test failed with error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    test_review_submission()
