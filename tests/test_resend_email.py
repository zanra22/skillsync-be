#!/usr/bin/env python
"""
Test script to send actual emails via Resend.com
This bypasses Django's development console backend to test real email delivery.
"""
import os
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.base')
django.setup()

def test_resend_direct():
    """Test Resend API directly without Django settings override"""
    try:
        import resend
        
        # Set API key directly (replace with your actual key)
        resend.api_key = "re_g33y1aGk_CyhMaXnUUu32fSJ6cSVAGeM7"
        
        # Test email data
        email_data = {
            "from": "SkillSync Test <test@skillsync.studio>",
            "to": ["arnazdj69@gmail.com"],
            "subject": "SkillSync - Resend Test Email",
            "html": """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>SkillSync - Test Email</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background: #4F46E5; color: white; padding: 20px; text-align: center; }
                    .content { padding: 30px 20px; background: #f9f9f9; }
                    .test-code { 
                        font-size: 32px; 
                        font-weight: bold; 
                        text-align: center; 
                        background: #10B981; 
                        color: white; 
                        padding: 15px; 
                        margin: 20px 0; 
                        border-radius: 8px;
                        letter-spacing: 3px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>SkillSync</h1>
                        <p>Resend Integration Test</p>
                    </div>
                    
                    <div class="content">
                        <h2>🎉 Success!</h2>
                        
                        <p>This email was sent successfully via Resend.com API!</p>
                        
                        <div class="test-code">TEST-123</div>
                        
                        <p><strong>Integration Status:</strong> ✅ Working</p>
                        <p><strong>Email Service:</strong> Resend.com</p>
                        <p><strong>Test Time:</strong> September 10, 2025</p>
                        
                        <p>Your SkillSync OTP email system is now ready for production!</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            "text": """
            SkillSync - Resend Integration Test
            
            🎉 Success!
            
            This email was sent successfully via Resend.com API!
            
            Test Code: TEST-123
            
            Integration Status: ✅ Working
            Email Service: Resend.com
            Test Time: September 10, 2025
            
            Your SkillSync OTP email system is now ready for production!
            """
        }
        
        # Send email
        print("📧 Sending test email via Resend.com...")
        response = resend.Emails.send(email_data)
        
        print(f"✅ Email sent successfully!")
        print(f"📨 Email ID: {response.get('id')}")
        print(f"📍 Sent to: arnazdj69@gmail.com")
        print(f"🕒 Check your Gmail inbox (including spam folder)")
        
        return True
        
    except ImportError:
        print("❌ Resend package not installed. Run: pip install resend")
        return False
    except Exception as e:
        print(f"❌ Error sending email: {str(e)}")
        return False

def test_django_email_service():
    """Test our Django email service with forced Resend usage"""
    try:
        from helpers.email_service import send_email_with_resend
        
        print("📧 Testing Django email service with Resend...")
        
        success = send_email_with_resend(
            to_email="arnazdj69@gmail.com",
            subject="SkillSync - Django Service Test",
            html_content="""
            <h2>Django Email Service Test</h2>
            <p>This email was sent through the Django email service using Resend.com!</p>
            <div style="background: #4F46E5; color: white; padding: 10px; text-align: center; border-radius: 5px;">
                <strong>Integration Working! 🎉</strong>
            </div>
            """,
            text_content="Django Email Service Test\n\nThis email was sent through the Django email service using Resend.com!\n\nIntegration Working! 🎉"
        )
        
        if success:
            print("✅ Django email service test successful!")
            print("📍 Check your Gmail inbox")
        else:
            print("❌ Django email service test failed")
            
        return success
        
    except Exception as e:
        print(f"❌ Error testing Django email service: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 SkillSync Email Integration Test")
    print("=" * 50)
    
    print("\n1️⃣ Testing direct Resend API...")
    direct_success = test_resend_direct()
    
    print("\n2️⃣ Testing Django email service...")
    django_success = test_django_email_service()
    
    print("\n" + "=" * 50)
    if direct_success or django_success:
        print("🎉 SUCCESS: Email integration is working!")
        print("📧 Check your Gmail inbox (arnazdj69@gmail.com)")
        print("📝 Note: Check spam folder if you don't see the email")
    else:
        print("❌ FAILED: Email integration needs configuration")
        print("🔧 Check your Resend API key and try again")
