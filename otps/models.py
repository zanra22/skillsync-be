from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import random
import string
import hashlib
import secrets
from helpers.generate_short_id import generate_short_id

User = get_user_model()


class TrustedDevice(models.Model):
    """
    Model for tracking user's trusted devices to determine when OTP is required.
    """
    
    id = models.CharField(
        max_length=10,
        primary_key=True,
        default=generate_short_id,
        editable=False
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='trusted_devices'
    )
    device_fingerprint = models.CharField(
        max_length=64,  # SHA-256 hash of device info
        help_text="Hashed device fingerprint (IP + User-Agent + other factors)"
    )
    device_name = models.CharField(
        max_length=255,
        help_text="Human-readable device name (e.g., Chrome on Windows)"
    )
    ip_address = models.GenericIPAddressField()
    last_used = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'trusted_devices'
        ordering = ['-last_used']
        verbose_name = 'Trusted Device'
        verbose_name_plural = 'Trusted Devices'
        unique_together = [['user', 'device_fingerprint']]
        indexes = [
            models.Index(fields=['user', 'device_fingerprint']),
            models.Index(fields=['user', 'is_active', 'last_used']),
        ]

    def __str__(self):
        return f"{self.device_name} for {self.user.email}"

    @staticmethod
    def generate_device_fingerprint(ip_address, user_agent, additional_data=None):
        """
        Generate a unique device fingerprint based on multiple factors.
        
        Args:
            ip_address: Client IP address
            user_agent: Browser user agent string
            additional_data: Additional device info (optional)
            
        Returns:
            str: SHA-256 hash of device fingerprint
        """
        fingerprint_data = f"{ip_address}:{user_agent}"
        if additional_data:
            fingerprint_data += f":{additional_data}"
        
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()

    @staticmethod
    def is_device_trusted(user, device_fingerprint):
        """
        Check if a device is trusted for the user.
        
        Args:
            user: User instance
            device_fingerprint: Device fingerprint hash
            
        Returns:
            bool: True if device is trusted, False otherwise
        """
        return TrustedDevice.objects.filter(
            user=user,
            device_fingerprint=device_fingerprint,
            is_active=True
        ).exists()

    @staticmethod
    def trust_device(user, ip_address, user_agent, device_name=None):
        """
        Mark a device as trusted for the user.
        
        Args:
            user: User instance
            ip_address: Client IP address
            user_agent: Browser user agent string
            device_name: Human-readable device name (optional)
            
        Returns:
            TrustedDevice: Created or updated device instance
        """
        device_fingerprint = TrustedDevice.generate_device_fingerprint(ip_address, user_agent)
        
        if not device_name:
            # Generate a basic device name from user agent
            device_name = TrustedDevice._parse_device_name(user_agent)
        
        device, created = TrustedDevice.objects.update_or_create(
            user=user,
            device_fingerprint=device_fingerprint,
            defaults={
                'device_name': device_name,
                'ip_address': ip_address,
                'last_used': timezone.now(),
                'is_active': True
            }
        )
        
        return device

    @staticmethod
    def _parse_device_name(user_agent):
        """
        Parse user agent to create a human-readable device name.
        
        Args:
            user_agent: Browser user agent string
            
        Returns:
            str: Human-readable device name
        """
        user_agent_lower = user_agent.lower()
        
        # Detect browser
        if 'chrome' in user_agent_lower:
            browser = 'Chrome'
        elif 'firefox' in user_agent_lower:
            browser = 'Firefox'
        elif 'safari' in user_agent_lower and 'chrome' not in user_agent_lower:
            browser = 'Safari'
        elif 'edge' in user_agent_lower:
            browser = 'Edge'
        else:
            browser = 'Unknown Browser'
        
        # Detect OS
        if 'windows' in user_agent_lower:
            os_name = 'Windows'
        elif 'mac' in user_agent_lower:
            os_name = 'macOS'
        elif 'linux' in user_agent_lower:
            os_name = 'Linux'
        elif 'android' in user_agent_lower:
            os_name = 'Android'
        elif 'ios' in user_agent_lower or 'iphone' in user_agent_lower or 'ipad' in user_agent_lower:
            os_name = 'iOS'
        else:
            os_name = 'Unknown OS'
        
        return f"{browser} on {os_name}"

    def revoke_trust(self):
        """Revoke trust for this device."""
        self.is_active = False
        self.save()

    @staticmethod
    def cleanup_old_devices(days=90):
        """
        Remove devices that haven't been used for specified days.
        
        Args:
            days: Number of days of inactivity before cleanup
            
        Returns:
            int: Number of devices cleaned up
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        old_devices = TrustedDevice.objects.filter(last_used__lt=cutoff_date)
        count = old_devices.count()
        old_devices.delete()
        return count


class OTPVerificationLink(models.Model):
    """
    Model for storing secure verification links as an alternative to OTP codes.
    """
    
    id = models.CharField(
        max_length=10,
        primary_key=True,
        default=generate_short_id,
        editable=False
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='verification_links'
    )
    token = models.CharField(
        max_length=64,  # Secure random token
        unique=True,
        help_text="Secure verification token for email links"
    )
    purpose = models.CharField(
        max_length=20,
        choices=[
            ('signin', 'Sign In'),
            ('signup', 'Sign Up'),
            ('password_reset', 'Password Reset'),
        ],
        default='signin'
    )
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'otp_verification_links'
        ordering = ['-created_at']
        verbose_name = 'Verification Link'
        verbose_name_plural = 'Verification Links'
        indexes = [
            models.Index(fields=['user', 'purpose', 'expires_at']),
            models.Index(fields=['token', 'purpose']),
        ]

    def __str__(self):
        return f"Verification link for {self.user.email} ({self.purpose})"

    @staticmethod
    def generate_token():
        """Generate a secure random token for verification links."""
        return secrets.token_urlsafe(48)[:64]  # 64 characters

    def is_expired(self):
        """Check if verification link is expired."""
        return timezone.now() >= self.expires_at

    def is_used(self):
        """Check if verification link has been used."""
        return self.used_at is not None

    def is_valid(self):
        """Check if verification link is valid (not expired and not used)."""
        return not self.is_expired() and not self.is_used()

    def mark_as_used(self):
        """Mark verification link as used."""
        self.used_at = timezone.now()
        self.save()

    @staticmethod
    def create_verification_link(user, purpose='signin', expiry_hours=1):
        """
        Create a new verification link for a user.
        
        Args:
            user: User instance
            purpose: Purpose of verification (signin, signup, password_reset)
            expiry_hours: Link expiry time in hours
            
        Returns:
            OTPVerificationLink instance
        """
        # Delete any existing links for this user and purpose
        OTPVerificationLink.objects.filter(
            user=user, 
            purpose=purpose
        ).delete()
        
        # Clean up expired links for this user
        OTPVerificationLink.objects.filter(
            user=user,
            expires_at__lt=timezone.now()
        ).delete()
        
        # Generate unique token
        while True:
            token = OTPVerificationLink.generate_token()
            if not OTPVerificationLink.objects.filter(token=token).exists():
                break
        
        # Create new verification link
        link = OTPVerificationLink.objects.create(
            user=user,
            token=token,
            purpose=purpose,
            expires_at=timezone.now() + timedelta(hours=expiry_hours)
        )
        
        return link

    @staticmethod
    def verify_token(token, purpose):
        """
        Verify a token and return the associated user if valid.
        
        Args:
            token: Verification token
            purpose: Expected purpose
            
        Returns:
            tuple: (User instance or None, success boolean, message)
        """
        try:
            link = OTPVerificationLink.objects.get(
                token=token,
                purpose=purpose
            )
            
            if link.is_used():
                return None, False, "Verification link has already been used"
            
            if link.is_expired():
                return None, False, "Verification link has expired"
            
            # Mark as used and return user
            link.mark_as_used()
            return link.user, True, "Verification successful"
            
        except OTPVerificationLink.DoesNotExist:
            return None, False, "Invalid verification link"


class OTP(models.Model):
    """
    Model for storing OTP codes for user authentication with enhanced security.
    """
    
    id = models.CharField(
        max_length=10,
        primary_key=True,
        default=generate_short_id,
        editable=False
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='otp_codes'
    )
    code_hash = models.CharField(
        max_length=64,  # SHA-256 hash of the OTP code
        help_text="Hashed OTP code for security"
    )
    purpose = models.CharField(
        max_length=20,
        choices=[
            ('signin', 'Sign In'),
            ('signup', 'Sign Up'),
            ('password_reset', 'Password Reset'),
            ('device_verification', 'Device Verification'),
        ],
        default='signin'
    )
    attempts = models.PositiveIntegerField(
        default=0,
        help_text="Number of failed verification attempts"
    )
    max_attempts = models.PositiveIntegerField(
        default=3,
        help_text="Maximum allowed verification attempts"
    )
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'otp_codes'
        ordering = ['-created_at']
        verbose_name = 'OTP Code'
        verbose_name_plural = 'OTP Codes'
        indexes = [
            models.Index(fields=['user', 'purpose', 'expires_at']),
            models.Index(fields=['user', 'used_at']),
        ]

    def __str__(self):
        return f"OTP for {self.user.email} ({self.purpose})"

    @staticmethod
    def generate_code():
        """Generate a 6-digit OTP code."""
        return ''.join(random.choices(string.digits, k=6))

    @staticmethod
    def hash_code(code):
        """Hash OTP code for secure storage."""
        return hashlib.sha256(code.encode()).hexdigest()

    def verify_code(self, code):
        """
        Verify the provided OTP code against the stored hash.
        
        Args:
            code: The OTP code to verify
            
        Returns:
            tuple: (success boolean, message)
        """
        # Check if already used
        if self.is_used():
            return False, "OTP has already been used"
        
        # Check if expired
        if self.is_expired():
            return False, "OTP has expired"
        
        # Check if too many attempts
        if self.attempts >= self.max_attempts:
            return False, "Too many failed attempts. Please request a new OTP"
        
        # Verify the code
        code_hash = self.hash_code(code)
        if code_hash == self.code_hash:
            # Mark as used
            self.used_at = timezone.now()
            self.save()
            return True, "OTP verified successfully"
        else:
            # Increment attempts
            self.attempts += 1
            self.save()
            remaining_attempts = self.max_attempts - self.attempts
            
            if remaining_attempts <= 0:
                return False, "Too many failed attempts. Please request a new OTP"
            else:
                return False, f"Invalid OTP. {remaining_attempts} attempts remaining"

    def is_expired(self):
        """Check if OTP is expired."""
        return timezone.now() >= self.expires_at

    def is_used(self):
        """Check if OTP has been used."""
        return self.used_at is not None

    def is_valid(self):
        """Check if OTP is still valid (not expired, not used, attempts remaining)."""
        return (not self.is_expired() and 
                not self.is_used() and 
                self.attempts < self.max_attempts)

    @staticmethod
    def create_otp(user, purpose='signin', expiry_minutes=10):
        """
        Create a new OTP for a user with enhanced security.
        
        Args:
            user: User instance
            purpose: Purpose of OTP (signin, signup, password_reset, device_verification)
            expiry_minutes: OTP expiry time in minutes
            
        Returns:
            tuple: (OTP instance, plain_code)
        """
        # Delete any existing OTPs for this user and purpose
        OTP.objects.filter(
            user=user, 
            purpose=purpose
        ).delete()
        
        # Clean up expired OTPs for this user
        OTP.objects.filter(
            user=user,
            expires_at__lt=timezone.now()
        ).delete()
        
        # Generate unique code
        while True:
            plain_code = OTP.generate_code()
            code_hash = OTP.hash_code(plain_code)
            
            # Ensure code hash is unique for active OTPs with same purpose
            if not OTP.objects.filter(
                code_hash=code_hash, 
                purpose=purpose,
                expires_at__gt=timezone.now(),
                used_at__isnull=True
            ).exists():
                break
        
        # Create new OTP
        otp = OTP.objects.create(
            user=user,
            code_hash=code_hash,
            purpose=purpose,
            expires_at=timezone.now() + timedelta(minutes=expiry_minutes)
        )
        
        # Return both OTP instance and plain code (for sending via email)
        return otp, plain_code

    @staticmethod
    def verify_user_otp(user, code, purpose):
        """
        Verify OTP for a specific user and purpose.
        
        Args:
            user: User instance
            code: OTP code to verify
            purpose: Expected purpose
            
        Returns:
            tuple: (success boolean, message)
        """
        try:
            otp = OTP.objects.get(
                user=user,
                purpose=purpose,
                used_at__isnull=True,
                expires_at__gt=timezone.now()
            )
            return otp.verify_code(code)
            
        except OTP.DoesNotExist:
            return False, "No valid OTP found for this user and purpose"

    @staticmethod
    def cleanup_expired_otps():
        """
        Cleanup expired and used OTP codes.
        
        Returns:
            int: Number of OTPs cleaned up
        """
        try:
            # Clean expired OTPs
            expired_count = OTP.objects.filter(
                expires_at__lt=timezone.now()
            ).count()
            
            # Clean used OTPs older than 24 hours
            used_cutoff = timezone.now() - timedelta(hours=24)
            used_count = OTP.objects.filter(
                used_at__lt=used_cutoff
            ).count()
            
            total_count = expired_count + used_count
            
            # Delete them
            OTP.objects.filter(
                models.Q(expires_at__lt=timezone.now()) |
                models.Q(used_at__lt=used_cutoff)
            ).delete()
            
            return total_count
            
        except Exception:
            return 0

    @staticmethod
    def get_user_active_otps(user, purpose=None):
        """
        Get active OTPs for a user.
        
        Args:
            user: User instance
            purpose: Filter by purpose (optional)
            
        Returns:
            QuerySet: Active OTPs for the user
        """
        queryset = OTP.objects.filter(
            user=user,
            expires_at__gt=timezone.now(),
            used_at__isnull=True
        )
        
        if purpose:
            queryset = queryset.filter(purpose=purpose)
            
        return queryset.order_by('-created_at')
