# core/settings/prod.py
from .base import *
from config.constants import DATABASES, CORS_CONFIG, ALLOWED_HOSTS, FRONTEND_URL
import os

DEBUG = False

ALLOWED_HOSTS = ['*']

FRONTEND_URL = FRONTEND_URL["production"]

DATABASES = {
    "default": DATABASES["production"],
}