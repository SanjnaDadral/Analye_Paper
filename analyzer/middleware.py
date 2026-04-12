import time
from django.http import JsonResponse


class RateLimitMiddleware:
    """Simple rate limiting middleware"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.requests = {}
        self.limit = 30
        self.window = 60
    
    def __call__(self, request):
        if request.path in ['/analyze/', '/contact/']:
            client_ip = self.get_client_ip(request)
            current_time = time.time()
            
            if client_ip not in self.requests:
                self.requests[client_ip] = []
            
            self.requests[client_ip] = [
                t for t in self.requests[client_ip]
                if current_time - t < self.window
            ]
            
            if len(self.requests[client_ip]) >= self.limit:
                return JsonResponse({
                    'success': False,
                    'error': 'Rate limit exceeded. Please try again later.'
                }, status=429)
            
            self.requests[client_ip].append(current_time)
        
        return self.get_response(request)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')


rate_limit_middleware = RateLimitMiddleware
