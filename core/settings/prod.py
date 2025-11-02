# core/settings/prod.py
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

# Explicitly set CORS configuration for production
if CORS_ALLOWED_ORIGINS_CONFIG:
    CORS_ALLOWED_ORIGINS = CORS_ALLOWED_ORIGINS_CONFIG
    print(f"Production CORS_ALLOWED_ORIGINS: {CORS_ALLOWED_ORIGINS}")