#!/bin/bash

# Set environment variables for Azure App Service
export PYTHONUNBUFFERED=1
export ENVIRONMENT=production
export DISABLE_COLLECTSTATIC=1

# Change to app directory
cd /home/site/wwwroot

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run migrations
python manage.py migrate --noinput --settings=core.settings.prod

# Start gunicorn
gunicorn --bind 0.0.0.0:8000 --workers 4 core.wsgi:application
