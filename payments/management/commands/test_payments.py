from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from payments.models import PaymentMethod, Wallet, Transaction
from payments.services import PaymentService
from decimal import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = 'Test payments functionality'

    def handle(self, *args, **options):
        self.stdout.write('Testing Payments App...')
        
        user, created = User.objects.get_or_create(
            email='test@mengedmate.com',
            defaults={'password': 'testpass123'}
        )
        
        if created:
            self.stdout.write(f'Created test user: {user.email}')
        else:
            self.stdout.write(f'Using existing user: {user.email}')
        
        payment_method = PaymentMethod.objects.create(
            user=user,
            method_type=PaymentMethod.MethodType.MPESA,
            phone_number='+251912345678',
            is_default=True
        )
        self.stdout.write(f'Created payment method: {payment_method}')
        
        wallet, created = Wallet.objects.get_or_create(user=user)
        self.stdout.write(f'Wallet balance: {wallet.balance} {wallet.currency}')
        
        transaction = Transaction.objects.create(
            user=user,
            transaction_type=Transaction.TransactionType.DEPOSIT,
            amount=Decimal('100.00'),
            reference_number='TEST123456',
            phone_number='+251912345678',
            description='Test transaction'
        )
        self.stdout.write(f'Created transaction: {transaction}')
        
        payment_service = PaymentService()
        updated_wallet = payment_service.credit_wallet(user, Decimal('100.00'), transaction)
        self.stdout.write(f'Updated wallet balance: {updated_wallet.balance} {updated_wallet.currency}')
        
        self.stdout.write(self.style.SUCCESS('Payments app test completed successfully!'))
