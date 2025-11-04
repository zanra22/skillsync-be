# core/settings/prod.py
# Deployment: Retry after Azure 409 conflict
from .base import *
from config.constants import DATABASE_CONFIG, FRONTEND_URL, CORS_ALLOWED_ORIGINS_CONFIG
import os

DEBUG = False

ALLOWED_HOSTS = ['.azurewebsites.net', '127.0.0.1', 'localhost', '.skillsync.studio']

# FRONTEND_URL is already resolved based on ENVIRONMENT in constants.py
print(f"Production FRONTEND_URL: {FRONTEND_URL}")
print('production checkpoint')

DATABASES = {
    "default": DATABASE_CONFIG,
}

print(f"Production DATABASES: {DATABASES}")

# CRITICAL FIX: Explicitly set CORS_ALLOWED_ORIGINS = None in production
# This ensures django-cors-headers respects CORS_ALLOW_ALL_ORIGINS = True
# When CORS_ALLOWED_ORIGINS has any value (including the list from base.py),
# django-cors-headers uses that whitelist and ignores CORS_ALLOW_ALL_ORIGINS
# By setting it to None, we force django-cors-headers to check CORS_ALLOW_ALL_ORIGINS
if CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOWED_ORIGINS = None
    print("Production: CORS_ALLOWED_ORIGINS set to None to enable CORS_ALLOW_ALL_ORIGINS")
print(f"Production CORS_ALLOW_ALL_ORIGINS: {CORS_ALLOW_ALL_ORIGINS}")
print(f"Production CORS_ALLOWED_ORIGINS: {CORS_ALLOWED_ORIGINS}")