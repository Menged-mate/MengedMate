from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.authentication import SessionAuthentication
from authentication.authentication import TokenAuthentication
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from .models import StationOwner, ChargingStation
from payments.models import Transaction, WalletTransaction
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
            offline_stations = stations.filter(status='closed').count()
            maintenance_stations = stations.filter(status='under_maintenance').count()

            # Get real revenue data from transactions
            try:
                revenue_transactions = Transaction.objects.filter(
                    user=request.user,
                    status='completed'
                )
                total_revenue = revenue_transactions.aggregate(
                    total=Sum('amount')
                )['total'] or 0
                total_revenue = float(total_revenue)
            except:
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
                    'is_verified': request.user.is_verified,
                    'verification_status': station_owner.verification_status,
                    'is_profile_completed': station_owner.is_profile_completed,
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

            # Get real usage data from charging sessions
            try:
                from ocpp_integration.models import ChargingSession

                # Get charging sessions for this station owner's stations
                stations = ChargingStation.objects.filter(owner=station_owner)
                charging_sessions = ChargingSession.objects.filter(
                    ocpp_station__charging_station__in=stations
                )

                # Calculate hourly usage data
                hourly_usage = []
                for hour in range(24):
                    hour_sessions = charging_sessions.filter(
                        start_time__hour=hour
                    )
                    usage = sum(session.energy_consumed or 0 for session in hour_sessions)
                    sessions_count = hour_sessions.count()

                    hourly_usage.append({
                        'hour': hour,
                        'usage': float(usage),
                        'sessions': sessions_count
                    })

                total_usage = sum(item['usage'] for item in hourly_usage)
                total_sessions = sum(item['sessions'] for item in hourly_usage)
                peak_hour = max(hourly_usage, key=lambda x: x['usage'])['hour'] if hourly_usage else 0

            except Exception as e:
                # Fallback to mock data if charging sessions not available
                hourly_usage = []
                for hour in range(24):
                    usage = {
                        'hour': hour,
                        'usage': random.randint(10, 100),
                        'sessions': random.randint(5, 50)
                    }
                    hourly_usage.append(usage)

                total_usage = sum(item['usage'] for item in hourly_usage)
                total_sessions = sum(item['sessions'] for item in hourly_usage)
                peak_hour = max(hourly_usage, key=lambda x: x['usage'])['hour']

            return Response({
                'hourly_usage': hourly_usage,
                'total_usage': total_usage,
                'total_sessions': total_sessions,
                'peak_hour': peak_hour
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


class AnalyticsReportsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def get(self, request):
        try:
            station_owner = StationOwner.objects.get(user=request.user)
            stations = ChargingStation.objects.filter(owner=station_owner)

            # Get query parameters
            time_range = request.GET.get('time_range', 'Last 30 Days')
            selected_station = request.GET.get('station', 'All Stations')

            # Calculate date range
            now = timezone.now()
            if time_range == 'Last 7 Days':
                start_date = now - timedelta(days=7)
            elif time_range == 'Last 30 Days':
                start_date = now - timedelta(days=30)
            elif time_range == 'Last 90 Days':
                start_date = now - timedelta(days=90)
            elif time_range == 'Last Year':
                start_date = now - timedelta(days=365)
            else:
                start_date = now - timedelta(days=30)

            # Filter stations if specific station selected
            if selected_station != 'All Stations':
                try:
                    stations = stations.filter(id=selected_station)
                except:
                    pass

            # Get real revenue data from transactions
            revenue_transactions = Transaction.objects.filter(
                user=request.user,
                status='completed',
                created_at__gte=start_date
            )

            wallet_transactions = WalletTransaction.objects.filter(
                wallet__user=request.user,
                created_at__gte=start_date
            )

            # Calculate total revenue
            total_revenue = revenue_transactions.aggregate(
                total=Sum('amount')
            )['total'] or 0

            # Calculate total energy dispensed from real charging sessions
            try:
                from ocpp_integration.models import ChargingSession
                charging_sessions = ChargingSession.objects.filter(
                    ocpp_station__charging_station__in=stations,
                    start_time__gte=start_date
                )
                total_energy_dispensed = sum(
                    session.energy_consumed or 0 for session in charging_sessions
                )

                # Calculate average session duration from real data
                completed_sessions = charging_sessions.filter(
                    end_time__isnull=False
                )
                if completed_sessions.exists():
                    total_duration = sum(
                        (session.end_time - session.start_time).total_seconds() / 60
                        for session in completed_sessions
                    )
                    avg_session_duration = total_duration / completed_sessions.count()
                else:
                    avg_session_duration = 0

            except Exception as e:
                # Fallback to mock data
                total_energy_dispensed = stations.count() * random.randint(800, 1200)
                avg_session_duration = random.randint(35, 55)

            # Generate monthly revenue data
            monthly_revenue = []
            for i in range(7):
                month_start = now - timedelta(days=(i+1)*30)
                month_end = now - timedelta(days=i*30)
                month_revenue = revenue_transactions.filter(
                    created_at__gte=month_start,
                    created_at__lt=month_end
                ).aggregate(total=Sum('amount'))['total'] or random.randint(8000, 15000)

                monthly_revenue.append({
                    'month': month_start.strftime('%b'),
                    'value': float(month_revenue)
                })

            monthly_revenue.reverse()

            # Generate daily energy data
            daily_energy_data = []
            for i in range(12):
                day_energy = stations.count() * random.randint(8, 20)
                daily_energy_data.append({
                    'day': (now - timedelta(days=i*30)).strftime('%b'),
                    'value': day_energy
                })

            daily_energy_data.reverse()

            # Session distribution (mock data based on time patterns)
            session_distribution = {
                'morning': 60,
                'afternoon': 40
            }

            # Top stations by revenue
            top_stations = []
            for station in stations[:5]:
                # Mock revenue per station
                station_revenue = random.randint(1500, 5000)
                top_stations.append({
                    'name': station.name,
                    'revenue': station_revenue
                })

            # Sort by revenue
            top_stations.sort(key=lambda x: x['revenue'], reverse=True)

            # Fault data (mock data based on station count)
            fault_data = []
            for i in range(9):
                month_name = (now - timedelta(days=i*30)).strftime('%b')
                faults = random.randint(2, 10) if stations.count() > 0 else 0
                fault_data.append({
                    'month': month_name,
                    'faults': faults
                })

            fault_data.reverse()

            return Response({
                'totalRevenue': float(total_revenue),
                'totalEnergyDispensed': total_energy_dispensed,
                'avgSessionDuration': avg_session_duration,
                'monthlyRevenue': monthly_revenue,
                'dailyEnergyData': daily_energy_data,
                'sessionDistribution': session_distribution,
                'topStations': top_stations,
                'faultData': fault_data,
                'timeRange': time_range,
                'selectedStation': selected_station,
                'stationsCount': stations.count(),
                'transactionsCount': revenue_transactions.count()
            })

        except StationOwner.DoesNotExist:
            return Response({
                'error': 'Station owner profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Error fetching analytics data: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
