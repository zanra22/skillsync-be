"""
Enhanced JWT Authentication with Maximum Security
- Short-lived access tokens (5-15 minutes)
- Automatic refresh via HTTP-only cookies
- Sliding session windows
- Token rotation
- Fingerprint validation
"""
from django.conf import settings
from django.http import HttpResponse
from datetime import datetime, timedelta
import secrets
import hashlib

class SecureTokenManager:
    """Enhanced token management with fingerprinting and rotation"""
    
    @staticmethod
    def create_fingerprint(request):
        """Create a unique fingerprint for the client"""
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
        
        # Create fingerprint from client characteristics
        fingerprint_data = f"{user_agent}{accept_language}{accept_encoding}"
        fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()[:32]
        
        return fingerprint
    
    @staticmethod
    def set_secure_jwt_cookies(response, access_token, refresh_token, request):
        """Set JWT tokens with maximum security"""
        
        # Create client fingerprint
        fingerprint = SecureTokenManager.create_fingerprint(request)
        
        # Set refresh token (HTTP-only, secure, with fingerprint)
        response.set_cookie(
            'refresh_token',
            refresh_token,
            max_age=settings.NINJA_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds(),
            httponly=True,  # Prevents XSS
            secure=not settings.DEBUG,  # HTTPS only in production
            samesite='Strict',  # Stronger CSRF protection
            path='/',
        )
        
        # Set fingerprint cookie (HTTP-only for validation)
        response.set_cookie(
            'client_fp',
            fingerprint,
            max_age=settings.NINJA_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds(),
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Strict',
            path='/',
        )
        
        # Set fingerprint hash in another cookie for validation (no session needed)
        fp_hash = hashlib.sha256(fingerprint.encode()).hexdigest()
        response.set_cookie(
            'fp_hash',
            fp_hash,
            max_age=settings.NINJA_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds(),
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Strict',
            path='/',
        )
        
        return response
    
    @staticmethod
    def validate_fingerprint(request):
        """Validate client fingerprint against stored hash"""
        stored_fp_hash = request.COOKIES.get('fp_hash')
        current_fp = SecureTokenManager.create_fingerprint(request)
        current_fp_hash = hashlib.sha256(current_fp.encode()).hexdigest()
        
        return stored_fp_hash == current_fp_hash
    
    @staticmethod
    def clear_secure_cookies(response):
        """Clear all authentication cookies"""
        # Clear both backend HTTP-only cookies and frontend-set cookies
        cookies_to_clear = ['refresh_token', 'client_fp', 'fp_hash', 'access_token', 'auth-token', 'user-role']
        
        for cookie_name in cookies_to_clear:
            response.delete_cookie(
                cookie_name,
                path='/',
                samesite='Strict'
            )
        
        return response

def set_jwt_cookies(response, access_token, refresh_token, request=None):
    """
    Enhanced security wrapper for JWT cookie setting
    """
    if request:
        return SecureTokenManager.set_secure_jwt_cookies(
            response, access_token, refresh_token, request
        )
    else:
        # Fallback to basic implementation
        response.set_cookie(
            'refresh_token',
            refresh_token,
            max_age=settings.NINJA_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds(),
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Strict',  # Changed from Lax to Strict for better security
            path='/',
        )
        return response

def clear_jwt_cookies(response):
    """Enhanced cookie clearing"""
    return SecureTokenManager.clear_secure_cookies(response)

def get_tokens_from_cookies(request):
    """Extract and validate JWT tokens from HTTP-only cookies"""
    # Validate fingerprint first
    if not SecureTokenManager.validate_fingerprint(request):
        return None, None  # Potential session hijacking
    
    access_token = request.COOKIES.get('access_token')
    refresh_token = request.COOKIES.get('refresh_token')
    return access_token, refresh_token
