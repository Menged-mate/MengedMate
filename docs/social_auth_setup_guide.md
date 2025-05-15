# Social Authentication Setup Guide for Mengedmate

This guide provides detailed instructions for setting up social authentication (Google, Facebook, and Apple) in the Mengedmate application.

## Table of Contents
1. [Backend Setup](#backend-setup)
2. [Frontend Setup](#frontend-setup)
3. [OAuth Provider Configuration](#oauth-provider-configuration)
4. [Environment Variables](#environment-variables)
5. [Testing](#testing)
6. [Troubleshooting](#troubleshooting)

## Backend Setup

### 1. Install Required Packages

Make sure you have all the required packages installed:

```bash
pip install -r requirements.txt
```

### 2. Configure Django Settings

The following settings should be added to your `settings.py` file:

```python
# Social Authentication Settings
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': os.environ.get('GOOGLE_CLIENT_ID', ''),
            'secret': os.environ.get('GOOGLE_CLIENT_SECRET', ''),
            'key': ''
        },
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        }
    },
    'facebook': {
        'APP': {
            'client_id': os.environ.get('FACEBOOK_CLIENT_ID', ''),
            'secret': os.environ.get('FACEBOOK_CLIENT_SECRET', ''),
            'key': ''
        },
        'SCOPE': [
            'email',
            'public_profile',
        ],
        'FIELDS': [
            'id',
            'email',
            'name',
            'first_name',
            'last_name',
            'picture',
        ],
    },
    'apple': {
        'APP': {
            'client_id': os.environ.get('APPLE_CLIENT_ID', ''),
            'secret': os.environ.get('APPLE_CLIENT_SECRET', ''),
            'key': os.environ.get('APPLE_KEY_ID', ''),
            'certificate_key': os.environ.get('APPLE_CERTIFICATE_KEY', '')
        },
        'SCOPE': [
            'email',
            'name',
        ],
    }
}

# Social account settings
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_ADAPTER = 'authentication.adapters.CustomSocialAccountAdapter'

# REST Auth settings
REST_USE_JWT = True
JWT_AUTH_COOKIE = 'mengedmate-auth'
JWT_AUTH_REFRESH_COOKIE = 'mengedmate-refresh'
```

### 3. Configure URLs

Make sure your `urls.py` includes the necessary URL patterns:

```python
urlpatterns = [
    # Django allauth URLs
    path("accounts/", include("allauth.urls")),
    path("api/dj-rest-auth/", include("dj_rest_auth.urls")),
    path("api/dj-rest-auth/registration/", include("dj_rest_auth.registration.urls")),
    
    # Social authentication endpoints
    path('api/auth/social/google/', GoogleLoginView.as_view(), name='google-login'),
    path('api/auth/social/facebook/', FacebookLoginView.as_view(), name='facebook-login'),
    path('api/auth/social/apple/', AppleLoginView.as_view(), name='apple-login'),
    path('api/auth/social/callback/', SocialAuthCallbackView.as_view(), name='social-callback'),
]
```

## Frontend Setup

### 1. Android Configuration

1. Update your `android/app/src/main/AndroidManifest.xml` to include:

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.INTERNET"/>
    
    <!-- Rest of your manifest -->
    
    <queries>
        <!-- Required for Google Sign-In -->
        <intent>
            <action android:name="android.intent.action.VIEW" />
            <data android:scheme="https" />
        </intent>
        <package android:name="com.google.android.gms" />
    </queries>
</manifest>
```

2. Create or update `android/app/src/main/res/values/strings.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">MengedMate</string>
    <!-- Replace with your actual Google Web Client ID -->
    <string name="server_client_id">YOUR_GOOGLE_WEB_CLIENT_ID</string>
</resources>
```

### 2. iOS Configuration

Update your `ios/Runner/Info.plist` to include:

```xml
<!-- Google Sign-in Section -->
<key>CFBundleURLTypes</key>
<array>
    <dict>
        <key>CFBundleTypeRole</key>
        <string>Editor</string>
        <key>CFBundleURLSchemes</key>
        <array>
            <!-- Replace this value with your Google Client ID reversed -->
            <string>com.googleusercontent.apps.YOUR_GOOGLE_CLIENT_ID_REVERSED</string>
        </array>
    </dict>
</array>
<!-- End of Google Sign-in Section -->

<!-- Apple Sign-in Section -->
<key>com.apple.developer.applesignin</key>
<array>
    <string>Default</string>
</array>
<!-- End of Apple Sign-in Section -->
```

## OAuth Provider Configuration

### Google

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to "APIs & Services" > "Credentials"
4. Click "Create Credentials" > "OAuth client ID"
5. Select "Web application" for the backend and "Android" and "iOS" for the mobile apps
6. Add your domain to the "Authorized JavaScript origins"
7. Add your callback URLs to the "Authorized redirect URIs":
   - `https://your-domain.com/accounts/google/login/callback/`
   - `https://your-domain.com/api/auth/social/callback/`
8. Copy the Client ID and Client Secret to your environment variables

### Facebook

1. Go to the [Facebook Developer Portal](https://developers.facebook.com/)
2. Create a new app or select an existing one
3. Add the "Facebook Login" product to your app
4. In the Facebook Login settings, add your OAuth redirect URI:
   - `https://your-domain.com/accounts/facebook/login/callback/`
   - `https://your-domain.com/api/auth/social/callback/`
5. In the "Basic" settings, copy the App ID and App Secret to your environment variables

### Apple

1. Go to the [Apple Developer Portal](https://developer.apple.com/)
2. Navigate to "Certificates, Identifiers & Profiles"
3. Create a new "Services ID" for your app
4. Enable "Sign In with Apple" for the Service ID
5. Configure your domain and redirect URLs:
   - `https://your-domain.com/accounts/apple/login/callback/`
   - `https://your-domain.com/api/auth/social/callback/`
6. Create a private key for "Sign In with Apple"
7. Download the key and note the Key ID
8. Set up the environment variables with the Client ID (Service ID), Key ID, and the contents of the private key file

## Environment Variables

Add the following environment variables to your backend server:

```
# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Facebook OAuth
FACEBOOK_CLIENT_ID=your_facebook_app_id
FACEBOOK_CLIENT_SECRET=your_facebook_app_secret

# Apple OAuth
APPLE_CLIENT_ID=your_apple_client_id
APPLE_CLIENT_SECRET=your_apple_client_secret
APPLE_KEY_ID=your_apple_key_id
APPLE_CERTIFICATE_KEY=your_apple_certificate_key
```

## Testing

### Backend Testing

You can test the backend API endpoints using tools like Postman or curl:

```bash
# Google Sign-In
curl -X POST https://your-domain.com/api/auth/social/google/ \
  -H "Content-Type: application/json" \
  -d '{"access_token": "google_access_token", "id_token": "google_id_token"}'

# Facebook Sign-In
curl -X POST https://your-domain.com/api/auth/social/facebook/ \
  -H "Content-Type: application/json" \
  -d '{"access_token": "facebook_access_token"}'

# Apple Sign-In
curl -X POST https://your-domain.com/api/auth/social/apple/ \
  -H "Content-Type: application/json" \
  -d '{"code": "apple_authorization_code", "id_token": "apple_id_token"}'
```

### Frontend Testing

1. Make sure you have the correct OAuth credentials configured
2. Run the app in debug mode
3. Try signing in with each social provider
4. Check the logs for any errors

## Troubleshooting

### Common Issues

1. **MissingPluginException**: Make sure you have the correct plugin dependencies and have run `flutter pub get`.

2. **Invalid Client ID**: Double-check your OAuth client IDs in both the backend and frontend configurations.

3. **Redirect URI Mismatch**: Ensure that the redirect URIs in your OAuth provider settings match exactly what your application is using.

4. **CORS Issues**: If you're experiencing CORS errors, check that your backend has the correct CORS settings for your frontend domain.

5. **Token Validation Errors**: Make sure the access tokens you're sending to the backend are valid and not expired.

For more detailed troubleshooting, check the server logs and the Flutter app logs.
