import os

# Application Configuration
ENVIRONMENT = os.getenv("ENVIRONMENT")

SECRET_KEY = {
    "development": os.getenv("DEV_SECRET_KEY"),
    "staging": os.getenv("STAG_SECRET_KEY"),
    "production": os.getenv("PROD_SECRET_KEY"),
}.get(ENVIRONMENT, os.getenv("DEV_SECRET_KEY"))