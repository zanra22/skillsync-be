#!/usr/bin/env python3
"""
Test the regular OTP email function now that we've fixed the development configuration.
"""

import os
import sys
import django
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.base')
django.setup()

from helpers.email_service import send_otp_email

def test_regular_otp():
    """Test the regular OTP email function."""
    print("🧪 Testing Regular OTP Email Function")
    print("=" * 50)
    print("📝 Configuration: Development mode now uses Resend")
    print("🌐 Should send real emails via Resend API")
    print("-" * 50)
    
    # Test email details
    test_email = "arnazdj69@gmail.com"
    test_otp = "555777"
    test_verification_url = "http://localhost:3000/verify?token=updated-config-test&purpose=signin"
    test_username = "Arnaz"
    
    print(f"📧 Sending OTP email to: {test_email}")
    print(f"🔢 OTP Code: {test_otp}")
    print(f"👤 Username: {test_username}")
    print("-" * 50)
    
    # Send email using regular function (should now use Resend in development)
    success = send_otp_email(
        to_email=test_email,
        otp_code=test_otp,
        verification_url=test_verification_url,
        username=test_username,
        purpose="signin"
    )
    
    print("-" * 50)
    if success:
        print("✅ SUCCESS: OTP email sent!")
        print("📬 Check your Gmail inbox")
        print("🔍 Should be a professional HTML email (not console output)")
    else:
        print("❌ FAILED: Could not send OTP email")
    
    print("=" * 50)
    return success

if __name__ == "__main__":
    test_regular_otp()
