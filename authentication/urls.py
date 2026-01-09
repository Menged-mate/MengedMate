from django.urls import path, include
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter
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
    CheckEmailVerificationView,
    VehicleViewSet
)
from .notification_views import (
    NotificationListView,
    NotificationMarkReadView,
    NotificationDeleteView
)
from .social_auth_views import GoogleAuthView, AppleAuthView

app_name = 'authentication'

def test_view(request):
    return JsonResponse({"message": "API is working!"})

router = DefaultRouter()
router.register(r'vehicles', VehicleViewSet, basename='vehicle')

urlpatterns = [
    path('test/', test_view, name='test'),
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('resend-verification/', ResendVerificationView.as_view(), name='resend-verification'),
    path('check-verification/', CheckEmailVerificationView.as_view(), name='check-verification'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('password-reset/', ForgotPasswordView.as_view(), name='password-reset'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),

    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/mark-read/', NotificationMarkReadView.as_view(), name='notification-mark-all-read'),
    path('notifications/<int:notification_id>/mark-read/', NotificationMarkReadView.as_view(), name='notification-mark-read'),
    path('notifications/<int:notification_id>/delete/', NotificationDeleteView.as_view(), name='notification-delete'),

    # Social authentication
    path('social/google/', GoogleAuthView.as_view(), name='google-auth'),
    path('social/apple/', AppleAuthView.as_view(), name='apple-auth'),

    path('', include(router.urls)),
]
