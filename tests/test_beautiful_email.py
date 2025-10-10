#!/usr/bin/env python3
"""
Test the new beautiful SkillSync-themed email design.
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

def test_beautiful_email():
    """Test the new beautiful email design."""
    print("🎨 Testing New SkillSync Email Design")
    print("=" * 60)
    print("🌟 Features:")
    print("   • Neural Blue & Electric Cyan color scheme")
    print("   • Poppins & Inter fonts matching frontend")
    print("   • Gradient backgrounds and buttons")
    print("   • Professional responsive design")
    print("   • Enhanced security styling")
    print("   • Emoji and modern visual elements")
    print("-" * 60)
    
    # Test email details
    test_email = "arnazdj69@gmail.com"
    test_otp = "888999"
    test_verification_url = "http://localhost:3000/verify?token=beautiful-design-test&purpose=signin"
    test_username = "Arnaz"
    
    print(f"📧 Sending beautiful OTP email to: {test_email}")
    print(f"🎯 OTP Code: {test_otp}")
    print(f"👤 Username: {test_username}")
    print("-" * 60)
    
    # Send email using the new design
    success = send_otp_email(
        to_email=test_email,
        otp_code=test_otp,
        verification_url=test_verification_url,
        username=test_username,
        purpose="signin"
    )
    
    print("-" * 60)
    if success:
        print("✅ SUCCESS: Beautiful email sent!")
        print("📬 Check your Gmail inbox for the new design")
        print("🎨 You should see:")
        print("   • Neural blue gradient header")
        print("   • Electric cyan OTP code styling")
        print("   • Professional card layout")
        print("   • SkillSync branding and colors")
        print("   • Responsive mobile-friendly design")
    else:
        print("❌ FAILED: Could not send beautiful email")
    
    print("=" * 60)
    return success

if __name__ == "__main__":
    test_beautiful_email()
