from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
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
import uuid

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

            # Detect if request is from mobile app
            user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
            is_mobile_app = 'evmeri' in user_agent or 'flutter' in user_agent or 'dart' in user_agent

            result = payment_service.initiate_chapa_payment(
                user=request.user,
                amount=serializer.validated_data['amount'],
                phone_number=serializer.validated_data['phone_number'],
                description=serializer.validated_data.get('description', 'evmeri Payment'),
                use_mobile_return=is_mobile_app
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

        # If callback processing was successful, also process any pending credits
        if result.get('success'):
            try:
                pending_result = payment_service.process_pending_station_owner_credits()
                logger.info(f"Pending credits processed: {pending_result}")
            except Exception as e:
                logger.error(f"Error processing pending credits: {e}")

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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_pending_credits(request):
    """
    Manual endpoint to process pending station owner credits
    Only accessible by authenticated users (can be restricted to staff only)
    """
    try:
        payment_service = PaymentService()
        result = payment_service.process_pending_station_owner_credits()

        # Also get current wallet balance for the user if they're a station owner
        wallet_balance = 0
        try:
            from charging_stations.models import StationOwner
            station_owner = StationOwner.objects.get(user=request.user)
            wallet, created = Wallet.objects.get_or_create(user=request.user)
            wallet_balance = float(wallet.balance)
        except StationOwner.DoesNotExist:
            pass

        return Response({
            'success': True,
            'message': 'Pending credits processed successfully',
            'data': {
                **result,
                'current_wallet_balance': wallet_balance
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error processing pending credits: {e}")
        return Response({
            'success': False,
            'message': 'Failed to process pending credits',
            'error': str(e)
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
                'connector_info': serializer.data
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

                # Detect if request is from mobile app
                user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
                is_mobile_app = 'evmeri' in user_agent or 'flutter' in user_agent or 'dart' in user_agent

                result = payment_service.initiate_chapa_payment(
                    user=request.user,
                    amount=payment_amount,
                    phone_number=qr_session.phone_number,
                    description=f"Charging at {connector.station.name} - {connector.get_connector_type_display()}",
                    use_mobile_return=is_mobile_app
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
                    'id': session_token,
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

                # CRITICAL FIX: Credit station owner wallet when payment is completed
                try:
                    from .services import PaymentService
                    payment_service = PaymentService()

                    # Credit station owner wallet
                    success = payment_service._credit_station_owner_for_qr_payment(
                        qr_session,
                        qr_session.payment_transaction
                    )

                    if success:
                        logger.info(f"Successfully credited station owner for test payment completion: {session_token}")
                    else:
                        logger.error(f"Failed to credit station owner for test payment completion: {session_token}")

                except Exception as e:
                    logger.error(f"Error crediting station owner for test payment: {e}")

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


class StopChargingFromQRView(APIView):
    """Stop charging session from QR payment"""
    permission_classes = [IsAuthenticated]

    def post(self, request, session_token):
        try:
            qr_session = get_object_or_404(
                QRPaymentSession,
                session_token=session_token,
                user=request.user,
                status='charging_started'
            )

            # Update SimpleChargingSession if it exists
            if qr_session.simple_charging_session:
                charging_session = qr_session.simple_charging_session
                charging_session.status = 'completed'
                charging_session.stop_time = timezone.now()

                # Calculate duration
                if charging_session.start_time:
                    duration = timezone.now() - charging_session.start_time
                    charging_session.duration_seconds = int(duration.total_seconds())

                # Set some demo energy values
                charging_session.energy_delivered_kwh = 5.0  # Demo value
                charging_session.energy_consumed_kwh = 5.0   # Demo value
                charging_session.save()

                # Credit station owner's wallet with additional revenue from energy consumed
                if charging_session.energy_consumed_kwh and charging_session.cost_per_kwh:
                    additional_revenue = float(charging_session.energy_consumed_kwh * charging_session.cost_per_kwh)

                    # Only credit if there's additional revenue beyond the initial payment
                    initial_payment = float(qr_session.payment_transaction.amount) if qr_session.payment_transaction else 0
                    if additional_revenue > initial_payment:
                        extra_revenue = additional_revenue - initial_payment

                        # Create a new transaction for the additional revenue
                        from .models import Transaction
                        additional_transaction = Transaction.objects.create(
                            user=qr_session.connector.station.owner.user,
                            transaction_type=Transaction.TransactionType.PAYMENT,
                            status=Transaction.TransactionStatus.COMPLETED,
                            amount=extra_revenue,
                            description=f"Additional revenue from charging session {charging_session.transaction_id}",
                            reference_number=f"ENERGY_{charging_session.transaction_id}",
                            completed_at=timezone.now()
                        )

                        # Credit the station owner's wallet
                        from .services import PaymentService
                        payment_service = PaymentService()
                        payment_service.credit_wallet(
                            qr_session.connector.station.owner.user,
                            extra_revenue,
                            additional_transaction
                        )

            # Update QR session status to completed
            qr_session.status = 'charging_completed'
            qr_session.save()

            # Make connector available again
            if qr_session.connector:
                qr_session.connector.is_available = True
                qr_session.connector.save()

            session_serializer = QRPaymentSessionSerializer(qr_session)
            return Response({
                'success': True,
                'message': 'Charging session stopped successfully',
                'qr_session': session_serializer.data
            }, status=status.HTTP_200_OK)

        except QRPaymentSession.DoesNotExist:
            return Response({
                'success': False,
                'message': 'QR payment session not found or not in charging state'
            }, status=status.HTTP_404_NOT_FOUND)


class TestCreateChargingSessionView(APIView):
    """Test endpoint to manually create a charging session for testing"""
    permission_classes = [IsAuthenticated]

    def post(self, request, session_token):
        try:
            qr_session = get_object_or_404(
                QRPaymentSession,
                session_token=session_token,
                user=request.user,
                status='payment_completed'
            )

            # Create a test charging session if it doesn't exist
            if not qr_session.simple_charging_session:
                from .services import PaymentService
                payment_service = PaymentService()
                payment_service._auto_start_charging_if_enabled(qr_session)
                qr_session.refresh_from_db()

            session_serializer = QRPaymentSessionSerializer(qr_session)
            return Response({
                'success': True,
                'message': 'Charging session created for testing',
                'qr_session': session_serializer.data,
                'charging_session_created': qr_session.simple_charging_session is not None
            }, status=status.HTTP_200_OK)

        except QRPaymentSession.DoesNotExist:
            return Response({
                'success': False,
                'message': 'QR payment session not found or payment not completed'
            }, status=status.HTTP_404_NOT_FOUND)


class ChargingHistoryView(generics.ListAPIView):
    """Get user's charging history"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Return completed charging sessions for the user
        return QRPaymentSession.objects.select_related(
            'connector', 'connector__station', 'simple_charging_session'
        ).filter(
            user=self.request.user,
            status__in=['charging_completed', 'charging_started', 'payment_completed']
        ).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        from .serializers import QRPaymentSessionWithChargingSerializer

        queryset = self.get_queryset()
        serializer = QRPaymentSessionWithChargingSerializer(queryset, many=True)

        # Add summary statistics
        total_sessions = queryset.count()
        total_amount_spent = sum(
            float(session.payment_amount) for session in queryset
            if session.payment_amount
        )

        return Response({
            'success': True,
            'charging_history': serializer.data,
            'summary': {
                'total_sessions': total_sessions,
                'total_amount_spent': total_amount_spent,
                'currency': 'ETB'
            }
        }, status=status.HTTP_200_OK)


class MobileReturnView(APIView):
    """Handle mobile app return from Chapa payment"""
    permission_classes = [AllowAny]

    def get(self, request):
        # Get payment parameters from Chapa
        tx_ref = request.GET.get('tx_ref')
        status_param = request.GET.get('status')
        trx_ref = request.GET.get('trx_ref')

        # Build deep link URL with parameters
        deep_link_params = []
        if tx_ref:
            deep_link_params.append(f'tx_ref={tx_ref}')
        if status_param:
            deep_link_params.append(f'status={status_param}')
        if trx_ref:
            deep_link_params.append(f'trx_ref={trx_ref}')

        params_string = '&'.join(deep_link_params)
        deep_link_url = f'evmeri://payment/success?{params_string}'

        # Create HTML page that redirects to mobile app
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Payment Complete - Redirecting to evmeri</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    margin: 0;
                }}
                .container {{
                    background: white;
                    color: #333;
                    padding: 30px;
                    border-radius: 10px;
                    max-width: 400px;
                    margin: 0 auto;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                }}
                .logo {{
                    font-size: 2em;
                    font-weight: bold;
                    color: #667eea;
                    margin-bottom: 20px;
                }}
                .status {{
                    font-size: 1.2em;
                    margin: 20px 0;
                }}
                .success {{ color: #28a745; }}
                .failed {{ color: #dc3545; }}
                .btn {{
                    background: #667eea;
                    color: white;
                    padding: 12px 24px;
                    border: none;
                    border-radius: 5px;
                    text-decoration: none;
                    display: inline-block;
                    margin: 10px;
                    cursor: pointer;
                }}
                .spinner {{
                    border: 4px solid #f3f3f3;
                    border-top: 4px solid #667eea;
                    border-radius: 50%;
                    width: 40px;
                    height: 40px;
                    animation: spin 1s linear infinite;
                    margin: 20px auto;
                }}
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">⚡ evmeri</div>
                <div class="status {'success' if status_param == 'success' else 'failed'}">
                    {'Payment Successful!' if status_param == 'success' else 'Payment Status: ' + (status_param or 'Unknown')}
                </div>
                <div class="spinner"></div>
                <p>Redirecting to evmeri app...</p>
                <a href="{deep_link_url}" class="btn">Open evmeri App</a>
                <p style="font-size: 0.9em; color: #666; margin-top: 20px;">
                    If the app doesn't open automatically, tap the button above.
                </p>
            </div>

            <script>
                // Attempt automatic redirect
                setTimeout(function() {{
                    window.location.href = '{deep_link_url}';
                }}, 2000);

                // Fallback for manual redirect
                document.addEventListener('DOMContentLoaded', function() {{
                    document.querySelector('.btn').addEventListener('click', function(e) {{
                        e.preventDefault();
                        window.location.href = '{deep_link_url}';
                    }});
                }});
            </script>
        </body>
        </html>
        '''

        return HttpResponse(html_content, content_type='text/html')


class WithdrawalView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = WithdrawSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            payment_service = PaymentService()
            
            # Create withdrawal transaction
            transaction = Transaction.objects.create(
                user=request.user,
                transaction_type=Transaction.TransactionType.WITHDRAWAL,
                amount=serializer.validated_data['amount'],
                phone_number=serializer.validated_data['phone_number'],
                description=serializer.validated_data.get('description', 'Withdrawal'),
                reference_number=str(uuid.uuid4()),
                status=Transaction.TransactionStatus.PENDING
            )
            
            # Debit the wallet
            wallet = payment_service.debit_wallet(request.user, transaction.amount, transaction)
            
            if wallet:
                transaction.status = Transaction.TransactionStatus.COMPLETED
                transaction.completed_at = timezone.now()
                transaction.save()
                
                return Response({
                    'success': True,
                    'message': 'Withdrawal successful',
                    'data': {
                        'transaction_id': transaction.id,
                        'amount': transaction.amount,
                        'new_balance': wallet.balance
                    }
                }, status=status.HTTP_200_OK)
            else:
                transaction.status = Transaction.TransactionStatus.FAILED
                transaction.save()
                
                return Response({
                    'success': False,
                    'message': 'Insufficient wallet balance'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_wallet_status(request):
    """
    Check current wallet status and missing credits for station owners
    """
    try:
        from charging_stations.models import StationOwner

        # Check if user is a station owner
        try:
            station_owner = StationOwner.objects.get(user=request.user)
        except StationOwner.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User is not a station owner'
            }, status=status.HTTP_403_FORBIDDEN)

        # Get wallet
        wallet, created = Wallet.objects.get_or_create(user=request.user)

        # Get completed QR sessions
        qr_sessions = QRPaymentSession.objects.filter(
            connector__station__owner=station_owner,
            payment_transaction__status='completed'
        )

        total_expected = 0
        credited_amount = 0
        missing_credits = []

        for qr_session in qr_sessions:
            if qr_session.payment_transaction:
                amount = float(qr_session.payment_transaction.amount)
                total_expected += amount

                # Check if credited
                existing_credit = WalletTransaction.objects.filter(
                    wallet=wallet,
                    transaction=qr_session.payment_transaction,
                    transaction_type=WalletTransaction.TransactionType.CREDIT
                ).first()

                if existing_credit:
                    credited_amount += float(existing_credit.amount)
                else:
                    missing_credits.append({
                        'session_token': qr_session.session_token,
                        'amount': amount,
                        'transaction_ref': qr_session.payment_transaction.reference_number,
                        'created_at': qr_session.created_at.isoformat()
                    })

        return Response({
            'success': True,
            'wallet_status': {
                'current_balance': float(wallet.balance),
                'total_expected': total_expected,
                'total_credited': credited_amount,
                'missing_amount': total_expected - credited_amount,
                'missing_credits_count': len(missing_credits),
                'missing_credits': missing_credits[:5],  # Show first 5
                'needs_fix': len(missing_credits) > 0
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error checking wallet status: {e}")
        return Response({
            'success': False,
            'message': 'Failed to check wallet status',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
