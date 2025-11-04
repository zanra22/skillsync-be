import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

# Get the base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Application Configuration
ENVIRONMENT = os.getenv("ENVIRONMENT")

# ⚠️ TEMPORARY: Allow development CORS testing against production backend
# TODO: REMOVE BEFORE PRODUCTION LAUNCH - See SECURITY_REVERT_CHECKLIST.md
ALLOW_DEV_CORS = os.getenv("ALLOW_DEV_CORS", "false").lower() == "true"

SECRET_KEY = {
    "development": os.getenv("DEV_SECRET_KEY"),
    "staging": os.getenv("STAG_SECRET_KEY"),
    "production": os.getenv("PROD_SECRET_KEY"),
}.get(ENVIRONMENT, os.getenv("DEV_SECRET_KEY"))

ALLOWED_HOSTS = {
    "development": [
        "localhost",
        "127.0.0.1"
    ],
    "production": [
        ".azurewebsites.net",  # Replace with actual production URL
        "api.skillsync.studio",                   # Replace with actual production API domain
        "skillsync.studio",                       # Main domain
        "127.0.0.1", 
        "localhost"
    ],
}

# Get the current allowed hosts for the environment
ALLOWED_HOSTS_CONFIG = ALLOWED_HOSTS.get(ENVIRONMENT)
print(f"Allowed Hosts: {ALLOWED_HOSTS_CONFIG}")
print(f"Environment: {ENVIRONMENT}\nSecret Key: {SECRET_KEY}")

FRONTEND_URL = {
    "development": os.getenv("DEV_FRONTEND_URL", "http://localhost:3000"),
    "staging": os.getenv("STAG_FRONTEND_URL"),
    "production": os.getenv("PROD_FRONTEND_URL"),
}.get(ENVIRONMENT, os.getenv("DEV_FRONTEND_URL", "http://localhost:3000"))

# CORS Configuration - allow frontend origins
CORS_ALLOWED_ORIGINS = {
    "development": [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    "production": [
        "https://www.skillsync.studio",
        "https://skillsync.studio",
        "http://localhost:3000",  # Allow localhost for testing against prod backend
        "http://127.0.0.1:3000",
    ],
}

# Get current CORS config
CORS_ALLOWED_ORIGINS_CONFIG = CORS_ALLOWED_ORIGINS.get(ENVIRONMENT)
print(f"CORS Allowed Origins: {CORS_ALLOWED_ORIGINS_CONFIG}")

# CSRF Trusted Origins - must include HTTPS variants
CSRF_TRUSTED_ORIGINS = {
    "development": [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
    ],
    "production": [
        'https://www.skillsync.studio',
        'https://skillsync.studio',
        'http://localhost:3000',  # Allow localhost for testing
        'http://127.0.0.1:3000',
    ],
}

# Get current CSRF config
CSRF_TRUSTED_ORIGINS_CONFIG = CSRF_TRUSTED_ORIGINS.get(ENVIRONMENT)
print(f"CSRF Trusted Origins: {CSRF_TRUSTED_ORIGINS_CONFIG}")

DATABASES = {
    "development": {
        "ENGINE": os.getenv("DEV_DB_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.getenv("DEV_DB_NAME"),
        "USER": os.getenv("DEV_DB_USER"),
        "PASSWORD": os.getenv("DEV_DB_PASSWORD"),
        "HOST": os.getenv("DEV_DB_HOST", "localhost"),
        "PORT": os.getenv("DEV_DB_PORT", "5432"),
    },
    "production": {
        "ENGINE": os.getenv("PROD_DB_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.getenv("PROD_DB_NAME"),
        "USER": os.getenv("PROD_DB_USER"),
        "PASSWORD": os.getenv("PROD_DB_PASSWORD"),
        "HOST": os.getenv("PROD_DB_HOST", "localhost"),
        "PORT": os.getenv("PROD_DB_PORT", "5432"),
    },
}

# Get the current database config
DATABASE_CONFIG = DATABASES.get(ENVIRONMENT)
print(f"Database Config: {DATABASE_CONFIG}")
# Django Ninja JWT Configuration - MAXIMUM SECURITY
NINJA_JWT_CONFIG = {
    # Increased access token lifetime for onboarding/lesson generation (30 minutes)
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    
    # Refresh token lifetime (7 days max recommended)
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    
    # Enable token rotation for maximum security
    'ROTATE_REFRESH_TOKENS': True,
    
    # Blacklist tokens on refresh (prevents replay attacks)
    'BLACKLIST_AFTER_ROTATION': True,
    
    # Update last login on token refresh
    'UPDATE_LAST_LOGIN': True,
    
    # Algorithm and signing
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': 'SkillSync',
    
    # Token claims
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'TOKEN_TYPE_CLAIM': 'token_type',
    
    # Enhanced security claims
    'JTI_CLAIM': 'jti',
    'REFRESH_TOKEN_STRICT': True,
    
    # Sliding tokens for automatic refresh
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
    
    # Security enhancements
    'AUTH_COOKIE_SECURE': ENVIRONMENT != 'development',
    'AUTH_COOKIE_HTTP_ONLY': True,
    'AUTH_COOKIE_SAMESITE': 'Strict',
}

# Email Configuration - Resend.com
EMAIL_CONFIG = {
    "development": {
        "BACKEND": "django.core.mail.backends.smtp.EmailBackend",  # Use Resend for dev too
        "RESEND_API_KEY": os.getenv("RESEND_API_KEY"),
        "DEFAULT_FROM_EMAIL": "SkillSync Dev <dev@skillsync.studio>",  # Use working domain
    },
    "staging": {
        "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "RESEND_API_KEY": os.getenv("RESEND_API_KEY"),
        "DEFAULT_FROM_EMAIL": "SkillSync Staging <staging@skillsync.studio>",  # Use working domain
    },
    "production": {
        "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "RESEND_API_KEY": os.getenv("RESEND_API_KEY"),
        "DEFAULT_FROM_EMAIL": "SkillSync <support@skillsync.studio>",  # Use working domain
    },
}

# Get current email config
EMAIL_SETTINGS = EMAIL_CONFIG.get(ENVIRONMENT, EMAIL_CONFIG["development"])
print(f"Email Config: {EMAIL_SETTINGS}")
print(NINJA_JWT_CONFIG)