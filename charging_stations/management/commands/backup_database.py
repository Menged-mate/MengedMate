import os
import subprocess
import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import send_mail
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Create a database backup'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default='/tmp/db_backups',
            help='Directory to store backup files'
        )
        parser.add_argument(
            '--email-backup',
            action='store_true',
            help='Email the backup file to admin'
        )

    def handle(self, *args, **options):
        output_dir = options['output_dir']
        email_backup = options['email_backup']
        
        # Create backup directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'evmeri_backup_{timestamp}.sql'
        backup_path = os.path.join(output_dir, backup_filename)
        
        try:
            # Get database settings
            db_settings = settings.DATABASES['default']
            
            if db_settings['ENGINE'] == 'django.db.backends.postgresql':
                self.backup_postgresql(db_settings, backup_path)
            elif db_settings['ENGINE'] == 'django.db.backends.sqlite3':
                self.backup_sqlite(db_settings, backup_path)
            else:
                self.stdout.write(
                    self.style.ERROR(f'Unsupported database engine: {db_settings["ENGINE"]}')
                )
                return
            
            # Get file size
            file_size = os.path.getsize(backup_path)
            file_size_mb = file_size / (1024 * 1024)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Database backup created successfully: {backup_path} ({file_size_mb:.2f} MB)'
                )
            )
            
            # Email backup if requested
            if email_backup:
                self.email_backup_notification(backup_filename, file_size_mb)
            
            # Clean up old backups (keep last 7 days)
            self.cleanup_old_backups(output_dir)
            
        except Exception as e:
            logger.error(f'Database backup failed: {str(e)}')
            self.stdout.write(
                self.style.ERROR(f'Database backup failed: {str(e)}')
            )

    def backup_postgresql(self, db_settings, backup_path):
        """Create PostgreSQL backup using pg_dump"""
        cmd = [
            'pg_dump',
            '--host', db_settings.get('HOST', 'localhost'),
            '--port', str(db_settings.get('PORT', 5432)),
            '--username', db_settings['USER'],
            '--dbname', db_settings['NAME'],
            '--file', backup_path,
            '--verbose',
            '--no-password'
        ]
        
        # Set password via environment variable
        env = os.environ.copy()
        env['PGPASSWORD'] = db_settings['PASSWORD']
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f'pg_dump failed: {result.stderr}')

    def backup_sqlite(self, db_settings, backup_path):
        """Create SQLite backup by copying the database file"""
        import shutil
        db_path = db_settings['NAME']
        
        if not os.path.exists(db_path):
            raise Exception(f'SQLite database file not found: {db_path}')
        
        shutil.copy2(db_path, backup_path)

    def email_backup_notification(self, filename, file_size_mb):
        """Send email notification about backup completion"""
        try:
            subject = f'evmeri Database Backup Completed - {filename}'
            message = f'''
Database backup has been completed successfully.

Backup Details:
- Filename: {filename}
- Size: {file_size_mb:.2f} MB
- Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

The backup file has been stored securely on the server.

Best regards,
evmeri System
            '''
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL],
                fail_silently=False
            )
            
            self.stdout.write(
                self.style.SUCCESS('Backup notification email sent successfully')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Failed to send backup notification email: {str(e)}')
            )

    def cleanup_old_backups(self, backup_dir):
        """Remove backup files older than 7 days"""
        try:
            cutoff_time = datetime.datetime.now() - datetime.timedelta(days=7)
            
            for filename in os.listdir(backup_dir):
                if filename.startswith('evmeri_backup_') and filename.endswith('.sql'):
                    file_path = os.path.join(backup_dir, filename)
                    file_time = datetime.datetime.fromtimestamp(os.path.getctime(file_path))
                    
                    if file_time < cutoff_time:
                        os.remove(file_path)
                        self.stdout.write(
                            self.style.WARNING(f'Removed old backup: {filename}')
                        )
                        
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Failed to cleanup old backups: {str(e)}')
            )
