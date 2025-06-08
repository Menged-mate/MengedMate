from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from charging_stations.admin_views import DatabaseBackupView
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Test database backup functionality'

    def handle(self, *args, **options):
        self.stdout.write('Testing database backup functionality...')
        
        try:
            # Create a test superuser if it doesn't exist
            if not User.objects.filter(is_superuser=True).exists():
                user = User.objects.create_superuser(
                    email='admin@test.com',
                    password='testpass123'
                )
                self.stdout.write(f'Created test superuser: {user.email}')
            else:
                user = User.objects.filter(is_superuser=True).first()
                self.stdout.write(f'Using existing superuser: {user.email}')
            
            # Test backup directory creation
            backup_dir = '/tmp/db_backups'
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir, exist_ok=True)
                self.stdout.write(f'Created backup directory: {backup_dir}')
            else:
                self.stdout.write(f'Backup directory exists: {backup_dir}')
            
            # Test backup view instantiation
            factory = RequestFactory()
            request = factory.get('/admin/database-backup/')
            request.user = user
            
            view = DatabaseBackupView()
            view.request = request
            
            # Test get_backup_history method
            backup_history = view.get_backup_history()
            self.stdout.write(f'Found {len(backup_history)} existing backups')
            
            self.stdout.write(
                self.style.SUCCESS('✅ Database backup functionality test completed successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Database backup test failed: {str(e)}')
            )
