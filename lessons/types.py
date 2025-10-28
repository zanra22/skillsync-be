import strawberry
from typing import Optional, List
from datetime import datetime
# === Roadmap & Module Types ===
@strawberry.type
class ModuleType:
    id: int
    roadmap_id: int
    title: str
    description: str
    order: int
    estimated_duration: str
    difficulty: str
    resources: strawberry.scalars.JSON

@strawberry.type
class RoadmapType:
    id: int
    title: str
    description: str
    user_id: str
    goal_id: str
    difficulty_level: str
    total_duration: str
    generated_at: datetime
    user_profile_snapshot: strawberry.scalars.JSON
    ai_model_version: str
    status: str
    progress: strawberry.scalars.JSON
    modules: List[ModuleType]



@strawberry.type
class LessonContentType:
    """
    Represents a single version of lesson content for a specific topic.
    Multiple versions can exist for the same topic/step.
    """
    id: int
    roadmap_step_title: str
    lesson_number: int
    learning_style: str
    
    # Content stored as JSON
    content: strawberry.scalars.JSON
    
    # Metadata
    title: str
    description: str
    estimated_duration: int
    difficulty_level: str
    
    # Content Creation Info
    created_by: str
    generated_by_id: Optional[int]
    generated_at: datetime
    generation_prompt: str
    ai_model_version: str
    
    # ✨ NEW: Multi-Source Research Attribution (Phase 2)
    source_type: str
    source_attribution: strawberry.scalars.JSON
    research_metadata: strawberry.scalars.JSON
    
    # Community Feedback
    upvotes: int
    downvotes: int
    approval_status: str
    
    # Quality Metrics
    view_count: int
    completion_rate: float
    average_quiz_score: float
    
    # Cache Key
    cache_key: str
    
    @strawberry.field
    def net_votes(self) -> int:
        """Calculate net vote score (upvotes - downvotes)"""
        return self.upvotes - self.downvotes
    
    @strawberry.field
    def approval_rate(self) -> float:
        """Calculate approval percentage"""
        total = self.upvotes + self.downvotes
        return (self.upvotes / total * 100) if total > 0 else 0.0
    
    @strawberry.field
    def is_approved(self) -> bool:
        """Check if lesson is approved by community or mentor"""
        return self.approval_status in ['approved', 'mentor_verified']
    
    @strawberry.field
    def is_mentor_verified(self) -> bool:
        """Check if lesson is verified by a mentor"""
        return self.approval_status == 'mentor_verified'
    
    @strawberry.field
    def is_ai_generated(self) -> bool:
        """Check if lesson was AI-generated"""
        return self.created_by in ['gemini-ai', 'openai', 'claude-ai', 'gpt-4', 'llama']
    
    @strawberry.field
    def is_mentor_created(self) -> bool:
        """Check if lesson was created by a mentor"""
        return self.created_by.startswith('mentor:')
    
    @strawberry.field
    def is_manual_created(self) -> bool:
        """Check if lesson was manually created"""
        return self.created_by.startswith('manual:')
    
    @strawberry.field
    def creator_display_name(self) -> str:
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
    
    @strawberry.field
    def quality_score(self) -> float:
        """
        Calculate overall quality score based on multiple factors.
        Used for ranking lessons.
        """
        score = 0.0
        
        # Net votes (most important)
        score += self.net_votes * 10
        
        # Mentor verification (huge bonus)
        if self.approval_status == 'mentor_verified':
            score += 500
        
        # Completion rate (quality indicator)
        score += self.completion_rate * 100
        
        # Quiz performance (learning effectiveness)
        score += self.average_quiz_score * 5
        
        # Recency (bonus for newer content)
        from django.utils import timezone
        days_old = (timezone.now() - self.generated_at).days
        freshness_bonus = max(0, 30 - days_old)
        score += freshness_bonus
        
        return score
    
    # ✨ NEW: Multi-Source Research Properties
    @strawberry.field
    def is_multi_source(self) -> bool:
        """Check if lesson was generated with multi-source research"""
        return self.source_type == 'multi_source'
    
    @strawberry.field
    def research_quality_score(self) -> int:
        """
        Calculate research quality score based on sources used (0-100).
        Returns 0 for AI-only lessons, 1-100 for multi-source lessons.
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
        score += min(so_count * 5, 20)
        
        # GitHub examples (+20 points)
        github_count = len(sources.get('github_examples', []))
        score += min(github_count * 5, 20)
        
        # Dev.to articles (+15 points)
        devto_count = len(sources.get('dev_articles', []))
        score += min(devto_count * 3, 15)
        
        # YouTube videos (+20 points)
        youtube_count = len(sources.get('youtube_videos', []))
        score += min(youtube_count * 7, 20)
        
        return min(score, 100)
    
    @strawberry.field
    def source_summary(self) -> str:
        """
        Get human-readable summary of research sources used.
        Example: "Verified with 5 sources: Official Docs, Stack Overflow (5), GitHub (5)"
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


@strawberry.type
class LessonVoteType:
    """Track individual user votes on lessons"""
    id: int
    user_id: int
    lesson_content_id: int
    vote_type: str
    comment: str
    created_at: datetime


@strawberry.type
class UserRoadmapLessonType:
    """
    Maps user's roadmap to specific lesson content versions.
    Tracks which version of the lesson the user is using.
    """
    id: int
    user_id: int
    roadmap_step_id: int
    lesson_number: int
    lesson_content_id: Optional[int]
    
    # Progress tracking
    status: str
    quiz_score: Optional[int]
    exercises_completed: int
    time_spent: int
    
    # Timestamps
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    @strawberry.field
    def is_completed(self) -> bool:
        """Check if lesson is completed"""
        return self.status == 'completed'
    
    @strawberry.field
    def is_in_progress(self) -> bool:
        """Check if lesson is in progress"""
        return self.status == 'in_progress'
    
    @strawberry.field
    def progress_percentage(self) -> float:
        """Calculate progress percentage based on exercises completed"""
        # Assuming lessons have 3-5 exercises on average
        total_exercises = 4  # Average
        return min(100.0, (self.exercises_completed / total_exercises) * 100)


@strawberry.type
class MentorReviewType:
    """
    Mentor-specific reviews carry more weight than community votes.
    """
    id: int
    mentor_id: int
    lesson_content_id: int
    status: str
    feedback: str
    expertise_area: str
    reviewed_at: datetime
    
    @strawberry.field
    def is_verified(self) -> bool:
        """Check if mentor verified the lesson"""
        return self.status == 'verified'


# Input types for mutations

@strawberry.input
class VoteLessonInput:
    """Input for voting on a lesson"""
    lesson_id: int
    vote_type: str  # 'upvote' or 'downvote'
    comment: Optional[str] = ""


@strawberry.input
class RegenerateLessonInput:
    """Input for regenerating a lesson"""
    lesson_id: int


@strawberry.input
class GetOrGenerateLessonInput:
    """Input for getting or generating a lesson"""
    step_title: str
    lesson_number: int
    learning_style: str  # 'hands_on', 'video', 'reading', 'mixed'
    difficulty: Optional[str] = 'beginner'  # 'beginner', 'intermediate', 'advanced'
    context: Optional[str] = None  # Additional context for generation
    
    # ✨ NEW: Multi-Source Research Parameters (Phase 2)
    enable_research: Optional[bool] = True  # Enable multi-source research (default: True)
    category: Optional[str] = None  # e.g., 'python', 'javascript', 'react'
    programming_language: Optional[str] = None  # e.g., 'python', 'javascript'


@strawberry.input
class LessonFiltersInput:
    """Input for filtering lessons in search"""
    learning_style: Optional[str] = None
    difficulty_level: Optional[str] = None
    min_upvotes: Optional[int] = None


@strawberry.input
class MentorReviewInput:
    """Input for mentor reviewing a lesson"""
    lesson_id: int
    status: str  # 'verified', 'needs_improvement', 'rejected'
    feedback: str
    expertise_area: str


# Payload types for mutations

@strawberry.type
class VoteLessonPayload:
    """Response payload for voting on a lesson"""
    success: bool
    message: str
    lesson: Optional[LessonContentType] = None


@strawberry.type
class RegenerateLessonPayload:
    """Response payload for regenerating a lesson"""
    success: bool
    message: str
    old_lesson: Optional[LessonContentType] = None
    new_lesson: Optional[LessonContentType] = None


@strawberry.type
class GetOrGenerateLessonPayload:
    """Response payload for getting or generating a lesson"""
    success: bool
    message: str
    lesson: Optional[LessonContentType] = None
    was_cached: bool  # True if lesson was retrieved from cache, False if generated


@strawberry.type
class MentorReviewPayload:
    """Response payload for mentor review"""
    success: bool
    message: str
    review: Optional[MentorReviewType] = None
    lesson: Optional[LessonContentType] = None


@strawberry.type
class LessonVersionsPayload:
    """Response payload for getting all lesson versions"""
    success: bool
    message: str
    versions: List[LessonContentType]
    recommended_version: Optional[LessonContentType] = None  # Highest quality score
