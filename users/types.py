import strawberry
import strawberry_django
from django.contrib.auth import get_user_model
User = get_user_model()


@strawberry_django.type(User)
class UserType:
    id: strawberry.auto
    email: strawberry.auto
    username: strawberry.auto
    role: strawberry.auto
    account_status: strawberry.auto
    is_premium: strawberry.auto
    date_joined: strawberry.auto
    last_login: strawberry.auto