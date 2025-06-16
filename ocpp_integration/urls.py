from django.urls import path
from . import views

app_name = 'ocpp_integration'

urlpatterns = [
    # OCPP Station Management
    path('stations/', views.OCPPStationListView.as_view(), name='ocpp-station-list'),
    path('stations/<str:station_id>/', views.OCPPStationDetailView.as_view(), name='ocpp-station-detail'),
    path('sync-station/', views.SyncStationView.as_view(), name='sync-station'),
    
    path('initiate-charging/', views.InitiateChargingView.as_view(), name='initiate-charging'),
    path('stop-charging/', views.StopChargingView.as_view(), name='stop-charging'),
    path('session-status/', views.SessionStatusView.as_view(), name='session-status'),
    
    path('sessions/', views.ChargingSessionListView.as_view(), name='charging-session-list'),
    path('sessions/<int:transaction_id>/', views.ChargingSessionDetailView.as_view(), name='charging-session-detail'),
    
    path('webhook/', views.ocpp_webhook, name='ocpp-webhook'),
    
    
    path('logs/', views.OCPPLogListView.as_view(), name='ocpp-log-list'),
]
