from utils.firestore_repo import firestore_repo
from rest_framework import status, generics, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from .authentication import AnonymousAuthentication
from .models import Vehicle, CustomUser
from django.contrib.auth import get_user_model, authenticate
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
import random
import string
import json
import hmac
import hashlib
from urllib.parse import parse_qs, unquote
from base64 import b64encode
from datetime import datetime, timedelta
from charging_stations.models import StationOwner

import time

from .serializers import (
    UserSerializer,
    UserProfileSerializer,
    RegisterSerializer,
    VerifyEmailSerializer,
    LoginSerializer,
    ResendVerificationSerializer,
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    VehicleSerializer,
    VehicleListSerializer,
    VehicleSwitchSerializer,
    VehicleStatsSerializer
)

User = get_user_model()


from .serializers_firestore import FirestoreUserSerializer, FirestoreVehicleSerializer

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    authentication_classes = [AnonymousAuthentication]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        # 1. Create SQL User (Auth)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # 2. Create Firestore Profile
        profile_data = {
            'email': user.email,
            'first_name': request.data.get('first_name', ''),
            'last_name': request.data.get('last_name', ''),
            'phone_number': request.data.get('phone_number', ''),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'is_verified': False
        }
        firestore_repo.create_user_profile(user.id, profile_data)
        
        self.send_verification_email(user)

        return Response({
            "message": "User registered successfully. Please check your email for verification code.",
            "user": UserSerializer(user, context=self.get_serializer_context()).data
        }, status=status.HTTP_201_CREATED)

    def send_verification_email(self, user):
        subject = 'Verify your email for EV Charging Station Locator'

        context = {
            'user': user,
            'verification_code': user.verification_code,
            'app_name': 'EV Charging Station Locator'
        }

        html_message = render_to_string('email/verification_email.html', context)
        plain_message = strip_tags(html_message)

        from_email = settings.EMAIL_HOST_USER
        recipient_list = [user.email]

        send_mail(
            subject,
            plain_message,
            from_email,
            recipient_list,
            html_message=html_message,
            fail_silently=False
        )


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [AnonymousAuthentication]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']

            user = User.objects.get(email=email)
            user.is_verified = True
            user.verification_code = None
            user.save()
            
            # Sync verification status to Firestore
            firestore_repo.update_user_profile(user.id, {'is_verified': True})

            token, created = Token.objects.get_or_create(user=user)

            return Response({
                "message": "Email verified successfully.",
                "token": token.key
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [AnonymousAuthentication] 

    def send_verification_email(self, user):
        subject = 'Verify your email for MengedMate'

        context = {
            'user': user,
            'verification_code': user.verification_code,
            'app_name': 'MengedMate'
        }

        html_message = render_to_string('email/verification_email.html', context)
        plain_message = strip_tags(html_message)

        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [user.email]

        send_mail(
            subject,
            plain_message,
            from_email,
            recipient_list,
            html_message=html_message,
            fail_silently=False
        )

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            user = authenticate(request, username=email, password=password)

            if user is not None:
                if not user.is_verified:
                    if not user.verification_code:
                        verification_code = ''.join(random.choices(string.digits, k=6))
                        user.verification_code = verification_code
                        user.save()
                        self.send_verification_email(user)

                    return Response({
                        "message": "Email not verified. Please verify your email first.",
                        "requires_verification": True,
                        "email": user.email,
                        "status": "unverified"
                    }, status=status.HTTP_200_OK)

                token, created = Token.objects.get_or_create(user=user)

                is_station_owner = StationOwner.objects.filter(user=user).exists()
                
                # Fetch profile from Firestore
                profile = firestore_repo.get_user_profile(user.id)
                if not profile:
                    # Lazy create if missing (migration path)
                    profile = {
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'is_verified': True
                    }
                    firestore_repo.create_user_profile(user.id, profile)

                user_data = FirestoreUserSerializer(profile).data
                user_data['is_station_owner'] = is_station_owner

                return Response({
                    "message": "Login successful.",
                    "token": token.key,
                    "user": user_data,
                    "status": "verified"
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "message": "Invalid credentials."
                }, status=status.HTTP_401_UNAUTHORIZED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResendVerificationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [AnonymousAuthentication]

    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']

            user = User.objects.get(email=email)

            verification_code = ''.join(random.choices(string.digits, k=6))
            user.verification_code = verification_code
            user.save()

            subject = 'Verify your email for EV Charging Station Locator'

            context = {
                'user': user,
                'verification_code': user.verification_code,
                'app_name': 'EV Charging Station Locator'
            }

            html_message = render_to_string('email/verification_email.html', context)
            plain_message = strip_tags(html_message)

            from_email = settings.EMAIL_HOST_USER
            recipient_list = [user.email]

            send_mail(
                subject,
                plain_message,
                from_email,
                recipient_list,
                html_message=html_message,
                fail_silently=False
            )

            return Response({
                "message": "Verification code resent. Please check your email."
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def post(self, request):
        try:
            if hasattr(request.user, 'auth_token'):
                request.user.auth_token.delete()

            return Response({
                "message": "Logged out successfully."
            }, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Error during logout: {str(e)}")
            return Response({
                "message": "Logged out successfully."
            }, status=status.HTTP_200_OK)


class UserProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = FirestoreUserSerializer

    def get_object(self):
        # Get from Firestore
        profile = firestore_repo.get_user_profile(self.request.user.id)
        if not profile:
             # Just in case
             return {}
        return profile

    def update(self, request, *args, **kwargs):
        # Update Firestore
        updated_profile = firestore_repo.update_user_profile(request.user.id, request.data)
        serializer = self.get_serializer(updated_profile)
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        profile = self.get_object()
        serializer = self.get_serializer(profile)
        return Response(serializer.data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def put(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Password changed successfully."
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [AnonymousAuthentication]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']

            try:
                user = User.objects.get(email=email)

                token = ''.join(random.choices(string.ascii_letters + string.digits, k=50))
                user.password_reset_token = token
                user.save()

                reset_url = f"https://evvmeri.onrender.com/reset-password?token={token}&email={email}"

                subject = 'Reset Your Password'
                html_message = render_to_string('password_reset_email.html', {
                    'user': user,
                    'reset_url': reset_url,
                })
                plain_message = strip_tags(html_message)

                send_mail(
                    subject,
                    plain_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    html_message=html_message,
                    fail_silently=False,
                )

                return Response({
                    "message": "Password reset instructions have been sent to your email."
                }, status=status.HTTP_200_OK)
            except User.DoesNotExist:

                pass

            return Response({
                "message": "If an account with that email exists, password reset instructions have been sent."
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [AnonymousAuthentication]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save()
                return Response({
                    "message": "Password has been reset successfully."
                }, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({
                    "error": str(e)
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CheckEmailVerificationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [AnonymousAuthentication]

    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response({
                "message": "Email is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)

            if user.is_verified:
                return Response({
                    "is_verified": True,
                    "message": "Email is verified."
                }, status=status.HTTP_200_OK)
            else:
                if not user.verification_code:
                    verification_code = ''.join(random.choices(string.digits, k=6))
                    user.verification_code = verification_code
                    user.save()

                    subject = 'Verify your email for MengedMate'
                    context = {
                        'user': user,
                        'verification_code': user.verification_code,
                        'app_name': 'MengedMate'
                    }
                    html_message = render_to_string('email/verification_email.html', context)
                    plain_message = strip_tags(html_message)

                    send_mail(
                        subject,
                        plain_message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        html_message=html_message,
                        fail_silently=False
                    )

                return Response({
                    "is_verified": False,
                    "message": "Email is not verified. A verification code has been sent to your email.",
                    "email": email
                }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({
                "message": "User with this email does not exist."
            }, status=status.HTTP_404_NOT_FOUND)


class VehicleViewSet(viewsets.ViewSet):
    """ViewSet for managing vehicles in Firestore"""
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = FirestoreVehicleSerializer

    def list(self, request):
        vehicles = firestore_repo.list_vehicles(request.user.id)
        serializer = FirestoreVehicleSerializer(vehicles, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        serializer = FirestoreVehicleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vehicle = firestore_repo.create_vehicle(request.user.id, serializer.validated_data)
        
        # Check if first vehicle, if so make active?
        # Logic: If no active vehicle in profile, set this one.
        profile = firestore_repo.get_user_profile(request.user.id)
        if not profile.get('active_vehicle_id'):
            firestore_repo.update_user_profile(request.user.id, {'active_vehicle_id': vehicle['id']})
            
        return Response(vehicle, status=status.HTTP_201_CREATED)
        
    def retrieve(self, request, pk=None):
        vehicle = firestore_repo.get_vehicle(request.user.id, pk)
        if not vehicle:
             return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(vehicle)
        
    def update(self, request, pk=None):
        serializer = FirestoreVehicleSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        vehicle = firestore_repo.update_vehicle(request.user.id, pk, serializer.validated_data)
        if not vehicle:
             return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(vehicle)
        
    def destroy(self, request, pk=None):
        firestore_repo.delete_vehicle(request.user.id, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def set_active(self, request, pk=None):
        vehicle = firestore_repo.get_vehicle(request.user.id, pk)
        if not vehicle:
             return Response({"error": "Vehicle not found"}, status=404)
        
        firestore_repo.update_user_profile(request.user.id, {'active_vehicle_id': pk})
        return Response({
            'message': f'{vehicle.get("name", "Vehicle")} is now your active vehicle',
            'active_vehicle_id': pk
        })

    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        # "Primary" might just be a boolean flag on vehicles.
        # We need to unset others and set this one.
        vehicles = firestore_repo.list_vehicles(request.user.id)
        for v in vehicles:
            if v['id'] == pk:
                 firestore_repo.update_vehicle(request.user.id, v['id'], {'is_primary': True})
            elif v.get('is_primary'):
                 firestore_repo.update_vehicle(request.user.id, v['id'], {'is_primary': False})
        
        return Response({
            'message': 'Primary vehicle updated',
            'primary_vehicle_id': pk
        })

    @action(detail=False, methods=['get'])
    def active(self, request):
        profile = firestore_repo.get_user_profile(request.user.id)
        active_id = profile.get('active_vehicle_id')
        
        if active_id:
            vehicle = firestore_repo.get_vehicle(request.user.id, active_id)
            if vehicle:
                return Response(vehicle)
                
        return Response({
            'message': 'No active vehicle set',
            'active_vehicle': None
        })

    @action(detail=False, methods=['get'])
    def summary(self, request):
        vehicles = firestore_repo.list_vehicles(request.user.id)
        profile = firestore_repo.get_user_profile(request.user.id)
        active_id = profile.get('active_vehicle_id')
        
        active_count = sum(1 for v in vehicles if v.get('is_active', True))
        primary = next((v for v in vehicles if v.get('is_primary')), None)
        
        return Response({
            'total_vehicles': len(vehicles),
            'active_vehicles': active_count,
            'primary_vehicle': primary['id'] if primary else None,
            'active_vehicle': active_id,
            'vehicles': FirestoreVehicleSerializer(vehicles, many=True).data
        })





    def verify_telegram_data(self, init_data: str) -> dict:
        """Verify Telegram Web App init data."""
        try:
            bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
            if not bot_token:
                raise ValueError("TELEGRAM_BOT_TOKEN not configured")

            # Parse the init_data string into a dictionary with URL decoding
            data_dict = {}
            for param in init_data.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    data_dict[key] = unquote(value)

            # Get the hash from the data
            received_hash = data_dict.pop('hash', None)
            if not received_hash:
                raise ValueError("No hash provided in init data")

            # Sort the data alphabetically
            data_check_string = '\n'.join(f"{k}={v}" for k, v in sorted(data_dict.items()))

            # Create a secret key using the bot token
            secret_key = hashlib.sha256(bot_token.encode()).digest()

            # Calculate the hash
            calculated_hash = hmac.new(
                secret_key,
                data_check_string.encode(),
                hashlib.sha256
            ).hexdigest()

            # Verify the hash
            if calculated_hash != received_hash:
                raise ValueError("Invalid hash - authentication failed")

            # Verify auth date is not too old (within last 24 hours)
            auth_date = int(data_dict.get('auth_date', 0))
            current_time = int(time.time())
            if current_time - auth_date > 86400:
                raise ValueError("Auth date expired (older than 24 hours)")

            # Parse user data
            user_json = data_dict.get('user', '{}')
            if not user_json:
                raise ValueError("No user data provided")

            user_data = json.loads(user_json)

            # Validate required user fields
            if not user_data.get('id'):
                raise ValueError("User ID missing from Telegram data")

            return user_data

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in user data: {str(e)}")
        except Exception as e:
            raise ValueError(f"Invalid init data: {str(e)}")

    def post(self, request):
        try:
            # Log the request for debugging
            import logging
            logger = logging.getLogger(__name__)

            logger.info(f"Telegram login request received")
            logger.info(f"Request data: {request.data}")
            logger.info(f"Request data keys: {list(request.data.keys())}")
            logger.info(f"Request content type: {request.content_type}")

            # Get and verify Telegram data
            init_data = request.data.get('initData')
            if not init_data:
                # Try alternative key names
                init_data = request.data.get('init_data') or request.data.get('initdata')

            logger.info(f"init_data value: {init_data}")

            if not init_data:
                logger.error("No init data found in request")
                return Response({
                    'error': 'No init data provided',
                    'received_keys': list(request.data.keys()),
                    'expected_key': 'initData'
                }, status=status.HTTP_400_BAD_REQUEST)

            logger.info(f"Attempting to verify init data: {init_data[:50]}...")
            user_data = self.verify_telegram_data(init_data)
            logger.info(f"Verification successful, user data: {user_data}")
            
            # Get or create user
            User = get_user_model()
            user, created = User.objects.get_or_create(
                telegram_id=str(user_data.get('id')),
                defaults={
                    'email': f"{user_data.get('id')}@telegram.user",
                    'telegram_username': user_data.get('username'),
                    'telegram_first_name': user_data.get('first_name'),
                    'telegram_last_name': user_data.get('last_name'),
                    'telegram_photo_url': user_data.get('photo_url'),
                    'is_verified': True,
                    'first_name': user_data.get('first_name', ''),
                    'last_name': user_data.get('last_name', ''),
                }
            )

            # Update user data if not created
            if not created:
                user.telegram_username = user_data.get('username')
                user.telegram_first_name = user_data.get('first_name')
                user.telegram_last_name = user_data.get('last_name')
                user.telegram_photo_url = user_data.get('photo_url')
                user.telegram_auth_date = timezone.now()
                user.save()

            # Create or get token
            token, _ = Token.objects.get_or_create(user=user)

            return Response({
                'token': token.key,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'telegram_username': user.telegram_username,
                    'telegram_photo_url': user.telegram_photo_url,
                }
            })

        except ValueError as e:
            logger.error(f"Telegram authentication ValueError: {str(e)}")
            logger.error(f"Request data (on error): {request.data}")
            import sys
            print("\n" + "="*40)
            print("TELEGRAM LOGIN ERROR (ValueError)")
            print(f"Request data: {request.data}")
            print(f"Error: {str(e)}")
            print("="*40 + "\n", file=sys.stderr)
            return Response({
                'error': str(e),
                'error_type': 'validation_error'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Telegram authentication Exception: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            logger.error(f"Request data (on exception): {request.data}")
            import sys
            print("\n" + "="*40)
            print("TELEGRAM LOGIN ERROR (Exception)")
            print(f"Request data: {request.data}")
            print(f"Error: {str(e)}")
            print("="*40 + "\n", file=sys.stderr)
            return Response({
                'error': 'Authentication failed',
                'error_type': 'server_error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



