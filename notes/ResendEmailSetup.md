# Resend.com Email Service Setup Guide

## Overview
This guide explains how to configure Resend.com for SkillSync's email system, replacing the Gmail SMTP configuration with a professional transactional email service.

## Why Resend.com?
- Professional transactional email service
- Better deliverability rates than Gmail SMTP
- Detailed email analytics and tracking
- No daily sending limits like Gmail
- Built specifically for application emails

## Setup Steps

### 1. Create Resend Account
1. Go to [resend.com](https://resend.com)
2. Sign up for a free account (100 emails/day on free tier)
3. Verify your email address

### 2. Add Your Domain (Recommended)
1. In Resend dashboard, go to "Domains"
2. Add your domain (e.g., `skillsync.studio`)
3. Configure DNS records as shown:
   - Add MX record
   - Add DKIM record
   - Add DMARC record (optional but recommended)
4. Verify domain ownership

### 3. Get API Key
1. Go to "API Keys" in Resend dashboard
2. Click "Create API Key"
3. Name it (e.g., "SkillSync Production")
4. Copy the API key (starts with `re_`)

### 4. Configure Environment Variables
Add to your `.env` file:
```bash
RESEND_API_KEY=re_your_actual_api_key_here
```

### 5. Update Email Settings
The email configuration is already set up in `config/constants.py`:

```python
EMAIL_CONFIG = {
    "development": {
        "BACKEND": "django.core.mail.backends.console.EmailBackend",  # Console for dev
        "RESEND_API_KEY": os.getenv("RESEND_API_KEY"),
        "DEFAULT_FROM_EMAIL": "SkillSync Dev <dev@skillsync.studio>",
    },
    "production": {
        "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "RESEND_API_KEY": os.getenv("RESEND_API_KEY"),
        "DEFAULT_FROM_EMAIL": "SkillSync <noreply@skillsync.studio>",
    },
}
```

### 6. Email Address Configuration
Update the `DEFAULT_FROM_EMAIL` addresses in `config/constants.py`:

- **Development**: `dev@skillsync.studio` (for testing)
- **Staging**: `staging@skillsync.studio` (for staging tests)
- **Production**: `noreply@skillsync.studio` (for live emails)

### 7. Testing the Integration

#### Test in Development:
```python
# Development uses console backend, so emails appear in terminal
python manage.py shell
from helpers.email_service import send_otp_email
send_otp_email(
    to_email="test@example.com",
    otp_code="123456",
    verification_url="http://localhost:3000/verify?token=abc123",
    username="Test User"
)
```

#### Test in Production:
```python
# Production uses Resend API
from helpers.email_service import send_otp_email
success = send_otp_email(
    to_email="your-email@example.com",
    otp_code="123456",
    verification_url="https://skillsync.studio/verify?token=abc123",
    username="Test User"
)
print(f"Email sent: {success}")
```

## Email Templates

The new email service includes professional HTML templates with:
- Responsive design
- SkillSync branding
- Security warnings
- Clear call-to-action buttons
- Fallback plain text version

## Monitoring and Analytics

### Resend Dashboard
- Track email delivery rates
- Monitor bounces and complaints
- View email opens and clicks
- Debug delivery issues

### Django Logs
Email sending is logged at the INFO level:
```
[INFO] Email sent successfully to user@example.com via Resend. ID: abc123
[ERROR] Failed to send email via Resend: API key not configured
```

## Security Best Practices

### API Key Security
- Never commit API keys to version control
- Use different API keys for different environments
- Regularly rotate API keys
- Set up IP restrictions in Resend dashboard

### Email Security
- Use DKIM signing (automatic with Resend)
- Configure SPF records
- Set up DMARC policy
- Monitor for email spoofing

## Troubleshooting

### Common Issues

1. **API Key Not Working**
   - Check if API key is correctly set in `.env`
   - Verify API key hasn't expired
   - Check Resend dashboard for key status

2. **Domain Not Verified**
   - Complete DNS record setup
   - Wait for DNS propagation (up to 24 hours)
   - Use Resend's verification tools

3. **Emails Not Delivering**
   - Check Resend logs for bounces
   - Verify recipient email addresses
   - Check spam folders
   - Review domain reputation

4. **Development Issues**
   - Development mode uses console backend
   - Check terminal output for emails
   - Verify ENVIRONMENT variable is set correctly

### Fallback System
The email service automatically falls back to Django SMTP if Resend fails:
1. Tries Resend API first
2. Falls back to Django `send_mail` if Resend fails
3. Logs all attempts for debugging

## Migration from Gmail SMTP

### Before Migration
- OTP emails sent via Gmail SMTP
- Limited to Gmail's sending limits
- Basic text-only emails
- No delivery tracking

### After Migration
- Professional email service
- Higher sending limits
- Rich HTML email templates
- Delivery analytics and tracking
- Better spam folder avoidance

## Cost Considerations

### Resend Pricing (as of 2024)
- **Free Tier**: 100 emails/day
- **Pro Tier**: $20/month for 50,000 emails
- **Business Tier**: $80/month for 100,000 emails

### Gmail SMTP Limitations
- 500 emails/day limit
- Potential account suspension
- No delivery analytics
- Poor deliverability for app emails

## Next Steps

1. ✅ Install Resend Python SDK (`pip install resend`)
2. ⏳ Create Resend account and get API key
3. ⏳ Add API key to environment variables
4. ⏳ Test email sending in development
5. ⏳ Configure production domain and DNS
6. ⏳ Deploy to production and test live emails

## Support

- **Resend Documentation**: https://resend.com/docs
- **Resend Support**: https://resend.com/support
- **Django Email Documentation**: https://docs.djangoproject.com/en/stable/topics/email/
