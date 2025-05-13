from rest_framework.authentication import BaseAuthentication, TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model

User = get_user_model()

class AnonymousAuthentication(BaseAuthentication):
    """
    Custom authentication class that allows anonymous access.
    """
    def authenticate(self, request):
        # Return None to indicate that this authentication class
        # does not authenticate the current request.
        return None

class BypassableTokenAuthentication(TokenAuthentication):
    """
    Custom token authentication that can be bypassed for specific endpoints.
    """
    def authenticate(self, request):
        # Check if the request should bypass authentication
        if request.META.get('BYPASS_AUTH', False):
            return None

        # Otherwise, use the standard token authentication
        return super().authenticate(request)
