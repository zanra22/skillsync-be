# core/settings/prod.py
from .base import *
from config.constants import DATABASE_CONFIG, FRONTEND_URL
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