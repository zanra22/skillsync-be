import strawberry
import strawberry_django
from typing import List

from django.contrib.auth.models import User

@strawberry_django.type(User)
class UserType:
    id: strawberry.auto
    username: strawberry.auto
    email: strawberry.auto
    first_name: strawberry.auto
    last_name: strawberry.auto
    is_active: strawberry.auto
    date_joined: strawberry.auto

@strawberry.type
class Query:

    @strawberry.field
    def users(self) -> List[UserType]:
        return User.objects.all()

schema = strawberry.Schema(query=Query)