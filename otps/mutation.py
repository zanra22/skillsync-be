import strawberry
import strawberry_django
from typing import Optional
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from asgiref.sync import sync_to_async
from helpers.email_service import send_otp_email
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
    async def send_otp(self, input: SendOTPInput, device_info: Optional[DeviceInfoInput] = None) -> SendOTPPayload:
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
                user = await sync_to_async(User.objects.get)(email=input.email)
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
                
                # For super_admin, ALWAYS require OTP regardless of device trust
                if user.role == 'super_admin':
                    requires_otp = True
                    # Continue to send OTP, don't return early
                else:
                    # Check if this is the user's first login
                    user_has_logged_in = user.last_login is not None
                    
                    if not user_has_logged_in:
                        # First time login always requires OTP
                        requires_otp = True
                    else:
                        # Check if device is trusted for returning users
                        if await sync_to_async(TrustedDevice.is_device_trusted)(user, device_fingerprint):
                            requires_otp = False
                            return SendOTPPayload(
                                success=True,
                                message="Device is trusted, OTP not required",
                                requires_otp=False
                            )
            
            # Create OTP and verification link
            # Create OTP with extended expiry for testing
            otp, plain_code = await sync_to_async(OTP.create_otp)(user, input.purpose, expiry_minutes=10)
            verification_link = await sync_to_async(OTPVerificationLink.create_verification_link)(
                user, input.purpose, expiry_hours=1
            )
            
            # Send email with both OTP and verification link
            success = await self._send_otp_email(user, plain_code, verification_link.token, input.purpose)
            
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
    async def verify_otp(self, input: VerifyOTPInput, device_info: Optional[DeviceInfoInput] = None) -> VerifyOTPPayload:
        """
        Verify OTP code for a user.
        
        Args:
            input: VerifyOTPInput with email, code, and purpose
            device_info: Optional device information for trusting
            
        Returns:
            VerifyOTPPayload: Result of the verification
        """
        try:
            # Debug logging
            print(f"DEBUG: Verifying OTP for email={input.email}, purpose={input.purpose}, code={input.code}")
            
            # Get user
            try:
                user = await sync_to_async(User.objects.get)(email=input.email)
                print(f"DEBUG: Found user {user.email}")
            except User.DoesNotExist:
                print(f"DEBUG: No user found with email {input.email}")
                return VerifyOTPPayload(
                    success=False,
                    message="No account found with this email address"
                )
            
            # Check for valid OTPs
            active_otps = await sync_to_async(list)(OTP.objects.filter(
                user=user,
                purpose=input.purpose,
                used_at__isnull=True,
                expires_at__gt=timezone.now()
            ))
            print(f"DEBUG: Found {len(active_otps)} active OTPs for this user and purpose")
            
            # Verify OTP
            success, message = await sync_to_async(OTP.verify_user_otp)(user, input.code, input.purpose)
            print(f"DEBUG: Verification result: success={success}, message={message}")
            
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
                await sync_to_async(user.save)()
            
            # Trust device if requested and device info provided
            if input.trust_device and device_info:
                await sync_to_async(TrustedDevice.trust_device)(
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
    async def verify_link(self, input: VerifyLinkInput) -> VerifyLinkPayload:
        """
        Verify email verification link.
        
        Args:
            input: VerifyLinkInput with token and purpose
            
        Returns:
            VerifyLinkPayload: Result of the verification
        """
        try:
            user, success, message = await sync_to_async(OTPVerificationLink.verify_token)(input.token, input.purpose)
            
            if not success:
                return VerifyLinkPayload(
                    success=False,
                    message=message
                )
            
            # Handle post-verification actions based on purpose
            if input.purpose == 'signup':
                # Activate user account
                user.account_status = 'active'
                await sync_to_async(user.save)()
            
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
    async def check_device_trust(self, input: DeviceInfoInput, email: str) -> DeviceCheckPayload:
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
                user = await sync_to_async(User.objects.get)(email=email)
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
            
            # For super_admin, ALWAYS require OTP regardless of device trust or login history
            if user.role == 'super_admin':
                return DeviceCheckPayload(
                    is_trusted=False,  # Force untrusted for super admin
                    requires_otp=True,
                    message="Super admin requires OTP verification"
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
            
            is_trusted = await sync_to_async(TrustedDevice.is_device_trusted)(user, device_fingerprint)
            
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
    async def revoke_trusted_device(self, input: RevokeTrustedDeviceInput) -> RevokeTrustedDevicePayload:
        """
        Revoke trust for a specific device.
        
        Args:
            input: RevokeTrustedDeviceInput with device ID
            
        Returns:
            RevokeTrustedDevicePayload: Result of the operation
        """
        try:
            device = await sync_to_async(TrustedDevice.objects.get)(id=input.device_id)
            await sync_to_async(device.revoke_trust)()
            
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

    async def _send_otp_email(self, user, otp_code, verification_token, purpose):
        """
        Send OTP email with both code and verification link using Resend service.
        
        Args:
            user: User instance
            otp_code: Plain text OTP code
            verification_token: Verification link token
            purpose: Purpose of the OTP
            
        Returns:
            bool: True if email sent successfully
        """
        try:
            # Create verification URL
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            verification_url = f"{frontend_url}/verify?token={verification_token}&purpose={purpose}"
            
            # Get user's display name
            username = user.username or user.first_name or user.email.split('@')[0]
            
            # Send email using our Resend service (make it async if needed)
            success = await sync_to_async(send_otp_email)(
                to_email=user.email,
                otp_code=otp_code,
                verification_url=verification_url,
                username=username,
                purpose=purpose  # Pass purpose for potential customization
            )
            
            if success:
                print(f"OTP email sent successfully to {user.email} for {purpose}")
            else:
                print(f"Failed to send OTP email to {user.email} for {purpose}")
            
            return success
            
        except Exception as e:
            print(f"Email sending error: {e}")
            return False
