"""
Rate Limiting Middleware for Enhanced Security
Prevents brute force attacks and API abuse
"""
import time
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings
import hashlib

class RateLimitMiddleware:
    """
    Rate limiting middleware to prevent abuse
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Check rate limit before processing request
        if self.is_rate_limited(request):
            return JsonResponse({
                'error': 'Rate limit exceeded. Please try again later.',
                'retry_after': 300  # 5 minutes
            }, status=429)
            
        response = self.get_response(request)
        return response
    
    def is_rate_limited(self, request):
        """Check if the request should be rate limited"""
        
        # Only rate limit authentication endpoints
        if not self.is_auth_endpoint(request):
            return False
            
        # Get client identifier
        client_id = self.get_client_identifier(request)
        
        # Different limits for different endpoints
        if 'login' in request.path.lower():
            return self.check_login_rate_limit(client_id)
        elif 'refresh' in request.path.lower():
            return self.check_refresh_rate_limit(client_id)
        elif 'password' in request.path.lower():
            return self.check_password_rate_limit(client_id)
            
        return False
    
    def is_auth_endpoint(self, request):
        """Check if this is an authentication endpoint"""
        auth_paths = ['/graphql/', '/auth/', '/api/auth/']
        return any(path in request.path for path in auth_paths)
    
    def get_client_identifier(self, request):
        """Get a unique identifier for the client"""
        # Use IP address and User-Agent for identification
        ip = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Create hash for privacy
        identifier = f"{ip}:{user_agent}"
        return hashlib.sha256(identifier.encode()).hexdigest()[:16]
    
    def get_client_ip(self, request):
        """Get the real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def check_login_rate_limit(self, client_id):
        """Check login attempt rate limit"""
        key = f"login_attempts:{client_id}"
        attempts = cache.get(key, 0)
        
        # Allow 5 attempts per 5 minutes
        if attempts >= 5:
            return True
            
        # Increment counter
        cache.set(key, attempts + 1, 300)  # 5 minutes
        return False
    
    def check_refresh_rate_limit(self, client_id):
        """Check token refresh rate limit"""
        key = f"refresh_attempts:{client_id}"
        attempts = cache.get(key, 0)
        
        # Allow 20 refresh attempts per minute
        if attempts >= 20:
            return True
            
        cache.set(key, attempts + 1, 60)  # 1 minute
        return False
    
    def check_password_rate_limit(self, client_id):
        """Check password reset rate limit"""
        key = f"password_attempts:{client_id}"
        attempts = cache.get(key, 0)
        
        # Allow 3 password reset attempts per hour
        if attempts >= 3:
            return True
            
        cache.set(key, attempts + 1, 3600)  # 1 hour
        return False

class SecurityHeadersMiddleware:
    """
    Add security headers to all responses
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Add CSP header for API endpoints
        if request.path.startswith('/api/') or request.path.startswith('/graphql/'):
            response['Content-Security-Policy'] = "default-src 'none'; script-src 'none';"
        
        return response

class RequestLoggingMiddleware:
    """
    Log suspicious authentication attempts
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Log authentication attempts
        if self.is_auth_request(request):
            self.log_auth_attempt(request)
            
        response = self.get_response(request)
        
        # Log failed authentication
        if response.status_code in [401, 403, 429]:
            self.log_failed_auth(request, response.status_code)
            
        return response
    
    def is_auth_request(self, request):
        """Check if this is an auth request"""
        return ('login' in request.path.lower() or 
                'refresh' in request.path.lower() or
                'password' in request.path.lower())
    
    def log_auth_attempt(self, request):
        """Log authentication attempt"""
        ip = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # In production, you'd use proper logging
        print(f"Auth attempt from {ip} - {user_agent[:50]}")
    
    def log_failed_auth(self, request, status_code):
        """Log failed authentication"""
        ip = self.get_client_ip(request)
        print(f"Failed auth ({status_code}) from {ip}")
    
    def get_client_ip(self, request):
        """Get client IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
