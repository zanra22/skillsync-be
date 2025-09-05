import strawberry
import strawberry_django
from typing import List, Optional
from .types import UserType

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
User = get_user_model()

@strawberry.type
class UsersQuery:  # Renamed from Query to UsersQuery
    @strawberry.field
    async def users(self) -> List[UserType]:
        return await sync_to_async(list)(User.objects.all())
    
    @strawberry.field
    async def user(self, id: int) -> Optional[UserType]:
        try:
            return await sync_to_async(User.objects.get)(id=id)
        except User.DoesNotExist:
            return None