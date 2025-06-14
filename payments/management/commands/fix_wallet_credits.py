from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from payments.models import Wallet, WalletTransaction, Transaction, QRPaymentSession, SimpleChargingSession
from charging_stations.models import StationOwner
from payments.services import PaymentService
from django.utils import timezone
from decimal import Decimal


class Command(BaseCommand):
    help = 'Fix missing wallet credits for completed transactions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        self.stdout.write(self.style.SUCCESS('🔧 Fixing Missing Wallet Credits'))
        self.stdout.write('=' * 50)
        
        payment_service = PaymentService()
        
        # 1. Fix completed QR payment sessions that didn't credit station owner wallets
        self.stdout.write('\n1️⃣ Fixing QR Payment Sessions...')
        
        qr_sessions = QRPaymentSession.objects.filter(
            status='payment_completed',
            payment_transaction__status='completed'
        ).select_related('payment_transaction', 'connector__station__owner__user')
        
        self.stdout.write(f'Found {qr_sessions.count()} completed QR payment sessions')
        
        fixed_qr_count = 0
        for qr_session in qr_sessions:
            if qr_session.payment_transaction and qr_session.connector:
                station_owner = qr_session.connector.station.owner
                transaction = qr_session.payment_transaction
                
                # Check if wallet transaction already exists for this
                existing_wallet_tx = WalletTransaction.objects.filter(
                    transaction=transaction,
                    wallet__user=station_owner.user
                ).first()
                
                if not existing_wallet_tx:
                    self.stdout.write(f'  💰 Would credit {station_owner.user.email} with {transaction.amount} ETB')
                    self.stdout.write(f'     Transaction: {transaction.reference_number}')
                    
                    if not dry_run:
                        try:
                            payment_service.credit_wallet(
                                station_owner.user, 
                                transaction.amount, 
                                transaction
                            )
                            self.stdout.write(self.style.SUCCESS('  ✅ Successfully credited wallet'))
                            fixed_qr_count += 1
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f'  ❌ Error crediting wallet: {e}'))
                    else:
                        fixed_qr_count += 1
                else:
                    self.stdout.write(f'  ✅ Wallet already credited for transaction {transaction.reference_number}')
        
        # 2. Fix completed charging sessions that should generate additional revenue
        self.stdout.write('\n2️⃣ Fixing Charging Session Revenue...')
        
        completed_sessions = SimpleChargingSession.objects.filter(
            status__in=['completed', 'stopped'],
            energy_consumed_kwh__gt=0,
            cost_per_kwh__gt=0
        ).select_related('qr_session__payment_transaction', 'connector__station__owner__user')
        
        self.stdout.write(f'Found {completed_sessions.count()} completed charging sessions with energy consumption')
        
        fixed_session_count = 0
        for session in completed_sessions:
            if session.qr_session and session.qr_session.payment_transaction:
                station_owner = session.connector.station.owner
                
                # Calculate total revenue from energy consumed
                total_revenue = float(session.energy_consumed_kwh * session.cost_per_kwh)
                initial_payment = float(session.qr_session.payment_transaction.amount)
                
                self.stdout.write(f'  ⚡ Session {session.transaction_id}')
                self.stdout.write(f'     Energy: {session.energy_consumed_kwh} kWh × {session.cost_per_kwh} ETB/kWh = {total_revenue:.2f} ETB')
                self.stdout.write(f'     Initial payment: {initial_payment:.2f} ETB')
                
                if total_revenue > initial_payment:
                    additional_revenue = total_revenue - initial_payment
                    
                    # Check if additional revenue transaction already exists
                    existing_additional_tx = Transaction.objects.filter(
                        reference_number=f"ENERGY_{session.transaction_id}"
                    ).first()
                    
                    if not existing_additional_tx:
                        self.stdout.write(f'     💰 Would create additional revenue transaction: {additional_revenue:.2f} ETB')
                        
                        if not dry_run:
                            try:
                                # Create additional revenue transaction
                                additional_transaction = Transaction.objects.create(
                                    user=station_owner.user,
                                    transaction_type=Transaction.TransactionType.PAYMENT,
                                    status=Transaction.TransactionStatus.COMPLETED,
                                    amount=Decimal(str(additional_revenue)),
                                    description=f"Additional revenue from charging session {session.transaction_id}",
                                    reference_number=f"ENERGY_{session.transaction_id}",
                                    completed_at=timezone.now()
                                )
                                
                                # Credit the wallet
                                payment_service.credit_wallet(
                                    station_owner.user,
                                    Decimal(str(additional_revenue)),
                                    additional_transaction
                                )
                                
                                self.stdout.write(self.style.SUCCESS('     ✅ Successfully created additional revenue transaction'))
                                fixed_session_count += 1
                            except Exception as e:
                                self.stdout.write(self.style.ERROR(f'     ❌ Error creating additional revenue: {e}'))
                        else:
                            fixed_session_count += 1
                    else:
                        self.stdout.write('     ✅ Additional revenue already processed')
                else:
                    self.stdout.write('     ℹ️  No additional revenue needed (total <= initial payment)')
        
        # Summary
        self.stdout.write('\n📊 Summary')
        self.stdout.write('=' * 30)
        self.stdout.write(f'QR Payment Sessions Fixed: {fixed_qr_count}')
        self.stdout.write(f'Charging Sessions Fixed: {fixed_session_count}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a dry run. Run without --dry-run to apply changes.'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Wallet credit fix process completed!'))
