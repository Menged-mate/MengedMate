from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings


class Command(BaseCommand):
    help = 'Test email templates and configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Email address to send test email to',
            required=True
        )
        parser.add_argument(
            '--template',
            type=str,
            choices=['verification', 'password_reset', 'notification', 'station_owner'],
            default='verification',
            help='Email template to test'
        )

    def handle(self, *args, **options):
        email_address = options['email']
        template_type = options['template']
        
        self.stdout.write(f"Testing {template_type} email template...")
        self.stdout.write(f"Sending to: {email_address}")
        
        try:
            if template_type == 'verification':
                self.send_verification_email(email_address)
            elif template_type == 'password_reset':
                self.send_password_reset_email(email_address)
            elif template_type == 'notification':
                self.send_notification_email(email_address)
            elif template_type == 'station_owner':
                self.send_station_owner_email(email_address)
                
            self.stdout.write(
                self.style.SUCCESS(f'✅ {template_type} email sent successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to send email: {str(e)}')
            )

    def send_verification_email(self, email_address):
        html_content = render_to_string('email/verification_email.html', {
            'user': {'first_name': 'John', 'email': email_address},
            'verification_code': '123456'
        })
        
        email = EmailMultiAlternatives(
            '[MengedMate] Verify Your Email',
            'Please verify your email address.',
            settings.DEFAULT_FROM_EMAIL,
            [email_address]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

    def send_password_reset_email(self, email_address):
        html_content = render_to_string('password_reset_email.html', {
            'user': {'first_name': 'John', 'email': email_address},
            'reset_url': 'https://mengedmate.com/reset-password/abc123'
        })
        
        email = EmailMultiAlternatives(
            '[MengedMate] Reset Your Password',
            'Reset your password.',
            settings.DEFAULT_FROM_EMAIL,
            [email_address]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

    def send_notification_email(self, email_address):
        html_content = render_to_string('email/notification_email.html', {
            'user': {'first_name': 'John', 'email': email_address},
            'notification': {
                'title': 'New Charging Station Available',
                'message': 'A new charging station has been added near your location. Check it out now!',
                'link': 'https://mengedmate.com/stations/123'
            }
        })
        
        email = EmailMultiAlternatives(
            '[MengedMate] New Charging Station Available',
            'New notification from MengedMate.',
            settings.DEFAULT_FROM_EMAIL,
            [email_address]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

    def send_station_owner_email(self, email_address):
        html_content = render_to_string('station_owner_verification_email.html', {
            'station_owner': {
                'user': {'first_name': 'John', 'email': email_address},
                'verification_status': 'verified'
            }
        })
        
        email = EmailMultiAlternatives(
            '[MengedMate] Station Owner Verification Update',
            'Your verification status has been updated.',
            settings.DEFAULT_FROM_EMAIL,
            [email_address]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
