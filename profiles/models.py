from django.db import models
from django.contrib.auth import get_user_model
from .choices import (
    MentorshipStatus, 
    CareerStage, 
    IndustryType,
    SkillLevel,
    OnboardingStep,
    GoalStatus
)
from helpers.generate_short_id import generate_short_id

User = get_user_model()

# Create your models here.
class UserProfile(models.Model):
    id = models.CharField(
        max_length=10,
        primary_key=True,
        default=generate_short_id,
        unique=True,
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    first_name = models.CharField(max_length=150, blank=False)
    last_name = models.CharField(max_length=150, blank=False)
    bio = models.TextField(max_length=500, blank=True, help_text="Tell us about yourself")
    profile_picture = models.ImageField(
        upload_to='profile_pictures/', 
        blank=True, 
        null=True
    )
    
    # Onboarding Information
    onboarding_completed = models.BooleanField(default=False)
    onboarding_step = models.CharField(
        max_length=20,
        choices=OnboardingStep.choices,
        default=OnboardingStep.WELCOME,
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
    
    # Learning preferences (from onboarding)
    learning_style = models.CharField(
        max_length=20, 
        blank=True,
        help_text="Preferred learning style: hands_on, video, reading, mixed"
    )
    time_commitment = models.CharField(
        max_length=10, 
        blank=True,
        help_text="Weekly time commitment: 1-3, 3-5, 5-10, 10+"
    )
    
    # Career transition information (for career changers)
    transition_timeline = models.CharField(
        max_length=15,
        blank=True,
        help_text="Career transition timeline: immediate, 6_months, 1_year, long_term"
    )
    
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
    
    def get_onboarding_progress(self):
        """Get onboarding progress as percentage."""
        steps = list(OnboardingStep.choices)
        current_index = next((i for i, (value, _) in enumerate(steps) if value == self.onboarding_step), 0)
        return (current_index / (len(steps) - 1)) * 100 if len(steps) > 1 else 0
    
    def advance_onboarding(self):
        """Move to next onboarding step."""
        steps = [choice[0] for choice in OnboardingStep.choices]
        current_index = steps.index(self.onboarding_step) if self.onboarding_step in steps else 0
        
        if current_index < len(steps) - 1:
            self.onboarding_step = steps[current_index + 1]
            if self.onboarding_step == OnboardingStep.COMPLETE:
                self.onboarding_completed = True
            self.save()
            return True
        return False
    
    def set_user_role(self, role):
        """Set user role during onboarding process."""
        from users.choices import UserRole
        if role in [choice[0] for choice in UserRole.choices]:
            self.user.role = role
            self.user.save()
            return True
        return False
    
    def get_available_roles_for_onboarding(self):
        """Get roles available for selection during onboarding."""
        from users.choices import UserRole
        return [
            (UserRole.LEARNER, "I want to learn new skills"),
            (UserRole.PROFESSIONAL, "I'm a working professional looking to upskill"),
            (UserRole.MENTOR, "I want to mentor and teach others"),
        ]
    
    def is_onboarding_complete(self):
        """Check if onboarding is complete."""
        return self.onboarding_completed and self.onboarding_step == OnboardingStep.COMPLETE


class UserIndustry(models.Model):
    """Model to handle multiple industries per user with subscription limits."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_industries')
    industry = models.CharField(
        max_length=20,
        choices=IndustryType.choices,
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary industry for the user"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'industry']
        verbose_name = "User Industry"
        verbose_name_plural = "User Industries"
        ordering = ['-is_primary', '-created_at']
    
    def __str__(self):
        primary_text = " (Primary)" if self.is_primary else ""
        return f"{self.user.email} - {self.get_industry_display()}{primary_text}"
    
    def save(self, *args, **kwargs):
        # Ensure only one primary industry per user
        if self.is_primary:
            UserIndustry.objects.filter(user=self.user, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def set_primary_industry(cls, user, industry_type):
        """Set a specific industry as primary for a user."""
        # Remove primary from all industries
        cls.objects.filter(user=user).update(is_primary=False)
        # Set the specified industry as primary
        industry, created = cls.objects.get_or_create(
            user=user, 
            industry=industry_type,
            defaults={'is_primary': True}
        )
        if not created:
            industry.is_primary = True
            industry.save()
        return industry


class UserLearningGoal(models.Model):
    """Model to handle specific learning goals/skills per industry with AI roadmap integration."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='learning_goals')
    industry = models.ForeignKey(UserIndustry, on_delete=models.CASCADE, related_name='goals')
    
    # Goal Information
    skill_name = models.CharField(
        max_length=100,
        help_text="Name of the skill or learning goal"
    )
    description = models.TextField(
        max_length=500,
        blank=True,
        help_text="Detailed description of what you want to learn"
    )
    target_skill_level = models.CharField(
        max_length=15,
        choices=SkillLevel.choices,
        default=SkillLevel.BEGINNER,
    )
    current_skill_level = models.CharField(
        max_length=15,
        choices=SkillLevel.choices,
        default=SkillLevel.BEGINNER,
    )
    
    # Progress Tracking
    status = models.CharField(
        max_length=15,
        choices=GoalStatus.choices,
        default=GoalStatus.NOT_STARTED,
    )
    progress_percentage = models.PositiveIntegerField(
        default=0,
        help_text="Progress completion percentage (0-100)"
    )
    
    # AI Integration
    ai_roadmap_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="MongoDB document ID for AI-generated roadmap"
    )
    roadmap_generated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the AI roadmap was last generated"
    )
    
    # Timeline
    target_completion_date = models.DateField(
        null=True,
        blank=True,
        help_text="Target date to achieve this goal"
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the user started working on this goal"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the goal was completed"
    )
    
    # Priority and Organization
    priority = models.PositiveIntegerField(
        default=1,
        help_text="Priority level (1=highest, 5=lowest)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this goal is currently active"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'industry', 'skill_name']
        verbose_name = "User Learning Goal"
        verbose_name_plural = "User Learning Goals"
        ordering = ['priority', '-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.skill_name} ({self.industry.get_industry_display()})"
    
    def update_progress(self, percentage):
        """Update progress and automatically set status based on percentage."""
        self.progress_percentage = min(100, max(0, percentage))
        
        if self.progress_percentage == 0:
            self.status = GoalStatus.NOT_STARTED
            self.started_at = None
        elif self.progress_percentage == 100:
            self.status = GoalStatus.COMPLETED
            if not self.completed_at:
                from django.utils import timezone
                self.completed_at = timezone.now()
        else:
            if self.status == GoalStatus.NOT_STARTED:
                self.status = GoalStatus.IN_PROGRESS
                if not self.started_at:
                    from django.utils import timezone
                    self.started_at = timezone.now()
        
        self.save()
    
    def get_estimated_duration(self):
        """Get estimated duration based on skill level and complexity."""
        if self.target_skill_level == SkillLevel.BEGINNER:
            return "2-4 weeks"
        elif self.target_skill_level == SkillLevel.INTERMEDIATE:
            return "1-3 months"
        else:  # EXPERT
            return "3-6 months"
    
    def has_ai_roadmap(self):
        """Check if this goal has an AI-generated roadmap."""
        return bool(self.ai_roadmap_id)
    
    def can_generate_roadmap(self):
        """Check if user can generate a new roadmap based on subscription limits."""
        # This would integrate with the subscription system
        limits = self.user.get_subscription_limits()
        # Add logic to check monthly generation limits
        return limits.get('ai_roadmap_generations_per_month', 0) > 0