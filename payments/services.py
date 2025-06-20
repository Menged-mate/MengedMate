import requests
import base64
import json
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from .models import Transaction, Wallet, WalletTransaction
import uuid

logger = logging.getLogger(__name__)

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

    def initiate_payment(self, phone_number, amount, account_reference, transaction_desc, email, first_name, last_name, use_mobile_return=False):
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
            # Use a fallback email for testing (keep it short for Chapa's 50 char limit)
            short_ref = account_reference[:8] if len(account_reference) > 8 else account_reference
            email = f"user{short_ref}@gmail.com"

        # Choose return URL based on request source
        return_url = self.return_url if use_mobile_return else self.config.get('WEB_RETURN_URL', self.return_url)

        payload = {
            'amount': str(amount),
            'currency': 'ETB',
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'phone_number': phone_number,
            'tx_ref': account_reference,
            'callback_url': self.callback_url,
            'return_url': return_url,
            'description': transaction_desc,
            'meta': {
                'hide_receipt': 'true'
            }
        }

        try:
            logger.info(f"Chapa payload: {payload}")
            response = requests.post(url, json=payload, headers=headers)
            logger.info(f"Chapa response status: {response.status_code}")
            logger.info(f"Chapa response: {response.text}")
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
                    logger.error(f"Chapa error response: {error_data}")
                except:
                    error_message = e.response.text or str(e)
                    logger.error(f"Chapa error text: {e.response.text}")

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

    def create_transaction_for_wallet_deposit(self, user, amount, phone_number, description="Wallet Deposit"):
        """Create a transaction for wallet deposit without PaymentSession"""
        reference_number = str(uuid.uuid4())

        transaction = Transaction.objects.create(
            user=user,
            transaction_type=Transaction.TransactionType.DEPOSIT,
            amount=amount,
            phone_number=phone_number,
            description=description,
            reference_number=reference_number,
            external_reference=reference_number
        )

        return transaction

    def initiate_chapa_payment(self, user, amount, phone_number, description="evmeri Payment", use_mobile_return=False):
        transaction = self.create_transaction_for_wallet_deposit(user, amount, phone_number, description)

        result = self.chapa.initiate_payment(
            phone_number=phone_number,
            amount=amount,
            account_reference=transaction.reference_number,
            transaction_desc=description,
            email=user.email,
            first_name=user.first_name or 'User',
            last_name=user.last_name or 'Name',
            use_mobile_return=use_mobile_return
        )

        if result['success']:
            data = result['data']
            checkout_url = data.get('data', {}).get('checkout_url', '')

            # Update transaction with provider response
            transaction.provider_response = data
            transaction.save()

            return {
                'success': True,
                'checkout_url': checkout_url,
                'tx_ref': transaction.reference_number,
                'transaction_id': transaction.id
            }
        else:
            transaction.status = Transaction.TransactionStatus.FAILED
            transaction.save()
            return result

    def process_callback(self, callback_data):
        try:
            tx_ref = callback_data.get('tx_ref')
            logger.info(f"Processing callback for tx_ref: {tx_ref}")
            logger.info(f"Full callback data: {callback_data}")

            if not tx_ref:
                logger.error("Missing tx_ref in callback data")
                return {'success': False, 'message': 'Missing tx_ref'}

            # Check for QR payment session - try multiple ways to find it
            from .models import QRPaymentSession
            qr_session = QRPaymentSession.objects.filter(
                payment_transaction__external_reference=tx_ref
            ).first()

            # If not found, try by session token (in case tx_ref is the session token)
            if not qr_session:
                qr_session = QRPaymentSession.objects.filter(
                    session_token=tx_ref
                ).first()

            logger.info(f"Found QR session: {qr_session}")

            if not qr_session:
                logger.error(f"No QR session found for tx_ref: {tx_ref}")
                # Try to find transaction directly
                transaction = Transaction.objects.filter(
                    external_reference=tx_ref
                ).first()
                if transaction:
                    logger.info(f"Found orphaned transaction: {transaction.reference_number}")
                    # Try to find QR session by transaction
                    qr_session = QRPaymentSession.objects.filter(
                        payment_transaction=transaction
                    ).first()
                    if qr_session:
                        logger.info(f"Found QR session via transaction: {qr_session.session_token}")

                if not qr_session:
                    return {'success': False, 'message': 'Session not found'}

            transaction = Transaction.objects.filter(
                external_reference=tx_ref
            ).first()

            logger.info(f"Found transaction: {transaction}")

            if not transaction:
                logger.error(f"No transaction found for tx_ref: {tx_ref}")
                return {'success': False, 'message': 'Transaction not found'}

            status = callback_data.get('status', 'failed')

            if status == 'success':
                transaction.status = Transaction.TransactionStatus.COMPLETED
                transaction.completed_at = timezone.now()

                if qr_session:
                    logger.info(f"Processing QR session payment completion: {qr_session.session_token}")
                    qr_session.status = 'payment_completed'
                    qr_session.payment_transaction = transaction
                    qr_session.save()

                    # Credit station owner wallet - this is the critical part
                    success = self._credit_station_owner_for_qr_payment(qr_session, transaction)

                    if success:
                        try:
                            # Send charging payment notification
                            self._send_payment_notification(transaction.user, transaction.amount, 'charging_payment', qr_session)

                            # Send notification to station owner
                            self._send_station_owner_payment_notification(qr_session, transaction)

                            # Auto-start charging if configured
                            self._auto_start_charging_if_enabled(qr_session)
                        except Exception as e:
                            logger.error(f"Error sending notifications: {e}")
                    else:
                        logger.error(f"Failed to credit station owner for QR session {qr_session.session_token}")
                else:
                    # For non-QR payments (direct wallet deposits), credit user's wallet
                    self.credit_wallet(transaction.user, transaction.amount, transaction)
                    logger.info(f"Credited user wallet: {transaction.user.email} with {transaction.amount}")

                    # Send payment received notification
                    self._send_payment_notification(transaction.user, transaction.amount, 'wallet_credit')
            else:
                transaction.status = Transaction.TransactionStatus.FAILED

                if qr_session:
                    qr_session.status = 'failed'
                    qr_session.save()

            transaction.callback_data = callback_data
            transaction.save()

            return {'success': True, 'message': 'Callback processed successfully'}

        except Exception as e:
            logger.error(f"Callback processing failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {'success': False, 'message': str(e)}

    def _auto_start_charging_if_enabled(self, qr_session):
        """Auto-start charging after successful payment"""
        try:
            from .models import SimpleChargingSession
            import uuid

            # Auto-start charging session
            if qr_session.connector and qr_session.connector.is_available:
                # Create charging session
                charging_session = SimpleChargingSession.objects.create(
                    transaction_id=str(uuid.uuid4()),
                    user=qr_session.user,
                    connector=qr_session.connector,
                    qr_session=qr_session,
                    payment_transaction_id=str(qr_session.payment_transaction.id) if qr_session.payment_transaction else None,
                    status='started',
                    estimated_duration_minutes=60,  # Default 1 hour
                    energy_delivered_kwh=0.0,
                    cost_per_kwh=qr_session.connector.price_per_kwh or 5.50,  # Default price if None
                    max_power_kw=qr_session.connector.power_kw or 50.0,  # Default power if None
                    id_tag='mobile_app'
                )

                # Update QR session status and link to charging session
                qr_session.status = 'charging_started'
                qr_session.simple_charging_session = charging_session
                qr_session.save()

                # Make connector unavailable
                qr_session.connector.is_available = False
                qr_session.connector.save()

                logger.info(f"Auto-started charging session {charging_session.transaction_id} for QR session {qr_session.session_token}")

        except Exception as e:
            logger.error(f"Auto-start charging failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    def _credit_station_owner_for_qr_payment(self, qr_session, transaction):
        """
        Credit station owner wallet for QR payment - dedicated method with comprehensive error handling
        """
        try:
            logger.info(f"Starting station owner credit process for QR session: {qr_session.session_token}")

            # Validate QR session has all required components
            if not qr_session.connector:
                logger.error(f"QR session {qr_session.session_token} has no connector")
                return False

            if not qr_session.connector.station:
                logger.error(f"QR session {qr_session.session_token} connector has no station")
                return False

            if not qr_session.connector.station.owner:
                logger.error(f"QR session {qr_session.session_token} station has no owner")
                return False

            station_owner = qr_session.connector.station.owner
            logger.info(f"Station owner identified: {station_owner.user.email}")
            logger.info(f"Station: {qr_session.connector.station.name}")
            logger.info(f"Connector: {qr_session.connector.name}")
            logger.info(f"Payment amount: {transaction.amount} ETB")

            # Check if wallet already credited for this transaction
            existing_credit = WalletTransaction.objects.filter(
                wallet__user=station_owner.user,
                transaction=transaction,
                transaction_type=WalletTransaction.TransactionType.CREDIT
            ).first()

            if existing_credit:
                logger.info(f"Station owner wallet already credited for transaction {transaction.reference_number}")
                logger.info(f"Existing credit amount: {existing_credit.amount} ETB")
                return True

            # Credit the wallet
            logger.info(f"Crediting station owner wallet: {station_owner.user.email} with {transaction.amount} ETB")
            wallet = self.credit_wallet(station_owner.user, transaction.amount, transaction)

            if wallet:
                logger.info(f"Successfully credited station owner wallet")
                logger.info(f"New wallet balance: {wallet.balance} ETB")
                return True
            else:
                logger.error(f"Failed to credit station owner wallet")
                return False

        except Exception as e:
            logger.error(f"Error crediting station owner wallet for QR session {qr_session.session_token}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def credit_wallet(self, user, amount, transaction):
        try:
            logger.info(f"Attempting to credit wallet for user: {user.email} with amount: {amount}")
            
            # Get or create wallet
            wallet, created = Wallet.objects.get_or_create(
                user=user,
                defaults={
                    'balance': 0,
                    'currency': 'ETB',
                    'is_active': True
                }
            )
            
            if created:
                logger.info(f"Created new wallet for user: {user.email}")

            # Get current balance
            balance_before = wallet.balance
            logger.info(f"Current wallet balance for {user.email}: {balance_before}")

            # Update balance
            wallet.balance += amount
            wallet.save()
            logger.info(f"Updated wallet balance for {user.email}: {wallet.balance}")

            # Create wallet transaction record
            wallet_transaction = WalletTransaction.objects.create(
                wallet=wallet,
                transaction=transaction,
                transaction_type=WalletTransaction.TransactionType.CREDIT,
                amount=amount,
                balance_before=balance_before,
                balance_after=wallet.balance,
                description=f"Credit from payment {transaction.reference_number}"
            )
            logger.info(f"Created wallet transaction: {wallet_transaction.id}")

            return wallet
            
        except Exception as e:
            logger.error(f"Error crediting wallet for user {user.email}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

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

    def _send_payment_notification(self, user, amount, payment_type, qr_session=None):
        """Send notification when payment is received"""
        try:
            from authentication.notifications import create_notification, Notification

            if payment_type == 'wallet_credit':
                title = 'Payment Received'
                message = f'Your wallet has been credited with {amount} ETB. Payment successful!'
                link = '/dashboard/wallet'
            elif payment_type == 'charging_payment':
                station_name = qr_session.connector.station.name if qr_session else 'Unknown Station'
                title = 'Charging Payment Successful'
                message = f'Payment of {amount} ETB received for charging at {station_name}. Charging will start shortly.'
                link = f'/charging-history'
            else:
                title = 'Payment Received'
                message = f'Payment of {amount} ETB has been processed successfully.'
                link = '/dashboard'

            create_notification(
                user=user,
                notification_type=Notification.NotificationType.PAYMENT,
                title=title,
                message=message,
                link=link
            )

        except Exception as e:
            logger.error(f"Error sending payment notification: {e}")

    def _send_station_owner_payment_notification(self, qr_session, transaction):
        """Send notification to station owner when payment is received"""
        try:
            from authentication.notifications import create_notification, Notification

            station_owner = qr_session.connector.station.owner

            create_notification(
                user=station_owner.user,
                notification_type=Notification.NotificationType.PAYMENT,
                title='Payment Received',
                message=f'Payment of {transaction.amount} ETB received for charging at {qr_session.connector.station.name}.',
                link=f'/dashboard/stations/{qr_session.connector.station.id}'
            )

        except Exception as e:
            logger.error(f"Error sending station owner payment notification: {e}")

    def get_transaction_status(self, tx_ref):
        return self.chapa.query_transaction_status(tx_ref)

    def process_pending_station_owner_credits(self):
        """
        Process any completed QR payments that haven't credited station owner wallets yet.
        This can be called periodically to catch any missed credits.
        """
        logger.info("Processing pending station owner credits...")

        from .models import QRPaymentSession

        # Find completed QR payments that should have credited station owners
        qr_sessions = QRPaymentSession.objects.filter(
            status='payment_completed',
            payment_transaction__status='completed'
        ).select_related(
            'payment_transaction',
            'connector__station__owner__user'
        )

        processed_count = 0
        error_count = 0

        for qr_session in qr_sessions:
            try:
                if (qr_session.connector and
                    qr_session.connector.station and
                    qr_session.connector.station.owner and
                    qr_session.payment_transaction):

                    station_owner = qr_session.connector.station.owner
                    transaction = qr_session.payment_transaction

                    # Check if already credited
                    existing_credit = WalletTransaction.objects.filter(
                        wallet__user=station_owner.user,
                        transaction=transaction,
                        transaction_type=WalletTransaction.TransactionType.CREDIT
                    ).first()

                    if not existing_credit:
                        logger.info(f"Processing missed credit for QR session {qr_session.session_token}")
                        success = self._credit_station_owner_for_qr_payment(qr_session, transaction)
                        if success:
                            processed_count += 1
                        else:
                            error_count += 1

            except Exception as e:
                logger.error(f"Error processing QR session {qr_session.session_token}: {e}")
                error_count += 1

        logger.info(f"Processed {processed_count} pending credits, {error_count} errors")
        return {'processed': processed_count, 'errors': error_count}
