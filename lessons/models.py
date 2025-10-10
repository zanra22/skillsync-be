"""
Lesson Content Models for SkillSync AI-Powered Learning Platform.

This module contains models for:
- LessonContent: AI-generated lesson versions with community validation
- LessonVote: User votes on lesson quality (upvote/downvote)
- UserRoadmapLesson: Maps users to specific lesson versions with progress tracking
- MentorReview: Mentor-specific reviews with higher trust weight
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import hashlib

User = get_user_model()


class LessonContent(models.Model):
    """
    Represents a single version of lesson content for a specific topic.
    Multiple versions can exist for the same topic/learning style.
    Community votes determine which version is the "best".
    """
    
    # Identification
    roadmap_step_title = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Topic title (e.g., 'Python Variables')"
    )
    lesson_number = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Lesson sequence number (1, 2, 3...)"
    )
    learning_style = models.CharField(
        max_length=50,
        choices=[
            ('hands_on', 'Hands-on Projects'),
            ('video', 'Video Tutorials'),
            ('reading', 'Reading & Research'),
            ('mixed', 'Mix of Everything'),
        ],
        db_index=True,
        help_text="Learning style this lesson is optimized for"
    )
    
    # Content (JSON field - flexible for different lesson types)
    content = models.JSONField(
        help_text="Lesson data structure (text, exercises, videos, diagrams, etc.)"
    )
    
    # Metadata
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    estimated_duration = models.IntegerField(
        default=30,
        help_text="Estimated time to complete (minutes)"
    )
    difficulty_level = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
        ],
        default='beginner'
    )
    
    # Content Creation Info
    created_by = models.CharField(
        max_length=100,
        default='gemini-ai',
        db_index=True,
        help_text="Content source: 'gemini-ai', 'openai', 'claude-ai', 'mentor:{user_id}', 'manual:{user_id}'"
    )
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_lessons',
        help_text="User who triggered AI generation or created lesson manually"
    )
    generated_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when lesson was created/generated"
    )
    generation_prompt = models.TextField(
        blank=True,
        help_text="Prompt sent to AI (empty for manual creation)"
    )
    ai_model_version = models.CharField(
        max_length=50,
        default='gemini-1.5-flash',
        help_text="AI model version (e.g., 'gemini-1.5-flash', 'gpt-4', 'claude-3-opus', 'manual')"
    )
    
    # ✨ NEW: Multi-Source Research Attribution (Phase 2)
    source_type = models.CharField(
        max_length=50,
        choices=[
            ('ai_only', 'AI-Generated Only'),
            ('multi_source', 'Multi-Source Research'),
            ('community_created', 'Community-Created'),
            ('mentor_created', 'Mentor-Created'),
            ('manual', 'Manually Created'),
        ],
        default='ai_only',
        db_index=True,
        help_text="Content generation method: AI-only vs multi-source research"
    )
    source_attribution = models.JSONField(
        default=dict,
        blank=True,
        help_text="Research sources used (official docs, Stack Overflow, GitHub, Dev.to, YouTube)"
    )
    research_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Research metadata: time, sources count, quality metrics"
    )
    
    # Community Feedback
    upvotes = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of community upvotes"
    )
    downvotes = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of community downvotes"
    )
    approval_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Review'),
            ('approved', 'Community Approved'),
            ('rejected', 'Community Rejected'),
            ('mentor_verified', 'Mentor Verified'),
        ],
        default='pending',
        db_index=True,
        help_text="Approval status (mentor_verified has highest trust)"
    )
    
    # Quality Metrics
    view_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of times lesson was viewed"
    )
    completion_rate = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Percentage of users who complete this lesson"
    )
    average_quiz_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Average quiz score from all users (learning effectiveness)"
    )
    
    # Cache Key (for quick lookups)
    cache_key = models.CharField(
        max_length=32,
        db_index=True,
        unique=False,
        help_text="MD5 hash of topic+lesson_num+style for fast lookups"
    )
    
    class Meta:
        verbose_name = "Lesson Content"
        verbose_name_plural = "Lesson Contents"
        indexes = [
            models.Index(fields=['cache_key', '-upvotes']),
            models.Index(fields=['approval_status', '-upvotes']),
            models.Index(fields=['roadmap_step_title', 'lesson_number', 'learning_style']),
            models.Index(fields=['-generated_at']),
        ]
        ordering = ['-upvotes', '-generated_at']
    
    @property
    def net_votes(self):
        """Calculate net vote score (upvotes - downvotes)"""
        return self.upvotes - self.downvotes
    
    @property
    def approval_rate(self):
        """Calculate approval percentage"""
        total = self.upvotes + self.downvotes
        return (self.upvotes / total * 100) if total > 0 else 0
    
    @property
    def is_ai_generated(self):
        """Check if lesson was AI-generated"""
        return self.created_by in ['gemini-ai', 'openai', 'claude-ai', 'gpt-4', 'llama']
    
    @property
    def is_mentor_created(self):
        """Check if lesson was created by a mentor"""
        return self.created_by.startswith('mentor:')
    
    @property
    def is_manual_created(self):
        """Check if lesson was manually created by a user"""
        return self.created_by.startswith('manual:')
    
    @property
    def creator_display_name(self):
        """Get human-readable creator name"""
        if self.created_by == 'gemini-ai':
            return 'Gemini AI'
        elif self.created_by == 'openai':
            return 'GPT-4'
        elif self.created_by == 'claude-ai':
            return 'Claude AI'
        elif self.created_by.startswith('mentor:'):
            return f'Mentor (ID: {self.created_by.split(":")[1]})'
        elif self.created_by.startswith('manual:'):
            return f'Manual (ID: {self.created_by.split(":")[1]})'
        else:
            return self.created_by.replace('-', ' ').title()
    
    @property
    def days_old(self):
        """Calculate how many days old this lesson is"""
        return (timezone.now() - self.generated_at).days
    
    @property
    def is_multi_source(self):
        """Check if lesson was generated with multi-source research"""
        return self.source_type == 'multi_source'
    
    @property
    def research_quality_score(self):
        """
        Calculate research quality score based on sources used.
        Returns 0-100 score.
        """
        if not self.is_multi_source or not self.source_attribution:
            return 0
        
        score = 0
        sources = self.source_attribution
        
        # Official docs (+25 points)
        if sources.get('official_docs'):
            score += 25
        
        # Stack Overflow answers (+20 points)
        so_count = len(sources.get('stackoverflow_answers', []))
        score += min(so_count * 5, 20)  # Max 20 points
        
        # GitHub examples (+20 points)
        github_count = len(sources.get('github_examples', []))
        score += min(github_count * 5, 20)  # Max 20 points
        
        # Dev.to articles (+15 points)
        devto_count = len(sources.get('dev_articles', []))
        score += min(devto_count * 3, 15)  # Max 15 points
        
        # YouTube videos (+20 points)
        youtube_count = len(sources.get('youtube_videos', []))
        score += min(youtube_count * 7, 20)  # Max 20 points
        
        return min(score, 100)  # Cap at 100
    
    @property
    def source_summary(self):
        """
        Get human-readable summary of research sources used.
        Returns string like: "Verified with 5 sources: Official Docs, Stack Overflow (5), GitHub (5), Dev.to (5)"
        """
        if not self.is_multi_source or not self.source_attribution:
            return "AI-generated without external research"
        
        sources = self.source_attribution
        parts = []
        total_sources = 0
        
        if sources.get('official_docs'):
            parts.append("Official Docs")
            total_sources += 1
        
        so_count = len(sources.get('stackoverflow_answers', []))
        if so_count > 0:
            parts.append(f"Stack Overflow ({so_count})")
            total_sources += so_count
        
        github_count = len(sources.get('github_examples', []))
        if github_count > 0:
            parts.append(f"GitHub ({github_count})")
            total_sources += github_count
        
        devto_count = len(sources.get('dev_articles', []))
        if devto_count > 0:
            parts.append(f"Dev.to ({devto_count})")
            total_sources += devto_count
        
        youtube_count = len(sources.get('youtube_videos', []))
        if youtube_count > 0:
            parts.append(f"YouTube ({youtube_count})")
            total_sources += youtube_count
        
        if not parts:
            return "Multi-source research (no sources recorded)"
        
        sources_str = ", ".join(parts)
        return f"Verified with {total_sources} sources: {sources_str}"
    
    @staticmethod
    def generate_cache_key(step_title: str, lesson_number: int, learning_style: str, multi_source: bool = False) -> str:
        """
        Generate consistent cache key for lookup.
        
        Args:
            step_title: Topic title (e.g., 'Python Variables')
            lesson_number: Lesson sequence number
            learning_style: Learning style ('hands_on', 'video', 'reading', 'mixed')
            multi_source: Whether multi-source research was used (default: False for backward compatibility)
        
        Returns:
            MD5 hash string (32 characters)
        
        Note: multi_source flag ensures different cache entries for AI-only vs multi-source lessons
        """
        # Include multi_source flag to differentiate cache entries
        source_suffix = ":multi_source_v1" if multi_source else ""
        key_string = f"{step_title}:{lesson_number}:{learning_style}{source_suffix}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def save(self, *args, **kwargs):
        """Override save to auto-generate cache_key"""
        if not self.cache_key:
            # Determine if multi-source based on source_type
            is_multi_source = self.source_type == 'multi_source'
            self.cache_key = self.generate_cache_key(
                self.roadmap_step_title,
                self.lesson_number,
                self.learning_style,
                multi_source=is_multi_source
            )
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.roadmap_step_title} - Lesson {self.lesson_number} ({self.learning_style})"


class LessonVote(models.Model):
    """
    Track individual user votes on lessons.
    One vote per user per lesson (can change vote).
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='lesson_votes'
    )
    lesson_content = models.ForeignKey(
        LessonContent,
        on_delete=models.CASCADE,
        related_name='votes'
    )
    vote_type = models.CharField(
        max_length=10,
        choices=[
            ('upvote', 'Upvote'),
            ('downvote', 'Downvote'),
        ],
        help_text="Vote type"
    )
    comment = models.TextField(
        blank=True,
        help_text="Optional feedback about the lesson"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Lesson Vote"
        verbose_name_plural = "Lesson Votes"
        unique_together = ['user', 'lesson_content']
        indexes = [
            models.Index(fields=['lesson_content', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} {self.vote_type}d {self.lesson_content.title}"


class UserRoadmapLesson(models.Model):
    """
    Maps user's roadmap to specific lesson content versions.
    Tracks which version of the lesson the user is using and their progress.
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='roadmap_lessons'
    )
    roadmap_step_title = models.CharField(
        max_length=255,
        help_text="Reference to roadmap step (denormalized for performance)"
    )
    lesson_number = models.IntegerField(
        validators=[MinValueValidator(1)]
    )
    
    # Which version of the lesson content
    lesson_content = models.ForeignKey(
        LessonContent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_assignments',
        help_text="Specific lesson version assigned to this user"
    )
    
    # Progress tracking
    status = models.CharField(
        max_length=20,
        choices=[
            ('not_started', 'Not Started'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
        ],
        default='not_started',
        db_index=True
    )
    
    # Performance metrics
    quiz_score = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Quiz score percentage (0-100)"
    )
    exercises_completed = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of exercises completed"
    )
    time_spent = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Time spent on lesson (minutes)"
    )
    
    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Roadmap Lesson"
        verbose_name_plural = "User Roadmap Lessons"
        unique_together = ['user', 'roadmap_step_title', 'lesson_number']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['lesson_content', 'status']),
        ]
        ordering = ['roadmap_step_title', 'lesson_number']
    
    def __str__(self):
        return f"{self.user.email} - {self.roadmap_step_title} Lesson {self.lesson_number}"


class MentorReview(models.Model):
    """
    Mentor-specific reviews carry more weight than community votes.
    Mentors can verify, reject, or suggest improvements.
    """
    
    mentor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'mentor'},
        related_name='mentor_reviews',
        help_text="Mentor who reviewed this lesson"
    )
    lesson_content = models.ForeignKey(
        LessonContent,
        on_delete=models.CASCADE,
        related_name='mentor_reviews'
    )
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('verified', 'Verified Correct'),
            ('needs_improvement', 'Needs Improvement'),
            ('rejected', 'Rejected'),
        ],
        help_text="Mentor's verdict on lesson quality"
    )
    
    feedback = models.TextField(
        help_text="Detailed mentor feedback for improvement"
    )
    expertise_area = models.CharField(
        max_length=100,
        help_text="Mentor's area of expertise (e.g., 'Python Programming')"
    )
    
    reviewed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Mentor Review"
        verbose_name_plural = "Mentor Reviews"
        unique_together = ['mentor', 'lesson_content']
        indexes = [
            models.Index(fields=['lesson_content', '-reviewed_at']),
            models.Index(fields=['status']),
        ]
        ordering = ['-reviewed_at']
    
    def __str__(self):
        return f"{self.mentor.email} {self.status} {self.lesson_content.title}"
