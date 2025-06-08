from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.management import call_command
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views import View
import subprocess
import os
import datetime
import json


@method_decorator(staff_member_required, name='dispatch')
class DatabaseBackupView(View):
    """Admin view for database backup functionality"""
    
    def get(self, request):
        """Display backup management page"""
        context = {
            'title': 'Database Backup Management',
            'backup_history': self.get_backup_history(),
        }
        return render(request, 'admin/database_backup.html', context)
    
    def post(self, request):
        """Handle backup creation"""
        action = request.POST.get('action')
        
        if action == 'create_backup':
            return self.create_backup(request)
        elif action == 'download_backup':
            return self.download_backup(request)
        elif action == 'delete_backup':
            return self.delete_backup(request)
        
        return JsonResponse({'success': False, 'error': 'Invalid action'})
    
    def create_backup(self, request):
        """Create a new database backup"""
        try:
            # Create backup directory
            backup_dir = '/tmp/db_backups'
            os.makedirs(backup_dir, exist_ok=True)
            
            # Generate backup filename
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f'evmeri_backup_{timestamp}.sql'
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # Get database settings
            db_settings = settings.DATABASES['default']
            
            if db_settings['ENGINE'] == 'django.db.backends.postgresql':
                self.backup_postgresql(db_settings, backup_path)
            elif db_settings['ENGINE'] == 'django.db.backends.sqlite3':
                self.backup_sqlite(db_settings, backup_path)
            else:
                return JsonResponse({
                    'success': False, 
                    'error': f'Unsupported database engine: {db_settings["ENGINE"]}'
                })
            
            # Get file size
            file_size = os.path.getsize(backup_path)
            file_size_mb = file_size / (1024 * 1024)
            
            # Send notification
            self.send_backup_notification(backup_filename, file_size_mb)
            
            messages.success(
                request, 
                f'Database backup created successfully: {backup_filename} ({file_size_mb:.2f} MB)'
            )
            
            return JsonResponse({
                'success': True,
                'filename': backup_filename,
                'size_mb': round(file_size_mb, 2),
                'message': 'Backup created successfully'
            })
            
        except Exception as e:
            messages.error(request, f'Backup failed: {str(e)}')
            return JsonResponse({'success': False, 'error': str(e)})
    
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
    
    def get_backup_history(self):
        """Get list of existing backup files"""
        backup_dir = '/tmp/db_backups'
        backups = []
        
        if os.path.exists(backup_dir):
            for filename in os.listdir(backup_dir):
                if filename.startswith('evmeri_backup_') and filename.endswith('.sql'):
                    file_path = os.path.join(backup_dir, filename)
                    file_stat = os.stat(file_path)
                    
                    backups.append({
                        'filename': filename,
                        'size_mb': round(file_stat.st_size / (1024 * 1024), 2),
                        'created_at': datetime.datetime.fromtimestamp(file_stat.st_ctime),
                        'path': file_path
                    })
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        return backups
    
    def download_backup(self, request):
        """Download a backup file"""
        filename = request.POST.get('filename')
        backup_path = f'/tmp/db_backups/{filename}'
        
        if not os.path.exists(backup_path):
            return JsonResponse({'success': False, 'error': 'Backup file not found'})
        
        try:
            with open(backup_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    def delete_backup(self, request):
        """Delete a backup file"""
        filename = request.POST.get('filename')
        backup_path = f'/tmp/db_backups/{filename}'
        
        if not os.path.exists(backup_path):
            return JsonResponse({'success': False, 'error': 'Backup file not found'})
        
        try:
            os.remove(backup_path)
            messages.success(request, f'Backup {filename} deleted successfully')
            return JsonResponse({'success': True, 'message': 'Backup deleted successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    def send_backup_notification(self, filename, file_size_mb):
        """Send notification about backup completion"""
        try:
            from django.core.mail import send_mail
            
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
                fail_silently=True
            )
            
        except Exception as e:
            print(f"Failed to send backup notification email: {str(e)}")


@staff_member_required
def system_stats_view(request):
    """Display system statistics"""
    from django.db import connection
    from charging_stations.models import StationOwner, ChargingStation, ChargingConnector, StationReview
    from authentication.models import CustomUser
    
    # Get database stats
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
        db_size = cursor.fetchone()[0] if cursor.fetchone() else "Unknown"
    
    stats = {
        'total_users': CustomUser.objects.count(),
        'verified_station_owners': StationOwner.objects.filter(verification_status='verified').count(),
        'pending_station_owners': StationOwner.objects.filter(verification_status='pending').count(),
        'total_stations': ChargingStation.objects.count(),
        'active_stations': ChargingStation.objects.filter(is_active=True).count(),
        'total_connectors': ChargingConnector.objects.count(),
        'available_connectors': ChargingConnector.objects.filter(is_available=True).count(),
        'total_reviews': StationReview.objects.count(),
        'verified_reviews': StationReview.objects.filter(is_verified_review=True).count(),
        'database_size': db_size,
    }
    
    context = {
        'title': 'System Statistics',
        'stats': stats,
    }
    
    return render(request, 'admin/system_stats.html', context)
