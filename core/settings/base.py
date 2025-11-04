import os
import ssl
from dotenv import load_dotenv
from pathlib import Path

from config.constants import SECRET_KEY, FRONTEND_URL, ENVIRONMENT, DATABASE_CONFIG, NINJA_JWT_CONFIG, ALLOWED_HOSTS_CONFIG, EMAIL_SETTINGS, CORS_ALLOWED_ORIGINS_CONFIG, CSRF_TRUSTED_ORIGINS_CONFIG

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / '.env'
load_dotenv(env_path)

SECRET_KEY = SECRET_KEY

ALLOWED_HOSTS = ALLOWED_HOSTS_CONFIG

print(f"Current Environment: {ENVIRONMENT}")
print(f"Using SECRET_KEY: {SECRET_KEY}")

DEBUG = True

INSTALLED_APPS = [
    # "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    "corsheaders",  # Add CORS headers
    "ninja_jwt",
    "ninja_jwt.token_blacklist",  # ✅ Token blacklist for security (rotation)
    "strawberry.django",
    "users",
    "profiles",
    "otps",  # OTP verification system
    "admin",
    "onboarding",
    "lessons",  # AI-powered lesson content system
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # Enable CORS - MUST be early
    "django.middleware.security.SecurityMiddleware",
    "auth.rate_limiting.SecurityHeadersMiddleware",  # Security headers
    "auth.rate_limiting.RateLimitMiddleware",  # Rate limiting
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "api.middleware.JWTAuthMiddleware",  # Add JWT auth middleware
    "auth.rate_limiting.RequestLoggingMiddleware",  # Security logging
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

AUTH_USER_MODEL = "users.User"

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# AWS_LOCATION = "static"
# AWS_MEDIA_LOCATION = "media"
# AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
# AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
# AWS_STORAGE_BUCKET_NAME = "simpleprojexbucket"
# AWS_S3_REGION_NAME = "us-west-1"
# AWS_S3_CUSTOM_DOMAIN = "%s.s3.amazonaws.com" % AWS_STORAGE_BUCKET_NAME
# AWS_S3_FILE_OVERWRITE = False

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"

# STORAGES = {
#     "default": {
#         "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
#         "OPTIONS": {
#             "location": AWS_MEDIA_LOCATION,
#         },
#     },
#     "staticfiles": {
#         "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
#     },
# }

FRONTEND_URL = FRONTEND_URL

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024

DATABASES = {
    "default": DATABASE_CONFIG,
}

# Django Ninja JWT Settings
NINJA_JWT = NINJA_JWT_CONFIG

# Email Configuration
EMAIL_BACKEND = EMAIL_SETTINGS["BACKEND"]
DEFAULT_FROM_EMAIL = EMAIL_SETTINGS["DEFAULT_FROM_EMAIL"]
RESEND_API_KEY = EMAIL_SETTINGS["RESEND_API_KEY"]

# CORS Configuration for frontend integration - ENHANCED SECURITY
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = CORS_ALLOWED_ORIGINS_CONFIG

# STRICT: Only allow in development
CORS_ALLOW_ALL_ORIGINS = False  # Never allow all origins

CORS_ALLOWED_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

CORS_ALLOW_METHODS = [
    'GET',
    'POST',
    'PUT',
    'DELETE',
    'PATCH',
    'OPTIONS',
]

# Expose additional headers
CORS_EXPOSE_HEADERS = [
    'content-type',
    'x-csrftoken',
]

# Cache preflight requests for 1 hour
CORS_PREFLIGHT_MAX_AGE = 3600

# Enhanced Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Session Security
SESSION_COOKIE_SECURE = ENVIRONMENT != 'development'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 3600  # 1 hour

# CSRF Protection
CSRF_COOKIE_SECURE = ENVIRONMENT != 'development'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_TRUSTED_ORIGINS = CSRF_TRUSTED_ORIGINS_CONFIG

# Cache for rate limiting
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'skillsync-cache',
    }
}
