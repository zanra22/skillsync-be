import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

# Get the base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Application Configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

SECRET_KEY = {
    "development": os.getenv("DEV_SECRET_KEY"),
    "staging": os.getenv("STAG_SECRET_KEY"),
    "production": os.getenv("PROD_SECRET_KEY"),
}.get(ENVIRONMENT, os.getenv("DEV_SECRET_KEY"))

ALLOWED_HOSTS = {
    "production": [
        ".azurewebsites.studio",  # Replace with actual production URL
        "api.skillsync.studio",                   # Replace with actual production API domain
        "skillsync.studio",                       # Main domain
        "127.0.0.1", 
        "localhost"
    ],
}

# Get the current allowed hosts for the environment
ALLOWED_HOSTS_CONFIG = ALLOWED_HOSTS.get(ENVIRONMENT)
print(f"Allowed Hosts: {ALLOWED_HOSTS_CONFIG}")
print(f"Environment: {ENVIRONMENT}"
      f"\nSecret Key: {SECRET_KEY}")

FRONTEND_URL = {
    "development": os.getenv("DEV_FRONTEND_URL", "http://localhost:3000"),
    "staging": os.getenv("STAG_FRONTEND_URL"),
    "production": os.getenv("PROD_FRONTEND_URL"),
}.get(ENVIRONMENT, os.getenv("DEV_FRONTEND_URL", "http://localhost:3000"))

DATABASES = {
    "development": {
        "ENGINE": os.getenv("DEV_DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": BASE_DIR / os.getenv("DEV_DB_NAME", "db.sqlite3"),
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
DATABASE_CONFIG = DATABASES.get(ENVIRONMENT, DATABASES["development"])
print()
# Django Ninja JWT Configuration - MAXIMUM SECURITY
NINJA_JWT_CONFIG = {
    # CRITICAL: Very short access token lifetime (5 minutes)
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    
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

print(NINJA_JWT_CONFIG)