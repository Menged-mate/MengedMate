from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from django.conf import settings
import random

User = get_user_model()


class CustomAccountAdapter:
    """Custom account adapter for basic authentication functionality"""

    def populate_username(self, request, user):
        """Populate username - not needed for email-based auth"""
        pass

    def save_user(self, request, user, form, commit=True):
        """Save user with verification code"""
        # Note: This would need to be adapted if using with a form framework
        user.verification_code = ''.join(random.choices('0123456789', k=6))

        if commit:
            user.save()

        return user