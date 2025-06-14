from rest_framework import generics, status, permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from math import cos, radians
from .models import (
    StationOwner, ChargingStation, StationImage, ChargingConnector,
    AppContent, StationReview, ReviewReply, StationOwnerSettings, NotificationTemplate,
    PayoutMethod, WithdrawalRequest
)
from .serializers import (
    StationOwnerRegistrationSerializer,
    StationOwnerProfileSerializer,
    ChargingStationSerializer,
    ChargingConnectorSerializer,
    StationImageSerializer,
    StationReviewSerializer,
    StationReviewListSerializer,
    ReviewReplySerializer,
    ReviewReplyListSerializer,
    StationOwnerSettingsSerializer,
    NotificationTemplateSerializer,
    AvailableStationSerializer,
    PayoutMethodSerializer,
    WithdrawalRequestSerializer,
    WithdrawalRequestAdminSerializer
)
from authentication.authentication import AnonymousAuthentication, TokenAuthentication
from rest_framework.authentication import SessionAuthentication

User = get_user_model()

class StationOwnerRegistrationView(generics.GenericAPIView):

    permission_classes = [permissions.AllowAny]
    authentication_classes = [AnonymousAuthentication]
    serializer_class = StationOwnerRegistrationSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        user = result['user']
        verification_code = result['verification_code']

        subject = 'Verify Your evmeri EV Charging Station Owner Account'
        html_message = render_to_string('station_owner_email_verification.html', {
            'user': user,
            'verification_code': verification_code,
            'frontend_url': settings.FRONTEND_URL
        })
        plain_message = strip_tags(html_message)

        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )

        return Response({
            "message": "Registration successful. Please check your email for verification code.",
            "email": user.email
        }, status=status.HTTP_201_CREATED)

class StationOwnerVerifyEmailView(APIView):

    permission_classes = [permissions.AllowAny]
    authentication_classes = [AnonymousAuthentication]

    def post(self, request):
        email = request.data.get('email')
        verification_code = request.data.get('verification_code')

        if not email or not verification_code:
            return Response({
                "message": "Email and verification code are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                "message": "User with this email does not exist."
            }, status=status.HTTP_404_NOT_FOUND)

        if user.is_verified:
            return Response({
                "message": "Email is already verified."
            }, status=status.HTTP_400_BAD_REQUEST)

        if user.verification_code != verification_code:
            return Response({
                "message": "Invalid verification code."
            }, status=status.HTTP_400_BAD_REQUEST)

        user.is_verified = True
        user.verification_code = None
        user.save()

        try:
            station_owner = StationOwner.objects.get(user=user)
        except StationOwner.DoesNotExist:
            return Response({
                "message": "Station owner profile not found."
            }, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "message": "Email verified successfully. Please complete your profile.",
            "station_owner_id": station_owner.id
        }, status=status.HTTP_200_OK)

class StationOwnerProfileView(generics.RetrieveUpdateAPIView):

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = StationOwnerProfileSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self):
        try:
            return StationOwner.objects.get(user=self.request.user)
        except StationOwner.DoesNotExist:
            return Response({
                "message": "Station owner profile not found."
            }, status=status.HTTP_404_NOT_FOUND)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if instance.is_profile_completed and not instance.verified_at:
            # Send admin notification
            subject = 'New Station Owner Requires Verification'
            message = f'A new station owner ({instance.company_name}) has completed their profile and requires verification.'
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL],
                fail_silently=True,
            )

            # Send real-time notification to user
            from authentication.notifications import create_notification, Notification
            create_notification(
                user=instance.user,
                notification_type=Notification.NotificationType.SYSTEM,
                title='Profile Submitted for Verification',
                message='Your station owner profile has been submitted for verification. Our team will review your documents within 1-3 business days.',
                link='/dashboard/profile'
            )

        return Response(serializer.data)

class ChargingStationListCreateView(generics.ListCreateAPIView):

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = ChargingStationSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        try:
            station_owner = StationOwner.objects.get(user=self.request.user)
            return ChargingStation.objects.filter(owner=station_owner)
        except StationOwner.DoesNotExist:
            return ChargingStation.objects.none()

    def perform_create(self, serializer):
        serializer.save()

class ChargingStationDetailView(generics.RetrieveUpdateDestroyAPIView):

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = ChargingStationSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_field = 'id'

    def get_queryset(self):
        try:
            station_owner = StationOwner.objects.get(user=self.request.user)
            return ChargingStation.objects.filter(owner=station_owner)
        except StationOwner.DoesNotExist:
            return ChargingStation.objects.none()

class ConnectorCreateView(generics.CreateAPIView):

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = ChargingConnectorSerializer

    def post(self, request, *args, **kwargs):
        station_id = self.kwargs.get('station_id')
        try:
            station_owner = StationOwner.objects.get(user=request.user)
            station = ChargingStation.objects.get(id=station_id, owner=station_owner)

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            connector_type = serializer.validated_data.get('connector_type')
            power_kw = serializer.validated_data.get('power_kw')
            price_per_kwh = serializer.validated_data.get('price_per_kwh')
            quantity_to_add = serializer.validated_data.get('quantity', 1)

            existing_connector = ChargingConnector.objects.filter(
                station=station,
                connector_type=connector_type,
                power_kw=power_kw,
                price_per_kwh=price_per_kwh
            ).first()

            if existing_connector:
                existing_connector.quantity += quantity_to_add
                existing_connector.available_quantity += quantity_to_add
                existing_connector.save()
                connector = existing_connector
            else:
                connector = serializer.save(station=station)

            station.update_connector_counts()
            return Response({
                'success': True,
                'message': 'Connector added successfully',
                'connector': ChargingConnectorSerializer(connector).data
            }, status=status.HTTP_201_CREATED)
        except (StationOwner.DoesNotExist, ChargingStation.DoesNotExist):
            raise permissions.PermissionDenied("You don't have permission to add connectors to this station.")

class ConnectorDetailView(generics.RetrieveUpdateDestroyAPIView):

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = ChargingConnectorSerializer
    lookup_field = 'id'

    def get_queryset(self):
        try:
            station_owner = StationOwner.objects.get(user=self.request.user)
            station_id = self.kwargs.get('station_id')
            station = ChargingStation.objects.get(id=station_id, owner=station_owner)
            return ChargingConnector.objects.filter(station=station)
        except (StationOwner.DoesNotExist, ChargingStation.DoesNotExist):
            return ChargingConnector.objects.none()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def perform_update(self, serializer):
        connector = serializer.save()
        # Update station connector counts after update
        connector.station.update_connector_counts()

    def perform_destroy(self, instance):
        station = instance.station
        instance.delete()
        # Update station connector counts after deletion
        station.update_connector_counts()

class StationImageCreateView(generics.CreateAPIView):

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = StationImageSerializer
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        station_id = self.kwargs.get('station_id')
        try:
            station_owner = StationOwner.objects.get(user=self.request.user)
            station = ChargingStation.objects.get(id=station_id, owner=station_owner)
            serializer.save(station=station)
        except (StationOwner.DoesNotExist, ChargingStation.DoesNotExist):
            raise permissions.PermissionDenied("You don't have permission to add images to this station.")


class StationQRCodesView(APIView):
    """View to get QR codes for all connectors of a station"""
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def get(self, request, station_id):
        try:
            station_owner = StationOwner.objects.get(user=request.user)
            station = get_object_or_404(ChargingStation, id=station_id, owner=station_owner)

            connectors = station.connectors.all()
            qr_data = []

            for connector in connectors:
                qr_data.append({
                    'connector_id': connector.id,
                    'connector_type': connector.connector_type,
                    'connector_type_display': connector.get_connector_type_display(),
                    'power_kw': connector.power_kw,
                    'quantity': connector.quantity,
                    'available_quantity': connector.available_quantity,
                    'price_per_kwh': connector.price_per_kwh,
                    'qr_code_token': connector.qr_code_token,
                    'qr_code_url': connector.get_qr_code_url(),
                    'qr_payment_url': f"https://mengedmate.onrender.com/api/payments/qr-initiate/{connector.qr_code_token}/" if connector.qr_code_token else None,
                    'is_available': connector.is_available,
                    'status': connector.status,
                    'status_display': connector.get_status_display()
                })

            return Response({
                'success': True,
                'station': {
                    'id': station.id,
                    'name': station.name,
                    'address': station.address
                },
                'connectors': qr_data
            })

        except StationOwner.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Station owner profile not found'
            }, status=status.HTTP_404_NOT_FOUND)


class ConnectorQRCodeView(APIView):
    """View to get or regenerate QR code for a specific connector"""
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def get(self, request, connector_id):
        try:
            station_owner = StationOwner.objects.get(user=request.user)
            connector = get_object_or_404(
                ChargingConnector,
                id=connector_id,
                station__owner=station_owner
            )

            return Response({
                'success': True,
                'connector': {
                    'id': connector.id,
                    'connector_type': connector.connector_type,
                    'connector_type_display': connector.get_connector_type_display(),
                    'power_kw': connector.power_kw,
                    'price_per_kwh': connector.price_per_kwh,
                    'qr_code_token': connector.qr_code_token,
                    'qr_code_url': connector.get_qr_code_url(),
                    'qr_payment_url': f"https://mengedmate.onrender.com/api/payments/qr-initiate/{connector.qr_code_token}/" if connector.qr_code_token else None,
                    'station_name': connector.station.name
                }
            })

        except StationOwner.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Station owner profile not found'
            }, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, connector_id):
        """Regenerate QR code for connector"""
        try:
            station_owner = StationOwner.objects.get(user=request.user)
            connector = get_object_or_404(
                ChargingConnector,
                id=connector_id,
                station__owner=station_owner
            )

            # Clear existing QR code data to force regeneration
            connector.qr_code_token = None
            connector.qr_code_image = None
            connector.save()  # This will trigger QR code generation

            return Response({
                'success': True,
                'message': 'QR code regenerated successfully',
                'connector': {
                    'id': connector.id,
                    'qr_code_token': connector.qr_code_token,
                    'qr_code_url': connector.get_qr_code_url(),
                    'qr_payment_url': f"https://mengedmate.onrender.com/api/payments/qr-initiate/{connector.qr_code_token}/" if connector.qr_code_token else None
                }
            })

        except StationOwner.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Station owner profile not found'
            }, status=status.HTTP_404_NOT_FOUND)


class DownloadQRCodeView(APIView):
    """View to download QR code image for printing"""
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def get(self, request, connector_id):
        try:
            station_owner = StationOwner.objects.get(user=request.user)
            connector = get_object_or_404(
                ChargingConnector,
                id=connector_id,
                station__owner=station_owner
            )

            if not connector.qr_code_image:
                return Response({
                    'success': False,
                    'error': 'QR code not found for this connector'
                }, status=status.HTTP_404_NOT_FOUND)

            # Return the QR code image file
            try:
                with open(connector.qr_code_image.path, 'rb') as f:
                    response = HttpResponse(f.read(), content_type='image/png')
                    response['Content-Disposition'] = f'attachment; filename="qr_code_{connector.station.name}_{connector.get_connector_type_display()}_{connector.power_kw}kW.png"'
                    return response
            except FileNotFoundError:
                return Response({
                    'success': False,
                    'error': 'QR code image file not found'
                }, status=status.HTTP_404_NOT_FOUND)

        except StationOwner.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Station owner profile not found'
            }, status=status.HTTP_404_NOT_FOUND)


class AppContentView(APIView):
    """View to get app content like About, Privacy Policy, Terms of Service"""
    permission_classes = [permissions.AllowAny]
    authentication_classes = [AnonymousAuthentication]

    def get(self, request, content_type=None):
        try:
            if content_type:
                # Get specific content type
                content = get_object_or_404(AppContent, content_type=content_type, is_active=True)
                return Response({
                    'success': True,
                    'content': {
                        'content_type': content.content_type,
                        'title': content.title,
                        'content': content.content,
                        'version': content.version,
                        'updated_at': content.updated_at
                    }
                })
            else:
                # Get all active content
                contents = AppContent.objects.filter(is_active=True).order_by('content_type')
                content_data = []
                for content in contents:
                    content_data.append({
                        'content_type': content.content_type,
                        'title': content.title,
                        'content': content.content,
                        'version': content.version,
                        'updated_at': content.updated_at
                    })

                return Response({
                    'success': True,
                    'contents': content_data
                })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StationReviewListCreateView(generics.ListCreateAPIView):
    """View to list and create station reviews"""

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return StationReviewSerializer
        return StationReviewListSerializer

    def get_queryset(self):
        station_id = self.kwargs.get('station_id')
        return StationReview.objects.filter(
            station_id=station_id,
            is_active=True
        ).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        try:
            station_id = self.kwargs.get('station_id')
            station = get_object_or_404(ChargingStation, id=station_id)

            # Check if user already has a review for this station
            existing_review = StationReview.objects.filter(
                user=request.user,
                station=station
            ).first()

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            if existing_review:
                # Update existing review instead of creating new one
                for attr, value in serializer.validated_data.items():
                    setattr(existing_review, attr, value)
                existing_review.updated_at = timezone.now()
                existing_review.save()  # This will trigger the station rating update

                # Return the updated review using the list serializer
                response_serializer = StationReviewListSerializer(existing_review)
                return Response(response_serializer.data, status=status.HTTP_200_OK)
            else:
                # Create new review
                review = serializer.save(user=request.user, station=station)
                response_serializer = StationReviewListSerializer(review)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            # Log the error for debugging
            import traceback
            print(f"Error creating review: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")

            return Response({
                'success': False,
                'error': str(e),
                'details': 'Review submission failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StationReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View to retrieve, update, or delete a specific review"""

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = StationReviewSerializer
    lookup_field = 'id'

    def get_queryset(self):
        # Users can only access their own reviews
        return StationReview.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        # Soft delete - mark as inactive instead of deleting
        instance.is_active = False
        instance.save()


class UserReviewsView(generics.ListAPIView):
    """View to get all reviews by the current user"""

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = StationReviewListSerializer

    def get_queryset(self):
        return StationReview.objects.filter(
            user=self.request.user,
            is_active=True
        ).order_by('-created_at')


class StationReviewStatsView(APIView):
    """View to get review statistics for a station"""

    permission_classes = [permissions.AllowAny]
    authentication_classes = [AnonymousAuthentication]

    def get(self, request, station_id):
        try:
            station = get_object_or_404(ChargingStation, id=station_id)
            reviews = StationReview.objects.filter(station=station, is_active=True)

            # Calculate rating distribution
            rating_distribution = {}
            for i in range(1, 6):
                rating_distribution[str(i)] = reviews.filter(rating=i).count()

            # Calculate average ratings for different aspects
            from django.db.models import Avg

            avg_ratings = reviews.aggregate(
                overall_rating=Avg('rating'),
                charging_speed_rating=Avg('charging_speed_rating'),
                location_rating=Avg('location_rating'),
                amenities_rating=Avg('amenities_rating')
            )

            # Get recent reviews (last 5)
            recent_reviews = reviews[:5]
            recent_reviews_data = StationReviewListSerializer(recent_reviews, many=True).data

            return Response({
                'success': True,
                'station_id': station_id,
                'total_reviews': reviews.count(),
                'overall_rating': round(avg_ratings['overall_rating'] or 0, 2),
                'rating_distribution': rating_distribution,
                'average_ratings': {
                    'overall': round(avg_ratings['overall_rating'] or 0, 2),
                    'charging_speed': round(avg_ratings['charging_speed_rating'] or 0, 2),
                    'location': round(avg_ratings['location_rating'] or 0, 2),
                    'amenities': round(avg_ratings['amenities_rating'] or 0, 2),
                },
                'recent_reviews': recent_reviews_data,
                'verified_reviews_count': reviews.filter(is_verified_review=True).count()
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StationOwnerReviewsView(generics.ListAPIView):
    """View for station owners to see all reviews for their stations"""

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = StationReviewListSerializer

    def get_queryset(self):
        try:
            station_owner = StationOwner.objects.get(user=self.request.user)
            stations = ChargingStation.objects.filter(owner=station_owner)
            return StationReview.objects.filter(
                station__in=stations,
                is_active=True
            ).select_related('user', 'station').order_by('-created_at')
        except StationOwner.DoesNotExist:
            return StationReview.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # Add station information to each review
        reviews_data = []
        for review in queryset:
            review_data = self.get_serializer(review).data
            review_data['station_name'] = review.station.name
            review_data['station_id'] = str(review.station.id)
            reviews_data.append(review_data)

        return Response({
            'results': reviews_data,
            'count': len(reviews_data)
        })


class MobileChargingHistoryView(APIView):
    """Simplified charging history view for mobile users"""

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def get(self, request):
        try:
            all_sessions = []

            # Get QR Payment Sessions (most common for mobile app)
            try:
                from payments.models import QRPaymentSession

                # Get QR sessions with completed payments and charging
                qr_sessions = QRPaymentSession.objects.filter(
                    user=request.user,
                    status__in=['charging_completed', 'charging_started', 'payment_completed']
                ).select_related(
                    'connector__station',
                    'payment_transaction',
                    'simple_charging_session'
                ).order_by('-created_at')[:20]  # Reduced limit for debugging

                for qr_session in qr_sessions:
                    try:
                        # Calculate duration and cost
                        duration_seconds = 0
                        energy_kwh = 0.0
                        final_cost = 0.0
                        start_time = None
                        stop_time = None

                        # Get data from simple charging session if available
                        if hasattr(qr_session, 'simple_charging_session') and qr_session.simple_charging_session:
                            charging_session = qr_session.simple_charging_session
                            duration_seconds = charging_session.duration_seconds or 0
                            energy_kwh = float(charging_session.energy_delivered_kwh or 0)
                            start_time = charging_session.start_time
                            stop_time = charging_session.stop_time

                            # Calculate duration if not stored
                            if start_time and stop_time and not duration_seconds:
                                duration_seconds = int((stop_time - start_time).total_seconds())

                        # Calculate cost based on energy and connector price
                        if energy_kwh > 0 and qr_session.connector and qr_session.connector.price_per_kwh:
                            final_cost = energy_kwh * float(qr_session.connector.price_per_kwh)
                        elif qr_session.payment_transaction:
                            final_cost = float(qr_session.payment_transaction.amount)

                        # Format duration for display
                        duration_minutes = duration_seconds // 60 if duration_seconds else 0

                        # Safe access to connector and station data
                        station_name = qr_session.connector.station.name if qr_session.connector and qr_session.connector.station else 'Unknown Station'
                        station_address = qr_session.connector.station.address if qr_session.connector and qr_session.connector.station else 'Unknown Location'
                        station_city = qr_session.connector.station.city if qr_session.connector and qr_session.connector.station else 'Unknown City'
                        connector_type = qr_session.connector.get_connector_type_display() if qr_session.connector else 'Unknown'
                        connector_power = f"{qr_session.connector.power_kw} kW" if qr_session.connector else 'Unknown'

                        session_data = {
                            'id': str(qr_session.id),
                            'transaction_id': qr_session.session_token,
                            'station_name': station_name,
                            'station_address': station_address,
                            'station_city': station_city,
                            'connector_type': connector_type,
                            'connector_power': connector_power,
                            'start_time': start_time.isoformat() if start_time else qr_session.created_at.isoformat(),
                            'stop_time': stop_time.isoformat() if stop_time else None,
                            'energy_consumed_kwh': f"{energy_kwh:.3f}",
                            'final_cost': f"{final_cost:.2f}",
                            'currency': 'ETB',
                            'status': 'CHARGING_COMPLETED' if qr_session.status == 'charging_completed' else 'COMPLETED',
                            'payment_status': 'completed' if qr_session.payment_transaction else 'pending',
                            'duration_minutes': duration_minutes,
                            'duration_seconds': duration_seconds,
                            'payment_method': 'QR Code',
                            'payment_amount': str(qr_session.payment_transaction.amount) if qr_session.payment_transaction else '0.00',
                            'created_at': qr_session.created_at.isoformat(),
                        }
                        all_sessions.append(session_data)
                    except Exception as session_error:
                        # Skip problematic sessions but continue processing
                        continue

            except ImportError:
                pass
            except Exception as qr_error:
                # Log QR session error but continue
                pass

            # Sort all sessions by creation date (newest first)
            all_sessions.sort(key=lambda x: x['created_at'], reverse=True)

            return Response({
                'success': True,
                'results': all_sessions,
                'count': len(all_sessions)
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'results': [],
                'count': 0
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StationOwnerSettingsView(generics.RetrieveUpdateAPIView):
    """View to manage station owner settings"""

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = StationOwnerSettingsSerializer

    def get_object(self):
        try:
            station_owner = StationOwner.objects.get(user=self.request.user)
            settings_obj, created = StationOwnerSettings.objects.get_or_create(
                owner=station_owner,
                defaults={
                    'default_pricing_per_kwh': 5.50,
                    'auto_accept_bookings': True,
                    'max_session_duration_hours': 4,
                    'maintenance_mode': False,
                    'email_notifications': True,
                    'sms_notifications': False,
                    'booking_notifications': True,
                    'payment_notifications': True,
                    'maintenance_alerts': True,
                    'marketing_emails': False,
                    'station_updates': True,
                    'brand_color': '#3B82F6',
                    'display_company_info': True
                }
            )
            return settings_obj
        except StationOwner.DoesNotExist:
            from django.http import Http404
            raise Http404("Station owner profile not found")

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', True)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)

            if serializer.is_valid():
                self.perform_update(serializer)
                return Response({
                    'success': True,
                    'message': 'Settings updated successfully',
                    'data': serializer.data
                })
            else:
                return Response({
                    'success': False,
                    'message': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'success': False,
                'message': f'Failed to update settings: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NotificationTemplateListView(generics.ListAPIView):
    """View to list notification templates"""

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = NotificationTemplateSerializer
    queryset = NotificationTemplate.objects.filter(is_active=True)


class NotificationTemplateDetailView(generics.RetrieveUpdateAPIView):
    """View to retrieve and update notification templates"""

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = NotificationTemplateSerializer
    queryset = NotificationTemplate.objects.all()
    lookup_field = 'template_type'


class ReviewReplyCreateView(generics.CreateAPIView):
    """View for station owners to reply to reviews"""

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = ReviewReplySerializer

    def perform_create(self, serializer):
        try:
            station_owner = StationOwner.objects.get(user=self.request.user)
            review = serializer.validated_data['review']

            # Validate that the station owner owns the station being reviewed
            if review.station.owner != station_owner:
                raise permissions.PermissionDenied(
                    "You can only reply to reviews of your own stations."
                )

            # Check if reply already exists
            if hasattr(review, 'reply'):
                raise serializers.ValidationError(
                    "A reply already exists for this review. Use the update endpoint to modify it."
                )

            serializer.save(station_owner=station_owner)

        except StationOwner.DoesNotExist:
            raise permissions.PermissionDenied("Only station owners can reply to reviews.")


class ReviewReplyDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View for station owners to retrieve, update, or delete their replies"""

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = ReviewReplySerializer
    lookup_field = 'id'

    def get_queryset(self):
        try:
            station_owner = StationOwner.objects.get(user=self.request.user)
            return ReviewReply.objects.filter(station_owner=station_owner)
        except StationOwner.DoesNotExist:
            return ReviewReply.objects.none()

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        # Soft delete - mark as inactive instead of deleting
        instance.is_active = False
        instance.save()


class StationOwnerRepliesView(generics.ListAPIView):
    """View for station owners to see all their replies"""

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = ReviewReplyListSerializer

    def get_queryset(self):
        try:
            station_owner = StationOwner.objects.get(user=self.request.user)
            return ReviewReply.objects.filter(
                station_owner=station_owner,
                is_active=True
            ).select_related('review', 'review__station', 'review__user').order_by('-created_at')
        except StationOwner.DoesNotExist:
            return ReviewReply.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # Add review and station information to each reply
        reply_data = []
        for reply in queryset:
            reply_serializer = self.get_serializer(reply)
            reply_info = reply_serializer.data

            # Add review information
            reply_info['review_info'] = {
                'id': reply.review.id,
                'rating': reply.review.rating,
                'review_text': reply.review.review_text,
                'user_name': f"{reply.review.user.first_name} {reply.review.user.last_name}".strip() or reply.review.user.email.split('@')[0],
                'created_at': reply.review.created_at,
                'station_name': reply.review.station.name,
                'station_id': reply.review.station.id
            }

            reply_data.append(reply_info)

        return Response({
            'success': True,
            'count': len(reply_data),
            'results': reply_data
        })


class AvailableStationsView(generics.ListAPIView):
    """View to fetch only available charging stations with real-time data"""

    serializer_class = AvailableStationSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = [AnonymousAuthentication, TokenAuthentication, SessionAuthentication]

    def get_queryset(self):
        """Filter stations to show only available ones"""
        queryset = ChargingStation.objects.filter(
            is_active=True,
            is_public=True,
            status='operational',
            available_connectors__gt=0  # Only stations with available connectors
        ).select_related('owner').prefetch_related('connectors')

        # Apply additional filters
        queryset = self._apply_filters(queryset)

        # Update connector availability for all stations in queryset
        self._update_connector_availability(queryset)

        # Re-filter after updating availability
        queryset = queryset.filter(available_connectors__gt=0)

        # Order by distance if user location provided, otherwise by rating
        user_lat = self.request.query_params.get('user_lat')
        user_lng = self.request.query_params.get('user_lng')

        if user_lat and user_lng:
            # Order by distance (this is a simplified ordering)
            # In production, you might want to use PostGIS for better distance calculations
            queryset = queryset.extra(
                select={
                    'distance': """
                        6371 * acos(
                            cos(radians(%s)) * cos(radians(latitude)) *
                            cos(radians(longitude) - radians(%s)) +
                            sin(radians(%s)) * sin(radians(latitude))
                        )
                    """
                },
                select_params=[user_lat, user_lng, user_lat]
            ).order_by('distance')
        else:
            queryset = queryset.order_by('-rating', '-rating_count')

        return queryset

    def _apply_filters(self, queryset):
        """Apply various filters based on query parameters"""

        # Filter by connector type
        connector_type = self.request.query_params.get('connector_type')
        if connector_type:
            queryset = queryset.filter(
                connectors__connector_type=connector_type,
                connectors__is_available=True
            ).distinct()

        # Filter by minimum power
        min_power = self.request.query_params.get('min_power')
        if min_power:
            try:
                queryset = queryset.filter(
                    connectors__power_kw__gte=float(min_power),
                    connectors__is_available=True
                ).distinct()
            except ValueError:
                pass

        # Filter by maximum distance
        max_distance = self.request.query_params.get('max_distance')
        user_lat = self.request.query_params.get('user_lat')
        user_lng = self.request.query_params.get('user_lng')

        if max_distance and user_lat and user_lng:
            try:
                # Simple bounding box filter (more efficient than exact distance calculation)
                distance_km = float(max_distance)
                lat_delta = distance_km / 111.0  # Approximate km per degree latitude
                lng_delta = distance_km / (111.0 * cos(radians(float(user_lat))))

                queryset = queryset.filter(
                    latitude__range=[float(user_lat) - lat_delta, float(user_lat) + lat_delta],
                    longitude__range=[float(user_lng) - lng_delta, float(user_lng) + lng_delta]
                )
            except (ValueError, TypeError):
                pass

        # Filter by amenities
        amenities = self.request.query_params.getlist('amenities')
        for amenity in amenities:
            if amenity == 'restroom':
                queryset = queryset.filter(has_restroom=True)
            elif amenity == 'wifi':
                queryset = queryset.filter(has_wifi=True)
            elif amenity == 'restaurant':
                queryset = queryset.filter(has_restaurant=True)
            elif amenity == 'shopping':
                queryset = queryset.filter(has_shopping=True)

        # Filter by minimum rating
        min_rating = self.request.query_params.get('min_rating')
        if min_rating:
            try:
                queryset = queryset.filter(rating__gte=float(min_rating))
            except ValueError:
                pass

        # Filter by price range
        max_price = self.request.query_params.get('max_price')
        if max_price:
            try:
                queryset = queryset.filter(
                    connectors__price_per_kwh__lte=float(max_price),
                    connectors__is_available=True
                ).distinct()
            except ValueError:
                pass

        return queryset

    def _update_connector_availability(self, queryset):
        """Update connector availability for all stations"""
        for station in queryset:
            station.update_connector_counts()

    def list(self, request, *args, **kwargs):
        """Override list to add metadata"""
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response_data = self.get_paginated_response(serializer.data)

            # Add metadata
            response_data.data['metadata'] = self._get_metadata(queryset)
            return response_data

        serializer = self.get_serializer(queryset, many=True)

        return Response({
            'success': True,
            'count': len(serializer.data),
            'results': serializer.data,
            'metadata': self._get_metadata(queryset)
        })

    def _get_metadata(self, queryset):
        """Get metadata about the available stations"""
        total_stations = queryset.count()

        if total_stations == 0:
            return {
                'total_available_stations': 0,
                'total_available_connectors': 0,
                'average_rating': 0,
                'connector_types_available': [],
                'price_range': {'min': None, 'max': None}
            }

        # Calculate metadata
        total_connectors = sum(station.available_connectors for station in queryset)
        avg_rating = sum(station.rating for station in queryset) / total_stations

        # Get unique connector types
        connector_types = set()
        prices = []

        for station in queryset:
            for connector in station.connectors.filter(is_available=True):
                connector_types.add(connector.get_connector_type_display())
                if connector.price_per_kwh:
                    prices.append(float(connector.price_per_kwh))

        price_range = {
            'min': min(prices) if prices else None,
            'max': max(prices) if prices else None
        }

        return {
            'total_available_stations': total_stations,
            'total_available_connectors': total_connectors,
            'average_rating': round(avg_rating, 2),
            'connector_types_available': list(connector_types),
            'price_range': price_range,
            'last_updated': timezone.now().isoformat()
        }


class PayoutMethodListCreateView(generics.ListCreateAPIView):
    """View to list and create payout methods for station owners"""

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = PayoutMethodSerializer

    def get_queryset(self):
        try:
            station_owner = StationOwner.objects.get(user=self.request.user)
            return PayoutMethod.objects.filter(
                station_owner=station_owner,
                is_active=True
            ).order_by('-is_default', '-created_at')
        except StationOwner.DoesNotExist:
            return PayoutMethod.objects.none()

    def create(self, request, *args, **kwargs):
        try:
            # Check if user is a station owner
            station_owner = StationOwner.objects.get(user=request.user)

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # If this is the first payout method, make it default
            existing_methods = PayoutMethod.objects.filter(
                station_owner=station_owner,
                is_active=True
            ).count()

            if existing_methods == 0:
                serializer.validated_data['is_default'] = True

            payout_method = serializer.save()

            return Response({
                'success': True,
                'message': 'Payout method added successfully',
                'data': PayoutMethodSerializer(payout_method).data
            }, status=status.HTTP_201_CREATED)

        except StationOwner.DoesNotExist:
            return Response({
                'success': False,
                'error': 'You must be a registered station owner to add payout methods'
            }, status=status.HTTP_403_FORBIDDEN)


class PayoutMethodDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View to retrieve, update, or delete a specific payout method"""

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = PayoutMethodSerializer
    lookup_field = 'id'

    def get_queryset(self):
        try:
            station_owner = StationOwner.objects.get(user=self.request.user)
            return PayoutMethod.objects.filter(
                station_owner=station_owner,
                is_active=True
            )
        except StationOwner.DoesNotExist:
            return PayoutMethod.objects.none()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()

        # Don't allow updating sensitive fields after creation
        protected_fields = ['account_number', 'card_number', 'routing_number']
        for field in protected_fields:
            if field in request.data:
                request.data.pop(field)

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            'success': True,
            'message': 'Payout method updated successfully',
            'data': serializer.data
        })

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        # Don't allow deleting the default method if it's the only one
        station_owner = instance.station_owner
        active_methods = PayoutMethod.objects.filter(
            station_owner=station_owner,
            is_active=True
        ).count()

        if instance.is_default and active_methods == 1:
            return Response({
                'success': False,
                'error': 'Cannot delete the only payout method. Add another method first.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # If deleting default method, set another as default
        if instance.is_default:
            next_method = PayoutMethod.objects.filter(
                station_owner=station_owner,
                is_active=True
            ).exclude(id=instance.id).first()

            if next_method:
                next_method.is_default = True
                next_method.save()

        instance.is_active = False
        instance.save()

        return Response({
            'success': True,
            'message': 'Payout method deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


class SetDefaultPayoutMethodView(APIView):
    """View to set a payout method as default"""

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def post(self, request, method_id):
        try:
            station_owner = StationOwner.objects.get(user=request.user)

            # Get the payout method
            payout_method = get_object_or_404(
                PayoutMethod,
                id=method_id,
                station_owner=station_owner,
                is_active=True
            )

            # Set this method as default (this will automatically unset others)
            payout_method.is_default = True
            payout_method.save()

            return Response({
                'success': True,
                'message': 'Default payout method updated successfully',
                'data': PayoutMethodSerializer(payout_method).data
            })

        except StationOwner.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Station owner profile not found'
            }, status=status.HTTP_404_NOT_FOUND)


class WithdrawalRequestView(APIView):
    """View to handle withdrawal requests from station owners"""

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]

    def post(self, request):
        try:
            station_owner = StationOwner.objects.get(user=request.user)

            amount = request.data.get('amount')
            payment_method_id = request.data.get('payment_method_id')
            description = request.data.get('description', 'Withdrawal request')

            # Validate amount
            if not amount or float(amount) <= 0:
                return Response({
                    'success': False,
                    'error': 'Invalid withdrawal amount'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate payment method
            try:
                payout_method = PayoutMethod.objects.get(
                    id=payment_method_id,
                    station_owner=station_owner,
                    is_active=True
                )
            except PayoutMethod.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Invalid payment method'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check available balance from wallet system
            from payments.models import Wallet, WalletTransaction
            # Create wallet if it doesn't exist (similar to WalletDetailView)
            wallet, created = Wallet.objects.get_or_create(user=request.user)

            if wallet.balance < float(amount):
                return Response({
                    'success': False,
                    'error': f'Insufficient balance. Available: {wallet.balance} ETB'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Create withdrawal record in database
            withdrawal_request = WithdrawalRequest.objects.create(
                station_owner=station_owner,
                payout_method=payout_method,
                amount=float(amount),
                description=description,
                status=WithdrawalRequest.WithdrawalStatus.PENDING
            )

            # Create a Transaction object for the withdrawal
            from payments.models import Transaction
            withdrawal_transaction = Transaction.objects.create(
                user=request.user,
                amount=float(amount),
                currency='ETB',
                transaction_type='withdrawal',
                status='pending',
                reference_number=withdrawal_request.reference_number,
                description=f'Withdrawal request {withdrawal_request.reference_number}'
            )

            # Create a pending wallet transaction (will be completed when admin approves)
            balance_before = wallet.balance
            wallet.balance -= float(amount)
            balance_after = wallet.balance
            wallet.save()

            WalletTransaction.objects.create(
                wallet=wallet,
                transaction=withdrawal_transaction,
                transaction_type=WalletTransaction.TransactionType.DEBIT,
                amount=float(amount),
                balance_before=balance_before,
                balance_after=balance_after,
                description=f'Withdrawal request {withdrawal_request.reference_number}'
            )

            # Send notification to admins about new withdrawal request
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admin_users = User.objects.filter(is_staff=True, is_active=True)

            # TODO: Implement actual notification system (email, in-app notifications)
            # For now, we'll just log it
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f'New withdrawal request {withdrawal_request.reference_number} from {station_owner.company_name} for {amount} ETB')

            return Response({
                'success': True,
                'message': 'Withdrawal request submitted successfully. It will be processed within 1-3 business days.',
                'data': WithdrawalRequestSerializer(withdrawal_request).data
            })

        except StationOwner.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Station owner profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({
                'success': False,
                'error': 'Invalid amount format'
            }, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        """Get withdrawal requests for the authenticated station owner"""
        try:
            station_owner = StationOwner.objects.get(user=request.user)
            withdrawals = WithdrawalRequest.objects.filter(station_owner=station_owner).order_by('-created_at')

            return Response({
                'success': True,
                'data': WithdrawalRequestSerializer(withdrawals, many=True).data
            })
        except StationOwner.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Station owner profile not found'
            }, status=status.HTTP_404_NOT_FOUND)


class WithdrawalRequestDetailView(generics.RetrieveUpdateAPIView):
    """View to retrieve and update specific withdrawal requests"""

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    lookup_field = 'id'

    def get_serializer_class(self):
        """Return appropriate serializer based on user type"""
        if self.request.user.is_staff or self.request.user.is_superuser:
            return WithdrawalRequestAdminSerializer
        return WithdrawalRequestSerializer

    def get_queryset(self):
        """Get withdrawal requests based on user type"""
        if self.request.user.is_staff or self.request.user.is_superuser:
            # Admins can see all withdrawal requests
            return WithdrawalRequest.objects.all()
        else:
            # Station owners can only see their own requests
            try:
                station_owner = StationOwner.objects.get(user=self.request.user)
                return WithdrawalRequest.objects.filter(station_owner=station_owner)
            except StationOwner.DoesNotExist:
                return WithdrawalRequest.objects.none()

    def update(self, request, *args, **kwargs):
        """Update withdrawal request (admin only for status changes)"""
        instance = self.get_object()

        # Only admins can change status
        if 'status' in request.data and not (request.user.is_staff or request.user.is_superuser):
            return Response({
                'success': False,
                'error': 'Only administrators can change withdrawal status'
            }, status=status.HTTP_403_FORBIDDEN)

        # Station owners can only update their own requests and only if pending
        if not (request.user.is_staff or request.user.is_superuser):
            try:
                station_owner = StationOwner.objects.get(user=request.user)
                if instance.station_owner != station_owner:
                    return Response({
                        'success': False,
                        'error': 'You can only update your own withdrawal requests'
                    }, status=status.HTTP_403_FORBIDDEN)

                if instance.status != WithdrawalRequest.WithdrawalStatus.PENDING:
                    return Response({
                        'success': False,
                        'error': 'You can only update pending withdrawal requests'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except StationOwner.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Station owner profile not found'
                }, status=status.HTTP_404_NOT_FOUND)

        return super().update(request, *args, **kwargs)


class WithdrawalRequestListView(generics.ListAPIView):
    """Admin view to list all withdrawal requests"""

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = WithdrawalRequestAdminSerializer

    def get_queryset(self):
        """Only admins can access this view"""
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            return WithdrawalRequest.objects.none()

        queryset = WithdrawalRequest.objects.all()

        # Filter by status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by station owner if provided
        station_owner_id = self.request.query_params.get('station_owner')
        if station_owner_id:
            queryset = queryset.filter(station_owner_id=station_owner_id)

        return queryset.order_by('-created_at')
