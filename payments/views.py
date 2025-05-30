from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import PaymentMethod, Transaction, Wallet, WalletTransaction, PaymentSession
from .serializers import (
    PaymentMethodSerializer, TransactionSerializer, WalletSerializer,
    WalletTransactionSerializer, PaymentSessionSerializer, InitiatePaymentSerializer,
    PaymentCallbackSerializer, TransactionStatusSerializer, WithdrawSerializer
)
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

        payment_service = PaymentService()
        result = payment_service.process_callback(callback_data)

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
