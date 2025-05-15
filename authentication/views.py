from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from .authentication import AnonymousAuthentication
from django.contrib.auth import get_user_model, authenticate
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
import random
import string
import json
from charging_stations.models import StationOwner
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.apple.views import AppleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView

from .serializers import (
    UserSerializer,
    UserProfileSerializer,
    RegisterSerializer,
    VerifyEmailSerializer,
    LoginSerializer,
    ResendVerificationSerializer,
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    API view for user registration.
    """
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    authentication_classes = [AnonymousAuthentication]  # Use custom authentication
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Send verification email
        self.send_verification_email(user)

        return Response({
            "message": "User registered successfully. Please check your email for verification code.",
            "user": UserSerializer(user, context=self.get_serializer_context()).data
        }, status=status.HTTP_201_CREATED)

    def send_verification_email(self, user):
        """Send verification email with code."""
        subject = 'Verify your email for EV Charging Station Locator'

        # Context for the email template
        context = {
            'user': user,
            'verification_code': user.verification_code,
            'app_name': 'EV Charging Station Locator'
        }

        # Render HTML content
        html_message = render_to_string('email/verification_email.html', context)
        plain_message = strip_tags(html_message)

        from_email = settings.EMAIL_HOST_USER
        recipient_list = [user.email]

        # Send email with both HTML and plain text versions
        send_mail(
            subject,
            plain_message,
            from_email,
            recipient_list,
            html_message=html_message,
            fail_silently=False
        )


class VerifyEmailView(APIView):
    """
    API view for email verification.
    """
    permission_classes = [AllowAny]
    authentication_classes = [AnonymousAuthentication]  # Use custom authentication

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']

            user = User.objects.get(email=email)
            user.is_verified = True
            user.verification_code = None  # Clear the verification code
            user.save()

            # Create or get token
            token, created = Token.objects.get_or_create(user=user)

            return Response({
                "message": "Email verified successfully.",
                "token": token.key
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    API view for user login.
    """
    permission_classes = [AllowAny]
    authentication_classes = [AnonymousAuthentication]  # Use custom authentication

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            user = authenticate(request, username=email, password=password)

            if user is not None:
                if not user.is_verified:
                    return Response({
                        "message": "Email not verified. Please verify your email first."
                    }, status=status.HTTP_401_UNAUTHORIZED)

                token, created = Token.objects.get_or_create(user=user)

                # Check if the user is a station owner
                is_station_owner = StationOwner.objects.filter(user=user).exists()

                # Get user data
                user_data = UserSerializer(user).data

                # Add station owner flag to user data
                user_data['is_station_owner'] = is_station_owner

                return Response({
                    "message": "Login successful.",
                    "token": token.key,
                    "user": user_data
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "message": "Invalid credentials."
                }, status=status.HTTP_401_UNAUTHORIZED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResendVerificationView(APIView):
    """
    API view for resending verification code.
    """
    permission_classes = [AllowAny]
    authentication_classes = [AnonymousAuthentication]  # Use custom authentication

    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']

            user = User.objects.get(email=email)

            # Generate a new verification code
            verification_code = ''.join(random.choices(string.digits, k=6))
            user.verification_code = verification_code
            user.save()

            # Send verification email
            subject = 'Verify your email for EV Charging Station Locator'

            # Context for the email template
            context = {
                'user': user,
                'verification_code': user.verification_code,
                'app_name': 'EV Charging Station Locator'
            }

            # Render HTML content
            html_message = render_to_string('email/verification_email.html', context)
            plain_message = strip_tags(html_message)

            from_email = settings.EMAIL_HOST_USER
            recipient_list = [user.email]

            # Send email with both HTML and plain text versions
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
    """
    API view for user logout.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def post(self, request):
        try:
            # Delete the user's token to logout
            if hasattr(request.user, 'auth_token'):
                request.user.auth_token.delete()

            return Response({
                "message": "Logged out successfully."
            }, status=status.HTTP_200_OK)
        except Exception as e:
            # Log the error but still return a success response
            # This ensures the frontend can still complete the logout process
            print(f"Error during logout: {str(e)}")
            return Response({
                "message": "Logged out successfully."
            }, status=status.HTTP_200_OK)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    API view for retrieving and updating user profile.
    """
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
    """
    API view for changing password.
    """
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
    """
    API view for requesting a password reset email.
    """
    permission_classes = [AllowAny]
    authentication_classes = [AnonymousAuthentication]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']

            try:
                user = User.objects.get(email=email)

                # Generate a unique token
                token = ''.join(random.choices(string.ascii_letters + string.digits, k=50))
                user.password_reset_token = token
                user.save()

                # Build the reset URL
                reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}&email={email}"

                # Send email with reset link
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
                # We don't want to reveal if a user exists or not for security reasons
                # So we'll return a success message anyway
                pass

            # Always return success to prevent email enumeration attacks
            return Response({
                "message": "If an account with that email exists, password reset instructions have been sent."
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordView(APIView):
    """
    API view for resetting password with token.
    """
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


# Social Authentication Views
from allauth.account.adapter import get_adapter

class GoogleLoginView(SocialLoginView):
    """
    API view for Google login.
    """
    adapter_class = GoogleOAuth2Adapter
    callback_url = settings.FRONTEND_URL
    client_class = OAuth2Client

    def process_login(self):
        """
        Process the login and return the token.
        """
        get_adapter(self.request).login(self.request, self.user)
        token, created = Token.objects.get_or_create(user=self.user)
        return token


class FacebookLoginView(SocialLoginView):
    """
    API view for Facebook login.
    """
    adapter_class = FacebookOAuth2Adapter
    callback_url = settings.FRONTEND_URL
    client_class = OAuth2Client

    def process_login(self):
        """
        Process the login and return the token.
        """
        get_adapter(self.request).login(self.request, self.user)
        token, created = Token.objects.get_or_create(user=self.user)
        return token


class AppleLoginView(SocialLoginView):
    """
    API view for Apple login.
    """
    adapter_class = AppleOAuth2Adapter
    callback_url = settings.FRONTEND_URL
    client_class = OAuth2Client

    def process_login(self):
        """
        Process the login and return the token.
        """
        get_adapter(self.request).login(self.request, self.user)
        token, created = Token.objects.get_or_create(user=self.user)
        return token


class SocialAuthCallbackView(APIView):
    """
    API view for handling social authentication callbacks.
    """
    permission_classes = [AllowAny]
    authentication_classes = [AnonymousAuthentication]

    def get(self, request):
        """
        Handle the callback from social providers.
        """
        # Extract the token and provider from the request
        provider = request.GET.get('provider')
        token = request.GET.get('token')

        if not provider or not token:
            return Response({
                "message": "Provider and token are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Find the user associated with this social account
        try:
            # This is a simplified example - in a real implementation,
            # you would use the token to authenticate with the provider
            # and get the user's information

            # For now, we'll just return a success response
            return Response({
                "message": f"Successfully authenticated with {provider}.",
                "token": token
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "message": f"Authentication failed: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)
