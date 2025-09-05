# core/settings/prod.py
from .base import *
from config.constants import DATABASES, FRONTEND_URL
import os

DEBUG = False

ALLOWED_HOSTS = ['.azurewebsites.net', '127.0.0.1', 'localhost', '.skillsync.studio']

FRONTEND_URL = FRONTEND_URL["production"]

DATABASES = {
    "default": DATABASES["production"],
}