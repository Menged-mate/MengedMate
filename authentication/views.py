from rest_framework import status, generics, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from .authentication import AnonymousAuthentication
from .models import Vehicle, TelegramAuth, CustomUser
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
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.apple.views import AppleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
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


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    authentication_classes = [AnonymousAuthentication]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
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

                user_data = UserSerializer(user).data

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
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

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

                reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}&email={email}"

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


from allauth.account.adapter import get_adapter

class GoogleLoginView(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = settings.FRONTEND_URL
    client_class = OAuth2Client

    def process_login(self):
        get_adapter(self.request).login(self.request, self.user)
        token, created = Token.objects.get_or_create(user=self.user)
        return token


class FacebookLoginView(SocialLoginView):

    adapter_class = FacebookOAuth2Adapter
    callback_url = settings.FRONTEND_URL
    client_class = OAuth2Client

    def process_login(self):

        get_adapter(self.request).login(self.request, self.user)
        token, created = Token.objects.get_or_create(user=self.user)
        return token


class AppleLoginView(SocialLoginView):
    adapter_class = AppleOAuth2Adapter
    callback_url = settings.FRONTEND_URL
    client_class = OAuth2Client

    def process_login(self):

        get_adapter(self.request).login(self.request, self.user)
        token, created = Token.objects.get_or_create(user=self.user)
        return token


class SocialAuthCallbackView(APIView):

    permission_classes = [AllowAny]
    authentication_classes = [AnonymousAuthentication]

    def get(self, request):

        provider = request.GET.get('provider')
        token = request.GET.get('token')

        if not provider or not token:
            return Response({
                "message": "Provider and token are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            return Response({
                "message": f"Successfully authenticated with {provider}.",
                "token": token
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "message": f"Authentication failed: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)


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


class VehicleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = VehicleSerializer

    def get_queryset(self):
        queryset = Vehicle.objects.filter(user=self.request.user)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'list':
            return VehicleListSerializer
        elif self.action == 'stats':
            return VehicleStatsSerializer
        return VehicleSerializer

    @action(detail=True, methods=['post'])
    def set_active(self, request, pk=None):
        vehicle = self.get_object()
        success = request.user.set_active_vehicle(vehicle)

        if success:
            return Response({
                'message': f'{vehicle.get_display_name()} is now your active vehicle',
                'active_vehicle_id': vehicle.id
            })
        else:
            return Response({
                'error': 'Failed to set active vehicle'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        vehicle = self.get_object()

        Vehicle.objects.filter(user=request.user, is_primary=True).update(is_primary=False)

        vehicle.is_primary = True
        vehicle.save(update_fields=['is_primary'])

        return Response({
            'message': f'{vehicle.get_display_name()} is now your primary vehicle',
            'primary_vehicle_id': vehicle.id
        })

    @action(detail=True, methods=['get'])
    def charging_estimate(self, request, pk=None):
        vehicle = self.get_object()

        current_percentage = int(request.query_params.get('current_percentage', 20))
        target_percentage = int(request.query_params.get('target_percentage', 80))

        charging_time = vehicle.get_estimated_charging_time(target_percentage, current_percentage)
        range_at_target = vehicle.get_range_at_percentage(target_percentage)

        return Response({
            'vehicle_id': vehicle.id,
            'vehicle_name': vehicle.get_display_name(),
            'current_percentage': current_percentage,
            'target_percentage': target_percentage,
            'estimated_charging_time_minutes': charging_time,
            'estimated_range_at_target_km': range_at_target,
            'battery_capacity_kwh': float(vehicle.battery_capacity_kwh),
            'usable_battery_kwh': float(vehicle.usable_battery_kwh) if vehicle.usable_battery_kwh else None,
            'max_charging_speed_kw': float(vehicle.max_charging_speed_kw) if vehicle.max_charging_speed_kw else None
        })

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        vehicle = self.get_object()
        serializer = VehicleStatsSerializer(vehicle)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def active(self, request):
        active_vehicle = request.user.get_active_vehicle()

        if active_vehicle:
            serializer = VehicleSerializer(active_vehicle, context={'request': request})
            return Response(serializer.data)
        else:
            return Response({
                'message': 'No active vehicle set',
                'active_vehicle': None
            })

    @action(detail=False, methods=['post'])
    def switch_active(self, request):
        serializer = VehicleSwitchSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            vehicle_id = serializer.validated_data['vehicle_id']
            vehicle = Vehicle.objects.get(id=vehicle_id, user=request.user)

            success = request.user.set_active_vehicle(vehicle)

            if success:
                vehicle.update_usage_stats()

                return Response({
                    'message': f'Switched to {vehicle.get_display_name()}',
                    'active_vehicle': VehicleSerializer(vehicle, context={'request': request}).data
                })
            else:
                return Response({
                    'error': 'Failed to switch active vehicle'
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        vehicles = self.get_queryset()
        active_vehicle = request.user.get_active_vehicle()

        return Response({
            'total_vehicles': vehicles.count(),
            'active_vehicles': vehicles.filter(is_active=True).count(),
            'primary_vehicle': vehicles.filter(is_primary=True).first().id if vehicles.filter(is_primary=True).exists() else None,
            'active_vehicle': active_vehicle.id if active_vehicle else None,
            'connector_types': request.user.get_compatible_connector_types(),
            'vehicles': VehicleListSerializer(vehicles, many=True, context={'request': request}).data
        })


class TelegramLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [AnonymousAuthentication]

    def get(self, request):
        """Provide information about the Telegram login endpoint"""
        return Response({
            'message': 'Telegram Login Endpoint',
            'description': 'This endpoint accepts POST requests with Telegram Web App initData for authentication',
            'method': 'POST',
            'required_fields': ['initData'],
            'bot_configured': bool(settings.TELEGRAM_BOT_TOKEN),
            'example_usage': {
                'method': 'POST',
                'headers': {'Content-Type': 'application/json'},
                'body': {'initData': 'telegram_web_app_init_data_string'}
            }
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


class TelegramWebAppView(APIView):
    """Handle Telegram Web App initialization and validation"""
    permission_classes = [AllowAny]
    authentication_classes = [AnonymousAuthentication]

    def get(self, request):
        """Return necessary data for Telegram Web App initialization"""
        try:
            # Use getattr with default values to avoid AttributeError
            bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
            bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', '')
            return_url = getattr(settings, 'TELEGRAM_RETURN_URL', '')

            return Response({
                "bot_username": bot_username,
                "return_url": return_url,
                "bot_configured": bool(bot_token),
                "api_status": "ready",
                "endpoints": {
                    "login": "/api/auth/telegram/login/",
                    "webapp": "/api/auth/telegram/webapp/"
                },
                "settings_status": {
                    "TELEGRAM_BOT_TOKEN": "configured" if bot_token else "missing",
                    "TELEGRAM_BOT_USERNAME": "configured" if bot_username else "missing",
                    "TELEGRAM_RETURN_URL": "configured" if return_url else "missing"
                }
            })
        except Exception as e:
            return Response({
                "error": f"Configuration error: {str(e)}",
                "api_status": "error",
                "bot_configured": False
            }, status=500)

    def post(self, request):
        """Validate Telegram Web App data"""
        init_data = request.data.get('initData')
        if not init_data:
            return Response({
                "message": "No Telegram init data provided"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Verify the data using the same method as in TelegramLoginView
            telegram_login = TelegramLoginView()
            user_data = telegram_login.verify_telegram_data(init_data)

            return Response({
                "message": "Telegram Web App data validated successfully",
                "user_data": user_data
            })
        except ValueError as e:
            return Response({
                "message": f"Invalid Telegram data: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "message": "Validation failed"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
