from django.db import models
from .choices import (
    MentorshipStatus, 
    CareerStage, 
    IndustryType,
    SkillLevel
)
# Create your models here.
class UserProfile(models.Model):
    first_name = models.CharField(max_length=150, blank=False)
    last_name = models.CharField(max_length=150, blank=False)
    bio = models.TextField(max_length=500, blank=True, help_text="Tell us about yourself")
    profile_picture = models.ImageField(
        upload_to='profile_pictures/', 
        blank=True, 
        null=True
    )
# Professional Information
    skill_level = models.CharField(
        max_length=15,
        choices=SkillLevel.choices,
        blank=True,
    )
    career_stage = models.CharField(
        max_length=20,
        choices=CareerStage.choices,
        blank=True,
    )
    industry = models.CharField(
        max_length=20,
        choices=IndustryType.choices,
        blank=True,
    )
    job_title = models.CharField(max_length=100, blank=True)
    company = models.CharField(max_length=100, blank=True)
    years_of_experience = models.PositiveIntegerField(null=True, blank=True)
    
    learning_goals = models.TextField(max_length=1000, blank=True)
    
    # Mentorship Information (for mentors)
    mentorship_status = models.CharField(
        max_length=15,
        choices=MentorshipStatus.choices,
        default=MentorshipStatus.NOT_AVAILABLE,
    )
    mentorship_rate = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Hourly rate for mentorship in USD"
    )
    mentorship_bio = models.TextField(
        max_length=1000, 
        blank=True,
        help_text="Describe your mentoring style and expertise"
    )
    
    # Contact Information
    phone_number = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=100, blank=True)
    timezone = models.CharField(max_length=50, blank=True)
    
    # Social Links
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.job_title if self.job_title else 'No Job Title'}"