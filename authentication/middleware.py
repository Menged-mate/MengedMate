class AuthenticationBypassMiddleware:
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.public_paths = [
            '/api/auth/register/',
            '/api/auth/verify-email/',
            '/api/auth/login/',
            '/api/auth/resend-verification/',
        ]

    def __call__(self, request):
        if any(request.path.startswith(path) for path in self.public_paths):
            request.META['BYPASS_AUTH'] = True
        
        response = self.get_response(request)
        return response
