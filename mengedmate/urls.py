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
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from charging_stations.home_views import HomeView, AppConfigView
from charging_stations.admin_views import DatabaseBackupView

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

# Simple API information page
def api_info(request):
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mengedmate API</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                text-align: center;
                background-color: #f5f7fa;
            }
            h1 {
                color: #4a6cf7;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            a {
                display: inline-block;
                margin: 10px;
                padding: 10px 20px;
                background-color: #4a6cf7;
                color: white;
                text-decoration: none;
                border-radius: 4px;
            }
            code {
                background-color: #f0f0f0;
                padding: 2px 5px;
                border-radius: 3px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Mengedmate API</h1>
            <p>This is the backend API for the Mengedmate EV Charging Station Locator.</p>
            <p>The frontend is hosted separately at <a href="https://mengedmate.vercel.app" target="_blank">https://mengedmate.vercel.app</a></p>
            <div>
                <a href="/admin/">Admin Dashboard</a>
                <a href="/api/health/">API Health Check</a>
            </div>
            <div style="margin-top: 20px; text-align: left;">
                <h2>API Endpoints:</h2>
                <ul>
                    <li><code>/api/auth/</code> - Authentication endpoints</li>
                    <li><code>/api/</code> - Charging stations endpoints</li>
                    <li><code>/api/health/</code> - API health check</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html_content)

urlpatterns = [
    path("api/auth/", include("authentication.urls")),
    path("api/payments/", include("payments.urls")),
    path("api/ocpp/", include("ocpp_integration.urls")),
    path("api/support/", include("support.urls")),
    path("api/ai/", include("ai_recommendations.urls")),
    path("api/", include("charging_stations.urls")),
    path("api/test/", test_view, name="test"),
    path("api/register-test/", register_view, name="register-test"),
    path("api/health/", health_check, name="api-health"),

    path("docs/", include("docs.urls")),

    path("admin/", admin.site.urls),
    path("admin/database-backup/", DatabaseBackupView.as_view(), name="database-backup"),

    path("health/", health_check, name="health"),

    path("map/", HomeView.as_view(), name="home"),
    path("api/config/", AppConfigView.as_view(), name="app-config"),

    path("", api_info, name="api-info"),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
