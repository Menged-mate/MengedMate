from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from .models import StationOwner, ChargingStation, StationImage, ChargingConnector
from .serializers import (
    StationOwnerRegistrationSerializer,
    StationOwnerProfileSerializer,
    ChargingStationSerializer,
    ChargingConnectorSerializer,
    StationImageSerializer
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
    parser_classes = [MultiPartParser, FormParser]
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
