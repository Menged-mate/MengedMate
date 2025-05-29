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


class SafaricomEthiopiaService:
    def __init__(self):
        self.config = settings.SAFARICOM_ETHIOPIA_SETTINGS
        self.base_url = self.config['SANDBOX_URL'] if self.config['USE_SANDBOX'] else self.config['PRODUCTION_URL']
        self.consumer_key = self.config['CONSUMER_KEY']
        self.consumer_secret = self.config['CONSUMER_SECRET']
        self.business_short_code = self.config['BUSINESS_SHORT_CODE']
        self.passkey = self.config['PASSKEY']
        self.callback_url = self.config['CALLBACK_URL']

    def get_access_token(self):
        url = f"{self.base_url}/v1/token/generate?grant_type=client_credentials"
        
        credentials = f"{self.consumer_key}:{self.consumer_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json().get('access_token')
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get access token: {e}")
            return None

    def generate_password(self):
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_string = f"{self.business_short_code}{self.passkey}{timestamp}"
        password = base64.b64encode(password_string.encode()).decode()
        return password, timestamp

    def initiate_stk_push(self, phone_number, amount, account_reference, transaction_desc):
        access_token = self.get_access_token()
        if not access_token:
            return {'success': False, 'message': 'Failed to get access token'}

        password, timestamp = self.generate_password()
        
        url = f"{self.base_url}/mpesa/stkpush/v3/processrequest"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'BusinessShortCode': self.business_short_code,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': int(amount),
            'PartyA': phone_number,
            'PartyB': self.business_short_code,
            'PhoneNumber': phone_number,
            'CallBackURL': self.callback_url,
            'AccountReference': account_reference,
            'TransactionDesc': transaction_desc
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return {'success': True, 'data': response.json()}
        except requests.exceptions.RequestException as e:
            logger.error(f"STK Push failed: {e}")
            return {'success': False, 'message': str(e)}

    def query_transaction_status(self, checkout_request_id):
        access_token = self.get_access_token()
        if not access_token:
            return {'success': False, 'message': 'Failed to get access token'}

        password, timestamp = self.generate_password()
        
        url = f"{self.base_url}/mpesa/stkpushquery/v1/query"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'BusinessShortCode': self.business_short_code,
            'Password': password,
            'Timestamp': timestamp,
            'CheckoutRequestID': checkout_request_id
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return {'success': True, 'data': response.json()}
        except requests.exceptions.RequestException as e:
            logger.error(f"Transaction query failed: {e}")
            return {'success': False, 'message': str(e)}


class PaymentService:
    def __init__(self):
        self.safaricom = SafaricomEthiopiaService()

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

    def initiate_mpesa_payment(self, user, amount, phone_number, description="MengedMate Payment"):
        session = self.create_payment_session(user, amount, phone_number, description)
        
        result = self.safaricom.initiate_stk_push(
            phone_number=phone_number,
            amount=amount,
            account_reference=session.session_id,
            transaction_desc=description
        )
        
        if result['success']:
            data = result['data']
            session.checkout_request_id = data.get('CheckoutRequestID')
            session.merchant_request_id = data.get('MerchantRequestID')
            session.save()
            
            transaction = Transaction.objects.create(
                user=user,
                transaction_type=Transaction.TransactionType.DEPOSIT,
                amount=amount,
                phone_number=phone_number,
                description=description,
                reference_number=session.session_id,
                external_reference=session.checkout_request_id,
                provider_response=data
            )
            
            return {
                'success': True,
                'session_id': session.session_id,
                'checkout_request_id': session.checkout_request_id,
                'transaction_id': transaction.id
            }
        else:
            session.status = PaymentSession.SessionStatus.CANCELLED
            session.save()
            return result

    def process_callback(self, callback_data):
        try:
            checkout_request_id = callback_data.get('CheckoutRequestID')
            if not checkout_request_id:
                return {'success': False, 'message': 'Missing CheckoutRequestID'}

            session = PaymentSession.objects.filter(
                checkout_request_id=checkout_request_id
            ).first()
            
            if not session:
                return {'success': False, 'message': 'Session not found'}

            transaction = Transaction.objects.filter(
                external_reference=checkout_request_id
            ).first()
            
            if not transaction:
                return {'success': False, 'message': 'Transaction not found'}

            result_code = callback_data.get('ResultCode', 1)
            
            if result_code == 0:
                transaction.status = Transaction.TransactionStatus.COMPLETED
                transaction.completed_at = timezone.now()
                session.status = PaymentSession.SessionStatus.COMPLETED
                
                self.credit_wallet(transaction.user, transaction.amount, transaction)
            else:
                transaction.status = Transaction.TransactionStatus.FAILED
                session.status = PaymentSession.SessionStatus.CANCELLED

            transaction.callback_data = callback_data
            transaction.save()
            session.save()
            
            return {'success': True, 'message': 'Callback processed successfully'}
            
        except Exception as e:
            logger.error(f"Callback processing failed: {e}")
            return {'success': False, 'message': str(e)}

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

    def get_transaction_status(self, checkout_request_id):
        return self.safaricom.query_transaction_status(checkout_request_id)
