from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import perform_login
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from django.conf import settings
import random

User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter for social account authentication.
    """
    def pre_social_login(self, request, sociallogin):
        """
        Handle social login before the user is logged in.
        """
        email = sociallogin.account.extra_data.get('email')
        if not email:
            return

        try:
            user = User.objects.get(email=email)

           
            if not sociallogin.is_existing:
                sociallogin.connect(request, user)

            if not user.is_verified:
                user.is_verified = True
                user.save()

        except User.DoesNotExist:
            pass

    def save_user(self, request, sociallogin, form=None):
        """
        Save the user and perform additional actions.
        """
        user = super().save_user(request, sociallogin, form)

        user.is_verified = True

        if sociallogin.account.provider == 'google':
            self._process_google_data(user, sociallogin.account.extra_data)
        elif sociallogin.account.provider == 'facebook':
            self._process_facebook_data(user, sociallogin.account.extra_data)
        elif sociallogin.account.provider == 'apple':
            self._process_apple_data(user, sociallogin.account.extra_data)

        user.save()

        token, created = Token.objects.get_or_create(user=user)

        return user

    def _process_google_data(self, user, data):
        """
        Process Google account data.
        """
        if not user.first_name and 'given_name' in data:
            user.first_name = data['given_name']

        if not user.last_name and 'family_name' in data:
            user.last_name = data['family_name']

        if not user.profile_picture and 'picture' in data:
            pass

    def _process_facebook_data(self, user, data):
        """
        Process Facebook account data.
        """
        if not user.first_name and 'first_name' in data:
            user.first_name = data['first_name']

        if not user.last_name and 'last_name' in data:
            user.last_name = data['last_name']

        if not user.profile_picture and 'picture' in data and 'data' in data['picture'] and 'url' in data['picture']['data']:
            pass

    def _process_apple_data(self, user, data):
        """
        Process Apple account data.
        """
        if not user.first_name and 'first_name' in data:
            user.first_name = data['first_name']

        if not user.last_name and 'last_name' in data:
            user.last_name = data['last_name']


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom adapter for email-based authentication without username.
    """
    def populate_username(self, request, user):
        """
        Override the populate_username method to not require a username.
        """
        pass

    def save_user(self, request, user, form, commit=True):
        """
        Override the save_user method to use email as the primary identifier.
        """
        user = super().save_user(request, user, form, commit=False)

        user.verification_code = ''.join(random.choices('0123456789', k=6))

        if commit:
            user.save()

        return user