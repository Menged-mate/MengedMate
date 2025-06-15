import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from telegram_webapp_auth import check_webapp_signature, parse_webapp_init_data

User = get_user_model()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

class TelegramAuthView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        init_data_raw = None

        # Try to get initData from Authorization header first
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Telegram-Mini-App '):
            init_data_raw = auth_header.split(' ', 1)[1]
        # Fallback to body if not found in header
        if not init_data_raw:
            init_data_raw = request.data.get('init_data') or request.data.get('initData')

        if not init_data_raw:
            return Response(
                {"detail": "No Telegram initData found."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 1. Verify the initData signature
            is_valid = check_webapp_signature(TELEGRAM_BOT_TOKEN, init_data_raw)
            if not is_valid:
                return Response(
                    {"detail": "Invalid Telegram initData signature."},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # 2. Parse the initData to get user information
            parsed_data = parse_webapp_init_data(init_data_raw)
            telegram_user_data = parsed_data.get('user', {})

            if not telegram_user_data or not telegram_user_data.get('id'):
                return Response(
                    {"detail": "User data not found in initData."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            telegram_user_id = telegram_user_data['id']
            first_name = telegram_user_data.get('first_name', '')
            last_name = telegram_user_data.get('last_name', '')
            username = telegram_user_data.get('username', '')
            language_code = telegram_user_data.get('language_code', '')

            # 3. Authenticate or create the user
            user, created = User.objects.get_or_create(
                username=f'telegram_{telegram_user_id}',
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': f'{telegram_user_id}@telegram.com',
                }
            )
            if not created:
                user.first_name = first_name
                user.last_name = last_name
                user.save()

            # 4. Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            user_response_data = {
                'id': telegram_user_id,
                'first_name': first_name,
                'last_name': last_name,
                'username': username,
                'language_code': language_code,
            }

            return Response({
                "message": "Authentication successful",
                "user_data": user_response_data,
                "token": str(refresh.access_token),
                "refresh_token": str(refresh),
            }, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Authentication error: {e}")
            return Response(
                {"detail": f"Internal server error during authentication: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 