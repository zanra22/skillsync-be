from django.db import models
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    # Administrative roles
    SUPER_ADMIN = "super_admin", _("Super Admin")
    ADMIN = "admin", _("Admin")
    MODERATOR = "moderator", _("Moderator")
    
    # Learning & Development roles
    LEARNER = "learner", _("Learner")  # Default role for new users
    MENTOR = "mentor", _("Mentor")

    
    # Professional roles
    HR_MANAGER = "hr_manager", _("HR Manager")  # Company HR personnel
    RECRUITER = "recruiter", _("Recruiter")
    
    # Premium/VIP roles
    PREMIUM_USER = "premium_user", _("Premium User")
    VIP_MENTOR = "vip_mentor", _("VIP Mentor")  # Premium mentor with special features


class AccountStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    INACTIVE = "inactive", _("Inactive")
    PENDING = "pending", _("Pending Verification")
    SUSPENDED = "suspended", _("Suspended")
    BANNED = "banned", _("Banned")


class SkillLevel(models.TextChoices):
    BEGINNER = "beginner", _("Beginner")
    INTERMEDIATE = "intermediate", _("Intermediate")
    EXPERT = "expert", _("Expert")



