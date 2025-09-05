import strawberry
from .query import AuthQuery
from .mutation import AuthMutation
from .types import LoginInput, LoginPayload, LogoutPayload, TokenRefreshPayload

# Export the components for use in main schema
__all__ = ['AuthQuery', 'AuthMutation', 'LoginInput', 'LoginPayload', 'LogoutPayload', 'TokenRefreshPayload']

# Optional: Create a combined auth schema if needed
@strawberry.type
class AuthSchema:
    """
    Combined Auth Schema containing all authentication-related queries and mutations.
    This can be used independently or imported into the main schema.
    """
    query: AuthQuery = strawberry.field(default_factory=AuthQuery)
    mutation: AuthMutation = strawberry.field(default_factory=AuthMutation)

# Create a standalone schema for auth (optional)
auth_schema = strawberry.Schema(query=AuthQuery, mutation=AuthMutation)
