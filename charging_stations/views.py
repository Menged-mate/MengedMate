from rest_framework import generics, status, permissions
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
from .models import StationOwner, ChargingStation, StationImage, ChargingConnector, AppContent, StationReview
from .serializers import (
    StationOwnerRegistrationSerializer,
    StationOwnerProfileSerializer,
    ChargingStationSerializer,
    ChargingConnectorSerializer,
    StationImageSerializer,
    StationReviewSerializer,
    StationReviewListSerializer
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

        subject = 'Verify Your EV Charging Station Owner Account'
        html_message = render_to_string('station_owner_verification_email.html', {
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
            subject = 'New Station Owner Requires Verification'
            message = f'A new station owner ({instance.company_name}) has completed their profile and requires verification.'
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL],
                fail_silently=True,
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

    def perform_create(self, serializer):
        station_id = self.kwargs.get('station_id')
        try:
            station_owner = StationOwner.objects.get(user=self.request.user)
            station = ChargingStation.objects.get(id=station_id, owner=station_owner)

            # Check if a connector with the same type and power already exists
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
                # Update existing connector quantity
                existing_connector.quantity += quantity_to_add
                existing_connector.available_quantity += quantity_to_add
                existing_connector.save()
                connector = existing_connector
            else:
                # Create new connector
                connector = serializer.save(station=station)

            # Update station connector counts
            station.update_connector_counts()
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

    def perform_create(self, serializer):
        station_id = self.kwargs.get('station_id')
        station = get_object_or_404(ChargingStation, id=station_id)

        # Check if user already has a review for this station
        existing_review = StationReview.objects.filter(
            user=self.request.user,
            station=station
        ).first()

        if existing_review:
            # Update existing review instead of creating new one
            for attr, value in serializer.validated_data.items():
                setattr(existing_review, attr, value)
            existing_review.save()
        else:
            # Create new review
            serializer.save(user=self.request.user, station=station)


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
            # Try to get OCPP charging sessions first
            try:
                from ocpp_integration.models import ChargingSession as OCPPChargingSession
                ocpp_sessions = OCPPChargingSession.objects.filter(
                    user=request.user
                ).select_related(
                    'ocpp_station__charging_station',
                    'ocpp_connector__charging_connector'
                ).order_by('-created_at')[:50]  # Limit to last 50 sessions

                sessions_data = []
                for session in ocpp_sessions:
                    session_data = {
                        'id': str(session.id),
                        'transaction_id': session.transaction_id,
                        'station_name': session.ocpp_station.charging_station.name,
                        'station_address': session.ocpp_station.charging_station.address,
                        'connector_type': session.ocpp_connector.charging_connector.connector_type,
                        'start_time': session.start_time.isoformat() if session.start_time else None,
                        'stop_time': session.stop_time.isoformat() if session.stop_time else None,
                        'energy_consumed_kwh': str(session.energy_consumed_kwh),
                        'final_cost': str(session.final_cost) if session.final_cost else None,
                        'estimated_cost': str(session.estimated_cost),
                        'status': session.status,
                        'payment_status': session.payment_status,
                        'duration_seconds': session.duration_seconds,
                        'payment_method': session.payment_method,
                    }
                    sessions_data.append(session_data)

                return Response({
                    'success': True,
                    'results': sessions_data,
                    'count': len(sessions_data)
                })

            except ImportError:
                # OCPP integration not available, try simple charging sessions
                try:
                    from payments.models import SimpleChargingSession
                    simple_sessions = SimpleChargingSession.objects.filter(
                        user=request.user
                    ).select_related(
                        'connector__station'
                    ).order_by('-created_at')[:50]

                    sessions_data = []
                    for session in simple_sessions:
                        duration_seconds = session.duration_seconds
                        if session.start_time and session.stop_time:
                            duration_seconds = int((session.stop_time - session.start_time).total_seconds())

                        session_data = {
                            'id': str(session.id),
                            'transaction_id': session.transaction_id,
                            'station_name': session.connector.station.name,
                            'station_address': session.connector.station.address,
                            'connector_type': session.connector.connector_type,
                            'start_time': session.start_time.isoformat() if session.start_time else None,
                            'stop_time': session.stop_time.isoformat() if session.stop_time else None,
                            'energy_consumed_kwh': str(session.energy_consumed_kwh),
                            'final_cost': None,  # Calculate from QR session if needed
                            'estimated_cost': '0.00',
                            'status': session.status,
                            'payment_status': 'completed' if session.status == 'completed' else 'pending',
                            'duration_seconds': duration_seconds,
                            'payment_method': 'qr_code',
                        }
                        sessions_data.append(session_data)

                    return Response({
                        'success': True,
                        'results': sessions_data,
                        'count': len(sessions_data)
                    })

                except ImportError:
                    # No charging session models available, return empty
                    return Response({
                        'success': True,
                        'results': [],
                        'count': 0,
                        'message': 'No charging sessions found'
                    })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'results': [],
                'count': 0
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
