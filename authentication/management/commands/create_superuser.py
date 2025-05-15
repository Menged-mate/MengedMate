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
            # Check if the User model has a username field
            user_fields = {
                'email': email,
                'password': password,
                'is_verified': True,
                'is_staff': True,
                'is_superuser': True
            }

            # Create the user
            user = User.objects.create_user(**user_fields)
            user.set_password(password)
            user.save()

            self.stdout.write(self.style.SUCCESS(f'Superuser {email} created successfully!'))

        except IntegrityError as e:
            self.stdout.write(self.style.ERROR(f'Error creating superuser: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Unexpected error: {e}'))
