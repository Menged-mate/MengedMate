import os
import django
from unittest.mock import MagicMock, patch
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mengedmate.settings")
django.setup()

from charging_stations.dashboard_views import (
    DashboardStatsView,
    ActivitiesView,
    AnalyticsUsageView,
    AnalyticsReportsView,
    RevenueTransactionsView
)

def test_view(view_class, view_name):
    print(f"Testing {view_name}...")
    factory = APIRequestFactory()
    request = factory.get('/')
    request.user = MagicMock()
    request.user.id = 'test-user-id'
    request.user.first_name = 'Test'
    request.user.last_name = 'User'
    request.user.email = 'test@example.com'
    request.user.is_verified = True

    # Mock firestore_repo
    with patch('utils.firestore_repo.firestore_repo') as mock_repo:
        # Mock Station Owner
        mock_repo.get_station_owner.return_value = {
            'id': 'station-owner-id',
            'company_name': 'Test Company',
            'verification_status': 'verified',
            'is_profile_completed': True
        }
        
        # Mock Stations
        mock_repo.list_stations.return_value = [
            {'id': 'station-1', 'name': 'Station 1', 'status': 'operational'},
            {'id': 'station-2', 'name': 'Station 2', 'status': 'closed'},
            {'id': 'station-3', 'name': 'Station 3', 'status': 'under_maintenance', 'updated_at': '2024-01-01T00:00:00Z'}
        ]

        # Mock SQL models (fallback) - ensure no error if they don't exist or filtering works
        # We Mock the view execution environment
        try:
            view = view_class.as_view()
            response = view(request)
            
            if response.status_code == 200:
                print(f"SUCCESS: {view_name} returned 200 OK")
                # print(response.data)
            else:
                print(f"FAILURE: {view_name} returned {response.status_code}")
                print(response.data)
                
        except Exception as e:
            print(f"CRITICAL FAILURE: {view_name} raised exception: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_view(DashboardStatsView, "DashboardStatsView")
    test_view(ActivitiesView, "ActivitiesView")
    test_view(AnalyticsUsageView, "AnalyticsUsageView")
    test_view(AnalyticsReportsView, "AnalyticsReportsView")
    test_view(RevenueTransactionsView, "RevenueTransactionsView")
