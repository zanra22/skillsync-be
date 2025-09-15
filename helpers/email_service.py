"""
Email service utilities for SkillSync.
Handles both Django SMTP and Resend API integration.
"""
import logging
from typing import Optional, Dict, Any
from django.conf import settings
from django.core.mail import send_mail as django_send_mail

# Setup logging
logger = logging.getLogger(__name__)

def send_email_with_resend(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
    from_email: Optional[str] = None,
    **kwargs
) -> bool:
    """
    Send email using Resend API service.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email content
        text_content: Plain text content (optional)
        from_email: Sender email (optional, uses DEFAULT_FROM_EMAIL if not provided)
        **kwargs: Additional Resend API parameters
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        import resend
        
        # Configure Resend API
        resend.api_key = settings.RESEND_API_KEY
        
        if not resend.api_key:
            logger.error("RESEND_API_KEY not configured")
            return False
        
        # Prepare email data
        email_data = {
            "from": from_email or settings.DEFAULT_FROM_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }
        
        # Add text content if provided
        if text_content:
            email_data["text"] = text_content
        
        # Add any additional parameters
        email_data.update(kwargs)
        
        # Send email
        response = resend.Emails.send(email_data)
        
        logger.info(f"Email sent successfully to {to_email} via Resend. ID: {response.get('id')}")
        return True
        
    except ImportError:
        logger.error("Resend package not installed. Install with: pip install resend")
        return False
    except Exception as e:
        logger.error(f"Failed to send email via Resend: {str(e)}")
        return False


def send_email_fallback(
    to_email: str,
    subject: str,
    message: str,
    from_email: Optional[str] = None,
    html_message: Optional[str] = None,
) -> bool:
    """
    Send email using Django's built-in email backend as fallback.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        message: Plain text message
        from_email: Sender email (optional)
        html_message: HTML message content (optional)
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        django_send_mail(
            subject=subject,
            message=message,
            from_email=from_email or settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Email sent successfully to {to_email} via Django SMTP")
        return True
    except Exception as e:
        logger.error(f"Failed to send email via Django SMTP: {str(e)}")
        return False


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
    from_email: Optional[str] = None,
    use_resend: bool = True,
    force_resend: bool = False,
    **kwargs
) -> bool:
    """
    Universal email sending function with automatic fallback.
    
    Attempts to send via Resend API first, falls back to Django SMTP if needed.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email content
        text_content: Plain text content (optional, will use html_content if not provided)
        from_email: Sender email (optional)
        use_resend: Whether to attempt Resend API first (default: True)
        force_resend: Force using Resend even in development (for testing)
        **kwargs: Additional parameters for Resend API
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    # Validate inputs
    if not to_email or not subject or not html_content:
        logger.error("Missing required email parameters")
        return False
    
    # Force Resend usage if requested (for testing)
    if force_resend and use_resend and hasattr(settings, 'RESEND_API_KEY') and settings.RESEND_API_KEY:
        logger.info("Force using Resend API (bypassing development console backend)")
        success = send_email_with_resend(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            from_email=from_email,
            **kwargs
        )
        
        if success:
            return True
        
        logger.warning("Forced Resend API failed, falling back to Django SMTP")
    
    # For all environments, try Resend first if enabled
    if use_resend and hasattr(settings, 'RESEND_API_KEY') and settings.RESEND_API_KEY:
        success = send_email_with_resend(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            from_email=from_email,
            **kwargs
        )
        
        if success:
            return True
        
        logger.warning("Resend API failed, falling back to Django SMTP")
    
    # Fallback to Django SMTP
    return send_email_fallback(
        to_email=to_email,
        subject=subject,
        message=text_content or html_content,
        from_email=from_email,
        html_message=html_content,
    )


# OTP-specific email templates and functions
def send_otp_email(
    to_email: str,
    otp_code: str,
    verification_url: str,
    username: str = "User",
    force_resend: bool = False,
    **kwargs
) -> bool:
    """
    Send OTP verification email with consistent formatting.
    
    Args:
        to_email: Recipient email address
        otp_code: 6-digit OTP code
        verification_url: URL for email verification
        username: User's name for personalization
        force_resend: Force using Resend API even in development
        **kwargs: Additional email parameters
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    subject = "Your SkillSync Verification Code"
    
    # HTML email template
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SkillSync - Verification Code</title>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }}
            
            body {{ 
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                line-height: 1.6; 
                color: #1e293b; 
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 25%, #065f46 75%, #06b6d4 100%);
                margin: 0;
                padding: 20px 0;
            }}
            
            .email-container {{ 
                max-width: 600px; 
                margin: 0 auto; 
                background: #ffffff;
                border-radius: 16px;
                overflow: hidden;
                box-shadow: 0 10px 40px -10px rgba(15, 23, 42, 0.15);
            }}
            
            .header {{ 
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                color: white; 
                padding: 40px 20px; 
                text-align: center;
                position: relative;
                overflow: hidden;
            }}
            
            .header::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: radial-gradient(ellipse at top, rgba(6, 182, 212, 0.1) 0%, transparent 50%);
                pointer-events: none;
            }}
            
            .header-content {{
                position: relative;
                z-index: 1;
            }}
            
            .logo {{ 
                font-family: 'Poppins', sans-serif;
                font-size: 32px; 
                font-weight: 700; 
                margin-bottom: 8px;
                background: linear-gradient(135deg, #06b6d4, #8b5cf6);
                -webkit-background-clip: text;
                background-clip: text;
                -webkit-text-fill-color: transparent;
                color: transparent;
            }}
            
            .tagline {{ 
                font-size: 16px; 
                opacity: 0.9;
                font-weight: 400;
            }}
            
            .content {{ 
                padding: 40px 30px;
                background: #ffffff;
            }}
            
            .greeting {{ 
                font-family: 'Poppins', sans-serif;
                font-size: 24px; 
                font-weight: 600; 
                color: #0f172a;
                margin-bottom: 20px;
            }}
            
            .description {{ 
                font-size: 16px; 
                color: #475569; 
                margin-bottom: 30px;
                line-height: 1.7;
            }}
            
            .otp-section {{ 
                text-align: center; 
                margin: 35px 0;
            }}
            
            .otp-label {{ 
                font-family: 'Poppins', sans-serif;
                font-size: 14px; 
                font-weight: 600; 
                color: #06b6d4; 
                text-transform: uppercase; 
                letter-spacing: 1px;
                margin-bottom: 15px;
            }}
            
            .otp-code {{ 
                display: inline-block;
                font-family: 'Poppins', sans-serif;
                font-size: 36px; 
                font-weight: 700; 
                color: #ffffff;
                background: linear-gradient(135deg, #06b6d4, #0891b2);
                padding: 20px 30px; 
                border-radius: 12px;
                letter-spacing: 6px;
                box-shadow: 0 8px 30px rgba(6, 182, 212, 0.3);
                border: 3px solid rgba(255, 255, 255, 0.2);
            }}
            
            .divider {{ 
                text-align: center; 
                margin: 35px 0; 
                position: relative;
            }}
            
            .divider::before {{
                content: '';
                position: absolute;
                top: 50%;
                left: 0;
                right: 0;
                height: 1px;
                background: linear-gradient(90deg, transparent, #e2e8f0, transparent);
            }}
            
            .divider-text {{ 
                background: #ffffff; 
                padding: 0 20px; 
                color: #64748b; 
                font-size: 14px;
                font-weight: 500;
            }}
            
            .action-section {{ 
                text-align: center; 
                margin: 30px 0;
            }}
            
            .action-button {{ 
                display: inline-block;
                font-family: 'Poppins', sans-serif;
                background: linear-gradient(135deg, #0f172a, #1e293b);
                color: white; 
                padding: 16px 32px; 
                text-decoration: none; 
                border-radius: 12px; 
                font-weight: 600;
                font-size: 16px;
                transition: all 0.3s ease;
                box-shadow: 0 6px 20px rgba(15, 23, 42, 0.3);
                border: 2px solid rgba(6, 182, 212, 0.2);
            }}
            
            .action-button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(15, 23, 42, 0.4);
            }}
            
            .security-note {{ 
                background: linear-gradient(135deg, #fef3c7, #fde68a);
                border-left: 4px solid #f59e0b;
                border-radius: 8px;
                padding: 20px; 
                margin: 30px 0;
            }}
            
            .security-note-title {{
                font-family: 'Poppins', sans-serif;
                font-weight: 600; 
                color: #92400e;
                margin-bottom: 10px;
                display: flex;
                align-items: center;
            }}
            
            .security-note-title::before {{
                content: '🔒';
                margin-right: 8px;
                font-size: 18px;
            }}
            
            .security-list {{ 
                list-style: none; 
                padding-left: 0;
                color: #92400e;
            }}
            
            .security-list li {{ 
                margin: 8px 0;
                padding-left: 20px;
                position: relative;
            }}
            
            .security-list li::before {{
                content: '•';
                color: #f59e0b;
                font-weight: bold;
                position: absolute;
                left: 0;
            }}
            
            .footer {{ 
                background: linear-gradient(135deg, #f8fafc, #f1f5f9);
                text-align: center; 
                padding: 30px 20px; 
                border-top: 1px solid #e2e8f0;
            }}
            
            .footer-text {{ 
                color: #64748b; 
                font-size: 14px;
                margin: 5px 0;
            }}
            
            .footer-brand {{ 
                font-family: 'Poppins', sans-serif;
                font-weight: 600;
                color: #0f172a;
            }}
            
            .expiry-notice {{
                background: linear-gradient(135deg, #e0f2fe, #bae6fd);
                border: 1px solid #06b6d4;
                border-radius: 8px;
                padding: 15px;
                margin: 25px 0;
                text-align: center;
            }}
            
            .expiry-notice-text {{
                color: #0891b2;
                font-weight: 600;
                font-size: 14px;
            }}
            
            /* Responsive Design */
            @media only screen and (max-width: 600px) {{
                .email-container {{ margin: 10px; }}
                .content {{ padding: 30px 20px; }}
                .otp-code {{ font-size: 28px; padding: 15px 20px; letter-spacing: 4px; }}
                .greeting {{ font-size: 20px; }}
                .action-button {{ padding: 14px 24px; font-size: 15px; }}
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="header">
                <div class="header-content">
                    <div class="logo">SkillSync</div>
                    <div class="tagline">Your Learning Journey Continues</div>
                </div>
            </div>
            
            <div class="content">
                <h1 class="greeting">Hello {username}! 👋</h1>
                
                <p class="description">
                    We received a request to verify your email address. Use your verification code below to continue your SkillSync journey.
                </p>
                
                <div class="otp-section">
                    <div class="otp-label">Your Verification Code</div>
                    <div class="otp-code">{otp_code}</div>
                </div>
                
                <div class="expiry-notice">
                    <div class="expiry-notice-text">⏰ This code expires in 10 minutes</div>
                </div>
                
                <div class="divider">
                    <span class="divider-text">or verify with one click</span>
                </div>
                
                <div class="action-section">
                    <a href="{verification_url}" class="action-button">
                        ✨ Verify Email Address
                    </a>
                </div>
                
                <div class="security-note">
                    <div class="security-note-title">Security Information</div>
                    <ul class="security-list">
                        <li>This code expires in 10 minutes for your security</li>
                        <li>Never share this code with anyone</li>
                        <li>SkillSync will never ask for your code via phone or email</li>
                        <li>If you didn't request this, you can safely ignore this email</li>
                    </ul>
                </div>
                
                <p class="description" style="margin-top: 30px; text-align: center; font-style: italic;">
                    Ready to continue learning? We're excited to have you back! 🚀
                </p>
            </div>
            
            <div class="footer">
                <p class="footer-text footer-brand">© 2024 SkillSync. All rights reserved.</p>
                <p class="footer-text">Empowering learners with AI-powered skill development</p>
                <p class="footer-text" style="margin-top: 15px;">
                    This is an automated message, please do not reply to this email.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Plain text version
    text_content = f"""
    ═══════════════════════════════════════════════════════════
    ✨ SkillSync - Email Verification ✨
    ═══════════════════════════════════════════════════════════
    
    Hello {username}! 👋
    
    We received a request to verify your email address for your SkillSync account.
    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    🔐 YOUR VERIFICATION CODE: {otp_code}
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    ⏰ This code expires in 10 minutes
    
    🚀 Quick Verification Link:
    {verification_url}
    
    🔒 Security Information:
    • This code expires in 10 minutes for your security
    • Never share this code with anyone
    • SkillSync will never ask for your code via phone or email
    • If you didn't request this, you can safely ignore this email
    
    Ready to continue your learning journey? We're excited to have you back! 🎯
    
    ─────────────────────────────────────────────────────────────
    © 2024 SkillSync. All rights reserved.
    Empowering learners with AI-powered skill development
    
    This is an automated message, please do not reply.
    ═══════════════════════════════════════════════════════════
    """
    
    return send_email(
        to_email=to_email,
        subject=subject,
        html_content=html_content,
        text_content=text_content,
        force_resend=force_resend,
        **kwargs
    )
