from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.utils import perform_login
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from django.conf import settings

User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter for social account authentication.
    """
    def pre_social_login(self, request, sociallogin):
        """
        Handle social login before the user is logged in.
        """
        # Get the user's email from the social account
        email = sociallogin.account.extra_data.get('email')
        if not email:
            return

        # Check if a user with this email already exists
        try:
            user = User.objects.get(email=email)
            
            # If the user exists but doesn't have a social account,
            # connect the social account to the existing user
            if not sociallogin.is_existing:
                sociallogin.connect(request, user)
                
            # Mark the user as verified since they've authenticated via a social provider
            if not user.is_verified:
                user.is_verified = True
                user.save()
                
        except User.DoesNotExist:
            # User doesn't exist, will be created by the default adapter
            pass
            
    def save_user(self, request, sociallogin, form=None):
        """
        Save the user and perform additional actions.
        """
        user = super().save_user(request, sociallogin, form)
        
        # Set the user as verified
        user.is_verified = True
        
        # Extract profile information from social account
        if sociallogin.account.provider == 'google':
            self._process_google_data(user, sociallogin.account.extra_data)
        elif sociallogin.account.provider == 'facebook':
            self._process_facebook_data(user, sociallogin.account.extra_data)
        elif sociallogin.account.provider == 'apple':
            self._process_apple_data(user, sociallogin.account.extra_data)
            
        user.save()
        
        # Create or get token for the user
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
            
        # Add profile picture if available
        if not user.profile_picture and 'picture' in data:
            # This would require additional logic to download and save the image
            pass
            
    def _process_facebook_data(self, user, data):
        """
        Process Facebook account data.
        """
        if not user.first_name and 'first_name' in data:
            user.first_name = data['first_name']
            
        if not user.last_name and 'last_name' in data:
            user.last_name = data['last_name']
            
        # Add profile picture if available
        if not user.profile_picture and 'picture' in data and 'data' in data['picture'] and 'url' in data['picture']['data']:
            # This would require additional logic to download and save the image
            pass
            
    def _process_apple_data(self, user, data):
        """
        Process Apple account data.
        """
        # Apple provides minimal data, usually just the email
        # First name and last name might be available on first login only
        if not user.first_name and 'first_name' in data:
            user.first_name = data['first_name']
            
        if not user.last_name and 'last_name' in data:
            user.last_name = data['last_name']
