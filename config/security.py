"""
Ultra-Secure JWT Configuration
Following OWASP and industry best practices
"""
from datetime import timedelta
from django.conf import settings

def get_secure_jwt_settings(secret_key, debug=False):
    """
    Get JWT security configuration
    """
    return {
        # CRITICAL: Very short access token lifetime (5 minutes)
        'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
        
        # Refresh token lifetime (7 days max recommended)
        'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
        
        # Enable token rotation for maximum security
        'ROTATE_REFRESH_TOKENS': True,
        
        # Blacklist tokens on refresh (prevents replay attacks)
        'BLACKLIST_AFTER_ROTATION': True,
        
        # Algorithm and signing
        'ALGORITHM': 'HS256',
        'SIGNING_KEY': secret_key,
        
        # Token claims
        'AUTH_HEADER_TYPES': ('Bearer',),
        'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
        
        # Custom token classes for enhanced security
        'ACCESS_TOKEN_CLASS': 'ninja_jwt.tokens.AccessToken',
        'REFRESH_TOKEN_CLASS': 'ninja_jwt.tokens.RefreshToken',
        
        # Issuer validation
        'ISSUER': 'SkillSync',
        'AUDIENCE': None,
        
        # Sliding token configuration
        'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
        'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
        'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
    }

def get_security_settings(debug=False):
    """
    Get security settings based on environment
    """
    return {
        # Security Headers Configuration
        'SECURE_BROWSER_XSS_FILTER': True,
        'SECURE_CONTENT_TYPE_NOSNIFF': True,
        'X_FRAME_OPTIONS': 'DENY',

        # Session Security
        'SESSION_COOKIE_SECURE': not debug,  # HTTPS only in production
        'SESSION_COOKIE_HTTPONLY': True,
        'SESSION_COOKIE_SAMESITE': 'Strict',
        'SESSION_EXPIRE_AT_BROWSER_CLOSE': True,
        'SESSION_COOKIE_AGE': 3600,  # 1 hour

        # CSRF Protection
        'CSRF_COOKIE_SECURE': not debug,
        'CSRF_COOKIE_HTTPONLY': True,
        'CSRF_COOKIE_SAMESITE': 'Strict',
        'CSRF_TRUSTED_ORIGINS': [
            'http://localhost:3000',  # Development
            'https://yourdomain.com',  # Production
        ],

        # CORS Security (more restrictive)
        'CORS_ALLOW_CREDENTIALS': True,
        'CORS_ALLOWED_ORIGINS': [
            "http://localhost:3000",  # Development only
            # Add production URLs here
        ],

        # Remove CORS_ALLOW_ALL_ORIGINS in production!
        'CORS_ALLOW_ALL_ORIGINS': debug,  # Only for development

        'CORS_ALLOW_HEADERS': [
            'accept',
            'accept-encoding',
            'authorization',
            'content-type',
            'dnt',
            'origin',
            'user-agent',
            'x-csrftoken',
            'x-requested-with',
        ],

        # Rate limiting (add to middleware)
        'RATE_LIMIT_LOGIN_ATTEMPTS': 5,
        'RATE_LIMIT_WINDOW': 300,  # 5 minutes

        # Password validation (enhanced)
        'AUTH_PASSWORD_VALIDATORS': [
            {
                'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
            },
            {
                'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
                'OPTIONS': {
                    'min_length': 12,  # Increased from default 8
                }
            },
            {
                'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
            },
            {
                'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
            },
        ]
    }
