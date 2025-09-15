#!/usr/bin/env python3
"""
Test script to send actual OTP emails via Resend.com (forced mode).
This bypasses the development console backend and uses Resend directly.
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

def test_real_otp_email():
    """Test sending real OTP email via Resend API."""
    print("🚀 Testing REAL OTP Email via Resend.com")
    print("=" * 50)
    
    # Test email details
    test_email = "arnazdj69@gmail.com"
    test_otp = "987654"
    test_verification_url = "http://localhost:3000/verify?token=real-token-123&purpose=signin"
    test_username = "Arnaz"
    
    print(f"📧 Sending REAL OTP email to: {test_email}")
    print(f"🔢 OTP Code: {test_otp}")
    print(f"🔗 Verification URL: {test_verification_url}")
    print(f"👤 Username: {test_username}")
    print(f"🌐 Using: Resend API (FORCED MODE)")
    print("-" * 50)
    
    # Send email with force_resend=True to bypass console backend
    success = send_otp_email(
        to_email=test_email,
        otp_code=test_otp,
        verification_url=test_verification_url,
        username=test_username,
        force_resend=True,  # This forces Resend usage even in development
        purpose="signin"
    )
    
    print("-" * 50)
    if success:
        print("✅ SUCCESS: Real OTP email sent via Resend!")
        print("📬 Check your Gmail inbox for the actual email")
        print("🔍 If not in inbox, check spam folder")
        print("📧 You should receive a professional HTML email with OTP code")
    else:
        print("❌ FAILED: Could not send real OTP email")
        print("🔧 Check your Resend API key and try again")
    
    print("=" * 50)
    return success

if __name__ == "__main__":
    test_real_otp_email()
