import random
import string
from django.db import models
from django.contrib.auth.models import AbstractUser, PermissionsMixin, BaseUserManager
from django.utils import timezone

from .choices import (
    UserRole, 
    AccountStatus,
    SubscriptionTier,
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
        default=UserRole.NEW_USER,
        help_text="User role - defaults to new_user, updated during onboarding"
    )
    
    # Account and Profile Information
    account_status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.PENDING,
    )

    
    
    
    # Subscription and Premium Features
    # Legacy fields (will be removed in future migration)
    is_premium = models.BooleanField(default=False)
    premium_expires_at = models.DateTimeField(null=True, blank=True)
    
    # New subscription system
    subscription_tier = models.CharField(
        max_length=20,
        choices=SubscriptionTier.choices,
        default=SubscriptionTier.FREE,
    )
    subscription_expires_at = models.DateTimeField(null=True, blank=True)
    subscription_auto_renew = models.BooleanField(default=False)
    subscription_started_at = models.DateTimeField(null=True, blank=True)

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
        if not self.role:
            return False
        return self.role in [UserRole.MENTOR, UserRole.VIP_MENTOR, UserRole.EXPERT]
    
    def is_learner(self):
        """Check if user is a learner."""
        if not self.role:
            return False
        return self.role == UserRole.LEARNER
    
    def needs_onboarding(self):
        """Check if user needs to complete onboarding."""
        return self.role is None or not hasattr(self, 'profile') or not self.profile.onboarding_completed
    
    def has_completed_role_selection(self):
        """Check if user has selected their role during onboarding."""
        return self.role is not None
    
    def is_admin(self):
        """Check if user has admin privileges."""
        if not self.role:
            return False
        return self.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]
    
    def can_create_content(self):
        """Check if user can create learning content."""
        if not self.role:
            return False
        return self.role in [
            UserRole.INSTRUCTOR, 
            UserRole.CONTENT_CREATOR, 
            UserRole.EXPERT,
            UserRole.ADMIN,
            UserRole.SUPER_ADMIN
        ]
    
    def can_moderate(self):
        """Check if user can moderate content."""
        if not self.role:
            return False
        return self.role in [
            UserRole.MODERATOR, 
            UserRole.ADMIN, 
            UserRole.SUPER_ADMIN
        ]
    
    def is_premium_user(self):
        """Check if user has active premium subscription."""
        if self.subscription_tier == SubscriptionTier.FREE:
            return False
        if self.subscription_expires_at and self.subscription_expires_at < timezone.now():
            return False
        return True
    
    def is_enterprise_user(self):
        """Check if user has enterprise subscription."""
        return self.subscription_tier == SubscriptionTier.ENTERPRISE and self.is_premium_user()
    
    def get_subscription_limits(self):
        """Get subscription limits based on tier."""
        if self.subscription_tier == SubscriptionTier.FREE:
            return {
                'max_industries': 1,
                'max_goals_per_industry': 2,
                'ai_roadmap_generations_per_month': 3,
                'can_access_premium_content': False,
                'can_chat_with_ai': True,  # Basic chat
                'max_mentor_sessions': 0,
            }
        elif self.subscription_tier == SubscriptionTier.PREMIUM:
            return {
                'max_industries': 3,
                'max_goals_per_industry': 10,
                'ai_roadmap_generations_per_month': 50,
                'can_access_premium_content': True,
                'can_chat_with_ai': True,
                'max_mentor_sessions': 5,
            }
        elif self.subscription_tier == SubscriptionTier.ENTERPRISE:
            return {
                'max_industries': 10,
                'max_goals_per_industry': 50,
                'ai_roadmap_generations_per_month': 200,
                'can_access_premium_content': True,
                'can_chat_with_ai': True,
                'max_mentor_sessions': 20,
            }
        return {}
    
    def can_add_industry(self):
        """Check if user can add another industry."""
        from profiles.models import UserIndustry
        current_count = UserIndustry.objects.filter(user=self).count()
        limits = self.get_subscription_limits()
        return current_count < limits.get('max_industries', 0)
    
    def can_add_goal_to_industry(self, industry_id):
        """Check if user can add another goal to specific industry."""
        from profiles.models import UserLearningGoal
        current_count = UserLearningGoal.objects.filter(
            user=self, 
            industry_id=industry_id
        ).count()
        limits = self.get_subscription_limits()
        return current_count < limits.get('max_goals_per_industry', 0)
    
    def get_subscription_status(self):
        """Get detailed subscription status."""
        if self.subscription_tier == SubscriptionTier.FREE:
            return {
                'tier': self.subscription_tier,
                'is_active': True,
                'expires_at': None,
                'auto_renew': False,
                'status': 'active'
            }
        
        is_active = self.is_premium_user()
        status = 'active' if is_active else 'expired'
        
        return {
            'tier': self.subscription_tier,
            'is_active': is_active,
            'expires_at': self.subscription_expires_at,
            'auto_renew': self.subscription_auto_renew,
            'status': status,
            'started_at': self.subscription_started_at
        }
    
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
