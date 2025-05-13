"""
URL configuration for mengedmate project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/dev/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt

# Simple test view with explicit permission
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@csrf_exempt
def test_view(request):
    return JsonResponse({"message": "API is working!"})

# Simple register view with explicit permission
@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def register_view(request):
    return JsonResponse({"message": "Register endpoint is working!"})

# Simple health check that doesn't use DRF
@csrf_exempt
def health_check(request):
    return HttpResponse("OK", content_type="text/plain")

# Landing page view
def landing_page(request):
    return render(request, 'index.html')

urlpatterns = [
    path("", landing_page, name="landing"),
    path("admin/", admin.site.urls),
    path("api/auth/", include("authentication.urls")),
    path("api/", include("charging_stations.urls")),
    path("api/test/", test_view, name="test"),
    path("api/register-test/", register_view, name="register-test"),
    path("health/", health_check, name="health"),
    path("api/health/", health_check, name="api-health"),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
