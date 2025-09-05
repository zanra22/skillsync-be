from django.db import models
from django.utils.translation import gettext_lazy as _


class MentorshipStatus(models.TextChoices):
    AVAILABLE = "available", _("Available")
    BUSY = "busy", _("Busy")
    NOT_AVAILABLE = "not_available", _("Not Available")
    ON_BREAK = "on_break", _("On Break")
    
class CareerStage(models.TextChoices):
    STUDENT = "student", _("Student")
    ENTRY_LEVEL = "entry_level", _("Entry Level")
    MID_LEVEL = "mid_level", _("Mid Level")
    SENIOR_LEVEL = "senior_level", _("Senior Level")
    EXECUTIVE = "executive", _("Executive")
    CAREER_CHANGER = "career_changer", _("Career Changer")
    FREELANCER = "freelancer", _("Freelancer")


class IndustryType(models.TextChoices):
    TECHNOLOGY = "technology", _("Technology")
    HEALTHCARE = "healthcare", _("Healthcare")
    FINANCE = "finance", _("Finance")
    EDUCATION = "education", _("Education")
    MARKETING = "marketing", _("Marketing")
    DESIGN = "design", _("Design")
    SALES = "sales", _("Sales")
    MANUFACTURING = "manufacturing", _("Manufacturing")
    CONSULTING = "consulting", _("Consulting")
    STARTUP = "startup", _("Startup")
    NON_PROFIT = "non_profit", _("Non-Profit")
    GOVERNMENT = "government", _("Government")
    OTHER = "other", _("Other")
    
class SkillLevel(models.TextChoices):
    BEGINNER = "beginner", _("Beginner")
    INTERMEDIATE = "intermediate", _("Intermediate")
    EXPERT = "expert", _("Expert")