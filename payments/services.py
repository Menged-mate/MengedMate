import requests
import base64
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from .models import Transaction, PaymentSession, Wallet, WalletTransaction
import uuid
import logging

logger = logging.getLogger(__name__)


class ChapaService:
    def __init__(self):
        self.config = settings.CHAPA_SETTINGS
        self.base_url = self.config['SANDBOX_URL'] if self.config['USE_SANDBOX'] else self.config['PRODUCTION_URL']
        self.secret_key = self.config['SECRET_KEY']
        self.public_key = self.config['PUBLIC_KEY']
        self.callback_url = self.config['CALLBACK_URL']
        self.return_url = self.config['RETURN_URL']

    def get_headers(self):
        return {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json'
        }

    def initiate_payment(self, phone_number, amount, account_reference, transaction_desc, email, first_name, last_name):
        url = f"{self.base_url}/v1/transaction/initialize"

        headers = self.get_headers()

        # Convert phone number to local format for Chapa (09xxxxxxxx)
        if phone_number.startswith('+251'):
            phone_number = '0' + phone_number[4:]
        elif phone_number.startswith('251'):
            phone_number = '0' + phone_number[3:]

        # Validate email for Chapa - reject common test domains
        invalid_domains = ['example.com', 'test.com', 'localhost', 'invalid.com']
        email_domain = email.split('@')[-1].lower() if '@' in email else ''
        if email_domain in invalid_domains:
            # Use a fallback email for testing
            email = f"user_{account_reference}@gmail.com"

        payload = {
            'amount': str(amount),
            'currency': 'ETB',
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'phone_number': phone_number,
            'tx_ref': account_reference,
            'callback_url': self.callback_url,
            'return_url': self.return_url,
            'description': transaction_desc,
            'meta': {
                'hide_receipt': 'true'
            }
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return {'success': True, 'data': response.json()}
        except requests.exceptions.RequestException as e:
            logger.error(f"Chapa payment initiation failed: {e}")

            # Return more detailed error information
            error_message = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_message = error_data.get('message', str(e))
                except:
                    error_message = e.response.text or str(e)

            return {'success': False, 'message': error_message}

    def query_transaction_status(self, tx_ref):
        url = f"{self.base_url}/v1/transaction/verify/{tx_ref}"

        headers = self.get_headers()

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return {'success': True, 'data': response.json()}
        except requests.exceptions.RequestException as e:
            logger.error(f"Transaction query failed: {e}")
            return {'success': False, 'message': str(e)}


class PaymentService:
    def __init__(self):
        self.chapa = ChapaService()

    def create_payment_session(self, user, amount, phone_number, description="Payment"):
        session_id = str(uuid.uuid4())
        expires_at = timezone.now() + timedelta(minutes=10)

        session = PaymentSession.objects.create(
            user=user,
            session_id=session_id,
            amount=amount,
            phone_number=phone_number,
            expires_at=expires_at
        )

        return session

    def initiate_chapa_payment(self, user, amount, phone_number, description="MengedMate Payment"):
        session = self.create_payment_session(user, amount, phone_number, description)

        result = self.chapa.initiate_payment(
            phone_number=phone_number,
            amount=amount,
            account_reference=session.session_id,
            transaction_desc=description,
            email=user.email,
            first_name=user.first_name or 'User',
            last_name=user.last_name or 'Name'
        )

        if result['success']:
            data = result['data']
            session.checkout_request_id = data.get('data', {}).get('checkout_url', '')
            session.merchant_request_id = data.get('data', {}).get('tx_ref', '')
            session.save()

            transaction = Transaction.objects.create(
                user=user,
                transaction_type=Transaction.TransactionType.DEPOSIT,
                amount=amount,
                phone_number=phone_number,
                description=description,
                reference_number=session.session_id,
                external_reference=session.merchant_request_id,
                provider_response=data
            )

            return {
                'success': True,
                'session_id': session.session_id,
                'checkout_url': session.checkout_request_id,
                'tx_ref': session.merchant_request_id,
                'transaction_id': transaction.id
            }
        else:
            session.status = PaymentSession.SessionStatus.CANCELLED
            session.save()
            return result

    def process_callback(self, callback_data):
        try:
            tx_ref = callback_data.get('tx_ref')
            if not tx_ref:
                return {'success': False, 'message': 'Missing tx_ref'}

            # Check for regular payment session
            session = PaymentSession.objects.filter(
                merchant_request_id=tx_ref
            ).first()

            # Check for QR payment session
            from .models import QRPaymentSession
            qr_session = QRPaymentSession.objects.filter(
                payment_transaction__external_reference=tx_ref
            ).first()

            if not session and not qr_session:
                return {'success': False, 'message': 'Session not found'}

            transaction = Transaction.objects.filter(
                external_reference=tx_ref
            ).first()

            if not transaction:
                return {'success': False, 'message': 'Transaction not found'}

            status = callback_data.get('status', 'failed')

            if status == 'success':
                transaction.status = Transaction.TransactionStatus.COMPLETED
                transaction.completed_at = timezone.now()

                if session:
                    session.status = PaymentSession.SessionStatus.COMPLETED
                    session.save()
                    self.credit_wallet(transaction.user, transaction.amount, transaction)

                if qr_session:
                    qr_session.status = 'payment_completed'
                    qr_session.payment_transaction = transaction
                    qr_session.save()

                    # Auto-start charging if configured
                    self._auto_start_charging_if_enabled(qr_session)
            else:
                transaction.status = Transaction.TransactionStatus.FAILED

                if session:
                    session.status = PaymentSession.SessionStatus.CANCELLED
                    session.save()

                if qr_session:
                    qr_session.status = 'failed'
                    qr_session.save()

            transaction.callback_data = callback_data
            transaction.save()

            return {'success': True, 'message': 'Callback processed successfully'}

        except Exception as e:
            logger.error(f"Callback processing failed: {e}")
            return {'success': False, 'message': str(e)}

    def _auto_start_charging_if_enabled(self, qr_session):
        """Auto-start charging if enabled in settings"""
        try:
            # For now, we'll require manual start, but this can be configured
            # to auto-start charging after successful payment
            pass
        except Exception as e:
            logger.error(f"Auto-start charging failed: {e}")

    def credit_wallet(self, user, amount, transaction):
        wallet, created = Wallet.objects.get_or_create(user=user)

        balance_before = wallet.balance
        wallet.balance += amount
        wallet.save()

        WalletTransaction.objects.create(
            wallet=wallet,
            transaction=transaction,
            transaction_type=WalletTransaction.TransactionType.CREDIT,
            amount=amount,
            balance_before=balance_before,
            balance_after=wallet.balance,
            description=f"Credit from payment {transaction.reference_number}"
        )

        return wallet

    def debit_wallet(self, user, amount, transaction):
        wallet = Wallet.objects.filter(user=user).first()
        if not wallet or wallet.balance < amount:
            return None

        balance_before = wallet.balance
        wallet.balance -= amount
        wallet.save()

        WalletTransaction.objects.create(
            wallet=wallet,
            transaction=transaction,
            transaction_type=WalletTransaction.TransactionType.DEBIT,
            amount=amount,
            balance_before=balance_before,
            balance_after=wallet.balance,
            description=f"Debit for transaction {transaction.reference_number}"
        )

        return wallet

    def get_transaction_status(self, tx_ref):
        return self.chapa.query_transaction_status(tx_ref)
