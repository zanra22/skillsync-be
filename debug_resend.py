#!/usr/bin/env python3
"""
Debug script for Resend.com integration issues
"""
import os
import sys
import django

# Setup Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.base')
django.setup()

from dotenv import load_dotenv
load_dotenv()

def test_resend_api():
    """Test Resend API with detailed error reporting"""
    print("🔍 Debugging Resend.com Integration")
    print("=" * 50)
    
    # Check API key
    api_key = os.getenv('RESEND_API_KEY')
    print(f"📋 API Key: {api_key[:10]}...{api_key[-4:] if api_key else 'NOT FOUND'}")
    
    if not api_key:
        print("❌ ERROR: RESEND_API_KEY not found in environment")
        return False
    
    if not api_key.startswith('re_'):
        print("❌ ERROR: Invalid API key format (should start with 're_')")
        return False
    
    try:
        import resend
        print("✅ Resend package imported successfully")
    except ImportError as e:
        print(f"❌ ERROR: Cannot import resend package: {e}")
        print("💡 Install with: pip install resend")
        return False
    
    # Configure Resend
    resend.api_key = api_key
    print(f"✅ API key configured")
    
    # Test API connection
    try:
        print("\n🧪 Testing API connection...")
        
        # Simple test email
        email_data = {
            "from": "SkillSync <onboarding@resend.dev>",  # Use Resend's test domain
            "to": ["arnazdj69@gmail.com"],
            "subject": "SkillSync Test Email",
            "html": "<h1>Hello from SkillSync!</h1><p>This is a test email from Resend.com</p>",
            "text": "Hello from SkillSync! This is a test email from Resend.com"
        }
        
        print(f"📧 Sending test email to: arnazdj69@gmail.com")
        print(f"📧 From: {email_data['from']}")
        
        # Send email
        response = resend.Emails.send(email_data)
        
        print(f"✅ SUCCESS! Email sent successfully")
        print(f"📨 Response: {response}")
        print(f"🆔 Email ID: {response.get('id', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Failed to send email")
        print(f"🔍 Error type: {type(e).__name__}")
        print(f"🔍 Error message: {str(e)}")
        
        # Check for common issues
        if "401" in str(e) or "Unauthorized" in str(e):
            print("💡 Possible issue: Invalid API key")
        elif "403" in str(e) or "Forbidden" in str(e):
            print("💡 Possible issue: Domain not verified or sending limits exceeded")
        elif "domain" in str(e).lower():
            print("💡 Possible issue: Email domain not verified with Resend")
        elif "rate" in str(e).lower() or "limit" in str(e).lower():
            print("💡 Possible issue: Rate limit exceeded")
        
        return False

def test_domain_options():
    """Test different from domains"""
    print("\n🌐 Testing different from domains...")
    
    import resend
    resend.api_key = os.getenv('RESEND_API_KEY')
    
    test_domains = [
        "onboarding@resend.dev",  # Resend's test domain
        "test@skillsync.studio",  # Your domain (if verified)
        "noreply@skillsync.studio",  # Your domain (if verified)
    ]
    
    for from_email in test_domains:
        try:
            print(f"\n📧 Testing from: {from_email}")
            
            response = resend.Emails.send({
                "from": f"SkillSync <{from_email}>",
                "to": ["arnazdj69@gmail.com"],
                "subject": f"Test from {from_email}",
                "html": f"<p>Test email from {from_email}</p>",
            })
            
            print(f"✅ SUCCESS with {from_email}")
            print(f"🆔 Email ID: {response.get('id')}")
            return from_email
            
        except Exception as e:
            print(f"❌ FAILED with {from_email}: {str(e)}")
            continue
    
    return None

def main():
    """Main debugging function"""
    print("🚀 Starting Resend.com debug session...\n")
    
    # Test basic API
    success = test_resend_api()
    
    if not success:
        print("\n🔧 Trying different from domains...")
        working_domain = test_domain_options()
        
        if working_domain:
            print(f"\n✅ Found working domain: {working_domain}")
            print("💡 Update your email configuration to use this domain")
        else:
            print("\n❌ No working domains found")
            print("\n🔧 Troubleshooting steps:")
            print("1. Verify your Resend API key at https://resend.com/api-keys")
            print("2. Check if your domain is verified at https://resend.com/domains")
            print("3. Try using onboarding@resend.dev for testing")
            print("4. Check Resend logs at https://resend.com/logs")
    else:
        print("\n🎉 Resend integration is working correctly!")
    
    print("\n" + "=" * 50)
    print("Debug session complete")

if __name__ == "__main__":
    main()
