# core/settings/dev.py
from .base import *
from config.constants import DATABASE_CONFIG, FRONTEND_URL
import os

DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '0.0.0.0']

# FRONTEND_URL is already resolved based on ENVIRONMENT in constants.py
print(f"Development FRONTEND_URL: {FRONTEND_URL}")

DATABASES = {
    "default": DATABASE_CONFIG,
}

# Development-specific settings
CORS_ALLOW_ALL_ORIGINS = True  # Only for development

# Disable security features for development
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Additional development settings
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Logging for development
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'auth': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}