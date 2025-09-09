import strawberry
import strawberry_django
from typing import Optional
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import OTP, TrustedDevice, OTPVerificationLink
from .types import (
    SendOTPInput, VerifyOTPInput, VerifyLinkInput, DeviceInfoInput,
    SendOTPPayload, VerifyOTPPayload, VerifyLinkPayload, 
    TrustedDevicePayload, DeviceCheckPayload, RevokeTrustedDeviceInput,
    RevokeTrustedDevicePayload
)
from users.types import UserType

User = get_user_model()


@strawberry.type
class OTPMutation:
    """GraphQL mutations for OTP operations"""

    @strawberry.mutation
    def send_otp(self, input: SendOTPInput, device_info: Optional[DeviceInfoInput] = None) -> SendOTPPayload:
        """
        Send OTP or verification link via email.
        
        Args:
            input: SendOTPInput with email and purpose
            device_info: Optional device information for trust checking
            
        Returns:
            SendOTPPayload: Result of the operation
        """
        try:
            # Check if user exists
            try:
                user = User.objects.get(email=input.email)
            except User.DoesNotExist:
                if input.purpose == 'signup':
                    return SendOTPPayload(
                        success=False,
                        message="User registration is required before OTP verification"
                    )
                else:
                    return SendOTPPayload(
                        success=False,
                        message="No account found with this email address"
                    )
            
            # Check if OTP is required based on device trust (for signin)
            requires_otp = True
            if input.purpose == 'signin' and device_info:
                device_fingerprint = TrustedDevice.generate_device_fingerprint(
                    device_info.ip_address, 
                    device_info.user_agent
                )
                
                # Check if this is the user's first login
                user_has_logged_in = user.last_login is not None
                
                if user_has_logged_in and TrustedDevice.is_device_trusted(user, device_fingerprint):
                    requires_otp = False
                    return SendOTPPayload(
                        success=True,
                        message="Device is trusted, OTP not required",
                        requires_otp=False
                    )
            
            # Create OTP and verification link
            otp, plain_code = OTP.create_otp(user, input.purpose, expiry_minutes=10)
            verification_link = OTPVerificationLink.create_verification_link(
                user, input.purpose, expiry_hours=1
            )
            
            # Send email with both OTP and verification link
            success = self._send_otp_email(user, plain_code, verification_link.token, input.purpose)
            
            if success:
                return SendOTPPayload(
                    success=True,
                    message=f"OTP and verification link sent to {input.email}",
                    requires_otp=True,
                    verification_link_sent=True
                )
            else:
                return SendOTPPayload(
                    success=False,
                    message="Failed to send OTP email. Please try again."
                )
                
        except Exception as e:
            return SendOTPPayload(
                success=False,
                message=f"An error occurred: {str(e)}"
            )

    @strawberry.mutation
    def verify_otp(self, input: VerifyOTPInput, device_info: Optional[DeviceInfoInput] = None) -> VerifyOTPPayload:
        """
        Verify OTP code for a user.
        
        Args:
            input: VerifyOTPInput with email, code, and purpose
            device_info: Optional device information for trusting
            
        Returns:
            VerifyOTPPayload: Result of the verification
        """
        try:
            # Get user
            try:
                user = User.objects.get(email=input.email)
            except User.DoesNotExist:
                return VerifyOTPPayload(
                    success=False,
                    message="No account found with this email address"
                )
            
            # Verify OTP
            success, message = OTP.verify_user_otp(user, input.code, input.purpose)
            
            if not success:
                return VerifyOTPPayload(
                    success=False,
                    message=message
                )
            
            # Handle post-verification actions based on purpose
            device_trusted = False
            
            if input.purpose == 'signup':
                # Activate user account
                user.account_status = 'active'
                user.save()
            
            # Trust device if requested and device info provided
            if input.trust_device and device_info:
                TrustedDevice.trust_device(
                    user, 
                    device_info.ip_address, 
                    device_info.user_agent,
                    device_info.device_name
                )
                device_trusted = True
            
            return VerifyOTPPayload(
                success=True,
                message="OTP verified successfully",
                user=user,
                device_trusted=device_trusted
            )
            
        except Exception as e:
            return VerifyOTPPayload(
                success=False,
                message=f"An error occurred: {str(e)}"
            )

    @strawberry.mutation
    def verify_link(self, input: VerifyLinkInput) -> VerifyLinkPayload:
        """
        Verify email verification link.
        
        Args:
            input: VerifyLinkInput with token and purpose
            
        Returns:
            VerifyLinkPayload: Result of the verification
        """
        try:
            user, success, message = OTPVerificationLink.verify_token(input.token, input.purpose)
            
            if not success:
                return VerifyLinkPayload(
                    success=False,
                    message=message
                )
            
            # Handle post-verification actions based on purpose
            if input.purpose == 'signup':
                # Activate user account
                user.account_status = 'active'
                user.save()
            
            return VerifyLinkPayload(
                success=True,
                message="Email verification successful",
                user=user
            )
            
        except Exception as e:
            return VerifyLinkPayload(
                success=False,
                message=f"An error occurred: {str(e)}"
            )

    @strawberry.mutation
    def check_device_trust(self, input: DeviceInfoInput, email: str) -> DeviceCheckPayload:
        """
        Check if a device is trusted for a user.
        
        Args:
            input: DeviceInfoInput with device information
            email: User's email address
            
        Returns:
            DeviceCheckPayload: Device trust status
        """
        try:
            # Get user
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return DeviceCheckPayload(
                    is_trusted=False,
                    requires_otp=True,
                    message="No account found with this email address"
                )
            
            # Check device trust
            device_fingerprint = TrustedDevice.generate_device_fingerprint(
                input.ip_address, 
                input.user_agent
            )
            
            # Check if this is the user's first login
            user_has_logged_in = user.last_login is not None
            
            if not user_has_logged_in:
                # First time login always requires OTP
                return DeviceCheckPayload(
                    is_trusted=False,
                    requires_otp=True,
                    message="First time login requires OTP verification"
                )
            
            is_trusted = TrustedDevice.is_device_trusted(user, device_fingerprint)
            
            return DeviceCheckPayload(
                is_trusted=is_trusted,
                requires_otp=not is_trusted,
                message="Device is trusted" if is_trusted else "Device requires OTP verification"
            )
            
        except Exception as e:
            return DeviceCheckPayload(
                is_trusted=False,
                requires_otp=True,
                message=f"An error occurred: {str(e)}"
            )

    @strawberry.mutation
    def revoke_trusted_device(self, input: RevokeTrustedDeviceInput) -> RevokeTrustedDevicePayload:
        """
        Revoke trust for a specific device.
        
        Args:
            input: RevokeTrustedDeviceInput with device ID
            
        Returns:
            RevokeTrustedDevicePayload: Result of the operation
        """
        try:
            device = TrustedDevice.objects.get(id=input.device_id)
            device.revoke_trust()
            
            return RevokeTrustedDevicePayload(
                success=True,
                message="Device trust revoked successfully"
            )
            
        except TrustedDevice.DoesNotExist:
            return RevokeTrustedDevicePayload(
                success=False,
                message="Trusted device not found"
            )
        except Exception as e:
            return RevokeTrustedDevicePayload(
                success=False,
                message=f"An error occurred: {str(e)}"
            )

    def _send_otp_email(self, user, otp_code, verification_token, purpose):
        """
        Send OTP email with both code and verification link.
        
        Args:
            user: User instance
            otp_code: Plain text OTP code
            verification_token: Verification link token
            purpose: Purpose of the OTP
            
        Returns:
            bool: True if email sent successfully
        """
        try:
            # Email subject based on purpose
            subject_map = {
                'signin': 'Sign In Verification Code',
                'signup': 'Complete Your Account Registration',
                'password_reset': 'Password Reset Verification',
                'device_verification': 'New Device Verification'
            }
            
            subject = subject_map.get(purpose, 'Verification Code')
            
            # Create verification URL
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            verification_url = f"{frontend_url}/verify?token={verification_token}&purpose={purpose}"
            
            # Email context
            context = {
                'user': user,
                'otp_code': otp_code,
                'verification_url': verification_url,
                'purpose': purpose,
                'purpose_display': subject_map.get(purpose, 'Verification'),
                'expiry_minutes': 10,  # OTP expiry
                'link_expiry_hours': 1,  # Link expiry
            }
            
            # For now, send a simple email (you can create HTML templates later)
            message = f"""
            Hi {user.username or user.email},

            Your verification code is: {otp_code}

            Alternatively, you can click this link to verify:
            {verification_url}

            This code will expire in 10 minutes.
            The verification link will expire in 1 hour.

            If you didn't request this, please ignore this email.

            Best regards,
            SkillSync Team
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@skillsync.com'),
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            return True
            
        except Exception as e:
            print(f"Email sending error: {e}")
            return False
