import random
import string
from django.db import models
from django.contrib.auth.models import AbstractUser, PermissionsMixin, BaseUserManager
from django.utils import timezone

from .choices import (
    UserRole, 
    AccountStatus, 
)
from helpers.generate_short_id import generate_short_id


class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("User must have an email address")

        email = self.normalize_email(email)
        username = username

        if self.model.objects.filter(email=email).exists():
            raise ValueError("User with this email already exists")

        if self.model.objects.filter(username=username).exists():
            raise ValueError("User with this username already exists")

        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("account_status", AccountStatus.ACTIVE)
        extra_fields.setdefault("role", UserRole.SUPER_ADMIN)  # Changed from ADMIN to SUPER_ADMIN

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, username, password, **extra_fields)


class User(AbstractUser, PermissionsMixin):
    id = models.CharField(
        max_length=10,
        primary_key=True,
        default=generate_short_id,
        unique=True,
    )

    # User Details
    email = models.EmailField(unique=True, max_length=50)

    username = models.CharField(max_length=50, unique=True, blank=True)
    role = models.CharField(
        max_length=20,  # Increased from 15 to accommodate longer role names
        choices=UserRole.choices,
        default=UserRole.LEARNER,  # Changed from USER to LEARNER
    )
    
    # Account and Profile Information
    account_status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.PENDING,
    )

    
    
    
    # Subscription and Premium Features
    is_premium = models.BooleanField(default=False)
    premium_expires_at = models.DateTimeField(null=True, blank=True)

    # Email Verification
    email_verification_token = models.CharField(max_length=255, blank=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    # Flags
    last_login = models.DateTimeField(null=True, blank=True)
    is_email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_sign_in = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"
    
    def get_full_name(self):
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        """Return the user's first name."""
        return self.first_name
    
    def is_mentor(self):
        """Check if user is a mentor."""
        return self.role in [UserRole.MENTOR, UserRole.VIP_MENTOR, UserRole.EXPERT]
    
    def is_learner(self):
        """Check if user is a learner."""
        return self.role == UserRole.LEARNER
    
    def is_admin(self):
        """Check if user has admin privileges."""
        return self.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]
    
    def can_create_content(self):
        """Check if user can create learning content."""
        return self.role in [
            UserRole.INSTRUCTOR, 
            UserRole.CONTENT_CREATOR, 
            UserRole.EXPERT,
            UserRole.ADMIN,
            UserRole.SUPER_ADMIN
        ]
    
    def can_moderate(self):
        """Check if user can moderate content."""
        return self.role in [
            UserRole.MODERATOR, 
            UserRole.ADMIN, 
            UserRole.SUPER_ADMIN
        ]
    
    def is_premium_user(self):
        """Check if user has active premium subscription."""
        if not self.is_premium:
            return False
        if self.premium_expires_at and self.premium_expires_at < timezone.now():
            return False
        return True
    
    def get_mentorship_availability(self):
        """Get mentorship availability status."""
        if not self.is_mentor():
            return "Not a mentor"
        return self.get_mentorship_status_display()
    
    @property
    def display_name(self):
        """Return display name for the user."""
        full_name = self.get_full_name()
        return full_name if full_name else self.username

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_at"]
        db_table = "users"
