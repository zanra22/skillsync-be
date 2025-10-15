"""
Quick script to check user profile
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()

from users.models import User

# Check user
email = 'xarnaz22@gmail.com'
user = User.objects.filter(email=email).first()

if user:
    print(f"✅ User found: {user.email}")
    print(f"   Role: {user.role}")
    print(f"   Account Status: {user.account_status}")
    print(f"   First Name: {user.first_name}")
    print(f"   Last Name: {user.last_name}")
    
    # Check if profile exists
    try:
        profile = user.profile
        print(f"\n✅ Profile exists!")
        print(f"   Onboarding Completed: {profile.onboarding_completed}")
        print(f"   Profile ID: {profile.id}")
        print(f"   Bio: {profile.bio or '(empty)'}")
    except Exception as e:
        print(f"\n❌ No profile found: {str(e)}")
else:
    print(f"❌ User not found: {email}")
