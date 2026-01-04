from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import IntegrityError
import os

User = get_user_model()


class Command(BaseCommand):
    help = 'Create admin superuser for evmeri application'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            default='admin@evmeri.com',
            help='Admin email address'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='admin123',
            help='Admin password'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreate admin user if exists'
        )

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']
        force = options['force']

        self.stdout.write(f'🔍 Checking for existing admin user: {email}')

        # Check if admin user already exists
        try:
            admin_user = User.objects.get(email=email)
            if not force:
                self.stdout.write(
                    self.style.WARNING(f'✅ Admin user with email {email} already exists.')
                )
                self.stdout.write(f'📧 Email: {email}')
                self.stdout.write(f'🔑 Password: {password}')
                self.stdout.write(f'🌐 Admin URL: https://evmeri.fly.dev/admin/')
                return
            else:
                self.stdout.write(f'🗑️ Deleting existing admin user: {email}')
                admin_user.delete()
        except User.DoesNotExist:
            self.stdout.write('👤 No existing admin user found. Creating new one...')

        # Create new admin user
        try:
            self.stdout.write(f'🔨 Creating admin superuser: {email}')
            admin_user = User.objects.create_superuser(
                email=email,
                password=password,
                first_name='Admin',
                last_name='User',
                is_verified=True
            )

            self.stdout.write(
                self.style.SUCCESS(f'✅ Successfully created admin superuser!')
            )
            self.stdout.write(f'📧 Email: {email}')
            self.stdout.write(f'🔑 Password: {password}')
            self.stdout.write(f'🌐 Admin URL: https://evmeri.fly.dev/admin/')
            self.stdout.write(f'🚀 You can now access the Django admin interface!')

        except IntegrityError as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to create admin user (IntegrityError): {e}')
            )
            # Try to get the existing user info
            try:
                existing_user = User.objects.get(email=email)
                self.stdout.write(
                    self.style.WARNING(f'ℹ️ User already exists: {existing_user.email}')
                )
            except User.DoesNotExist:
                pass
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Unexpected error: {e}')
            )
            import traceback
            self.stdout.write(traceback.format_exc())
