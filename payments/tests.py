from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from .models import PaymentMethod, Transaction, Wallet, PaymentSession
from .services import PaymentService
from decimal import Decimal

User = get_user_model()


class PaymentModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

    def test_payment_method_creation(self):
        payment_method = PaymentMethod.objects.create(
            user=self.user,
            method_type=PaymentMethod.MethodType.CHAPA,
            phone_number='+251912345678'
        )
        self.assertEqual(payment_method.user, self.user)
        self.assertEqual(payment_method.method_type, PaymentMethod.MethodType.CHAPA)
        self.assertEqual(payment_method.phone_number, '+251912345678')

    def test_wallet_creation(self):
        wallet = Wallet.objects.create(user=self.user)
        self.assertEqual(wallet.user, self.user)
        self.assertEqual(wallet.balance, Decimal('0.00'))
        self.assertEqual(wallet.currency, 'ETB')

    def test_transaction_creation(self):
        transaction = Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.TransactionType.PAYMENT,
            amount=Decimal('100.00'),
            reference_number='TEST123456'
        )
        self.assertEqual(transaction.user, self.user)
        self.assertEqual(transaction.amount, Decimal('100.00'))
        self.assertEqual(transaction.status, Transaction.TransactionStatus.PENDING)


class PaymentAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

    def test_wallet_endpoint(self):
        response = self.client.get('/api/payments/wallet/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['balance'], '0.00')

    def test_payment_methods_list(self):
        response = self.client.get('/api/payments/payment-methods/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_create_payment_method(self):
        data = {
            'method_type': 'chapa',
            'phone_number': '+251912345678'
        }
        response = self.client.post('/api/payments/payment-methods/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['method_type'], 'chapa')

    def test_transactions_list(self):
        response = self.client.get('/api/payments/transactions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_initiate_payment_validation(self):
        data = {
            'amount': '100.00',
            'phone_number': 'invalid_phone'
        }
        response = self.client.post('/api/payments/initiate/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
