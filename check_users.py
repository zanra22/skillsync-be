#!/usr/bin/env python
"""
Script to check existing users in the database
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def check_users():
    print("Checking existing users...")
    users = User.objects.all()[:10]
    
    if not users:
        print("No users found in database")
        return
    
    print(f"Found {len(users)} users:")
    for user in users:
        role = getattr(user, 'role', 'no role attribute')
        print(f"- Email: {user.email}")
        print(f"  Role: {role}")
        print(f"  Is Active: {user.is_active}")
        print(f"  Is Staff: {user.is_staff}")
        print(f"  Is Superuser: {user.is_superuser}")
        print("---")

if __name__ == "__main__":
    check_users()