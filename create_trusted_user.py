"""
Script to create a new user and register a trusted device for OTP bypass (testing only)
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()

from users.models import User  # Adjust if your user model is custom
from otps.models import TrustedDevice, OTP  # Adjust if your trusted device model is elsewhere
from django.utils.crypto import get_random_string

# --- CONFIG ---
TEST_EMAIL = "trusted.test.user@skillsync.studio"
TEST_PASSWORD = "TestPassword123!"
DEVICE_FINGERPRINT = "test-device-fingerprint-001"  # Use a real fingerprint for your browser/device
DEVICE_NAME = "Test Device"

# --- CREATE USER ---

user, created = User.objects.get_or_create(
    email=TEST_EMAIL,
    defaults={
        "is_active": True,
    }
)
if created:
    print(f"✅ Created new user: {TEST_EMAIL}")
else:
    print(f"ℹ️ User already exists: {TEST_EMAIL}")
# Always set password and role to ensure login and onboarding redirect
user.set_password(TEST_PASSWORD)
user.role = "new_user"
user.is_verified = True  # Mark account as verified for testing
user.save()

# --- REGISTER TRUSTED DEVICE ---
trusted_device, td_created = TrustedDevice.objects.get_or_create(
    user=user,
    device_fingerprint=DEVICE_FINGERPRINT,
    defaults={
        "device_name": DEVICE_NAME,
        "is_active": True,
        "ip_address": "127.0.0.1",
    }
)
if td_created:
    print(f"✅ Registered trusted device: {DEVICE_NAME} ({DEVICE_FINGERPRINT})")
else:
    print(f"ℹ️ Trusted device already exists for user.")

print("\n🎉 Test user and trusted device setup complete!")
print(f"Login with: {TEST_EMAIL} / {TEST_PASSWORD}")
print(f"Device fingerprint: {DEVICE_FINGERPRINT}")
print("OTP should be skipped for this device.")
