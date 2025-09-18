from django.db import models
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    # New user role
    NEW_USER = "new_user", _("New User")  # Users who haven't completed onboarding
    
    # Administrative roles
    SUPER_ADMIN = "super_admin", _("Super Admin")
    ADMIN = "admin", _("Admin")
    MODERATOR = "moderator", _("Moderator")
    
    # Learning & Development roles
    LEARNER = "learner", _("Learner")  # Default role after onboarding
    PROFESSIONAL = "professional", _("Professional")  # Working professionals
    MENTOR = "mentor", _("Mentor")

    
    # Professional roles
    HR_MANAGER = "hr_manager", _("HR Manager")  # Company HR personnel
    RECRUITER = "recruiter", _("Recruiter")
    
    # Premium/VIP roles
    PREMIUM_USER = "premium_user", _("Premium User")
    VIP_MENTOR = "vip_mentor", _("VIP Mentor")  # Premium mentor with special features


class SubscriptionTier(models.TextChoices):
    FREE = "free", _("Free")
    PREMIUM = "premium", _("Premium")
    ENTERPRISE = "enterprise", _("Enterprise")


class AccountStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    INACTIVE = "inactive", _("Inactive")
    PENDING = "pending", _("Pending Verification")
    SUSPENDED = "suspended", _("Suspended")
    BANNED = "banned", _("Banned")






