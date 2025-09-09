import strawberry
import strawberry_django
from typing import Optional
from django.contrib.auth import get_user_model
from users.types import UserType
from .models import OTP, TrustedDevice, OTPVerificationLink

User = get_user_model()


@strawberry.input
class SendOTPInput:
    """Input type for sending OTP"""
    email: str
    purpose: str  # signin, signup, password_reset, device_verification


@strawberry.input
class VerifyOTPInput:
    """Input type for verifying OTP"""
    email: str
    code: str
    purpose: str
    trust_device: Optional[bool] = False


@strawberry.input
class VerifyLinkInput:
    """Input type for verifying email link"""
    token: str
    purpose: str


@strawberry.input
class DeviceInfoInput:
    """Input type for device information"""
    user_agent: str
    ip_address: str
    device_name: Optional[str] = None


@strawberry.type
class SendOTPPayload:
    """Response payload for send OTP mutation"""
    success: bool
    message: str
    requires_otp: bool = False
    verification_link_sent: bool = False


@strawberry.type
class VerifyOTPPayload:
    """Response payload for verify OTP mutation"""
    success: bool
    message: str
    user: Optional[UserType] = None
    device_trusted: bool = False


@strawberry.type
class VerifyLinkPayload:
    """Response payload for verify link mutation"""
    success: bool
    message: str
    user: Optional[UserType] = None


@strawberry_django.type(TrustedDevice)
class TrustedDeviceType:
    """GraphQL type for TrustedDevice model"""
    id: strawberry.auto
    device_name: strawberry.auto
    ip_address: strawberry.auto
    last_used: strawberry.auto
    is_active: strawberry.auto
    created_at: strawberry.auto


@strawberry.type
class TrustedDevicePayload:
    """Response payload for trusted device operations"""
    success: bool
    message: str
    device: Optional[TrustedDeviceType] = None


@strawberry.type
class DeviceCheckPayload:
    """Response payload for device trust check"""
    is_trusted: bool
    requires_otp: bool
    message: str


@strawberry.input
class RevokeTrustedDeviceInput:
    """Input type for revoking trusted device"""
    device_id: str


@strawberry.type
class RevokeTrustedDevicePayload:
    """Response payload for revoking trusted device"""
    success: bool
    message: str
