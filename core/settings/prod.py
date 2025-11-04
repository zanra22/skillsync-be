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

# IMPORTANT: Do NOT override base.py CORS settings
# base.py already handles CORS_ALLOWED_ORIGINS conditionally based on CORS_ALLOW_ALL_ORIGINS
# If we re-set CORS_ALLOWED_ORIGINS here, it will override the allow_all setting
print(f"Production CORS_ALLOW_ALL_ORIGINS: {CORS_ALLOW_ALL_ORIGINS}")
if hasattr(locals(), 'CORS_ALLOWED_ORIGINS'):
    print(f"Production CORS_ALLOWED_ORIGINS: {CORS_ALLOWED_ORIGINS}")
else:
    print("Production: CORS_ALLOWED_ORIGINS not set (CORS_ALLOW_ALL_ORIGINS is True)")