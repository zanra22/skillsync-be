import strawberry
import strawberry_django

from .types import UserType  # Import the UserType
from asgiref.sync import sync_to_async

from django.contrib.auth import get_user_model
User = get_user_model()

@strawberry.type
class UsersMutation:  # Renamed from Mutation to UsersMutation
    @strawberry.mutation
    async def create_user(self, username: str, email: str, password: str) -> UserType:
        user = await sync_to_async(User.objects.create_user)(
            username=username, 
            email=email, 
            password=password
        )
        return user