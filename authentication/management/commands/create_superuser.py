from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a superuser if one does not exist'

    def handle(self, *args, **options):
        email = 'mengedmate@gmail.com'
        password = '@Menged44'
        
        try:
            # Check if the superuser already exists
            if User.objects.filter(email=email).exists():
                self.stdout.write(self.style.WARNING(f'Superuser with email {email} already exists.'))
                return
                
            # Create the superuser
            user = User.objects.create_superuser(
                email=email,
                password=password,
                is_verified=True
            )
            
            self.stdout.write(self.style.SUCCESS(f'Superuser {email} created successfully!'))
            
        except IntegrityError as e:
            self.stdout.write(self.style.ERROR(f'Error creating superuser: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Unexpected error: {e}'))
