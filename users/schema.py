import strawberry
from .query import Query as UsersQuery
from .mutation import Mutation as UsersMutation
from .types import UserType

# Export the components for use in main schema
__all__ = ['UsersQuery', 'UsersMutation', 'UserType']

# Optional: Create a combined users schema if needed
@strawberry.type
class UsersSchema:
    """
    Combined Users Schema containing all user-related queries and mutations.
    This can be used independently or imported into the main schema.
    """
    query: UsersQuery = strawberry.field(default_factory=UsersQuery)
    mutation: UsersMutation = strawberry.field(default_factory=UsersMutation)

# Create a standalone schema for users (optional)
users_schema = strawberry.Schema(query=UsersQuery, mutation=UsersMutation)
