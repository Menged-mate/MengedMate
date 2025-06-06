from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from decimal import Decimal
from unittest.mock import patch, Mock
from .models import ChargingStation, ChargingConnector, StationReview, StationOwner
from .serializers import ChargingStationSerializer
import json

User = get_user_model()


class ChargingStationModelTests(TestCase):
    """Test cases for ChargingStation model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='owner@example.com',
            password='testpass123'
        )
        self.station_owner = StationOwner.objects.create(
            user=self.user,
            company_name='Test Business',
            business_registration_number='BL123456789',
            contact_phone='+251912345678',
            verification_status='verified'
        )
        self.station_data = {
            'name': 'Test Charging Station',
            'address': '123 Main Street',
            'city': 'Addis Ababa',
            'state': 'Addis Ababa',
            'zip_code': '1000',
            'latitude': 9.0320,
            'longitude': 38.7469,
            'owner': self.station_owner,
            'status': 'operational',
            'description': 'A test charging station'
        }

    def test_create_charging_station(self):
        """Test creating a charging station"""
        station = ChargingStation.objects.create(**self.station_data)
        self.assertEqual(station.name, 'Test Charging Station')
        self.assertEqual(station.owner, self.user)
        self.assertEqual(station.status, 'operational')
        self.assertEqual(float(station.latitude), 9.0320)
        self.assertEqual(float(station.longitude), 38.7469)
        self.assertTrue(station.is_active)

    def test_station_string_representation(self):
        """Test station string representation"""
        station = ChargingStation.objects.create(**self.station_data)
        self.assertEqual(str(station), 'Test Charging Station')

    def test_station_coordinates_validation(self):
        """Test station coordinates validation"""
        # Test valid coordinates
        station = ChargingStation.objects.create(**self.station_data)
        station.full_clean()  # Should not raise ValidationError

        # Test invalid latitude
        invalid_data = self.station_data.copy()
        invalid_data['latitude'] = 95.0  # Invalid latitude
        with self.assertRaises(ValidationError):
            station = ChargingStation(**invalid_data)
            station.full_clean()

        # Test invalid longitude
        invalid_data = self.station_data.copy()
        invalid_data['longitude'] = 185.0  # Invalid longitude
        with self.assertRaises(ValidationError):
            station = ChargingStation(**invalid_data)
            station.full_clean()

    def test_station_rating_calculation(self):
        """Test station rating calculation"""
        station = ChargingStation.objects.create(**self.station_data)

        # Initially no rating
        self.assertEqual(station.rating, 0.0)
        self.assertEqual(station.rating_count, 0)

        # Add some reviews
        user1 = User.objects.create_user(email='user1@example.com', password='pass123')
        user2 = User.objects.create_user(email='user2@example.com', password='pass123')

        Review.objects.create(station=station, user=user1, rating=4, comment='Good station')
        Review.objects.create(station=station, user=user2, rating=5, comment='Excellent!')

        # Refresh from database
        station.refresh_from_db()
        self.assertEqual(station.rating, 4.5)
        self.assertEqual(station.rating_count, 2)

    def test_station_available_connectors(self):
        """Test getting available connectors"""
        station = ChargingStation.objects.create(**self.station_data)

        # Create connectors
        connector1 = Connector.objects.create(
            station=station,
            connector_type='Type2',
            power_output=22.0,
            status='available'
        )
        connector2 = Connector.objects.create(
            station=station,
            connector_type='CCS',
            power_output=50.0,
            status='occupied'
        )
        connector3 = Connector.objects.create(
            station=station,
            connector_type='CHAdeMO',
            power_output=50.0,
            status='available'
        )

        available_connectors = station.get_available_connectors()
        self.assertEqual(available_connectors.count(), 2)
        self.assertIn(connector1, available_connectors)
        self.assertIn(connector3, available_connectors)
        self.assertNotIn(connector2, available_connectors)


class ConnectorModelTests(TestCase):
    """Test cases for Connector model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='owner@example.com',
            password='testpass123'
        )
        self.station = ChargingStation.objects.create(
            name='Test Station',
            address='123 Main Street',
            latitude=9.0320,
            longitude=38.7469,
            owner=self.user
        )
        self.connector_data = {
            'station': self.station,
            'connector_type': 'Type2',
            'power_output': 22.0,
            'price_per_kwh': Decimal('15.50'),
            'status': 'available'
        }

    def test_create_connector(self):
        """Test creating a connector"""
        connector = Connector.objects.create(**self.connector_data)
        self.assertEqual(connector.station, self.station)
        self.assertEqual(connector.connector_type, 'Type2')
        self.assertEqual(connector.power_output, 22.0)
        self.assertEqual(connector.price_per_kwh, Decimal('15.50'))
        self.assertEqual(connector.status, 'available')

    def test_connector_string_representation(self):
        """Test connector string representation"""
        connector = Connector.objects.create(**self.connector_data)
        expected = f"Test Station - Type2 (22.0kW)"
        self.assertEqual(str(connector), expected)

    def test_connector_is_available(self):
        """Test connector availability check"""
        connector = Connector.objects.create(**self.connector_data)
        self.assertTrue(connector.is_available())

        connector.status = 'occupied'
        connector.save()
        self.assertFalse(connector.is_available())

        connector.status = 'maintenance'
        connector.save()
        self.assertFalse(connector.is_available())

    def test_connector_power_output_validation(self):
        """Test connector power output validation"""
        # Valid power output
        connector = Connector.objects.create(**self.connector_data)
        connector.full_clean()  # Should not raise ValidationError

        # Invalid power output (negative)
        invalid_data = self.connector_data.copy()
        invalid_data['power_output'] = -10.0
        with self.assertRaises(ValidationError):
            connector = Connector(**invalid_data)
            connector.full_clean()

        # Invalid power output (too high)
        invalid_data = self.connector_data.copy()
        invalid_data['power_output'] = 1000.0
        with self.assertRaises(ValidationError):
            connector = Connector(**invalid_data)
            connector.full_clean()


class ReviewModelTests(TestCase):
    """Test cases for Review model"""

    def setUp(self):
        self.station_owner = User.objects.create_user(
            email='owner@example.com',
            password='testpass123'
        )
        self.reviewer = User.objects.create_user(
            email='reviewer@example.com',
            password='testpass123'
        )
        self.station = ChargingStation.objects.create(
            name='Test Station',
            address='123 Main Street',
            latitude=9.0320,
            longitude=38.7469,
            owner=self.station_owner
        )
        self.review_data = {
            'station': self.station,
            'user': self.reviewer,
            'rating': 4,
            'comment': 'Great charging station!'
        }

    def test_create_review(self):
        """Test creating a review"""
        review = Review.objects.create(**self.review_data)
        self.assertEqual(review.station, self.station)
        self.assertEqual(review.user, self.reviewer)
        self.assertEqual(review.rating, 4)
        self.assertEqual(review.comment, 'Great charging station!')

    def test_review_string_representation(self):
        """Test review string representation"""
        review = Review.objects.create(**self.review_data)
        expected = f"Test Station - 4 stars by reviewer@example.com"
        self.assertEqual(str(review), expected)

    def test_review_rating_validation(self):
        """Test review rating validation"""
        # Valid rating
        review = Review.objects.create(**self.review_data)
        review.full_clean()  # Should not raise ValidationError

        # Invalid rating (too low)
        invalid_data = self.review_data.copy()
        invalid_data['rating'] = 0
        with self.assertRaises(ValidationError):
            review = Review(**invalid_data)
            review.full_clean()

        # Invalid rating (too high)
        invalid_data = self.review_data.copy()
        invalid_data['rating'] = 6
        with self.assertRaises(ValidationError):
            review = Review(**invalid_data)
            review.full_clean()

    def test_unique_review_per_user_per_station(self):
        """Test that user can only review a station once"""
        Review.objects.create(**self.review_data)

        # Try to create another review for same station by same user
        with self.assertRaises(ValidationError):
            duplicate_review = Review(**self.review_data)
            duplicate_review.full_clean()


class ChargingStationAPITests(APITestCase):
    """Test cases for ChargingStation API endpoints"""

    def setUp(self):
        self.client = APIClient()

        # Create users
        self.station_owner = User.objects.create_user(
            email='owner@example.com',
            password='testpass123'
        )
        self.ev_owner = User.objects.create_user(
            email='evowner@example.com',
            password='testpass123'
        )

        # Create station owner profile
        self.station_owner_profile = StationOwnerProfile.objects.create(
            user=self.station_owner,
            business_name='Test Business',
            business_license_number='BL123456789',
            tax_identification_number='TIN987654321',
            phone_number='+251912345678',
            address='123 Test Street',
            verification_status='approved'
        )

        # Create tokens
        self.owner_token = Token.objects.create(user=self.station_owner)
        self.ev_owner_token = Token.objects.create(user=self.ev_owner)

        # Create test station
        self.station = ChargingStation.objects.create(
            name='Test Station',
            address='123 Main Street, Addis Ababa',
            latitude=9.0320,
            longitude=38.7469,
            owner=self.station_owner,
            status='operational'
        )

        # Create test connector
        self.connector = Connector.objects.create(
            station=self.station,
            connector_type='Type2',
            power_output=22.0,
            price_per_kwh=Decimal('15.50'),
            status='available'
        )

    def test_public_stations_list(self):
        """Test public stations list endpoint"""
        url = reverse('public-stations-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Test Station')

    def test_nearby_stations(self):
        """Test nearby stations endpoint"""
        url = reverse('nearby-stations')
        params = {
            'lat': 9.0320,
            'lng': 38.7469,
            'radius': 10
        }
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_station_detail_public(self):
        """Test station detail endpoint (public access)"""
        url = reverse('public-station-detail', kwargs={'pk': self.station.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Station')
        self.assertIn('connectors', response.data)

    def test_create_station_authenticated_owner(self):
        """Test creating station as authenticated station owner"""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.owner_token.key)

        station_data = {
            'name': 'New Test Station',
            'address': '456 New Street, Addis Ababa',
            'latitude': 9.0400,
            'longitude': 38.7500,
            'description': 'A new test station',
            'amenities': ['parking', 'restroom']
        }

        url = reverse('stations-list')
        response = self.client.post(url, station_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Test Station')
        self.assertEqual(response.data['owner'], self.station_owner.id)

    def test_create_station_unauthenticated(self):
        """Test creating station without authentication"""
        station_data = {
            'name': 'New Test Station',
            'address': '456 New Street, Addis Ababa',
            'latitude': 9.0400,
            'longitude': 38.7500
        }

        url = reverse('stations-list')
        response = self.client.post(url, station_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_station_as_ev_owner(self):
        """Test creating station as EV owner (should fail)"""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.ev_owner_token.key)

        station_data = {
            'name': 'New Test Station',
            'address': '456 New Street, Addis Ababa',
            'latitude': 9.0400,
            'longitude': 38.7500
        }

        url = reverse('stations-list')
        response = self.client.post(url, station_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_own_station(self):
        """Test updating own station"""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.owner_token.key)

        update_data = {
            'name': 'Updated Station Name',
            'description': 'Updated description'
        }

        url = reverse('station-detail', kwargs={'pk': self.station.id})
        response = self.client.patch(url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Station Name')

    def test_delete_own_station(self):
        """Test deleting own station"""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.owner_token.key)

        url = reverse('station-detail', kwargs={'pk': self.station.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify station was deleted
        self.assertFalse(ChargingStation.objects.filter(id=self.station.id).exists())
