import strawberry
import strawberry_django
from typing import Optional
from django.contrib.auth import get_user_model
from users.types import UserType  # Import UserType for use in payloads
User = get_user_model()


@strawberry.input
class LoginInput:
    """Input type for user login"""
    email: str
    password: str
    remember_me: Optional[bool] = False

@strawberry.type
class LoginPayload:
    """Response payload for login mutation"""
    success: bool
    message: str
    user: Optional[UserType] = None
    access_token: Optional[str] = None
    # refresh_token removed - now stored in HTTP-only cookie
    expires_in: Optional[int] = None  # Token expiration time in seconds

@strawberry.type
class LogoutPayload:
    """Response payload for logout mutation"""
    success: bool
    message: str

@strawberry.type
class TokenRefreshPayload:
    """Response payload for token refresh"""
    success: bool
    message: str
    access_token: Optional[str] = None
    expires_in: Optional[int] = None