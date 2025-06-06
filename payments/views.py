from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import PaymentMethod, Transaction, Wallet, WalletTransaction, PaymentSession, QRPaymentSession
from .serializers import (
    PaymentMethodSerializer, TransactionSerializer, WalletSerializer,
    WalletTransactionSerializer, PaymentSessionSerializer, InitiatePaymentSerializer,
    PaymentCallbackSerializer, TransactionStatusSerializer, WithdrawSerializer,
    QRConnectorInfoSerializer, QRPaymentInitiateSerializer, QRPaymentSessionSerializer
)
from charging_stations.models import ChargingConnector
from .services import PaymentService
import logging

logger = logging.getLogger(__name__)


class PaymentMethodListCreateView(generics.ListCreateAPIView):
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user, is_active=True)


class PaymentMethodDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


class TransactionListView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)


class TransactionDetailView(generics.RetrieveAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)


class WalletDetailView(generics.RetrieveAPIView):
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        wallet, created = Wallet.objects.get_or_create(user=self.request.user)
        return wallet


class WalletTransactionListView(generics.ListAPIView):
    serializer_class = WalletTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        wallet = get_object_or_404(Wallet, user=self.request.user)
        return WalletTransaction.objects.filter(wallet=wallet)


class InitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InitiatePaymentSerializer(data=request.data)
        if serializer.is_valid():
            payment_service = PaymentService()

            result = payment_service.initiate_chapa_payment(
                user=request.user,
                amount=serializer.validated_data['amount'],
                phone_number=serializer.validated_data['phone_number'],
                description=serializer.validated_data.get('description', 'MengedMate Payment')
            )

            if result['success']:
                return Response({
                    'success': True,
                    'message': 'Payment initiated successfully',
                    'data': result
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': result.get('message', 'Payment initiation failed')
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def payment_callback(request):
    try:
        callback_data = request.data
        logger.info(f"Payment callback received: {callback_data}")

        payment_service = PaymentService()
        result = payment_service.process_callback(callback_data)

        logger.info(f"Callback processing result: {result}")

        return Response({
            'status': 'success',
            'message': 'Callback processed successfully'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Payment callback error: {e}")
        return Response({
            'status': 'error',
            'message': 'Callback processing failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TransactionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TransactionStatusSerializer(data=request.data)
        if serializer.is_valid():
            payment_service = PaymentService()

            result = payment_service.get_transaction_status(
                serializer.validated_data['tx_ref']
            )

            return Response(result, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PaymentSessionListView(generics.ListAPIView):
    serializer_class = PaymentSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PaymentSession.objects.filter(user=self.request.user)


class QRConnectorInfoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, qr_token):
        try:
            connector = get_object_or_404(ChargingConnector, qr_code_token=qr_token)

            if not connector.is_available or connector.available_quantity <= 0:
                return Response({
                    'success': False,
                    'message': 'This connector is currently not available'
                }, status=status.HTTP_400_BAD_REQUEST)

            serializer = QRConnectorInfoSerializer(connector)
            return Response({
                'success': True,
                'connector': serializer.data
            }, status=status.HTTP_200_OK)

        except ChargingConnector.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Invalid QR code'
            }, status=status.HTTP_404_NOT_FOUND)


class QRPaymentInitiateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, qr_token):
        try:
            connector = get_object_or_404(ChargingConnector, qr_code_token=qr_token)

            if not connector.is_available or connector.available_quantity <= 0:
                return Response({
                    'success': False,
                    'message': 'This connector is currently not available'
                }, status=status.HTTP_400_BAD_REQUEST)

            serializer = QRPaymentInitiateSerializer(data=request.data)
            if serializer.is_valid():
                # Create QR payment session
                expires_at = timezone.now() + timezone.timedelta(minutes=15)

                qr_session = QRPaymentSession.objects.create(
                    user=request.user,
                    connector=connector,
                    payment_type=serializer.validated_data['payment_type'],
                    amount=serializer.validated_data.get('amount'),
                    kwh_requested=serializer.validated_data.get('kwh_requested'),
                    phone_number=serializer.validated_data['phone_number'],
                    expires_at=expires_at
                )

                # Initiate payment with Chapa
                payment_service = PaymentService()
                payment_amount = qr_session.get_payment_amount()

                if payment_amount <= 0:
                    return Response({
                        'success': False,
                        'message': 'Invalid payment amount calculated'
                    }, status=status.HTTP_400_BAD_REQUEST)

                result = payment_service.initiate_chapa_payment(
                    user=request.user,
                    amount=payment_amount,
                    phone_number=qr_session.phone_number,
                    description=f"Charging at {connector.station.name} - {connector.get_connector_type_display()}"
                )

                if result['success']:
                    # Link the QR session to the created transaction
                    from .models import Transaction
                    transaction = Transaction.objects.get(id=result['transaction_id'])
                    qr_session.payment_transaction = transaction
                    qr_session.status = 'payment_initiated'
                    qr_session.save()

                    session_serializer = QRPaymentSessionSerializer(qr_session)
                    return Response({
                        'success': True,
                        'message': 'Payment initiated successfully',
                        'qr_session': session_serializer.data,
                        'payment_data': result
                    }, status=status.HTTP_200_OK)
                else:
                    qr_session.status = 'failed'
                    qr_session.save()
                    return Response({
                        'success': False,
                        'message': result.get('message', 'Payment initiation failed')
                    }, status=status.HTTP_400_BAD_REQUEST)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except ChargingConnector.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Invalid QR code'
            }, status=status.HTTP_404_NOT_FOUND)


class QRPaymentSessionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_token):
        try:
            qr_session = get_object_or_404(QRPaymentSession, session_token=session_token, user=request.user)
            serializer = QRPaymentSessionSerializer(qr_session)

            response_data = {
                'success': True,
                'qr_session': serializer.data
            }

            # Include payment data if transaction exists and has provider response
            if qr_session.payment_transaction and qr_session.payment_transaction.provider_response:
                response_data['qr_session']['payment_data'] = qr_session.payment_transaction.provider_response

            return Response(response_data, status=status.HTTP_200_OK)

        except QRPaymentSession.DoesNotExist:
            return Response({
                'success': False,
                'message': 'QR payment session not found'
            }, status=status.HTTP_404_NOT_FOUND)


class QRPaymentSessionListView(generics.ListAPIView):
    serializer_class = QRPaymentSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return QRPaymentSession.objects.filter(user=self.request.user)


class StartChargingFromQRView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_token):
        try:
            qr_session = get_object_or_404(
                QRPaymentSession,
                session_token=session_token,
                user=request.user,
                status='payment_completed'
            )

            # Check if connector is still available
            if not qr_session.connector.is_available or qr_session.connector.available_quantity <= 0:
                return Response({
                    'success': False,
                    'message': 'Connector is no longer available'
                }, status=status.HTTP_400_BAD_REQUEST)

            # For now, just update the QR session status without creating a separate charging session
            # This avoids the complex OCPP integration and model dependencies
            import uuid

            # Generate a simple session ID for tracking
            session_id = str(uuid.uuid4())[:8]

            # Update QR session status
            qr_session.status = 'charging_started'
            qr_session.save()

            # Update connector status to occupied
            qr_session.connector.is_available = False
            qr_session.connector.available_quantity = max(0, qr_session.connector.available_quantity - 1)
            qr_session.connector.save()

            session_serializer = QRPaymentSessionSerializer(qr_session)
            return Response({
                'success': True,
                'message': 'Charging session started successfully',
                'qr_session': session_serializer.data,
                'charging_session': {
                    'id': session_id,
                    'status': 'started',
                    'start_time': timezone.now(),
                    'max_power_kw': qr_session.connector.power_kw
                }
            }, status=status.HTTP_200_OK)

        except QRPaymentSession.DoesNotExist:
            return Response({
                'success': False,
                'message': 'QR payment session not found or payment not completed'
            }, status=status.HTTP_404_NOT_FOUND)


class TestCompletePaymentView(APIView):
    """Test endpoint to manually complete a payment for testing purposes"""
    permission_classes = [IsAuthenticated]

    def post(self, request, session_token):
        try:
            qr_session = get_object_or_404(
                QRPaymentSession,
                session_token=session_token,
                user=request.user,
                status='payment_initiated'
            )

            if qr_session.payment_transaction:
                # Mark transaction as completed
                qr_session.payment_transaction.status = Transaction.TransactionStatus.COMPLETED
                qr_session.payment_transaction.completed_at = timezone.now()
                qr_session.payment_transaction.save()

                # Mark QR session as payment completed
                qr_session.status = 'payment_completed'
                qr_session.save()

                session_serializer = QRPaymentSessionSerializer(qr_session)
                return Response({
                    'success': True,
                    'message': 'Payment marked as completed for testing',
                    'qr_session': session_serializer.data
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': 'No payment transaction found'
                }, status=status.HTTP_400_BAD_REQUEST)

        except QRPaymentSession.DoesNotExist:
            return Response({
                'success': False,
                'message': 'QR payment session not found or not in payment_initiated status'
            }, status=status.HTTP_404_NOT_FOUND)
