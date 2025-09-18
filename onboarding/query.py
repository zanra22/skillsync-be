import strawberry
from typing import Optional
from .mutation import OnboardingMutation


@strawberry.type
class OnboardingQuery:
    """
    Query operations for onboarding (currently empty, but structured for future use)
    """
    
    @strawberry.field
    def onboarding_status(self, info) -> Optional[str]:
        """
        Get current onboarding status for authenticated user
        """
        if not info.context.request.user.is_authenticated:
            return None
        
        user = info.context.request.user
        if hasattr(user, 'profile') and user.profile:
            return user.profile.onboarding_step
        return "welcome"
