import strawberry
import strawberry_django
from django.contrib.auth import get_user_model
from typing import Optional, List
from onboarding.types import LearningGoalInput as OnboardingLearningGoalInput
from asgiref.sync import sync_to_async
User = get_user_model()


@strawberry_django.type(User)
class UserType:
    id: strawberry.auto
    email: strawberry.auto
    username: strawberry.auto
    first_name: strawberry.auto
    last_name: strawberry.auto
    role: strawberry.auto
    account_status: strawberry.auto
    is_premium: strawberry.auto
    date_joined: strawberry.auto
    last_login: strawberry.auto

    @strawberry.field
    async def profile(self) -> Optional['UserProfileType']:
        """Get user profile with onboarding status (async-safe)"""
        try:
            # Check if profile is already cached to avoid extra query
            if 'profile' in self._state.fields_cache:
                return self._state.fields_cache['profile']

            # Use sync_to_async to safely access profile relationship
            # This prevents "SynchronousOnlyOperation" error in async context
            profile_obj = await sync_to_async(lambda: getattr(self, 'profile', None))()
            return profile_obj
        except Exception as e:
            # Profile doesn't exist (new user without profile)
            return None


# Import after UserType to avoid circular imports
@strawberry.type
class UserProfileType:
    """Basic profile type for onboarding status"""
    onboarding_completed: bool
    onboarding_step: str


@strawberry.input
class _Unused_LearningGoalInput_Placeholder:
    # The actual LearningGoalInput is defined in onboarding.types to avoid
    # duplicate GraphQL input type definitions. This placeholder prevents
    # accidental redefinition during refactors.
    pass


@strawberry.input
class CompleteOnboardingInput:
    user: UserType
    role: str
    firstName: str
    lastName: str
    currentRole: str
    industry: str
    careerStage: str
    transitionTimeline: Optional[str] = None
    goals: Optional[List[OnboardingLearningGoalInput]] = None
    learningStyle: Optional[str] = None
    timeCommitment: Optional[str] = None


@strawberry.type
class OnboardingResponse:
    success: bool
    message: str
    user: Optional[UserType]
    roadmaps: str  # JSON string of roadmaps data