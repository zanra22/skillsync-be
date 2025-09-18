#!/usr/bin/env python
"""
Script to create a test user for JWT testing
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def create_test_user():
    email = "test@skillsync.com"
    username = "testuser"
    password = "test123456"
    
    # Check if user already exists
    if User.objects.filter(email=email).exists():
        user = User.objects.get(email=email)
        print(f"Test user already exists: {email}")
    else:
        # Create new test user
        user = User.objects.create_user(
            email=email,
            username=username,
            password=password,
            is_active=True,
            is_email_verified=True,
            account_status='active'  # Set account status to active
        )
        print(f"Created test user: {email}")
    
    # Ensure user is verified and active
    if not user.is_email_verified:
        user.is_email_verified = True
        user.account_status = 'active'
        user.save()
        print("Updated user to be verified and active")
    
    # Set role if it doesn't exist
    if hasattr(user, 'role'):
        if not user.role:
            user.role = 'learner'
            user.save()
            print(f"Set user role to: {user.role}")
        else:
            print(f"User role: {user.role}")
    else:
        print("User model doesn't have role field")
    
    print(f"Test credentials: {email} / {password}")
    return user

if __name__ == "__main__":
    create_test_user()