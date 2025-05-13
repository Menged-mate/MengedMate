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
    ResetPasswordView
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
]
