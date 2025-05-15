# Social Authentication Setup Guide

This guide explains how to set up social authentication for the Mengedmate application.

## Prerequisites

- A Mengedmate backend server running
- Access to the Google, Facebook, and Apple developer consoles
- Environment variables properly configured

## Environment Variables

Add the following environment variables to your `.env` file or your hosting platform (e.g., Render):

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

## Setting Up OAuth Providers

### Google OAuth Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to "APIs & Services" > "Credentials"
4. Click "Create Credentials" > "OAuth client ID"
5. Select "Web application" as the application type
6. Add your domain to the "Authorized JavaScript origins"
7. Add your callback URL to the "Authorized redirect URIs":
   - `https://your-domain.com/accounts/google/login/callback/`
   - `https://your-domain.com/api/auth/social/callback/`
8. Copy the Client ID and Client Secret to your environment variables

### Facebook OAuth Setup

1. Go to the [Facebook Developer Portal](https://developers.facebook.com/)
2. Create a new app or select an existing one
3. Add the "Facebook Login" product to your app
4. In the Facebook Login settings, add your OAuth redirect URI:
   - `https://your-domain.com/accounts/facebook/login/callback/`
   - `https://your-domain.com/api/auth/social/callback/`
5. In the "Basic" settings, copy the App ID and App Secret to your environment variables

### Apple OAuth Setup

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

## Testing Social Authentication

### API Endpoints

The following endpoints are available for social authentication:

- Google: `POST /api/auth/social/google/`
- Facebook: `POST /api/auth/social/facebook/`
- Apple: `POST /api/auth/social/apple/`
- Callback: `GET /api/auth/social/callback/`

### Testing with Postman

1. Set up a new request in Postman
2. Use the appropriate endpoint (e.g., `POST /api/auth/social/google/`)
3. In the request body, include:
   ```json
   {
     "access_token": "your_oauth_access_token"
   }
   ```
4. Send the request and verify that you receive a token in the response

### Testing in the Frontend

In your frontend application, you can use the social login buttons to initiate the OAuth flow. The frontend should:

1. Redirect the user to the OAuth provider's login page
2. After successful authentication, receive the access token
3. Send the access token to the backend API
4. Receive and store the authentication token from the backend

## Troubleshooting

### Common Issues

1. **Incorrect Redirect URIs**: Ensure that the redirect URIs in your OAuth provider settings match exactly what your application is using.

2. **CORS Issues**: If you're experiencing CORS errors, check that your backend has the correct CORS settings for your frontend domain.

3. **Token Validation Errors**: Make sure the access tokens you're sending to the backend are valid and not expired.

4. **Environment Variables**: Double-check that all environment variables are correctly set on your server.

### Debugging

To enable more detailed debugging, you can temporarily set `DEBUG=True` in your Django settings and check the server logs for more information about authentication errors.

## Security Considerations

- Always use HTTPS for OAuth redirects and API calls
- Keep your client secrets and private keys secure
- Regularly rotate your OAuth credentials
- Implement proper token validation and expiration
- Consider implementing rate limiting for authentication endpoints
