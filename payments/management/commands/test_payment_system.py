from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from payments.models import Wallet, WalletTransaction, Transaction, QRPaymentSession
from charging_stations.models import StationOwner
from payments.services import PaymentService
from decimal import Decimal


class Command(BaseCommand):
    help = 'Test and verify the payment system fixes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check-pending',
            action='store_true',
            help='Check for pending station owner credits',
        )
        parser.add_argument(
            '--process-pending',
            action='store_true',
            help='Process pending station owner credits',
        )
        parser.add_argument(
            '--show-wallets',
            action='store_true',
            help='Show all station owner wallet balances',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔧 Payment System Test & Verification'))
        self.stdout.write('=' * 50)
        
        if options['check_pending']:
            self.check_pending_credits()
        
        if options['process_pending']:
            self.process_pending_credits()
        
        if options['show_wallets']:
            self.show_wallet_balances()
        
        if not any([options['check_pending'], options['process_pending'], options['show_wallets']]):
            self.run_full_verification()

    def check_pending_credits(self):
        self.stdout.write('\n🔍 Checking for pending station owner credits...')
        
        completed_qr_sessions = QRPaymentSession.objects.filter(
            status='payment_completed',
            payment_transaction__status='completed'
        ).select_related('payment_transaction', 'connector__station__owner__user')
        
        self.stdout.write(f'Found {completed_qr_sessions.count()} completed QR payment sessions')
        
        pending_count = 0
        for qr_session in completed_qr_sessions:
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
                    pending_count += 1
                    self.stdout.write(
                        f'  📋 Pending: {qr_session.session_token} -> '
                        f'{station_owner.user.email} ({transaction.amount} ETB)'
                    )
        
        if pending_count == 0:
            self.stdout.write(self.style.SUCCESS('✅ No pending credits found'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠️  Found {pending_count} pending credits'))

    def process_pending_credits(self):
        self.stdout.write('\n🔄 Processing pending station owner credits...')
        
        payment_service = PaymentService()
        result = payment_service.process_pending_station_owner_credits()
        
        self.stdout.write(f'✅ Processing complete:')
        self.stdout.write(f'   - Processed: {result.get("processed", 0)}')
        self.stdout.write(f'   - Errors: {result.get("errors", 0)}')

    def show_wallet_balances(self):
        self.stdout.write('\n💰 Station Owner Wallet Balances:')
        
        station_owners = StationOwner.objects.all().select_related('user')
        
        for station_owner in station_owners:
            try:
                wallet = Wallet.objects.get(user=station_owner.user)
                self.stdout.write(f'   {station_owner.user.email}: {wallet.balance} ETB')
            except Wallet.DoesNotExist:
                self.stdout.write(f'   {station_owner.user.email}: No wallet (will be created when needed)')

    def run_full_verification(self):
        self.stdout.write('\n🧪 Running full payment system verification...')
        
        # Check models
        self.stdout.write('\n1️⃣ Checking models...')
        try:
            from payments.models import Transaction, Wallet, WalletTransaction, QRPaymentSession, SimpleChargingSession
            self.stdout.write(self.style.SUCCESS('✅ All required models available'))
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f'❌ Model import error: {e}'))
        
        # Check removed models
        try:
            from payments.models import PaymentMethod
            self.stdout.write(self.style.ERROR('❌ PaymentMethod model still exists (should be removed)'))
        except ImportError:
            self.stdout.write(self.style.SUCCESS('✅ PaymentMethod model successfully removed'))
        
        try:
            from payments.models import PaymentSession
            self.stdout.write(self.style.ERROR('❌ PaymentSession model still exists (should be removed)'))
        except ImportError:
            self.stdout.write(self.style.SUCCESS('✅ PaymentSession model successfully removed'))
        
        # Check database state
        self.stdout.write('\n2️⃣ Checking database state...')
        transaction_count = Transaction.objects.count()
        wallet_count = Wallet.objects.count()
        qr_session_count = QRPaymentSession.objects.count()
        
        self.stdout.write(f'   - Transactions: {transaction_count}')
        self.stdout.write(f'   - Wallets: {wallet_count}')
        self.stdout.write(f'   - QR Payment Sessions: {qr_session_count}')
        
        # Check pending credits
        self.check_pending_credits()
        
        # Show wallet balances
        self.show_wallet_balances()
        
        self.stdout.write(self.style.SUCCESS('\n🎉 Payment system verification complete!'))
