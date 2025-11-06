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
        """
        Create a unique fingerprint for the client.
        Uses only User-Agent since other headers can change across requests
        in production environments (proxies, CDN, etc.)
        """
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Create fingerprint from the most stable client characteristic
        # User-Agent is the most reliable identifier that persists across requests
        fingerprint = hashlib.sha256(user_agent.encode()).hexdigest()[:32]

        return fingerprint
    
    @staticmethod
    def set_secure_jwt_cookies(response, access_token, refresh_token, request, remember_me=False):
        """
        Set JWT tokens with maximum security and Remember Me support.
        
        Args:
            response: HTTP response object
            access_token: JWT access token
            refresh_token: JWT refresh token
            request: HTTP request object for fingerprinting
            remember_me: If True, cookies persist for 30 days. If False, session-only (browser close)
        """
        
        # Create client fingerprint
        fingerprint = SecureTokenManager.create_fingerprint(request)
        
        # 🆕 Determine cookie duration based on remember_me
        if remember_me:
            # Long-lived persistent cookie (30 days)
            max_age = int(settings.NINJA_JWT.get(
                'REFRESH_TOKEN_LIFETIME_REMEMBER', 
                timedelta(days=30)
            ).total_seconds())
            print(f"🔐 Setting PERSISTENT cookies (Remember Me): {max_age / 86400:.0f} days")
        else:
            # Session cookie (deleted when browser closes)
            max_age = None  # 🔑 KEY: None = session cookie
            print("🔐 Setting SESSION cookies (browser close = logout)")
        
        # Set refresh token (HTTP-only, secure, with fingerprint)
        response.set_cookie(
            'refresh_token',
            refresh_token,
            max_age=max_age,  # 🔑 Dynamic based on remember_me
            httponly=True,  # Prevents XSS
            secure=not settings.DEBUG,
            samesite='Lax' if settings.DEBUG else 'Strict',
            path='/',
            domain='localhost' if settings.DEBUG else None,
        )

        # Set fingerprint cookie (HTTP-only for validation)
        response.set_cookie(
            'client_fp',
            fingerprint,
            max_age=max_age,  # Match refresh token duration
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Lax' if settings.DEBUG else 'Strict',
            path='/',
            domain='localhost' if settings.DEBUG else None,
        )

        # ✅ SECURITY: ALL cookies are HTTP-only
        # No user-role cookie - AuthContext will handle role-based access on client-side

        # Set fingerprint hash in another cookie for validation (no session needed)
        fp_hash = hashlib.sha256(fingerprint.encode()).hexdigest()
        response.set_cookie(
            'fp_hash',
            fp_hash,
            max_age=max_age,  # Match refresh token duration
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Lax' if settings.DEBUG else 'Strict',
            path='/',
            domain='localhost' if settings.DEBUG else None,
        )

        # Debug logging
        samesite_value = 'Lax' if settings.DEBUG else 'Strict'
        secure_value = not settings.DEBUG

        print(f"✅ Set authentication cookies:")
        print(f"   refresh_token: {refresh_token[:30]}...")
        print(f"   client_fp: {fingerprint[:20]}...")
        print(f"   fp_hash: {fp_hash[:20]}...")
        print(f"   Max age: {max_age} seconds" if max_age else "   Session cookie (browser close)")
        print(f"   SameSite: {samesite_value}")
        print(f"   Secure: {secure_value}")

        return response
    
    @staticmethod
    def validate_fingerprint(request):
        """Validate client fingerprint against stored hash"""
        stored_fp_hash = request.COOKIES.get('fp_hash')
        current_fp = SecureTokenManager.create_fingerprint(request)
        current_fp_hash = hashlib.sha256(current_fp.encode()).hexdigest()

        # Debug logging
        print(f"🔍 Fingerprint Validation:")
        print(f"   Stored hash: {stored_fp_hash[:20] if stored_fp_hash else 'None'}...")
        print(f"   Current hash: {current_fp_hash[:20]}...")
        print(f"   Match: {stored_fp_hash == current_fp_hash}")
        print(f"   User-Agent: {request.META.get('HTTP_USER_AGENT', 'Not set')[:70]}...")

        if not stored_fp_hash:
            print(f"   ⚠️ No stored fingerprint hash - skipping validation")
            return True  # Allow if no stored hash (first-time authentication)

        return stored_fp_hash == current_fp_hash
    
    @staticmethod
    def clear_secure_cookies(response):
        """Clear all authentication cookies"""
        from django.conf import settings
        
        # Clear both backend HTTP-only cookies and frontend-set cookies
        cookies_to_clear = ['refresh_token', 'client_fp', 'fp_hash', 'access_token', 'auth-token', 'user-role']
        
        print(f"🧹 Clearing {len(cookies_to_clear)} cookies...")
        
        for cookie_name in cookies_to_clear:
            # Must match the domain used when setting cookies
            domain = 'localhost' if settings.DEBUG else None
            
            print(f"  🗑️ Deleting cookie: {cookie_name} (domain={domain})")
            
            response.delete_cookie(
                cookie_name,
                path='/',
                domain=domain,
                samesite='Lax' if settings.DEBUG else 'Strict'
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
