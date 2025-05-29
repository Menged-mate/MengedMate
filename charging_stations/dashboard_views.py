from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.authentication import SessionAuthentication
from authentication.authentication import TokenAuthentication
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from .models import StationOwner, ChargingStation
from authentication.models import CustomUser
import random


class DashboardStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def get(self, request):
        try:
            station_owner = StationOwner.objects.get(user=request.user)
            stations = ChargingStation.objects.filter(owner=station_owner)

            # Calculate stats
            total_stations = stations.count()
            active_stations = stations.filter(status='operational').count()
            offline_stations = stations.filter(status__in=['under_maintenance', 'closed']).count()
            maintenance_stations = stations.filter(status='under_maintenance').count()

            # Mock revenue data (replace with actual revenue model when available)
            total_revenue = random.randint(1000, 50000)

            # Mock sessions data (replace with actual session model when available)
            total_sessions = random.randint(100, 1000)

            return Response({
                'user': {
                    'id': request.user.id,
                    'first_name': request.user.first_name,
                    'last_name': request.user.last_name,
                    'email': request.user.email,
                    'company_name': station_owner.company_name,
                },
                'stats': {
                    'totalStations': total_stations,
                    'activeStations': active_stations,
                    'offlineStations': offline_stations,
                    'maintenanceStations': maintenance_stations,
                    'revenue': total_revenue,
                    'sessions': total_sessions,
                }
            })
        except StationOwner.DoesNotExist:
            return Response({
                'error': 'Station owner profile not found'
            }, status=status.HTTP_404_NOT_FOUND)


class ActivitiesView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def get(self, request):
        try:
            station_owner = StationOwner.objects.get(user=request.user)
            stations = ChargingStation.objects.filter(owner=station_owner)

            # Mock activity data (replace with actual activity model when available)
            activities = []
            activity_types = [
                'Station Online',
                'Station Offline',
                'Maintenance Started',
                'Maintenance Completed',
                'New Charging Session',
                'Payment Received',
                'Station Added',
                'Station Updated'
            ]

            for i in range(10):
                station = random.choice(stations) if stations.exists() else None
                activity = {
                    'id': i + 1,
                    'type': random.choice(activity_types),
                    'station_name': station.name if station else 'Unknown Station',
                    'station_id': str(station.id) if station else None,
                    'description': f'Activity description for {random.choice(activity_types)}',
                    'timestamp': (timezone.now() - timedelta(hours=random.randint(1, 72))).isoformat(),
                    'status': random.choice(['success', 'warning', 'error', 'info'])
                }
                activities.append(activity)

            return Response({
                'results': activities,
                'count': len(activities)
            })
        except StationOwner.DoesNotExist:
            return Response({
                'error': 'Station owner profile not found'
            }, status=status.HTTP_404_NOT_FOUND)


class AnalyticsUsageView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def get(self, request):
        try:
            station_owner = StationOwner.objects.get(user=request.user)

            # Mock hourly usage data (replace with actual usage model when available)
            hourly_usage = []
            for hour in range(24):
                usage = {
                    'hour': hour,
                    'usage': random.randint(10, 100),
                    'sessions': random.randint(5, 50)
                }
                hourly_usage.append(usage)

            return Response({
                'hourly_usage': hourly_usage,
                'total_usage': sum(item['usage'] for item in hourly_usage),
                'total_sessions': sum(item['sessions'] for item in hourly_usage),
                'peak_hour': max(hourly_usage, key=lambda x: x['usage'])['hour']
            })
        except StationOwner.DoesNotExist:
            return Response({
                'error': 'Station owner profile not found'
            }, status=status.HTTP_404_NOT_FOUND)


class NotificationsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def get(self, request):
        try:
            station_owner = StationOwner.objects.get(user=request.user)
            stations = ChargingStation.objects.filter(owner=station_owner)

            # Mock notifications data (replace with actual notification model when available)
            notifications = []
            notification_types = [
                'Station maintenance required',
                'Payment received',
                'New charging session started',
                'Station went offline',
                'Station back online',
                'Monthly report available',
                'New user registered',
                'System update completed'
            ]

            for i in range(15):
                station = random.choice(stations) if stations.exists() else None
                notification = {
                    'id': i + 1,
                    'title': random.choice(notification_types),
                    'message': f'Notification message for {random.choice(notification_types)}',
                    'is_read': random.choice([True, False]),
                    'created_at': (timezone.now() - timedelta(hours=random.randint(1, 168))).isoformat(),
                    'station_id': str(station.id) if station else None,
                    'station_name': station.name if station else None,
                    'type': random.choice(['info', 'warning', 'success', 'error'])
                }
                notifications.append(notification)

            # Sort by created_at descending
            notifications.sort(key=lambda x: x['created_at'], reverse=True)

            return Response({
                'results': notifications,
                'count': len(notifications),
                'unread_count': len([n for n in notifications if not n['is_read']])
            })
        except StationOwner.DoesNotExist:
            return Response({
                'error': 'Station owner profile not found'
            }, status=status.HTTP_404_NOT_FOUND)


class MarkNotificationReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def post(self, request, notification_id):
        # Mock implementation - in real app, update notification in database
        return Response({
            'message': 'Notification marked as read',
            'notification_id': notification_id
        })


class MarkAllNotificationsReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def post(self, request):
        # Mock implementation - in real app, update all notifications in database
        return Response({
            'message': 'All notifications marked as read'
        })
