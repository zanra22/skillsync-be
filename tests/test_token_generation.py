#!/usr/bin/env python
"""
Test custom token generation
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from auth.custom_tokens import CustomRefreshToken, CustomAccessToken
import json
import base64

User = get_user_model()

def test_token_generation():
    # Get the user
    user = User.objects.get(id='sDV6TZHZjT')
    print(f'Testing token generation for user: {user.email}')
    print(f'User role: {user.role}')

    # Generate fresh tokens using our custom classes
    refresh = CustomRefreshToken.for_user(user)
    access_token = refresh.access_token

    print(f'Generated refresh token: {str(refresh)[:50]}...')
    print(f'Generated access token: {str(access_token)[:50]}...')

    # Decode the access token to check the role
    token_str = str(access_token)
    payload_b64 = token_str.split('.')[1]
    payload_b64 += '=' * (4 - len(payload_b64) % 4)
    payload = json.loads(base64.b64decode(payload_b64).decode())

    print('\nAccess token payload:')
    print(json.dumps(payload, indent=2))
    print(f'\nRole in token: {payload.get("role")}')
    print(f'User role in token: {payload.get("user_role")}')
    
    if payload.get("role") == user.role:
        print("✅ Token generation working correctly!")
    else:
        print(f"❌ Token role mismatch: expected {user.role}, got {payload.get('role')}")

if __name__ == "__main__":
    test_token_generation()