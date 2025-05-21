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
    authentication_classes = [AnonymousAuthentication]  # Use custom authentication

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
                    # Generate a new verification code if needed
                    if not user.verification_code:
                        verification_code = ''.join(random.choices(string.digits, k=6))
                        user.verification_code = verification_code
                        user.save()
                        # Send the verification email
                        self.send_verification_email(user)

                    return Response({
                        "message": "Email not verified. Please verify your email first.",
                        "requires_verification": True,
                        "email": user.email,
                        "status": "unverified"
                    }, status=status.HTTP_200_OK)  # Using 200 instead of 401 for better app handling

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
    """
    API view for checking if an email is verified.
    This is useful for the Flutter app to determine if it should show the verification page.
    """
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
                # Generate a new verification code if needed
                if not user.verification_code:
                    verification_code = ''.join(random.choices(string.digits, k=6))
                    user.verification_code = verification_code
                    user.save()

                    # Send verification email
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
