class AuthenticationBypassMiddleware:
    """
    Middleware to bypass authentication for specific endpoints.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Endpoints that don't require authentication
        self.public_paths = [
            '/api/auth/register/',
            '/api/auth/verify-email/',
            '/api/auth/login/',
            '/api/auth/resend-verification/',
        ]

    def __call__(self, request):
        # Check if the path is in the public paths
        if any(request.path.startswith(path) for path in self.public_paths):
            # Set a flag to indicate that this request should bypass authentication
            request.META['BYPASS_AUTH'] = True
        
        response = self.get_response(request)
        return response
