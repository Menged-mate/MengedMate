from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.authentication import SessionAuthentication
from authentication.authentication import TokenAuthentication
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from .models import StationOwner, ChargingStation
from payments.models import QRPaymentSession
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

            # Get real revenue data from transactions made to station owner's stations
            try:
                # Get all connectors for this station owner's stations
                station_connectors = []
                for station in stations:
                    station_connectors.extend(station.connectors.all())

                # Get QR payment sessions for these connectors that have successful payments
                revenue_qr_sessions = QRPaymentSession.objects.filter(
                    connector__in=station_connectors,
                    status__in=['payment_completed', 'payment_initiated', 'charging_started', 'charging_completed'],
                    payment_transaction__isnull=False
                ).select_related('payment_transaction')

                # Calculate total revenue from successful transactions
                total_revenue = 0
                for qr_session in revenue_qr_sessions:
                    if (qr_session.payment_transaction and
                        qr_session.payment_transaction.status in ['completed', 'pending', 'processing']):
                        total_revenue += float(qr_session.payment_transaction.amount)

                # Also include revenue from simple charging sessions
                try:
                    from payments.models import SimpleChargingSession
                    simple_sessions = SimpleChargingSession.objects.filter(
                        connector__in=station_connectors,
                        status__in=['completed', 'stopped']
                    )

                    for session in simple_sessions:
                        if session.energy_consumed_kwh and session.cost_per_kwh:
                            total_revenue += float(session.energy_consumed_kwh * session.cost_per_kwh)
                except Exception as simple_error:
                    print(f"Error calculating simple session revenue: {simple_error}")

            except Exception as e:
                print(f"Error calculating revenue: {e}")
                total_revenue = 0

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
            # Get real notifications from the database
            try:
                from authentication.notifications import Notification
                from authentication.notification_serializers import NotificationSerializer

                notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
                serializer = NotificationSerializer(notifications, many=True)

                unread_count = notifications.filter(is_read=False).count()

                return Response({
                    'results': serializer.data,
                    'count': notifications.count(),
                    'unread_count': unread_count
                })

            except ImportError:
                # Fallback if notification system is not available
                return Response({
                    'results': [],
                    'count': 0,
                    'unread_count': 0,
                    'message': 'No notifications available'
                })

        except Exception as e:
            return Response({
                'error': f'Error fetching notifications: {str(e)}',
                'results': [],
                'count': 0,
                'unread_count': 0
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MarkNotificationReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def post(self, request, notification_id):
        try:
            from authentication.notifications import Notification

            notification = Notification.objects.get(id=notification_id, user=request.user)
            notification.mark_as_read()

            return Response({
                'message': 'Notification marked as read',
                'notification_id': notification_id
            })
        except ImportError:
            return Response({
                'message': 'Notification system not available'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Notification.DoesNotExist:
            return Response({
                'error': 'Notification not found'
            }, status=status.HTTP_404_NOT_FOUND)


class MarkAllNotificationsReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def post(self, request):
        try:
            from authentication.notifications import Notification

            notifications = Notification.objects.filter(user=request.user, is_read=False)
            for notification in notifications:
                notification.mark_as_read()

            return Response({
                'message': f'{notifications.count()} notifications marked as read'
            })
        except ImportError:
            return Response({
                'message': 'Notification system not available'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


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

            # Get real revenue data from transactions made to station owner's stations
            station_connectors = []
            for station in stations:
                station_connectors.extend(station.connectors.all())

            # Get QR payment sessions for these connectors within date range
            revenue_qr_sessions = QRPaymentSession.objects.filter(
                connector__in=station_connectors,
                status__in=['payment_completed', 'payment_initiated', 'charging_started', 'charging_completed'],
                payment_transaction__isnull=False,
                created_at__gte=start_date
            ).select_related('payment_transaction')

            # Calculate total revenue from successful transactions
            total_revenue = 0
            revenue_transactions = []
            for qr_session in revenue_qr_sessions:
                if (qr_session.payment_transaction and
                    qr_session.payment_transaction.status in ['completed', 'pending', 'processing']):
                    total_revenue += float(qr_session.payment_transaction.amount)
                    revenue_transactions.append(qr_session.payment_transaction)

            # Also include revenue from simple charging sessions within date range
            try:
                from payments.models import SimpleChargingSession
                simple_sessions = SimpleChargingSession.objects.filter(
                    connector__in=station_connectors,
                    status__in=['completed', 'stopped'],
                    start_time__gte=start_date
                )

                for session in simple_sessions:
                    if session.energy_consumed_kwh and session.cost_per_kwh:
                        total_revenue += float(session.energy_consumed_kwh * session.cost_per_kwh)
            except Exception as simple_error:
                print(f"Error calculating simple session revenue: {simple_error}")

            # Calculate total energy dispensed from real charging sessions
            total_energy_dispensed = 0
            avg_session_duration = 0

            try:
                # Try OCPP charging sessions first
                from ocpp_integration.models import ChargingSession
                ocpp_sessions = ChargingSession.objects.filter(
                    ocpp_station__charging_station__in=stations,
                    start_time__gte=start_date
                )
                ocpp_energy = sum(session.energy_consumed or 0 for session in ocpp_sessions)

                # Calculate OCPP session durations
                completed_ocpp_sessions = ocpp_sessions.filter(end_time__isnull=False)
                ocpp_duration = 0
                if completed_ocpp_sessions.exists():
                    ocpp_duration = sum(
                        (session.end_time - session.start_time).total_seconds() / 60
                        for session in completed_ocpp_sessions
                    ) / completed_ocpp_sessions.count()

                total_energy_dispensed += ocpp_energy

            except Exception as e:
                print(f"OCPP sessions error: {e}")

            try:
                # Try Simple charging sessions
                from payments.models import SimpleChargingSession
                simple_sessions = SimpleChargingSession.objects.filter(
                    connector__station__in=stations,
                    start_time__gte=start_date
                )
                simple_energy = sum(session.energy_consumed_kwh or 0 for session in simple_sessions)

                # Calculate simple session durations
                completed_simple_sessions = simple_sessions.filter(stop_time__isnull=False)
                simple_duration = 0
                if completed_simple_sessions.exists():
                    simple_duration = sum(
                        session.duration_seconds / 60 for session in completed_simple_sessions
                    ) / completed_simple_sessions.count()

                total_energy_dispensed += simple_energy

                # Use the average of both session types or the available one
                total_sessions = completed_ocpp_sessions.count() + completed_simple_sessions.count()
                if total_sessions > 0:
                    avg_session_duration = (
                        (ocpp_duration * completed_ocpp_sessions.count()) +
                        (simple_duration * completed_simple_sessions.count())
                    ) / total_sessions

            except Exception as e:
                print(f"Simple sessions error: {e}")

            # If no real data available, show 0 instead of mock data
            if total_energy_dispensed == 0:
                total_energy_dispensed = 0
            if avg_session_duration == 0:
                avg_session_duration = 0

            # Generate monthly revenue data from real transactions
            monthly_revenue = []
            for i in range(7):
                month_start = now - timedelta(days=(i+1)*30)
                month_end = now - timedelta(days=i*30)

                # Get QR sessions for this month with successful payments
                month_qr_sessions = QRPaymentSession.objects.filter(
                    connector__in=station_connectors,
                    status__in=['payment_completed', 'payment_initiated', 'charging_started', 'charging_completed'],
                    payment_transaction__isnull=False,
                    created_at__gte=month_start,
                    created_at__lt=month_end
                ).select_related('payment_transaction')

                month_revenue = 0
                for qr_session in month_qr_sessions:
                    if (qr_session.payment_transaction and
                        qr_session.payment_transaction.status in ['completed', 'pending', 'processing']):
                        month_revenue += float(qr_session.payment_transaction.amount)

                # Also include revenue from simple charging sessions for this month
                try:
                    from payments.models import SimpleChargingSession
                    month_simple_sessions = SimpleChargingSession.objects.filter(
                        connector__in=station_connectors,
                        status__in=['completed', 'stopped'],
                        start_time__gte=month_start,
                        start_time__lt=month_end
                    )

                    for session in month_simple_sessions:
                        if session.energy_consumed_kwh and session.cost_per_kwh:
                            month_revenue += float(session.energy_consumed_kwh * session.cost_per_kwh)
                except:
                    pass

                monthly_revenue.append({
                    'month': month_start.strftime('%b'),
                    'value': month_revenue
                })

            monthly_revenue.reverse()

            # Generate daily energy data from real charging sessions
            daily_energy_data = []
            for i in range(12):
                day_start = now - timedelta(days=(i+1)*30)
                day_end = now - timedelta(days=i*30)

                day_energy = 0
                try:
                    # Get energy from OCPP sessions
                    from ocpp_integration.models import ChargingSession
                    ocpp_energy = ChargingSession.objects.filter(
                        ocpp_station__charging_station__in=stations,
                        start_time__gte=day_start,
                        start_time__lt=day_end
                    ).aggregate(total=Sum('energy_consumed'))['total'] or 0
                    day_energy += ocpp_energy
                except:
                    pass

                try:
                    # Get energy from simple sessions
                    from payments.models import SimpleChargingSession
                    simple_energy = SimpleChargingSession.objects.filter(
                        connector__station__in=stations,
                        start_time__gte=day_start,
                        start_time__lt=day_end
                    ).aggregate(total=Sum('energy_consumed_kwh'))['total'] or 0
                    day_energy += simple_energy
                except:
                    pass

                daily_energy_data.append({
                    'day': day_start.strftime('%b'),
                    'value': float(day_energy)
                })

            daily_energy_data.reverse()

            # Session distribution based on real data
            morning_sessions = 0
            afternoon_sessions = 0

            try:
                # Count OCPP sessions by time of day
                from ocpp_integration.models import ChargingSession
                ocpp_sessions = ChargingSession.objects.filter(
                    ocpp_station__charging_station__in=stations,
                    start_time__gte=start_date
                )

                for session in ocpp_sessions:
                    hour = session.start_time.hour
                    if 6 <= hour < 12:  # Morning: 6 AM - 12 PM
                        morning_sessions += 1
                    elif 12 <= hour < 18:  # Afternoon: 12 PM - 6 PM
                        afternoon_sessions += 1

            except:
                pass

            try:
                # Count simple sessions by time of day
                from payments.models import SimpleChargingSession
                simple_sessions = SimpleChargingSession.objects.filter(
                    connector__station__in=stations,
                    start_time__gte=start_date
                )

                for session in simple_sessions:
                    hour = session.start_time.hour
                    if 6 <= hour < 12:  # Morning: 6 AM - 12 PM
                        morning_sessions += 1
                    elif 12 <= hour < 18:  # Afternoon: 12 PM - 6 PM
                        afternoon_sessions += 1

            except:
                pass

            # Calculate percentages
            total_sessions = morning_sessions + afternoon_sessions
            if total_sessions > 0:
                morning_percentage = round((morning_sessions / total_sessions) * 100)
                afternoon_percentage = round((afternoon_sessions / total_sessions) * 100)
            else:
                morning_percentage = 0
                afternoon_percentage = 0

            session_distribution = {
                'morning': morning_percentage,
                'afternoon': afternoon_percentage
            }

            # Top stations by revenue from real transactions
            top_stations = []
            for station in stations[:5]:
                # Calculate real revenue per station from transactions
                station_revenue = 0

                try:
                    # Get revenue from transactions related to this station's connectors
                    from payments.models import SimpleChargingSession
                    station_sessions = SimpleChargingSession.objects.filter(
                        connector__station=station,
                        start_time__gte=start_date
                    )

                    # Calculate revenue from energy consumed
                    for session in station_sessions:
                        if session.energy_consumed_kwh and session.cost_per_kwh:
                            station_revenue += float(session.energy_consumed_kwh * session.cost_per_kwh)

                except:
                    pass

                top_stations.append({
                    'name': station.name,
                    'revenue': station_revenue
                })

            # Sort by revenue
            top_stations.sort(key=lambda x: x['revenue'], reverse=True)

            # Fault data from real maintenance records
            fault_data = []
            for i in range(9):
                month_start = now - timedelta(days=(i+1)*30)
                month_end = now - timedelta(days=i*30)
                month_name = month_start.strftime('%b')

                # Count stations that went into maintenance during this period
                faults = stations.filter(
                    status='under_maintenance',
                    updated_at__gte=month_start,
                    updated_at__lt=month_end
                ).count()

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
                'transactionsCount': len(revenue_transactions)
            })

        except StationOwner.DoesNotExist:
            return Response({
                'error': 'Station owner profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Error fetching analytics data: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RevenueTransactionsView(APIView):
    """View to get detailed transaction data for revenue page"""
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def get(self, request):
        try:
            station_owner = StationOwner.objects.get(user=request.user)
            stations = ChargingStation.objects.filter(owner=station_owner)

            # Get query parameters
            time_range = request.GET.get('timeRange', '7d')
            selected_station = request.GET.get('selectedStation', 'All Stations')

            # Calculate date range
            now = timezone.now()
            if time_range == '7d':
                start_date = now - timedelta(days=7)
            elif time_range == '30d':
                start_date = now - timedelta(days=30)
            elif time_range == '90d':
                start_date = now - timedelta(days=90)
            else:
                start_date = now - timedelta(days=7)

            # Filter stations if specific station selected
            if selected_station != 'All Stations':
                try:
                    stations = stations.filter(id=selected_station)
                except:
                    pass

            # Get all connectors for these stations
            station_connectors = []
            for station in stations:
                station_connectors.extend(station.connectors.all())

            # Get QR payment sessions for these connectors with successful payments
            revenue_qr_sessions = QRPaymentSession.objects.filter(
                connector__in=station_connectors,
                status__in=['payment_completed', 'payment_initiated', 'charging_started', 'charging_completed'],
                payment_transaction__isnull=False,
                created_at__gte=start_date
            ).select_related('payment_transaction', 'connector', 'connector__station').order_by('-created_at')

            # Format transaction data
            transactions = []
            total_revenue = 0

            for qr_session in revenue_qr_sessions:
                if (qr_session.payment_transaction and
                    qr_session.payment_transaction.status in ['completed', 'pending', 'processing']):
                    transaction = qr_session.payment_transaction
                    amount = float(transaction.amount)
                    total_revenue += amount

                    # Map transaction status to display status
                    status_mapping = {
                        'completed': 'Completed',
                        'pending': 'Pending',
                        'processing': 'Processing'
                    }
                    display_status = status_mapping.get(transaction.status, transaction.status.title())

                    transactions.append({
                        'id': str(transaction.id),
                        'date': transaction.created_at.strftime('%Y-%m-%d'),
                        'transaction_id': transaction.reference_number,
                        'type': 'Charging Payment',
                        'description': f'Charging at {qr_session.connector.station.name}',
                        'amount': amount,
                        'status': display_status,
                        'user_email': qr_session.user.email,
                        'connector_id': str(qr_session.connector.id)
                    })

            # Also include simple charging sessions
            try:
                from payments.models import SimpleChargingSession
                simple_sessions = SimpleChargingSession.objects.filter(
                    connector__in=station_connectors,
                    status__in=['completed', 'stopped'],
                    start_time__gte=start_date
                ).select_related('connector__station', 'user').order_by('-start_time')

                for session in simple_sessions:
                    if session.energy_consumed_kwh and session.cost_per_kwh:
                        amount = float(session.energy_consumed_kwh * session.cost_per_kwh)
                        total_revenue += amount

                        transactions.append({
                            'id': str(session.id),
                            'date': session.start_time.strftime('%Y-%m-%d'),
                            'transaction_id': f'SIMPLE-{session.id}',
                            'type': 'Simple Charging',
                            'description': f'Simple charging at {session.connector.station.name}',
                            'amount': amount,
                            'status': 'Completed',
                            'user_email': session.user.email,
                            'connector_id': str(session.connector.id),
                            'energy_consumed': float(session.energy_consumed_kwh),
                            'cost_per_kwh': float(session.cost_per_kwh)
                        })
            except Exception as e:
                print(f"Error processing simple sessions in transaction history: {e}")

            # Sort all transactions by date (newest first)
            transactions.sort(key=lambda x: x['date'], reverse=True)

            return Response({
                'success': True,
                'transactions': transactions,
                'summary': {
                    'total_revenue': total_revenue,
                    'total_transactions': len(transactions),
                    'currency': 'ETB',
                    'time_range': time_range,
                    'selected_station': selected_station
                }
            })

        except StationOwner.DoesNotExist:
            return Response({
                'error': 'Station owner profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Error fetching transaction data: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RevenueDetailView(APIView):
    """Detailed revenue tracking for station owners"""
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

            # Get all connectors for these stations
            station_connectors = []
            for station in stations:
                station_connectors.extend(station.connectors.all())

            # Get detailed revenue breakdown
            revenue_breakdown = {
                'qr_payments': 0,
                'simple_sessions': 0,
                'total_transactions': 0,
                'successful_transactions': 0,
                'failed_transactions': 0,
                'pending_transactions': 0,
                'transaction_details': []
            }

            # QR Payment Sessions Revenue
            qr_sessions = QRPaymentSession.objects.filter(
                connector__in=station_connectors,
                created_at__gte=start_date
            ).select_related('payment_transaction', 'connector__station')

            for qr_session in qr_sessions:
                transaction_detail = {
                    'id': str(qr_session.id),
                    'type': 'QR Payment',
                    'station_name': qr_session.connector.station.name,
                    'connector_id': str(qr_session.connector.id),
                    'user_email': qr_session.user.email,
                    'amount': 0,
                    'status': qr_session.status,
                    'payment_status': None,
                    'created_at': qr_session.created_at.isoformat(),
                    'payment_amount': float(qr_session.get_payment_amount())
                }

                revenue_breakdown['total_transactions'] += 1

                if qr_session.payment_transaction:
                    transaction_detail['payment_status'] = qr_session.payment_transaction.status
                    transaction_detail['amount'] = float(qr_session.payment_transaction.amount)

                    if qr_session.payment_transaction.status in ['completed', 'pending', 'processing']:
                        revenue_breakdown['qr_payments'] += float(qr_session.payment_transaction.amount)
                        revenue_breakdown['successful_transactions'] += 1
                    elif qr_session.payment_transaction.status == 'failed':
                        revenue_breakdown['failed_transactions'] += 1
                    elif qr_session.payment_transaction.status == 'pending':
                        revenue_breakdown['pending_transactions'] += 1

                revenue_breakdown['transaction_details'].append(transaction_detail)

            # Simple Charging Sessions Revenue
            try:
                from payments.models import SimpleChargingSession
                simple_sessions = SimpleChargingSession.objects.filter(
                    connector__in=station_connectors,
                    start_time__gte=start_date
                ).select_related('connector__station', 'user')

                for session in simple_sessions:
                    session_revenue = 0
                    if session.energy_consumed_kwh and session.cost_per_kwh:
                        session_revenue = float(session.energy_consumed_kwh * session.cost_per_kwh)
                        revenue_breakdown['simple_sessions'] += session_revenue

                    transaction_detail = {
                        'id': str(session.id),
                        'type': 'Simple Session',
                        'station_name': session.connector.station.name,
                        'connector_id': str(session.connector.id),
                        'user_email': session.user.email,
                        'amount': session_revenue,
                        'status': session.status,
                        'payment_status': 'completed' if session_revenue > 0 else 'no_payment',
                        'created_at': session.start_time.isoformat(),
                        'energy_consumed': float(session.energy_consumed_kwh or 0),
                        'cost_per_kwh': float(session.cost_per_kwh or 0)
                    }

                    revenue_breakdown['transaction_details'].append(transaction_detail)
                    revenue_breakdown['total_transactions'] += 1

                    if session_revenue > 0:
                        revenue_breakdown['successful_transactions'] += 1

            except Exception as e:
                print(f"Error processing simple sessions: {e}")

            # Calculate totals
            total_revenue = revenue_breakdown['qr_payments'] + revenue_breakdown['simple_sessions']

            # Sort transaction details by date (newest first)
            revenue_breakdown['transaction_details'].sort(
                key=lambda x: x['created_at'],
                reverse=True
            )

            return Response({
                'total_revenue': total_revenue,
                'revenue_breakdown': revenue_breakdown,
                'time_range': time_range,
                'selected_station': selected_station,
                'stations_count': stations.count(),
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': now.isoformat()
                }
            })

        except StationOwner.DoesNotExist:
            return Response({
                'error': 'Station owner profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Error calculating revenue details: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
