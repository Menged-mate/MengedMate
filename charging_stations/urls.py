from django.urls import path
from .views import (
    StationOwnerRegistrationView,
    StationOwnerVerifyEmailView,
    StationOwnerProfileView,
    ChargingStationListCreateView,
    ChargingStationDetailView,
    ConnectorCreateView,
    StationImageCreateView
)

app_name = 'charging_stations'

urlpatterns = [
    # Station owner registration and profile
    path('station-owners/register/', StationOwnerRegistrationView.as_view(), name='station-owner-register'),
    path('station-owners/verify-email/', StationOwnerVerifyEmailView.as_view(), name='station-owner-verify-email'),
    path('station-owners/profile/', StationOwnerProfileView.as_view(), name='station-owner-profile'),
    
    # Charging stations
    path('stations/', ChargingStationListCreateView.as_view(), name='station-list-create'),
    path('stations/<uuid:id>/', ChargingStationDetailView.as_view(), name='station-detail'),
    
    # Connectors and images
    path('stations/<uuid:station_id>/connectors/', ConnectorCreateView.as_view(), name='connector-create'),
    path('stations/<uuid:station_id>/images/', StationImageCreateView.as_view(), name='station-image-create'),
]
