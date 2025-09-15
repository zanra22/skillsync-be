#!/usr/bin/env python
"""
Test OTP email system with Resend.com integration
"""
import os
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.base')
django.setup()

from helpers.email_service import send_otp_email, send_email

def test_otp_email_with_resend():
    """Test OTP email using Resend API directly"""
    print("🧪 Testing OTP Email with Resend.com")
    print("=" * 50)
    
    # Test data
    test_email = "arnazdj69@gmail.com"
    test_otp = "123456"
    test_url = "http://localhost:3000/verify?token=abc123&purpose=signin"
    test_username = "Arnaz"
    
    print(f"📧 Sending OTP email to: {test_email}")
    print(f"🔢 OTP Code: {test_otp}")
    print(f"🔗 Verification URL: {test_url}")
    print(f"👤 Username: {test_username}")
    print()
    
    # Force Resend usage (bypass development mode)
    success = send_email(
        to_email=test_email,
        subject="Your SkillSync Verification Code",
        html_content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>SkillSync - Verification Code</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4F46E5; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px 20px; background: #f9f9f9; }}
                .otp-code {{ 
                    font-size: 32px; 
                    font-weight: bold; 
                    text-align: center; 
                    background: #4F46E5; 
                    color: white; 
                    padding: 15px; 
                    margin: 20px 0; 
                    border-radius: 8px;
                    letter-spacing: 3px;
                }}
                .button {{ 
                    display: inline-block; 
                    background: #4F46E5; 
                    color: white; 
                    padding: 12px 24px; 
                    text-decoration: none; 
                    border-radius: 6px; 
                    margin: 10px 0; 
                }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>SkillSync</h1>
                    <p>Your Verification Code</p>
                </div>
                
                <div class="content">
                    <h2>Hello {test_username},</h2>
                    
                    <p>We received a request to verify your email address. Use the verification code below:</p>
                    
                    <div class="otp-code">{test_otp}</div>
                    
                    <p>Or click the button below to verify automatically:</p>
                    
                    <div style="text-align: center;">
                        <a href="{test_url}" class="button">Verify Email Address</a>
                    </div>
                    
                    <p><strong>Security Note:</strong> This code expires in 10 minutes. Never share this code with anyone.</p>
                    
                    <p>If you didn't request this verification, you can safely ignore this email.</p>
                </div>
                
                <div class="footer">
                    <p>© 2024 SkillSync. All rights reserved.</p>
                    <p>This is an automated message, please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """,
        text_content=f"""
        SkillSync - Email Verification
        
        Hello {test_username},
        
        We received a request to verify your email address.
        
        Your verification code is: {test_otp}
        
        Or visit this link to verify automatically:
        {test_url}
        
        Security Notes:
        - This code expires in 10 minutes
        - Never share this code with anyone
        
        If you didn't request this verification, you can safely ignore this email.
        
        © 2024 SkillSync. All rights reserved.
        """,
        from_email="SkillSync <test@skillsync.studio>",
        use_resend=True  # Force Resend usage
    )
    
    if success:
        print("✅ SUCCESS: OTP email sent successfully!")
        print("📬 Check your Gmail inbox for the email")
        print("🔍 Check spam folder if not in inbox")
    else:
        print("❌ FAILED: OTP email could not be sent")
    
    print()
    print("=" * 50)
    return success

if __name__ == "__main__":
    test_otp_email_with_resend()
