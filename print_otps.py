#!/usr/bin/env python
"""
Shell script to print all OTPs for all users (or filter by email)
Usage:
    python print_otps.py [optional_email]
"""
import sys
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()

from otps.models import OTP

if len(sys.argv) > 1:
    email = sys.argv[1]
    from users.models import User
    try:
        user = User.objects.get(email=email)
        otps = OTP.objects.filter(user=user).order_by('-created_at')
        print(f"All OTPs for {email}:")
    except User.DoesNotExist:
        print(f"No user found with email: {email}")
        sys.exit(1)
else:
    otps = OTP.objects.all().order_by('-created_at')
    print("All OTPs for all users:")

for otp in otps:
    print(f"User: {otp.user.email} | Purpose: {otp.purpose} | Code Hash: {otp.code_hash} | Created: {otp.created_at} | Expires: {otp.expires_at} | Used: {otp.used_at is not None}")
