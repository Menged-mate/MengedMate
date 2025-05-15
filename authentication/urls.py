from django.urls import path
from django.http import JsonResponse
from .views import (
    RegisterView,
    VerifyEmailView,
    LoginView,
    LogoutView,
    ResendVerificationView,
    UserProfileView,
    ChangePasswordView,
    ForgotPasswordView,
    ResetPasswordView,
    GoogleLoginView,
    FacebookLoginView,
    AppleLoginView,
    SocialAuthCallbackView
)

app_name = 'authentication'

# Simple test view
def test_view(request):
    return JsonResponse({"message": "API is working!"})

urlpatterns = [
    path('test/', test_view, name='test'),
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('resend-verification/', ResendVerificationView.as_view(), name='resend-verification'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),

    # Social authentication endpoints
    path('social/google/', GoogleLoginView.as_view(), name='google-login'),
    path('social/facebook/', FacebookLoginView.as_view(), name='facebook-login'),
    path('social/apple/', AppleLoginView.as_view(), name='apple-login'),
    path('social/callback/', SocialAuthCallbackView.as_view(), name='social-callback'),
]
