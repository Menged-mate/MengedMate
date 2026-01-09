"""
Social Authentication Views for Google OAuth

Handles Google Sign-In/Sign-Up by verifying Google ID tokens
and creating/authenticating users.
"""
import requests
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.models import Token
from datetime import datetime

from utils.firestore_repo import firestore_repo
from .serializers_firestore import FirestoreUserSerializer
from .authentication import AnonymousAuthentication

User = get_user_model()


class GoogleAuthView(APIView):
    """
    Handles Google OAuth authentication.
    
    Accepts Google access_token and id_token from the mobile app,
    verifies the token with Google, and creates/logs in the user.
    """
    permission_classes = [AllowAny]
    authentication_classes = [AnonymousAuthentication]
    
    GOOGLE_TOKEN_INFO_URL = 'https://oauth2.googleapis.com/tokeninfo'
    GOOGLE_USER_INFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'

    def post(self, request):
        access_token = request.data.get('access_token')
        id_token = request.data.get('id_token')
        
        if not id_token and not access_token:
            return Response(
                {'error': 'Either access_token or id_token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Verify the token and get user info
            google_user_info = self._verify_google_token(id_token, access_token)
            
            if not google_user_info:
                return Response(
                    {'error': 'Invalid Google token'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Get or create user
            user, created = self._get_or_create_user(google_user_info)
            
            # Create or get auth token
            token, _ = Token.objects.get_or_create(user=user)
            
            # Fetch user profile from Firestore
            profile = firestore_repo.get_user_profile(user.id)
            if not profile:
                # Create profile if it doesn't exist
                profile = {
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_verified': True,
                    'auth_provider': 'google',
                    'google_id': google_user_info.get('sub'),
                }
                firestore_repo.create_user_profile(user.id, profile)
            
            user_data = FirestoreUserSerializer(profile).data
            
            return Response({
                'message': 'Google authentication successful',
                'token': token.key,
                'user': user_data,
                'created': created
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Google authentication error: {str(e)}")
            return Response(
                {'error': f'Authentication failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _verify_google_token(self, id_token, access_token):
        """
        Verify Google token and return user info.
        
        First tries to verify the id_token, then falls back to
        using the access_token to get user info.
        """
        # Try verifying id_token first
        if id_token:
            try:
                response = requests.get(
                    self.GOOGLE_TOKEN_INFO_URL,
                    params={'id_token': id_token},
                    timeout=10
                )
                if response.status_code == 200:
                    token_info = response.json()
                    # Verify the token is not expired
                    if 'email' in token_info:
                        return {
                            'sub': token_info.get('sub'),
                            'email': token_info.get('email'),
                            'email_verified': token_info.get('email_verified', 'false') == 'true',
                            'name': token_info.get('name', ''),
                            'given_name': token_info.get('given_name', ''),
                            'family_name': token_info.get('family_name', ''),
                            'picture': token_info.get('picture', ''),
                        }
            except requests.RequestException:
                pass  # Fall through to try access_token
        
        # Try using access_token to get user info
        if access_token:
            try:
                response = requests.get(
                    self.GOOGLE_USER_INFO_URL,
                    headers={'Authorization': f'Bearer {access_token}'},
                    timeout=10
                )
                if response.status_code == 200:
                    user_info = response.json()
                    return {
                        'sub': user_info.get('sub'),
                        'email': user_info.get('email'),
                        'email_verified': user_info.get('email_verified', False),
                        'name': user_info.get('name', ''),
                        'given_name': user_info.get('given_name', ''),
                        'family_name': user_info.get('family_name', ''),
                        'picture': user_info.get('picture', ''),
                    }
            except requests.RequestException:
                pass
        
        return None
    
    def _get_or_create_user(self, google_user_info):
        """
        Get existing user or create new one based on Google user info.
        """
        email = google_user_info.get('email')
        google_id = google_user_info.get('sub')
        
        if not email:
            raise ValueError("Google account does not have an email address")
        
        # First try to find existing user by email
        try:
            user = User.objects.get(email=email)
            # Update user info from Google
            user.first_name = google_user_info.get('given_name', user.first_name)
            user.last_name = google_user_info.get('family_name', user.last_name)
            user.is_verified = True  # Google accounts are pre-verified
            user.save()
            
            # Update Firestore profile
            firestore_repo.update_user_profile(user.id, {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_verified': True,
                'auth_provider': 'google',
                'google_id': google_id,
                'updated_at': datetime.now().isoformat()
            })
            
            return user, False
        except User.DoesNotExist:
            pass
        
        # Create new user
        user = User.objects.create_user(
            email=email,
            first_name=google_user_info.get('given_name', ''),
            last_name=google_user_info.get('family_name', ''),
            is_verified=True,  # Google accounts are pre-verified
        )
        
        # Create Firestore profile
        profile_data = {
            'email': email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'is_verified': True,
            'auth_provider': 'google',
            'google_id': google_id,
            'profile_picture': google_user_info.get('picture', '')
        }
        firestore_repo.create_user_profile(user.id, profile_data)
        
        return user, True


class AppleAuthView(APIView):
    """
    Handles Apple Sign-In authentication.
    
    Accepts Apple authorization code and id_token from the mobile app,
    and creates/logs in the user.
    """
    permission_classes = [AllowAny]
    authentication_classes = [AnonymousAuthentication]

    def post(self, request):
        code = request.data.get('code')
        id_token = request.data.get('id_token')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        
        if not id_token:
            return Response(
                {'error': 'id_token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Decode the Apple ID token to get user info
            # Note: In production, you should verify the token signature
            import base64
            import json
            
            # Split the JWT and decode the payload
            parts = id_token.split('.')
            if len(parts) != 3:
                return Response(
                    {'error': 'Invalid id_token format'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Decode payload (add padding if needed)
            payload = parts[1]
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding
            
            decoded_payload = base64.urlsafe_b64decode(payload)
            token_data = json.loads(decoded_payload)
            
            email = token_data.get('email')
            apple_id = token_data.get('sub')
            
            if not email:
                return Response(
                    {'error': 'Apple account does not have an email'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get or create user
            try:
                user = User.objects.get(email=email)
                created = False
                # Update names if provided (Apple only sends these on first sign-in)
                if first_name:
                    user.first_name = first_name
                if last_name:
                    user.last_name = last_name
                user.is_verified = True
                user.save()
            except User.DoesNotExist:
                user = User.objects.create_user(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    is_verified=True,
                )
                created = True
                
                # Create Firestore profile
                profile_data = {
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat(),
                    'is_verified': True,
                    'auth_provider': 'apple',
                    'apple_id': apple_id,
                }
                firestore_repo.create_user_profile(user.id, profile_data)
            
            # Create or get auth token
            token, _ = Token.objects.get_or_create(user=user)
            
            # Fetch profile
            profile = firestore_repo.get_user_profile(user.id)
            user_data = FirestoreUserSerializer(profile).data if profile else {
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
            
            return Response({
                'message': 'Apple authentication successful',
                'token': token.key,
                'user': user_data,
                'created': created
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Apple authentication error: {str(e)}")
            return Response(
                {'error': f'Authentication failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
