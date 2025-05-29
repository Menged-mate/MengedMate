from django.core.management.base import BaseCommand
from charging_stations.models import StationOwner


class Command(BaseCommand):
    help = 'Fix incorrectly marked profile completion status'

    def handle(self, *args, **options):
        # Find all station owners marked as completed
        completed_profiles = StationOwner.objects.filter(is_profile_completed=True)
        
        fixed_count = 0
        
        for profile in completed_profiles:
            # Check if all required fields have actual values
            required_text_fields = ['business_registration_number']
            required_file_fields = ['business_license', 'id_proof']
            
            # Check text fields are not empty
            text_fields_complete = all(
                getattr(profile, field) and str(getattr(profile, field)).strip() 
                for field in required_text_fields
            )
            
            # Check file fields have actual files uploaded
            file_fields_complete = all(
                getattr(profile, field) and getattr(profile, field).name
                for field in required_file_fields
            )
            
            is_actually_complete = text_fields_complete and file_fields_complete
            
            if not is_actually_complete:
                # Reset the profile completion status
                profile.is_profile_completed = False
                if profile.verification_status == 'pending':
                    profile.verification_status = 'pending'  # Keep as pending until actually completed
                profile.save()
                fixed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Fixed profile for {profile.company_name} ({profile.user.email})'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully fixed {fixed_count} incorrectly marked profiles'
            )
        )
