from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from charging_stations.models import StationOwner
import os

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a test station owner with sample documents for testing admin panel'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            default='testowner@example.com',
            help='Email for the test station owner'
        )
        parser.add_argument(
            '--company',
            type=str,
            default='Test EV Company',
            help='Company name for the test station owner'
        )

    def handle(self, *args, **options):
        email = options['email']
        company_name = options['company']
        
        self.stdout.write(f"Creating test station owner: {email}")
        
        # Create or get user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': 'Test',
                'last_name': 'Owner',
                'is_active': True
            }
        )
        
        if created:
            user.set_password('testpassword123')
            user.save()
            self.stdout.write(f"✅ Created user: {email}")
        else:
            self.stdout.write(f"📝 User already exists: {email}")
        
        # Create or get station owner
        station_owner, created = StationOwner.objects.get_or_create(
            user=user,
            defaults={
                'company_name': company_name,
                'business_registration_number': 'TEST-REG-123456',
                'verification_status': 'pending',
                'contact_phone': '+1-555-0123',
                'contact_email': email,
                'website': 'https://testevcompany.com',
                'description': 'Test EV charging company for demonstration purposes.',
                'is_profile_completed': True
            }
        )
        
        if created:
            self.stdout.write(f"✅ Created station owner: {company_name}")
            
            # Create sample document content
            sample_content = b"This is a sample document for testing purposes."
            
            # Add sample documents
            station_owner.business_document.save(
                'business_document.pdf',
                ContentFile(sample_content),
                save=False
            )
            
            station_owner.business_license.save(
                'business_license.pdf',
                ContentFile(sample_content),
                save=False
            )
            
            station_owner.id_proof.save(
                'id_proof.pdf',
                ContentFile(sample_content),
                save=False
            )
            
            station_owner.utility_bill.save(
                'utility_bill.pdf',
                ContentFile(sample_content),
                save=False
            )
            
            station_owner.save()
            
            self.stdout.write("✅ Added sample documents")
            
        else:
            self.stdout.write(f"📝 Station owner already exists: {company_name}")
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 Test station owner ready!\n'
                f'📧 Email: {email}\n'
                f'🏢 Company: {company_name}\n'
                f'🔑 Password: testpassword123\n'
                f'📋 Status: {station_owner.verification_status}\n'
                f'📄 Documents: {"✅ Uploaded" if station_owner.business_document else "❌ Missing"}\n'
                f'\n🔗 View in admin: /admin/charging_stations/stationowner/{station_owner.id}/change/'
            )
        )
