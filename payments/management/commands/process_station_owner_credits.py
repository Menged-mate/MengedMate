from django.core.management.base import BaseCommand
from payments.services import PaymentService
from payments.models import Wallet, WalletTransaction, QRPaymentSession
from charging_stations.models import StationOwner
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process pending station owner wallet credits for completed payments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))
        
        self.stdout.write(self.style.SUCCESS('🔧 Processing Station Owner Wallet Credits'))
        self.stdout.write('=' * 60)
        
        # Initialize payment service
        payment_service = PaymentService()
        
        # Get all completed QR payment sessions
        qr_sessions = QRPaymentSession.objects.filter(
            payment_transaction__status='completed'
        ).select_related(
            'payment_transaction',
            'connector__station__owner__user'
        )
        
        self.stdout.write(f'📊 Found {qr_sessions.count()} completed QR payment sessions')
        
        processed_count = 0
        already_credited_count = 0
        error_count = 0
        total_amount_credited = 0
        
        for qr_session in qr_sessions:
            try:
                # Validate QR session structure
                if not qr_session.connector:
                    if verbose:
                        self.stdout.write(f'⚠️  QR session {qr_session.session_token} has no connector')
                    continue
                    
                if not qr_session.connector.station:
                    if verbose:
                        self.stdout.write(f'⚠️  QR session {qr_session.session_token} connector has no station')
                    continue
                    
                if not qr_session.connector.station.owner:
                    if verbose:
                        self.stdout.write(f'⚠️  QR session {qr_session.session_token} station has no owner')
                    continue
                
                if not qr_session.payment_transaction:
                    if verbose:
                        self.stdout.write(f'⚠️  QR session {qr_session.session_token} has no payment transaction')
                    continue
                
                station_owner = qr_session.connector.station.owner
                transaction = qr_session.payment_transaction
                
                if verbose:
                    self.stdout.write(f'\n🎫 QR Session: {qr_session.session_token}')
                    self.stdout.write(f'   🏢 Station Owner: {station_owner.user.email}')
                    self.stdout.write(f'   🏪 Station: {qr_session.connector.station.name}')
                    self.stdout.write(f'   💰 Amount: {transaction.amount} ETB')
                
                # Check if station owner wallet was already credited
                station_wallet, created = Wallet.objects.get_or_create(user=station_owner.user)
                
                existing_credit = WalletTransaction.objects.filter(
                    wallet=station_wallet,
                    transaction=transaction,
                    transaction_type=WalletTransaction.TransactionType.CREDIT
                ).first()
                
                if existing_credit:
                    if verbose:
                        self.stdout.write(f'   ✅ Already credited: {existing_credit.amount} ETB')
                    already_credited_count += 1
                else:
                    self.stdout.write(f'❌ Missing credit for {station_owner.user.email}: {transaction.amount} ETB')
                    self.stdout.write(f'   Transaction: {transaction.reference_number}')
                    self.stdout.write(f'   Station: {qr_session.connector.station.name}')
                    
                    if not dry_run:
                        try:
                            # Credit the station owner's wallet
                            wallet = payment_service.credit_wallet(
                                station_owner.user,
                                transaction.amount,
                                transaction
                            )
                            if wallet:
                                self.stdout.write(self.style.SUCCESS(f'   ✅ Successfully credited {transaction.amount} ETB'))
                                processed_count += 1
                                total_amount_credited += float(transaction.amount)
                            else:
                                self.stdout.write(self.style.ERROR(f'   ❌ Failed to credit wallet'))
                                error_count += 1
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f'   ❌ Error crediting wallet: {e}'))
                            error_count += 1
                    else:
                        processed_count += 1
                        total_amount_credited += float(transaction.amount)
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error processing QR session {qr_session.session_token}: {e}'))
                error_count += 1
        
        # Summary
        self.stdout.write('\n📊 SUMMARY')
        self.stdout.write('=' * 30)
        self.stdout.write(f'✅ Already credited: {already_credited_count}')
        self.stdout.write(f'🔧 Processed (new credits): {processed_count}')
        self.stdout.write(f'❌ Errors: {error_count}')
        self.stdout.write(f'💰 Total amount credited: {total_amount_credited:.2f} ETB')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  This was a dry run. Run without --dry-run to apply changes.'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Station owner credit processing completed!'))
        
        # Show current wallet balances
        self.stdout.write('\n💼 Current Station Owner Wallet Balances:')
        self.stdout.write('-' * 50)
        
        station_owners = StationOwner.objects.all()
        for owner in station_owners:
            wallet, created = Wallet.objects.get_or_create(user=owner.user)
            self.stdout.write(f'{owner.company_name} ({owner.user.email}): {wallet.balance} ETB')
