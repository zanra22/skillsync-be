import strawberry
import strawberry_django
from django.contrib.auth import get_user_model
from typing import Optional
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
    def profile(self) -> Optional['UserProfileType']:
        """Get user profile with onboarding status"""
        if hasattr(self, 'profile'):
            return self.profile
        return None


# Import after UserType to avoid circular imports
@strawberry.type
class UserProfileType:
    """Basic profile type for onboarding status"""
    onboarding_completed: bool
    onboarding_step: str