import strawberry
from typing import List, Optional


@strawberry.input
class LearningGoalInput:
    """Input for creating learning goals during onboarding"""
    skill_name: str
    description: str
    target_skill_level: str  # beginner, intermediate, expert
    priority: int = 1


@strawberry.input
class PreferencesInput:
    """Input for user preferences during onboarding"""
    learning_style: Optional[str] = None
    time_commitment: Optional[str] = None


@strawberry.input
class CompleteOnboardingInput:
    """Input for completing user onboarding"""
    role: str
    first_name: str
    last_name: str
    bio: Optional[str] = None
    industry: str
    career_stage: str
    goals: List[LearningGoalInput]
    preferences: Optional[PreferencesInput] = None


@strawberry.type
class RoadmapStep:
    """Represents a step in an AI-generated learning roadmap"""
    title: str
    description: str
    estimated_duration: str
    difficulty: str
    resources: List[str]
    skills_covered: List[str]


@strawberry.type
class LearningRoadmap:
    """Represents an AI-generated learning roadmap"""
    skill_name: str
    description: str
    total_duration: str
    difficulty_level: str
    steps: List[RoadmapStep]


@strawberry.type
class OnboardingUser:
    """User information returned after onboarding completion"""
    id: str
    email: str
    first_name: str
    last_name: str
    role: str
    bio: str


@strawberry.type
class CompleteOnboardingPayload:
    """Response payload for onboarding completion"""
    success: bool
    message: str
    user: Optional[OnboardingUser] = None
    roadmaps: List[LearningRoadmap] = strawberry.field(default_factory=list)
    # Security: Fresh access token with updated role for seamless role transition
    access_token: Optional[str] = None
    expires_in: Optional[int] = None
