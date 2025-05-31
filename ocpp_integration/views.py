from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from .models import OCPPStation, OCPPConnector, ChargingSession, SessionMeterValue, OCPPLog
from .serializers import (
    OCPPStationSerializer, OCPPConnectorSerializer, ChargingSessionSerializer,
    ChargingSessionDetailSerializer, OCPPLogSerializer, SyncStationSerializer,
    InitiateChargingSerializer, StopChargingSerializer, SessionStatusSerializer,
    WebhookDataSerializer, StationStatusUpdateSerializer, ConnectorStatusUpdateSerializer
)
from .services import OCPPIntegrationService
from charging_stations.models import ChargingStation
from authentication.models import CustomUser
import logging

logger = logging.getLogger(__name__)


class OCPPStationListView(generics.ListAPIView):
    serializer_class = OCPPStationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'station_owner'):
            return OCPPStation.objects.filter(
                charging_station__owner=user.station_owner
            )
        return OCPPStation.objects.none()


class OCPPStationDetailView(generics.RetrieveAPIView):
    serializer_class = OCPPStationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'station_id'

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'station_owner'):
            return OCPPStation.objects.filter(
                charging_station__owner=user.station_owner
            )
        return OCPPStation.objects.none()


class SyncStationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SyncStationSerializer(data=request.data)
        if serializer.is_valid():
            charging_station_id = serializer.validated_data['charging_station_id']

            try:
                charging_station = ChargingStation.objects.get(id=charging_station_id)

                if hasattr(request.user, 'station_owner'):
                    if charging_station.owner != request.user.station_owner:
                        return Response(
                            {'error': 'You do not own this charging station'},
                            status=status.HTTP_403_FORBIDDEN
                        )

                ocpp_service = OCPPIntegrationService()
                result = ocpp_service.sync_station_to_ocpp(charging_station)

                if result['success']:
                    return Response({
                        'success': True,
                        'message': 'Station synced successfully',
                        'data': result['data']
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'success': False,
                        'error': result['error']
                    }, status=status.HTTP_400_BAD_REQUEST)

            except ChargingStation.DoesNotExist:
                return Response(
                    {'error': 'Charging station not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InitiateChargingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InitiateChargingSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = CustomUser.objects.get(id=serializer.validated_data['user_id'])

                owner_info = None
                if 'owner_id' in serializer.validated_data:
                    owner_info = {
                        'owner_id': serializer.validated_data.get('owner_id'),
                        'owner_name': serializer.validated_data.get('owner_name')
                    }

                ocpp_service = OCPPIntegrationService()
                result = ocpp_service.initiate_charging(
                    station_id=serializer.validated_data['station_id'],
                    connector_id=serializer.validated_data['connector_id'],
                    user=user,
                    payment_transaction_id=serializer.validated_data['payment_transaction_id'],
                    owner_info=owner_info
                )

                if result['success']:
                    session_serializer = ChargingSessionSerializer(result['charging_session'])
                    return Response({
                        'success': True,
                        'message': 'Charging session initiated successfully',
                        'charging_session': session_serializer.data,
                        'data': result['data']
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'success': False,
                        'error': result['error']
                    }, status=status.HTTP_400_BAD_REQUEST)

            except CustomUser.DoesNotExist:
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StopChargingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = StopChargingSerializer(data=request.data)
        if serializer.is_valid():
            ocpp_service = OCPPIntegrationService()
            result = ocpp_service.stop_charging(
                transaction_id=serializer.validated_data['transaction_id'],
                user_id=serializer.validated_data.get('user_id')
            )

            if result['success']:
                if 'charging_session' in result:
                    session_serializer = ChargingSessionSerializer(result['charging_session'])
                    return Response({
                        'success': True,
                        'message': 'Stop command sent successfully',
                        'charging_session': session_serializer.data,
                        'data': result['data']
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'success': True,
                        'message': 'Stop command sent successfully',
                        'data': result['data']
                    }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'error': result['error']
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SessionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = SessionStatusSerializer(data=request.query_params)
        if serializer.is_valid():
            transaction_id = serializer.validated_data['transaction_id']

            ocpp_service = OCPPIntegrationService()
            result = ocpp_service.get_session_data(transaction_id)

            if result['success']:
                if 'charging_session' in result:
                    session_serializer = ChargingSessionDetailSerializer(result['charging_session'])
                    return Response({
                        'success': True,
                        'charging_session': session_serializer.data,
                        'data': result['data']
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'success': True,
                        'data': result['data']
                    }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'error': result['error']
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChargingSessionListView(generics.ListAPIView):
    serializer_class = ChargingSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = ChargingSession.objects.all()

        if hasattr(user, 'station_owner'):
            queryset = queryset.filter(
                ocpp_station__charging_station__owner=user.station_owner
            )
        else:
            queryset = queryset.filter(user=user)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-created_at')


class ChargingSessionDetailView(generics.RetrieveAPIView):
    serializer_class = ChargingSessionDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'transaction_id'

    def get_queryset(self):
        user = self.request.user
        queryset = ChargingSession.objects.all()

        if hasattr(user, 'station_owner'):
            queryset = queryset.filter(
                ocpp_station__charging_station__owner=user.station_owner
            )
        else:
            queryset = queryset.filter(user=user)

        return queryset


@api_view(['POST'])
@permission_classes([AllowAny])
def ocpp_webhook(request):
    try:
        serializer = WebhookDataSerializer(data=request.data)
        if serializer.is_valid():
            webhook_data = serializer.validated_data
            webhook_type = webhook_data.get('type')

            if webhook_type == 'session_started':
                handle_session_started(webhook_data)
            elif webhook_type == 'session_progress':
                handle_session_progress(webhook_data)
            elif webhook_type == 'session_stopped':
                handle_session_stopped(webhook_data)
            elif webhook_type == 'availability_changed':
                handle_availability_changed(webhook_data)
            elif webhook_type == 'station_status':
                handle_station_status_update(webhook_data)
            elif webhook_type == 'connector_status':
                handle_connector_status_update(webhook_data)

            return Response({
                'status': 'success',
                'message': 'Webhook processed successfully'
            }, status=status.HTTP_200_OK)

        return Response({
            'status': 'error',
            'message': 'Invalid webhook data',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return Response({
            'status': 'error',
            'message': 'Webhook processing failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def handle_session_started(webhook_data):
    try:
        transaction_id = webhook_data.get('transaction_id')
        data = webhook_data.get('data', {})

        if transaction_id:
            session = ChargingSession.objects.filter(transaction_id=transaction_id).first()
            if session:
                session.status = ChargingSession.SessionStatus.STARTED
                session.start_time = timezone.now()
                session.save()

                session.ocpp_connector.status = OCPPConnector.ConnectorStatus.CHARGING
                session.ocpp_connector.save()

                logger.info(f"Session {transaction_id} started successfully")
    except Exception as e:
        logger.error(f"Error handling session started webhook: {e}")


def handle_session_progress(webhook_data):
    try:
        transaction_id = webhook_data.get('transaction_id')
        data = webhook_data.get('data', {})

        if transaction_id:
            session = ChargingSession.objects.filter(transaction_id=transaction_id).first()
            if session:
                session.energy_consumed_kwh = data.get('energy_consumed_kwh', session.energy_consumed_kwh)
                session.current_power_kw = data.get('current_power_kw', session.current_power_kw)
                session.duration_seconds = data.get('duration_seconds', session.duration_seconds)
                session.estimated_cost = data.get('estimated_cost', session.estimated_cost)
                session.status = ChargingSession.SessionStatus.CHARGING
                session.save()

                logger.debug(f"Session {transaction_id} progress updated")
    except Exception as e:
        logger.error(f"Error handling session progress webhook: {e}")


def handle_session_stopped(webhook_data):
    try:
        transaction_id = webhook_data.get('transaction_id')
        data = webhook_data.get('data', {})

        if transaction_id:
            session = ChargingSession.objects.filter(transaction_id=transaction_id).first()
            if session:
                session.status = ChargingSession.SessionStatus.COMPLETED
                session.stop_time = timezone.now()
                session.final_cost = data.get('final_cost', session.estimated_cost)
                session.stop_reason = data.get('stop_reason', 'User requested')
                session.meter_stop = data.get('meter_stop', session.meter_start)
                session.save()

                session.ocpp_connector.status = OCPPConnector.ConnectorStatus.AVAILABLE
                session.ocpp_connector.save()

                logger.info(f"Session {transaction_id} completed successfully")
    except Exception as e:
        logger.error(f"Error handling session stopped webhook: {e}")


def handle_availability_changed(webhook_data):
    try:
        station_id = webhook_data.get('station_id')
        data = webhook_data.get('data', {})

        if station_id:
            ocpp_station = OCPPStation.objects.filter(station_id=station_id).first()
            if ocpp_station:
                connector_id = data.get('connector_id')
                if connector_id:
                    connector = OCPPConnector.objects.filter(
                        ocpp_station=ocpp_station,
                        connector_id=connector_id
                    ).first()
                    if connector:
                        new_status = data.get('status', 'available')
                        connector.status = new_status
                        connector.save()

                        logger.info(f"Connector {connector_id} status changed to {new_status}")
    except Exception as e:
        logger.error(f"Error handling availability changed webhook: {e}")


def handle_station_status_update(webhook_data):
    try:
        station_id = webhook_data.get('station_id')
        data = webhook_data.get('data', {})

        if station_id:
            ocpp_station = OCPPStation.objects.filter(station_id=station_id).first()
            if ocpp_station:
                ocpp_station.status = data.get('status', ocpp_station.status)
                ocpp_station.is_online = data.get('is_online', ocpp_station.is_online)
                if data.get('last_heartbeat'):
                    ocpp_station.last_heartbeat = timezone.now()
                ocpp_station.save()

                logger.info(f"Station {station_id} status updated")
    except Exception as e:
        logger.error(f"Error handling station status update webhook: {e}")


def handle_connector_status_update(webhook_data):
    try:
        station_id = webhook_data.get('station_id')
        data = webhook_data.get('data', {})

        if station_id:
            ocpp_station = OCPPStation.objects.filter(station_id=station_id).first()
            if ocpp_station:
                connector_id = data.get('connector_id')
                if connector_id:
                    connector = OCPPConnector.objects.filter(
                        ocpp_station=ocpp_station,
                        connector_id=connector_id
                    ).first()
                    if connector:
                        connector.status = data.get('status', connector.status)
                        connector.error_code = data.get('error_code', connector.error_code)
                        connector.info = data.get('info', connector.info)
                        connector.vendor_id = data.get('vendor_id', connector.vendor_id)
                        connector.vendor_error_code = data.get('vendor_error_code', connector.vendor_error_code)
                        connector.save()

                        logger.info(f"Connector {connector_id} status updated")
    except Exception as e:
        logger.error(f"Error handling connector status update webhook: {e}")


class OCPPLogListView(generics.ListAPIView):
    serializer_class = OCPPLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = OCPPLog.objects.all()

        if hasattr(user, 'station_owner'):
            queryset = queryset.filter(
                ocpp_station__charging_station__owner=user.station_owner
            )

        level_filter = self.request.query_params.get('level')
        if level_filter:
            queryset = queryset.filter(level=level_filter)

        station_id = self.request.query_params.get('station_id')
        if station_id:
            queryset = queryset.filter(ocpp_station__station_id=station_id)

        return queryset.order_by('-timestamp')[:100]  # Limit to last 100 logs