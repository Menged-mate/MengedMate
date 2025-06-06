from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from unittest.mock import patch, Mock
from .models import CustomUser, Vehicle
from .serializers import UserRegistrationSerializer, UserLoginSerializer
from .views import UserRegistrationView, UserLoginView
import json

User = get_user_model()


class CustomUserModelTests(TestCase):
    """Test cases for CustomUser model"""

    def setUp(self):
        self.user_data = {
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'testpass123'
        }

    def test_create_user(self):
        """Test creating a regular user"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertTrue(user.check_password('testpass123'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        """Test creating a superuser"""
        user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )
        self.assertEqual(user.email, 'admin@example.com')
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_user_string_representation(self):
        """Test user string representation"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(str(user), 'test@example.com')

    def test_email_normalization(self):
        """Test email normalization"""
        user = User.objects.create_user(
            email='Test@EXAMPLE.COM',
            password='testpass123'
        )
        self.assertEqual(user.email, 'test@example.com')

    def test_user_without_email_raises_error(self):
        """Test creating user without email raises error"""
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='testpass123')

    def test_user_full_name_property(self):
        """Test user full name property"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.get_full_name(), 'Test User')


class VehicleModelTests(TestCase):
    """Test cases for Vehicle model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='owner@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.vehicle_data = {
            'user': self.user,
            'name': 'My Tesla',
            'make': 'Tesla',
            'model': 'Model 3',
            'year': 2023,
            'battery_capacity_kwh': 75.0,
            'connector_type': 'ccs2',
            'max_charging_speed_kw': 250.0
        }

    def test_create_vehicle(self):
        """Test creating a vehicle"""
        vehicle = Vehicle.objects.create(**self.vehicle_data)
        self.assertEqual(vehicle.user, self.user)
        self.assertEqual(vehicle.name, 'My Tesla')
        self.assertEqual(vehicle.make, 'Tesla')
        self.assertEqual(vehicle.model, 'Model 3')
        self.assertEqual(vehicle.year, 2023)
        self.assertTrue(vehicle.is_primary)  # First vehicle should be primary

    def test_vehicle_string_representation(self):
        """Test vehicle string representation"""
        vehicle = Vehicle.objects.create(**self.vehicle_data)
        expected = f"2023 Tesla Model 3 (My Tesla)"
        self.assertEqual(str(vehicle), expected)

    def test_vehicle_auto_primary(self):
        """Test that first vehicle becomes primary automatically"""
        vehicle = Vehicle.objects.create(**self.vehicle_data)
        self.assertTrue(vehicle.is_primary)

        # Create second vehicle
        vehicle2_data = self.vehicle_data.copy()
        vehicle2_data['name'] = 'My BMW'
        vehicle2_data['make'] = 'BMW'
        vehicle2_data['model'] = 'i3'
        vehicle2 = Vehicle.objects.create(**vehicle2_data)

        # First vehicle should still be primary
        vehicle.refresh_from_db()
        self.assertTrue(vehicle.is_primary)
        self.assertFalse(vehicle2.is_primary)

    def test_vehicle_usable_battery_calculation(self):
        """Test automatic usable battery calculation"""
        vehicle = Vehicle.objects.create(**self.vehicle_data)
        # Should be 92% of total capacity
        expected_usable = 75.0 * 0.92
        self.assertEqual(float(vehicle.usable_battery_kwh), expected_usable)

    def test_vehicle_charging_time_estimation(self):
        """Test charging time estimation"""
        vehicle = Vehicle.objects.create(**self.vehicle_data)
        # Test charging from 20% to 80%
        charging_time = vehicle.get_estimated_charging_time(80, 20)
        self.assertIsNotNone(charging_time)
        self.assertGreater(charging_time, 0)


class UserRegistrationSerializerTests(TestCase):
    """Test cases for UserRegistrationSerializer"""

    def setUp(self):
        self.valid_data = {
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
            'user_type': 'ev_owner'
        }

    def test_valid_registration_data(self):
        """Test serializer with valid data"""
        serializer = UserRegistrationSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())

    def test_password_mismatch(self):
        """Test password mismatch validation"""
        data = self.valid_data.copy()
        data['password2'] = 'differentpass'
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password2', serializer.errors)

    def test_duplicate_email(self):
        """Test duplicate email validation"""
        User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        serializer = UserRegistrationSerializer(data=self.valid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_invalid_email_format(self):
        """Test invalid email format"""
        data = self.valid_data.copy()
        data['email'] = 'invalid_email'
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_weak_password(self):
        """Test weak password validation"""
        data = self.valid_data.copy()
        data['password1'] = '123'
        data['password2'] = '123'
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_create_user(self):
        """Test user creation through serializer"""
        serializer = UserRegistrationSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertTrue(user.check_password('testpass123'))


class UserLoginSerializerTests(TestCase):
    """Test cases for UserLoginSerializer"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.valid_data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }

    def test_valid_login_data(self):
        """Test serializer with valid login data"""
        serializer = UserLoginSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())

    def test_invalid_email(self):
        """Test login with invalid email"""
        data = self.valid_data.copy()
        data['email'] = 'nonexistent@example.com'
        serializer = UserLoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_invalid_password(self):
        """Test login with invalid password"""
        data = self.valid_data.copy()
        data['password'] = 'wrongpassword'
        serializer = UserLoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_inactive_user_login(self):
        """Test login with inactive user"""
        self.user.is_active = False
        self.user.save()
        serializer = UserLoginSerializer(data=self.valid_data)
        self.assertFalse(serializer.is_valid())


class AuthenticationAPITests(APITestCase):
    """Test cases for Authentication API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.registration_url = reverse('user-register')
        self.login_url = reverse('user-login')
        self.logout_url = reverse('user-logout')

        self.user_data = {
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
            'user_type': 'ev_owner'
        }

        self.existing_user = User.objects.create_user(
            email='existing@example.com',
            password='testpass123'
        )

    def test_user_registration_success(self):
        """Test successful user registration"""
        response = self.client.post(self.registration_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['user']['email'], 'test@example.com')

        # Verify user was created in database
        user = User.objects.get(email='test@example.com')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')

    def test_user_registration_duplicate_email(self):
        """Test registration with duplicate email"""
        data = self.user_data.copy()
        data['email'] = 'existing@example.com'
        response = self.client.post(self.registration_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_user_registration_password_mismatch(self):
        """Test registration with password mismatch"""
        data = self.user_data.copy()
        data['password2'] = 'differentpass'
        response = self.client.post(self.registration_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_registration_missing_fields(self):
        """Test registration with missing required fields"""
        data = {'email': 'test@example.com'}
        response = self.client.post(self.registration_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_login_success(self):
        """Test successful user login"""
        login_data = {
            'email': 'existing@example.com',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['email'], 'existing@example.com')

    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        login_data = {
            'email': 'existing@example.com',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_login_nonexistent_user(self):
        """Test login with nonexistent user"""
        login_data = {
            'email': 'nonexistent@example.com',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_logout_success(self):
        """Test successful user logout"""
        # First login to get token
        token = Token.objects.create(user=self.existing_user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify token was deleted
        self.assertFalse(Token.objects.filter(user=self.existing_user).exists())

    def test_user_logout_without_authentication(self):
        """Test logout without authentication"""
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('authentication.views.send_verification_email')
    def test_registration_sends_verification_email(self, mock_send_email):
        """Test that registration sends verification email"""
        response = self.client.post(self.registration_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_send_email.assert_called_once()

    def test_station_owner_registration(self):
        """Test station owner registration creates profile"""
        data = self.user_data.copy()
        data['user_type'] = 'station_owner'
        data.update({
            'business_name': 'Test Charging Station',
            'business_license_number': 'BL123456789',
            'tax_identification_number': 'TIN987654321',
            'phone_number': '+251912345678',
            'address': '123 Test Street, Addis Ababa'
        })

        response = self.client.post(self.registration_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify station owner profile was created
        user = User.objects.get(email='test@example.com')
        self.assertTrue(hasattr(user, 'station_owner_profile'))
        self.assertEqual(user.station_owner_profile.business_name, 'Test Charging Station')
