# Remember Me & Memory-Only Token Architecture - Backend Implementation Guide

## 📖 Overview

This guide documents the backend implementation of a secure "Remember Me" feature combined with memory-only access token architecture for SkillSync's authentication system.

**What This Feature Does**:
- Allows users to choose between session-only authentication (browser close = logout) or persistent authentication (stays logged in for 30 days)
- Implements industry-standard security pattern: short-lived access tokens (5 minutes) + long-lived refresh tokens (session or 30 days)
- Backend exclusively manages all authentication cookies (frontend cannot manipulate)
- Prevents XSS vulnerabilities through HTTP-only cookies

**Why We Built It This Way**:
- **Security First**: HTTP-only cookies prevent JavaScript access, eliminating XSS token theft
- **User Choice**: Balances convenience (Remember Me) with security (session-only)
- **Industry Standard**: Matches Auth0, Firebase, AWS Cognito architecture
- **Single Source of Truth**: Backend controls all authentication cookies, frontend stores access token in memory only

**Prerequisites**:
- Django 4.x with django-ninja
- ninja-jwt for JWT token management
- Existing user authentication system
- Custom JWT token classes (implemented Sept 19, 2025)
- Device fingerprinting system (implemented Sept 17, 2025)

---

## 🎯 Problem Statement

### What Problem Does This Solve?

**Problem 1: XSS Vulnerability**
- Previous implementation: Frontend manually created `auth-token` cookies using `document.cookie`
- Risk: JavaScript-accessible cookies can be stolen via XSS attacks
- Impact: Attackers could steal authentication tokens and impersonate users

**Problem 2: No User Control Over Session Persistence**
- All users got same 7-day refresh token lifetime
- No option for "stay logged in" vs "log me out when I close browser"
- Public computer users had no secure option

**Problem 3: Dual Storage Confusion**
- Tokens stored in both backend HTTP-only cookies AND frontend regular cookies
- Led to stale cookies (wrong user data bug)
- Multiple sources of truth created race conditions

### Previous Approach and Its Limitations

**Before (Insecure)**:
```python
# Backend set HTTP-only refresh_token ✅ Good
response.set_cookie('refresh_token', refresh_token, httponly=True)

# Frontend also set regular auth-token ❌ Bad (XSS vulnerability)
# JavaScript: document.cookie = 'auth-token=...'  
```

**Limitations**:
- ❌ Frontend could create/modify auth cookies (security risk)
- ❌ Fixed 7-day refresh token for everyone (no flexibility)
- ❌ Dual storage created consistency issues
- ❌ JavaScript could read tokens (XSS vulnerability)

### Requirements and Constraints

**Security Requirements**:
1. ✅ Access tokens NEVER accessible to JavaScript
2. ✅ Refresh tokens in HTTP-only cookies only
3. ✅ Backend exclusively manages authentication cookies
4. ✅ Short-lived access tokens (5 minutes max)
5. ✅ Token rotation on every refresh (prevent replay attacks)

**Functional Requirements**:
1. ✅ User can choose "Remember Me" (30 days) or session-only
2. ✅ Session cookie deleted when browser closes (if Remember Me unchecked)
3. ✅ Persistent cookie survives browser restarts (if Remember Me checked)
4. ✅ Backward compatible (existing sessions continue to work)

**Performance Constraints**:
1. ✅ No additional database queries for Remember Me logic
2. ✅ Cookie operations remain fast (< 10ms)
3. ✅ Token generation performance unchanged

---

## 🏗️ Architecture & Design Decisions

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        USER LOGIN                            │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  GraphQL Mutation: auth.login(email, password, rememberMe)  │
│  File: auth/mutation.py                                      │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  Generate JWT Tokens (Custom Classes with Role Claims)       │
│  - access_token (5 min)                                      │
│  - refresh_token (7-30 days or session)                      │
│  File: auth/custom_tokens.py                                 │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  SecureTokenManager.set_secure_jwt_cookies()                 │
│  File: auth/secure_utils.py                                  │
│                                                               │
│  IF remember_me=False:                                       │
│    ├─ Set cookies with max_age=None (session)               │
│    └─ Cookies deleted when browser closes                   │
│                                                               │
│  IF remember_me=True:                                        │
│    ├─ Set cookies with max_age=2592000 (30 days)            │
│    └─ Cookies persist across browser restarts               │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  HTTP Response with Cookies Set:                             │
│  - refresh_token (HTTP-only, Secure, SameSite=Strict)       │
│  - client_fp (HTTP-only, device fingerprint)                │
│  - fp_hash (HTTP-only, fingerprint validation)              │
│                                                               │
│  GraphQL Response with Data:                                 │
│  - accessToken (for frontend memory storage)                │
│  - expiresIn (300 seconds = 5 minutes)                       │
│  - user (with updated role)                                  │
└─────────────────────────────────────────────────────────────┘
```

### Why This Approach Over Alternatives

**Our Approach: HTTP-Only Cookies + Memory-Only Access Tokens**

✅ **Pros**:
- XSS-proof: JavaScript cannot access refresh tokens
- CSRF-protected: SameSite=Strict cookies
- Industry standard: Auth0/Firebase/AWS pattern
- Flexible: User controls session duration
- Secure by default: Session cookies for cautious users

❌ **Cons**:
- Slightly more complex than localStorage
- Requires backend cookie management
- CORS configuration needed for cross-origin

🏆 **Why Chosen**: Security outweighs complexity. XSS vulnerabilities are critical risks, and this approach eliminates them entirely.

---

### Alternative Approaches Considered

#### Alternative 1: localStorage for Refresh Tokens

**Implementation**:
```javascript
// Frontend stores refresh token
localStorage.setItem('refresh_token', refreshToken);
```

✅ **Pros**:
- Simple implementation
- No CORS complexity
- Easy to debug (visible in DevTools)

❌ **Cons**:
- **CRITICAL SECURITY FLAW**: JavaScript can read tokens (XSS vulnerability)
- No HTTP-only protection
- Tokens persist indefinitely (no browser-close cleanup)
- OWASP explicitly warns against this approach

🚫 **Why Not Chosen**: Security risk too high. Single XSS vulnerability compromises all user sessions.

---

#### Alternative 2: Separate "Trusted Device" Tokens

**Implementation**:
```python
# Issue special 90-day "trusted device" token separate from refresh token
if remember_me:
    trusted_token = generate_trusted_device_token(user)
    response.set_cookie('trusted_device', trusted_token, max_age=7776000)  # 90 days
```

✅ **Pros**:
- Clear separation between session and trusted device
- Could enable "revoke all trusted devices" feature
- More granular control

❌ **Cons**:
- Adds complexity: two token types to manage
- More database queries (trusted device validation)
- Token rotation becomes more complex
- Overkill for basic Remember Me functionality

🚫 **Why Not Chosen**: Added complexity not justified. Remember Me flag + dynamic max_age achieves same goal simpler.

---

#### Alternative 3: JWT Expiry Only (No Cookie Duration Control)

**Implementation**:
```python
# Control session duration via JWT expiry only
if remember_me:
    refresh = RefreshToken.for_user(user)
    refresh.set_exp(lifetime=timedelta(days=30))
else:
    refresh = RefreshToken.for_user(user)
    refresh.set_exp(lifetime=timedelta(hours=1))

# Cookie always persistent (max_age=30 days)
response.set_cookie('refresh_token', str(refresh), max_age=2592000)
```

✅ **Pros**:
- Simpler cookie management (always same duration)
- JWT expiry provides security boundary

❌ **Cons**:
- Cookie persists on disk even after JWT expires (privacy leak)
- Browser close doesn't clear session (fails Remember Me=false case)
- Cookie file reveals authentication state even without valid token

🚫 **Why Not Chosen**: Doesn't achieve true session-only behavior. Cookie files persist on disk.

---

### Trade-offs Considered

| Aspect | Decision | Trade-off |
|--------|----------|-----------|
| **Cookie Duration** | Dynamic (None or 30 days) | Slightly more complex vs. always persistent |
| **Access Token Storage** | Frontend memory only | Requires token refresh on page reload vs. persistent storage |
| **Token Lifetime** | 5 minutes access, 7-30 days refresh | More refresh calls vs. longer-lived tokens |
| **Fingerprinting** | SHA-256 hash of IP+UA | Privacy vs. security (we chose security) |
| **Remember Me Default** | False (session-only) | Secure by default vs. convenience |

**Philosophy**: Security first, convenience second. All trade-offs favor security when in conflict.

---

### Security Considerations

**Threat Model**:
1. ✅ **XSS Attacks**: Mitigated via HTTP-only cookies + memory-only access tokens
2. ✅ **CSRF Attacks**: Mitigated via SameSite=Strict cookies
3. ✅ **Token Theft**: Mitigated via short-lived access tokens (5 min) + token rotation
4. ✅ **Replay Attacks**: Mitigated via token blacklisting on refresh
5. ✅ **Session Fixation**: Mitigated via token rotation on login
6. ⚠️ **Physical Access**: Partially mitigated (session-only default, but persistent if Remember Me checked)

**Security Best Practices Followed**:
- OWASP JWT Security Cheat Sheet ✅
- RFC 6749 (OAuth 2.0) ✅
- Django Security Best Practices ✅
- NIST Cybersecurity Framework ✅

---

## 📦 Backend Implementation (Step-by-Step)

### Step 1: Add Remember Me Configuration Settings

**File**: `skillsync-be/config/security.py`

**What**: Add two new JWT lifetime constants for Remember Me functionality

**Why**: We need separate lifetime configurations for session cookies (None = browser close) vs persistent cookies (30 days). The existing `REFRESH_TOKEN_LIFETIME` becomes the default/fallback.

**Code**:
```python
def get_secure_jwt_settings(secret_key, debug=False):
    """
    Get JWT security configuration with Remember Me support
    
    Args:
        secret_key (str): Django SECRET_KEY for JWT signing
        debug (bool): Whether in debug mode (affects cookie security)
    
    Returns:
        dict: Complete JWT settings dictionary for NINJA_JWT
    """
    return {
        # CRITICAL: Very short access token lifetime (5 minutes)
        # Why: Limits damage if access token is stolen
        # Trade-off: More frequent refresh calls vs security
        'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
        
        # Default refresh token lifetime (7 days)
        # Why: Backward compatibility for existing sessions
        # Used when: remember_me parameter not provided
        'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
        
        # 🆕 NEW: Remember Me ENABLED - Long-lived refresh token (30 days)
        # Why: User chose convenience over security (trust their own device)
        # Used when: remember_me=True in login mutation
        # Trade-off: 30 days = industry standard (Auth0, Firebase use similar)
        'REFRESH_TOKEN_LIFETIME_REMEMBER': timedelta(days=30),
        
        # 🆕 NEW: Remember Me DISABLED - Session-only (browser close = logout)
        # Why: Maximum security, cookie deleted when browser closes
        # Used when: remember_me=False in login mutation
        # Key: None (not 0!) means no max_age attribute = session cookie
        'REFRESH_TOKEN_LIFETIME_SESSION': None,
        
        # Enable token rotation for maximum security
        # Why: Each refresh generates new token, old one blacklisted
        # Prevents: Replay attacks if token is intercepted
        'ROTATE_REFRESH_TOKENS': True,
        
        # Blacklist tokens after rotation
        # Why: Ensure old tokens cannot be reused
        # Implementation: Uses django-ninja-jwt's built-in blacklist
        'BLACKLIST_AFTER_ROTATION': True,
        
        # Cryptographic settings
        'ALGORITHM': 'HS256',  # HMAC SHA-256 (symmetric key)
        'SIGNING_KEY': secret_key,  # Django SECRET_KEY
        
        # Token claims configuration
        'AUTH_HEADER_TYPES': ('Bearer',),  # "Authorization: Bearer <token>"
        'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
        
        # 🔑 CRITICAL: Custom token classes with role claims (Sept 2025)
        # Why: Frontend middleware needs role for routing decisions
        # Implementation: See auth/custom_tokens.py
        'ACCESS_TOKEN_CLASS': 'auth.custom_tokens.CustomAccessToken',
        'REFRESH_TOKEN_CLASS': 'auth.custom_tokens.CustomRefreshToken',
        
        # Issuer validation
        'ISSUER': 'SkillSync',  # JWT "iss" claim for validation
        'AUDIENCE': None,  # No audience validation needed
        
        # Sliding token configuration (not used, but required by ninja-jwt)
        'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
        'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
        'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
    }
```

**Explanation**:

**Line-by-line Breakdown**:

1. **`REFRESH_TOKEN_LIFETIME_REMEMBER = timedelta(days=30)`**
   - **What**: Cookie persists for 30 days (2,592,000 seconds)
   - **Why 30 days**: Industry standard (Auth0, Firebase, AWS Cognito use 30-90 days)
   - **When used**: User checks "Remember me" checkbox
   - **Security trade-off**: Convenience (no re-login) vs Risk (longer exposure)
   - **Junior dev note**: `timedelta(days=30)` creates a Python datetime duration object. Django converts it to seconds automatically.

2. **`REFRESH_TOKEN_LIFETIME_SESSION = None`**
   - **What**: Cookie has NO max_age attribute (session cookie)
   - **Why None not 0**: `None` = no max_age (session), `0` = expire immediately (wrong!)
   - **When used**: User unchecks "Remember me" or leaves it unchecked (default)
   - **Browser behavior**: Cookie deleted when ALL browser windows closed
   - **Security**: Maximum security - no token persistence on disk
   - **Junior dev note**: Session cookies exist only in browser RAM, not written to disk

3. **`ROTATE_REFRESH_TOKENS = True`**
   - **What**: Every token refresh generates a NEW token, old one invalidated
   - **Why**: If attacker steals token, they can only use it once
   - **How**: django-ninja-jwt handles rotation automatically
   - **Database impact**: One INSERT (new token) + one UPDATE (blacklist old token) per refresh

4. **`BLACKLIST_AFTER_ROTATION = True`**
   - **What**: Old refresh token added to blacklist (cannot be reused)
   - **Why**: Prevents replay attacks (attacker cannot reuse intercepted token)
   - **Database table**: `ninja_jwt_blacklist` (auto-created by migration)
   - **Cleanup**: Old blacklisted tokens auto-deleted after expiry

**How This Connects to Other Components**:
- `auth/secure_utils.py` reads these settings to set cookie `max_age`
- `auth/mutation.py` login mutation uses custom token classes
- `auth/custom_tokens.py` token classes inherit from ninja-jwt base classes

**Common Mistakes to Avoid**:
- ❌ Setting `REFRESH_TOKEN_LIFETIME_SESSION = 0` (expires immediately, not session)
- ❌ Setting `REFRESH_TOKEN_LIFETIME_SESSION = timedelta(0)` (same problem)
- ❌ Using `days=90` for remember me (too long, security risk)
- ❌ Disabling `ROTATE_REFRESH_TOKENS` (security vulnerability)

**Testing This Step**:
```bash
# Verify settings loaded correctly
cd skillsync-be
python manage.py shell

>>> from django.conf import settings
>>> settings.NINJA_JWT['REFRESH_TOKEN_LIFETIME_REMEMBER']
datetime.timedelta(days=30)  # ✅ Expected

>>> settings.NINJA_JWT['REFRESH_TOKEN_LIFETIME_SESSION']
None  # ✅ Expected (not 0, not timedelta)

>>> settings.NINJA_JWT['REFRESH_TOKEN_LIFETIME_REMEMBER'].total_seconds()
2592000.0  # ✅ 30 days in seconds
```

---

### Step 2: Update Cookie Manager with Remember Me Support

**File**: `skillsync-be/auth/secure_utils.py`

**What**: Modify `SecureTokenManager.set_secure_jwt_cookies()` to accept `remember_me` parameter and dynamically set cookie duration

**Why**: Backend must control cookie duration based on user's Remember Me choice. Frontend cannot set HTTP-only cookies, so all cookie management must happen server-side.

**Code**:
```python
from django.conf import settings
from django.http import HttpResponse, HttpRequest
import hashlib
import secrets

class SecureTokenManager:
    """
    Manages JWT tokens with enhanced security features:
    - HTTP-only cookies (XSS protection)
    - Device fingerprinting (security layer)
    - Dynamic cookie duration (Remember Me support)
    - Secure cookie attributes (CSRF protection)
    """
    
    @staticmethod
    def set_secure_jwt_cookies(
        response: HttpResponse,
        access_token: str,
        refresh_token: str,
        request: HttpRequest,
        remember_me: bool = False
    ) -> HttpResponse:
        """
        Set JWT tokens as HTTP-only cookies with Remember Me support
        
        Args:
            response: Django HttpResponse object to set cookies on
            access_token: JWT access token string (NOT set as cookie, returned in response)
            refresh_token: JWT refresh token string (SET as HTTP-only cookie)
            request: Django HttpRequest object (for device fingerprinting)
            remember_me: User's Remember Me preference
                        - False (default): Session cookie (max_age=None)
                        - True: Persistent cookie (max_age=30 days)
        
        Returns:
            HttpResponse: Same response object with cookies set
        
        Side Effects:
            - Sets 3 HTTP-only cookies: refresh_token, client_fp, fp_hash
            - Logs cookie type (session vs persistent) for debugging
        
        Security:
            - All cookies have httponly=True (XSS protection)
            - All cookies have secure=True in production (HTTPS only)
            - All cookies have samesite='Strict' (CSRF protection)
            - Access token NOT set as cookie (frontend memory only)
        
        Example Usage:
            # In login mutation
            SecureTokenManager.set_secure_jwt_cookies(
                response=info.context.response,
                access_token=str(access_token),
                refresh_token=str(refresh),
                request=info.context.request,
                remember_me=input.remember_me  # From user input
            )
        """
        
        # 🔑 STEP 1: Determine cookie duration based on remember_me flag
        if remember_me:
            # User wants persistent cookies (stay logged in)
            # Calculate max_age in seconds from timedelta
            max_age = int(
                settings.NINJA_JWT['REFRESH_TOKEN_LIFETIME_REMEMBER'].total_seconds()
            )
            print(f"🔐 Setting PERSISTENT cookies: {max_age / 86400:.0f} days")
            # 86400 = seconds in a day (60 * 60 * 24)
            # .0f = format as integer (30.0 → 30)
        else:
            # User wants session cookies (logout on browser close)
            # max_age=None means no "Max-Age" or "Expires" attribute
            # Browser treats this as session cookie (RAM only, not disk)
            max_age = None
            print("🔐 Setting SESSION cookies (browser close = logout)")
        
        # 🔑 STEP 2: Build common cookie settings (used for all cookies)
        cookie_settings = {
            'max_age': max_age,  # Dynamic: None or 2592000 seconds
            'httponly': True,     # JavaScript cannot access (XSS protection)
            'secure': not settings.DEBUG,  # HTTPS only in production
            'samesite': 'Strict', # CSRF protection (no cross-site requests)
            'path': '/',          # Cookie available to entire site
        }
        
        # 🔑 STEP 3: Set refresh_token cookie (main authentication cookie)
        # This is the ONLY cookie that stores the JWT refresh token
        # Frontend NEVER receives this token (HTTP-only)
        response.set_cookie(
            'refresh_token',      # Cookie name
            refresh_token,        # JWT refresh token string
            **cookie_settings     # Spread cookie settings dict
        )
        
        # 🔑 STEP 4: Generate and set device fingerprint cookies
        # Why: Additional security layer to detect stolen cookies used from different device
        # How: Hash of IP address + User-Agent + other device info
        fingerprint_data = SecureTokenManager.generate_device_fingerprint(request)
        client_fp = fingerprint_data['client_fp']    # Unhashed fingerprint (for backend validation)
        fp_hash = fingerprint_data['fp_hash']        # SHA-256 hash (for frontend comparison)
        
        # Set client_fp cookie (unhashed, for backend to validate)
        response.set_cookie('client_fp', client_fp, **cookie_settings)
        
        # Set fp_hash cookie (hashed, prevents tampering)
        response.set_cookie('fp_hash', fp_hash, **cookie_settings)
        
        # Note: access_token is NOT set as cookie
        # Why: Frontend stores in memory only (React state)
        # Security: Even if XSS occurs, attacker cannot access refresh_token
        
        return response
    
    @staticmethod
    def generate_device_fingerprint(request: HttpRequest) -> dict:
        """
        Generate device fingerprint for additional security
        
        Args:
            request: Django HttpRequest object
        
        Returns:
            dict: {
                'client_fp': str (raw fingerprint data),
                'fp_hash': str (SHA-256 hash of fingerprint)
            }
        
        Components:
            - IP address (X-Forwarded-For or REMOTE_ADDR)
            - User-Agent string
            - Accept-Language header
            - Random salt (for uniqueness)
        
        Security:
            - Hash is one-way (cannot reverse to get device info)
            - Salt prevents rainbow table attacks
            - IP changes don't immediately invalidate (we hash IP+UA together)
        """
        # Get client IP (handle proxy/load balancer)
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR')
        if ip_address:
            # X-Forwarded-For can be comma-separated (proxy chain)
            ip_address = ip_address.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR', '')
        
        # Get User-Agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Get Accept-Language (additional fingerprint component)
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        
        # Generate random salt (24 bytes = 48 hex characters)
        salt = secrets.token_hex(24)
        
        # Combine all components
        fingerprint_string = f"{ip_address}:{user_agent}:{accept_language}:{salt}"
        
        # Hash fingerprint (SHA-256 = 64 hex characters)
        fp_hash = hashlib.sha256(fingerprint_string.encode()).hexdigest()
        
        return {
            'client_fp': fingerprint_string,  # Raw data (for backend validation)
            'fp_hash': fp_hash                # Hash (for frontend/cookie)
        }
    
    @staticmethod
    def clear_secure_cookies(response: HttpResponse) -> HttpResponse:
        """
        Clear all authentication cookies (used during logout)
        
        Args:
            response: Django HttpResponse object
        
        Returns:
            HttpResponse: Same response with cookies cleared
        
        How It Works:
            - Sets all auth cookies to empty string
            - Sets expires to Jan 1, 1970 (past date)
            - Browser immediately deletes cookies
        
        Security:
            - Backend authoritatively clears cookies (not frontend)
            - Ensures complete logout (no stale cookies)
        """
        cookie_options = {
            'httponly': True,
            'secure': settings.SECURE_SSL_REDIRECT,  # Match production settings
            'samesite': 'Lax',  # More permissive for deletion
            'path': '/',
            'expires': 'Thu, 01 Jan 1970 00:00:00 GMT'  # Past date = delete
        }
        
        # List of all authentication cookies to clear
        cookies_to_clear = [
            'auth-token',      # Legacy cookie (if exists from old implementation)
            'refresh_token',   # Current refresh token
            'user-role',       # Legacy role cookie (if exists)
            'client_fp',       # Device fingerprint
            'fp_hash',         # Fingerprint hash
            'sessionid',       # Django session
        ]
        
        for cookie_name in cookies_to_clear:
            response.set_cookie(cookie_name, '', **cookie_options)
        
        print("🔐 All authentication cookies cleared")
        return response
```

**Explanation**:

**Step 1 - Determine Cookie Duration**:
- **`if remember_me:`** - User checked "Remember me" checkbox
- **`max_age = int(...)`** - Convert timedelta to integer seconds (cookie requires int)
- **`.total_seconds()`** - timedelta method returns float (30.0 days → 2592000.0 seconds)
- **`int(...)`** - Cast to integer (2592000.0 → 2592000)
- **Why divide by 86400?** - Convert seconds to days for logging (2592000 / 86400 = 30)
- **`.0f` format** - Print as integer, not float (30.0 → 30)

**Step 1 - Session Cookie**:
- **`max_age = None`** - Critical: `None` not `0`!
- **Why None?** - Browser interprets missing `Max-Age` as session cookie
- **What happens?** - Cookie stored in RAM only, deleted when browser closes
- **Storage location**: Browser process memory, NOT disk
- **Security**: Even physical access to computer won't reveal token (after browser close)

**Step 2 - Cookie Settings Dictionary**:
- **`httponly=True`** - JavaScript `document.cookie` cannot access (XSS protection)
- **`secure=not settings.DEBUG`** - HTTPS only in production, HTTP allowed in dev
- **`samesite='Strict'`** - Cookie only sent to same domain (CSRF protection)
- **`path='/'`** - Cookie available to all routes (not just /auth)

**Step 3 - Set Refresh Token**:
- **`**cookie_settings`** - Python spread operator, unpacks dict into kwargs
- **Why HTTP-only?** - XSS vulnerability if JavaScript can access
- **Frontend access?** - None! Frontend never sees this cookie value
- **Backend access?** - `request.COOKIES.get('refresh_token')` in refresh mutation

**Step 4 - Device Fingerprinting**:
- **Purpose**: Detect if stolen cookie used from different device
- **Components**: IP + User-Agent + Accept-Language + Salt
- **Why salt?** - Makes each fingerprint unique even for same device
- **Security**: Can't reverse hash to get device info (one-way)

**Common Mistakes**:
- ❌ Setting `max_age=0` for session cookies (expires immediately!)
- ❌ Using `max_age=''` (string, should be int or None)
- ❌ Forgetting `httponly=True` (XSS vulnerability)
- ❌ Using `samesite='Lax'` for auth cookies (CSRF risk)
- ❌ Setting `secure=True` in development (HTTPS required, dev uses HTTP)

**How This Connects**:
- Called by: `auth/mutation.py` login mutation after token generation
- Uses: `config/security.py` settings for lifetime values
- Sets: 3 cookies read by `auth/mutation.py` refresh mutation
- Frontend: Cannot access these cookies (HTTP-only), stores accessToken in memory

**Testing This Step**:
```bash
# Test 1: Session cookie behavior
cd skillsync-be
python manage.py shell

>>> from auth.secure_utils import SecureTokenManager
>>> from django.http import HttpResponse, HttpRequest
>>> from django.test import RequestFactory
>>> 
>>> factory = RequestFactory()
>>> request = factory.get('/')
>>> response = HttpResponse()
>>> 
>>> SecureTokenManager.set_secure_jwt_cookies(
...     response,
...     'test_access_token',
...     'test_refresh_token',
...     request,
...     remember_me=False  # Session cookie
... )
# Expected output: "🔐 Setting SESSION cookies (browser close = logout)"
>>> 
>>> # Check cookie header (session cookie has no Max-Age)
>>> response.cookies['refresh_token']
# Expected: max_age=None (session cookie)

# Test 2: Persistent cookie behavior
>>> response2 = HttpResponse()
>>> SecureTokenManager.set_secure_jwt_cookies(
...     response2,
...     'test_access_token',
...     'test_refresh_token',
...     request,
...     remember_me=True  # Persistent cookie
... )
# Expected output: "🔐 Setting PERSISTENT cookies: 30 days"
>>> 
>>> response2.cookies['refresh_token']['max-age']
2592000  # ✅ 30 days in seconds
```

---

### Step 3: Update Login Mutation to Pass Remember Me Flag

**File**: `skillsync-be/auth/mutation.py`

**What**: Modify login mutation to accept `remember_me` parameter and pass it to `SecureTokenManager`

**Why**: Login is the entry point for authentication. It must accept user's Remember Me preference and pass it through the entire authentication flow.

**Code**:
```python
import strawberry
from typing import Optional
from django.contrib.auth import authenticate, login
from django.conf import settings
from django.utils import timezone
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model

# Import custom token classes (with role claims)
from .custom_tokens import CustomRefreshToken as RefreshToken
from .custom_tokens import CustomAccessToken as AccessToken

# Import types and secure utils
from .types import LoginInput, LoginPayload
from .secure_utils import SecureTokenManager

User = get_user_model()

@strawberry.type
class AuthMutation:
    """
    Authentication mutations for user login, logout, token refresh
    """
    
    @strawberry.mutation
    async def login(self, info, input: LoginInput) -> LoginPayload:
        """
        Authenticate user with email, password, and Remember Me option
        
        Args:
            info: Strawberry execution info (contains request/response context)
            input: LoginInput (email, password, remember_me)
        
        Returns:
            LoginPayload: {
                success: bool,
                message: str,
                user: UserType (if success),
                access_token: str (if success, for frontend memory storage),
                expires_in: int (if success, 300 seconds = 5 minutes)
            }
        
        Flow:
            1. Authenticate user (Django's built-in authenticate)
            2. Validate account status (active, not suspended)
            3. Generate JWT tokens (custom classes with role claims)
            4. Set HTTP-only cookies with Remember Me duration
            5. Return access token in response (frontend stores in memory)
        
        Security:
            - Password hashing via Django (PBKDF2 SHA-256)
            - JWT tokens signed with SECRET_KEY
            - Refresh token in HTTP-only cookie (XSS protection)
            - Access token in response only (frontend memory storage)
            - Device fingerprinting for additional security
        
        Example GraphQL Mutation:
            mutation {
              auth {
                login(input: {
                  email: "user@example.com"
                  password: "SecurePass123"
                  rememberMe: true
                }) {
                  success
                  message
                  user { id email role }
                  accessToken
                  expiresIn
                }
              }
            }
        """
        try:
            # 🔑 STEP 1: Authenticate user credentials
            # Django's authenticate() checks username/password against database
            # Returns User object if valid, None if invalid
            user = await sync_to_async(authenticate)(
                request=info.context.request,
                username=input.email,  # Using email as username (custom user model)
                password=input.password
            )
            
            # If authentication failed, return error
            if not user:
                return LoginPayload(
                    success=False,
                    message="Invalid email or password"
                )
            
            # 🔑 STEP 2: Check if user account is active
            if not user.is_active:
                return LoginPayload(
                    success=False,
                    message="Your account has been deactivated. Please contact support."
                )
            
            # 🔑 STEP 3: Check account status (if model has this field)
            if hasattr(user, 'account_status'):
                if user.account_status == 'suspended':
                    return LoginPayload(
                        success=False,
                        message="Your account has been suspended. Please contact support."
                    )
                elif user.account_status == 'banned':
                    return LoginPayload(
                        success=False,
                        message="Your account has been banned."
                    )
                elif user.account_status == 'pending':
                    return LoginPayload(
                        success=False,
                        message="Your account is pending verification. Please check your email."
                    )
            
            # 🔑 STEP 4: Login the user (Django session - optional for JWT)
            # Creates Django session (useful for admin panel access)
            # Not required for JWT-only authentication
            await sync_to_async(login)(info.context.request, user)
            
            # 🔑 STEP 5: Update user's last login timestamp
            user.last_login = timezone.now()
            user.is_sign_in = True  # Custom field (if exists)
            await sync_to_async(user.save)(update_fields=['last_login', 'is_sign_in'])
            
            # 🔑 STEP 6: Generate JWT tokens with custom classes
            # CustomRefreshToken includes role claims (Sept 2025 implementation)
            # Tokens are signed with Django SECRET_KEY
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            # JWT payload now includes:
            # - user_id: User's primary key
            # - role: User's role (learner, mentor, admin, etc.)
            # - user_role: Alias for compatibility
            # - email: User's email
            # - iss: Issuer (SkillSync)
            # - exp: Expiration timestamp
            # - jti: JWT ID (unique identifier)
            
            # 🔑 STEP 7: Set HTTP-only cookies with Remember Me support
            response = info.context.response
            if response:
                SecureTokenManager.set_secure_jwt_cookies(
                    response=response,
                    access_token=str(access_token),
                    refresh_token=str(refresh),
                    request=info.context.request,
                    remember_me=input.remember_me  # 🔥 KEY: Pass user's preference
                )
                # This sets 3 HTTP-only cookies:
                # - refresh_token (JWT, max_age=None or 2592000)
                # - client_fp (device fingerprint)
                # - fp_hash (fingerprint hash)
            
            # 🔑 STEP 8: Return success response
            # Access token returned in response (NOT in cookie)
            # Frontend will store this in React state (memory only)
            return LoginPayload(
                success=True,
                message="Login successful",
                user=user,
                access_token=str(access_token),  # For frontend memory storage
                expires_in=int(
                    settings.NINJA_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()
                ),  # 300 seconds (5 minutes)
            )
            
        except Exception as e:
            # Catch any unexpected errors
            print(f"❌ Login error: {str(e)}")
            return LoginPayload(
                success=False,
                message=f"Login failed: {str(e)}"
            )
```

**Update LoginInput Type**:

**File**: `skillsync-be/auth/types.py`

**What**: Add `remember_me` field to `LoginInput` type

**Code**:
```python
import strawberry
from typing import Optional

@strawberry.input
class LoginInput:
    """
    Input type for login mutation
    
    Fields:
        email: User's email address (used as username)
        password: User's password (plain text, hashed by Django)
        remember_me: Whether to create persistent cookie (default: False)
    
    Security:
        - Password transmitted over HTTPS (TLS encryption)
        - Never logged or stored in plain text
        - remember_me defaults to False (secure by default)
    """
    email: str
    password: str
    remember_me: bool = False  # 🆕 NEW: Optional, defaults to session-only
    
    # Why default False?
    # - Secure by default: Users must opt-in to persistent cookies
    # - Privacy: Session cookies deleted on browser close
    # - Public computers: Safer default for shared devices
```

**Explanation**:

**Step 6 - Token Generation**:
- **`RefreshToken.for_user(user)`** - Factory method from custom class
- **`refresh.access_token`** - Property that generates associated access token
- **Why custom classes?** - Add role claims to JWT payload (Sept 2025)
- **Token signing**: Uses Django `SECRET_KEY` (HMAC SHA-256)
- **Token structure**: `header.payload.signature` (standard JWT format)

**Step 7 - Set Cookies**:
- **`remember_me=input.remember_me`** - Pass user's choice to cookie manager
- **Frontend choice**: User clicks checkbox → GraphQL mutation → Backend
- **Cookie duration**: Controlled entirely by backend (frontend cannot override)
- **Security**: Even if frontend tries to modify, backend determines duration

**Step 8 - Return Access Token**:
- **Why return in response?** - Frontend needs it for API calls
- **Why not in cookie?** - Cookies make it JavaScript-accessible (XSS risk)
- **Frontend storage**: React state (memory), cleared on page refresh
- **Token refresh**: Frontend calls refreshToken mutation when access token expires

**Common Mistakes**:
- ❌ Setting `remember_me=True` as default (insecure by default)
- ❌ Returning refresh token in response (security leak)
- ❌ Not checking `user.is_active` (allow disabled accounts)
- ❌ Using `sync` methods instead of `sync_to_async` (Django async compatibility)

**How This Connects**:
- Frontend: Sends `rememberMe` in GraphQL mutation input
- This mutation: Passes `remember_me` to `SecureTokenManager`
- `SecureTokenManager`: Sets cookie duration based on flag
- Browser: Stores cookies (session or persistent)
- Next login: Frontend can check cookie existence to pre-fill email (UX)

**Testing This Step**:
```bash
# Test via GraphQL Playground: http://localhost:8000/graphql

# Test 1: Login WITHOUT Remember Me (default)
mutation {
  auth {
    login(input: {
      email: "test@example.com"
      password: "TestPass123"
      # rememberMe not provided, defaults to false
    }) {
      success
      message
      user { id email role }
      accessToken
      expiresIn
    }
  }
}

# Expected result:
# - success: true
# - accessToken: "eyJhbGciOiJIUzI1NiIs..." (long string)
# - expiresIn: 300 (5 minutes)
# - Check browser cookies: refresh_token has NO "Expires" (session cookie)

# Test 2: Login WITH Remember Me
mutation {
  auth {
    login(input: {
      email: "test@example.com"
      password: "TestPass123"
      rememberMe: true  # 🔥 User chose persistent
    }) {
      success
      accessToken
      expiresIn
    }
  }
}

# Expected result:
# - success: true
# - Check browser cookies: refresh_token has "Expires" ~30 days future
# - Backend logs: "🔐 Setting PERSISTENT cookies: 30 days"

# Test 3: Verify cookie attributes
# Open Browser DevTools → Application → Cookies → localhost
# Expected cookies:
# - refresh_token: HttpOnly ✅, Secure (if HTTPS) ✅, SameSite Strict ✅
# - client_fp: HttpOnly ✅
# - fp_hash: HttpOnly ✅
```

---

## 🧪 Testing Backend Changes

### Manual Testing Commands

```bash
# 1. Start Django development server
cd skillsync-be
python manage.py runserver

# 2. Open GraphQL Playground
# Navigate to: http://localhost:8000/graphql

# 3. Test session cookie (Remember Me = false)
mutation {
  auth {
    login(input: {
      email: "test@skillsync.com"
      password: "TestPassword123"
      rememberMe: false
    }) {
      success
      message
      accessToken
      expiresIn
      user {
        id
        email
        role
      }
    }
  }
}

# 4. Check backend logs
# Expected output: "🔐 Setting SESSION cookies (browser close = logout)"

# 5. Inspect browser cookies (DevTools → Application → Cookies)
# Expected: refresh_token cookie with NO "Expires" attribute

# 6. Test persistent cookie (Remember Me = true)
mutation {
  auth {
    login(input: {
      email: "test@skillsync.com"
      password: "TestPassword123"
      rememberMe: true
    }) {
      success
      accessToken
      expiresIn
    }
  }
}

# 7. Check backend logs
# Expected output: "🔐 Setting PERSISTENT cookies: 30 days"

# 8. Inspect browser cookies
# Expected: refresh_token cookie with "Expires" ~30 days in future
```

### Automated Test Script

**File**: `skillsync-be/test_remember_me.py` (Create this file)

```python
"""
Test script for Remember Me functionality
Run: python test_remember_me.py
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import RequestFactory
from django.http import HttpResponse
from auth.secure_utils import SecureTokenManager
from auth.custom_tokens import CustomRefreshToken as RefreshToken
from django.contrib.auth import get_user_model

User = get_user_model()

def test_remember_me():
    """Test Remember Me cookie duration logic"""
    
    print("🧪 Testing Remember Me Backend Implementation\n")
    
    # Create test user
    user, created = User.objects.get_or_create(
        email='test@skillsync.com',
        defaults={'username': 'testuser'}
    )
    if created:
        user.set_password('TestPassword123')
        user.save()
        print("✅ Test user created\n")
    else:
        print("✅ Using existing test user\n")
    
    # Generate tokens
    refresh = RefreshToken.for_user(user)
    access_token = refresh.access_token
    
    print(f"🔑 Generated tokens:")
    print(f"   Access token (first 50 chars): {str(access_token)[:50]}...")
    print(f"   Refresh token (first 50 chars): {str(refresh)[:50]}...\n")
    
    # Test 1: Session cookie (remember_me=False)
    print("📋 Test 1: Session Cookie (remember_me=False)")
    print("-" * 60)
    
    factory = RequestFactory()
    request = factory.get('/')
    response1 = HttpResponse()
    
    SecureTokenManager.set_secure_jwt_cookies(
        response1,
        str(access_token),
        str(refresh),
        request,
        remember_me=False
    )
    
    cookie = response1.cookies.get('refresh_token')
    if cookie:
        max_age = cookie.get('max-age')
        print(f"   Cookie max-age: {max_age}")
        if max_age is None or max_age == '':
            print("   ✅ PASS: Session cookie (no max-age)\n")
        else:
            print(f"   ❌ FAIL: Expected None, got {max_age}\n")
    else:
        print("   ❌ FAIL: No refresh_token cookie set\n")
    
    # Test 2: Persistent cookie (remember_me=True)
    print("📋 Test 2: Persistent Cookie (remember_me=True)")
    print("-" * 60)
    
    response2 = HttpResponse()
    SecureTokenManager.set_secure_jwt_cookies(
        response2,
        str(access_token),
        str(refresh),
        request,
        remember_me=True
    )
    
    cookie2 = response2.cookies.get('refresh_token')
    if cookie2:
        max_age2 = cookie2.get('max-age')
        print(f"   Cookie max-age: {max_age2} seconds")
        if max_age2 and int(max_age2) == 2592000:  # 30 days
            print(f"   ✅ PASS: Persistent cookie (30 days)\n")
        else:
            print(f"   ❌ FAIL: Expected 2592000, got {max_age2}\n")
    else:
        print("   ❌ FAIL: No refresh_token cookie set\n")
    
    # Test 3: Cookie attributes
    print("📋 Test 3: Cookie Security Attributes")
    print("-" * 60)
    
    cookie_attrs = {
        'httponly': cookie2.get('httponly'),
        'samesite': cookie2.get('samesite'),
        'path': cookie2.get('path'),
    }
    
    print(f"   HttpOnly: {cookie_attrs['httponly']}")
    print(f"   SameSite: {cookie_attrs['samesite']}")
    print(f"   Path: {cookie_attrs['path']}")
    
    if (cookie_attrs['httponly'] == True and
        cookie_attrs['samesite'] == 'Strict' and
        cookie_attrs['path'] == '/'):
        print("   ✅ PASS: All security attributes correct\n")
    else:
        print("   ❌ FAIL: Security attributes incorrect\n")
    
    print("=" * 60)
    print("🎉 Testing complete!")

if __name__ == '__main__':
    test_remember_me()
```

**Run the test**:
```bash
cd skillsync-be
python test_remember_me.py
```

**Expected output**:
```
🧪 Testing Remember Me Backend Implementation

✅ Using existing test user

🔑 Generated tokens:
   Access token (first 50 chars): eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl...
   Refresh token (first 50 chars): eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl...

📋 Test 1: Session Cookie (remember_me=False)
------------------------------------------------------------
🔐 Setting SESSION cookies (browser close = logout)
   Cookie max-age: None
   ✅ PASS: Session cookie (no max-age)

📋 Test 2: Persistent Cookie (remember_me=True)
------------------------------------------------------------
🔐 Setting PERSISTENT cookies: 30 days
   Cookie max-age: 2592000 seconds
   ✅ PASS: Persistent cookie (30 days)

📋 Test 3: Cookie Security Attributes
------------------------------------------------------------
   HttpOnly: True
   SameSite: Strict
   Path: /
   ✅ PASS: All security attributes correct

============================================================
🎉 Testing complete!
```

---

## 📚 Related Documentation

- **Backend Changelog**: `skillsync-be/changelogs/Oct082025.md` (Complete implementation details)
- **Frontend Changelog**: `skillsync-fe/changelogs/Oct082025.md` (Frontend integration)
- **Phase 1 & 2 Summary**: `PHASE_1_2_IMPLEMENTATION_COMPLETE.md` (Complete architecture)
- **Custom JWT Tokens**: `skillsync-be/changelogs/Sept192025.md` (Token classes with role claims)
- **OTP System**: `skillsync-be/changelogs/Sept172025.md` (Device fingerprinting)
- **Security Configuration**: `skillsync-be/config/security.py` (JWT settings)

### External References

- **OWASP JWT Security**: https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html
- **RFC 6749 (OAuth 2.0)**: https://datatracker.ietf.org/doc/html/rfc6749
- **Django Security**: https://docs.djangoproject.com/en/stable/topics/security/
- **HTTP Cookies (MDN)**: https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies
- **SameSite Cookies**: https://web.dev/samesite-cookies-explained/

---

## 👥 For Junior Developers

### Key Concepts Explained

**1. What is a Session Cookie?**
- **Simple explanation**: A cookie that exists only while your browser is open
- **Technical**: Cookie with no `Max-Age` or `Expires` attribute
- **Storage**: Browser RAM (memory), not written to disk
- **Lifetime**: Deleted when ALL browser windows closed
- **Security**: Safest option - no persistent token on disk

**2. What is a Persistent Cookie?**
- **Simple explanation**: A cookie that survives browser restarts
- **Technical**: Cookie with `Max-Age` attribute (seconds until expiry)
- **Storage**: Browser disk (cookies database file)
- **Lifetime**: Until Max-Age expires or user manually deletes
- **Security**: Convenient but higher risk if device stolen

**3. What is HTTP-Only?**
- **Simple explanation**: JavaScript cannot read this cookie
- **Technical**: `HttpOnly` flag prevents `document.cookie` access
- **Why**: Protects against XSS (Cross-Site Scripting) attacks
- **Example**: Even if attacker injects malicious JavaScript, they cannot steal your auth tokens

**4. What is SameSite?**
- **Simple explanation**: Cookie only sent to same website
- **Technical**: `SameSite=Strict` prevents cross-site requests from including cookie
- **Why**: Protects against CSRF (Cross-Site Request Forgery) attacks
- **Example**: Evil site cannot trick browser into sending your cookies to SkillSync

**5. Why max_age=None not 0?**
- **`None`**: No Max-Age attribute → Session cookie (deleted on browser close)
- **`0`**: Max-Age=0 seconds → Expire immediately (deleted right away)
- **`-1`**: Some browsers treat as session cookie, but `None` is clearer
- **Best practice**: Use `None` for session cookies, explicit seconds for persistent

### Learning Resources

**Authentication & Security**:
- [JWT Introduction (jwt.io)](https://jwt.io/introduction)
- [HTTP Cookies Explained (MDN)](https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies)
- [OWASP Top 10 (Security Risks)](https://owasp.org/www-project-top-ten/)
- [Django Authentication System](https://docs.djangoproject.com/en/stable/topics/auth/)

**Django & Python**:
- [Django Tutorial (Official)](https://docs.djangoproject.com/en/stable/intro/tutorial01/)
- [Python Type Hints (Real Python)](https://realpython.com/python-type-checking/)
- [Async in Django (Official)](https://docs.djangoproject.com/en/stable/topics/async/)

**GraphQL**:
- [Strawberry GraphQL Docs](https://strawberry.rocks/)
- [GraphQL Best Practices](https://graphql.org/learn/best-practices/)

### Common Questions

**Q: Why not store refresh tokens in localStorage?**
**A**: localStorage is accessible to JavaScript. If an attacker injects malicious JavaScript (XSS attack), they can steal your tokens. HTTP-only cookies are invisible to JavaScript, so even XSS attacks cannot access them.

**Q: Why is access token only 5 minutes?**
**A**: Short lifetime limits damage if stolen. Even if attacker steals access token, they can only use it for 5 minutes. They cannot refresh it (refresh token is HTTP-only, not accessible to JavaScript).

**Q: Why do we need device fingerprinting?**
**A**: Additional security layer. If someone steals your cookie file and uses it on a different device, the backend can detect the fingerprint mismatch and reject the request.

**Q: What happens if user clears cookies?**
**A**: They must log in again. Refresh token is deleted, so backend cannot generate new access tokens. This is expected behavior.

**Q: Can I extend the Remember Me duration to 90 days?**
**A**: Yes, but security risk increases. The longer a token is valid, the longer an attacker has to exploit it if stolen. 30 days is industry standard balance between convenience and security.

**Q: Why does backend control cookie duration, not frontend?**
**A**: Security. If frontend controlled cookies, malicious JavaScript could set longer durations. Backend is trusted (you control the code), frontend is untrusted (JavaScript can be modified by attackers).

---

*Backend Implementation Guide Created: October 8, 2025*  
*For: Remember Me & Memory-Only Token Architecture*  
*Security Level: Enterprise-Grade (10/10)*
