# core/settings/dev.py
from .base import *
from config.constants import DATABASE_CONFIG, FRONTEND_URL
import os

DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '0.0.0.0']

# FRONTEND_URL is already resolved based on ENVIRONMENT in constants.py
print(f"Development FRONTEND_URL: {FRONTEND_URL}")
print('checkpoint')

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
        'roadmap_file': {
            'class': 'logging.FileHandler',
            'filename': 'roadmap_module_lesson.log',
            'level': 'INFO',
            'encoding': 'utf-8',
        },
    },
    'root': {
        'handlers': ['console', 'roadmap_file'],
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
        'ai_roadmap_service': {
            'handlers': ['roadmap_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'helpers.youtube': {
            'handlers': ['console', 'roadmap_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'helpers.youtube.youtube_service': {
            'handlers': ['console', 'roadmap_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'helpers.youtube.transcript_service': {
            'handlers': ['console', 'roadmap_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'helpers.multi_source_research': {
            'handlers': ['console', 'roadmap_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'helpers.ai_lesson_service': {
            'handlers': ['console', 'roadmap_file'],
            'level': 'INFO',
            'propagate': False,
        },
        # Suppress noisy Azure SDK loggers (for dev/testing in Azure)
        'azure': {
            'level': 'WARNING',
            'propagate': False,
        },
        'azure.core.pipeline.policies': {
            'level': 'WARNING',
            'propagate': False,
        },
        'urllib3': {
            'level': 'WARNING',
            'propagate': False,
        },
    },
}