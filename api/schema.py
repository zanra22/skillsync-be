import strawberry
from users.query import UsersQuery  # Updated import
from users.mutation import UsersMutation  # Updated import
from auth.query import AuthQuery  # Import auth query
from auth.mutation import AuthMutation  # Import auth mutation
from otps.query import OTPQuery  # Import OTP query
from otps.mutation import OTPMutation  # Import OTP mutation
# Add more imports as you create other apps
# from skills.query import SkillsQuery
# from skills.mutation import SkillsMutation

@strawberry.type
class Query:
    @strawberry.field
    def users(self) -> UsersQuery:
        return UsersQuery()
    
    @strawberry.field
    def auth(self) -> AuthQuery:
        return AuthQuery()
    
    @strawberry.field
    def otps(self) -> OTPQuery:
        return OTPQuery()
    
    # Add more app resolvers as you create them
    # @strawberry.field
    # def skills(self) -> SkillsQuery:
    #     return SkillsQuery()
    
    # Health check
    @strawberry.field
    def health(self) -> str:
        return "GraphQL API is running!"

@strawberry.type  
class Mutation:
    @strawberry.field
    def users(self) -> UsersMutation:
        return UsersMutation()
    
    @strawberry.field
    def auth(self) -> AuthMutation:
        return AuthMutation()
    
    @strawberry.field
    def otps(self) -> OTPMutation:
        return OTPMutation()
    
    # Add more app mutations as you create them
    # @strawberry.field
    # def skills(self) -> SkillsMutation:
    #     return SkillsMutation()

schema = strawberry.Schema(query=Query, mutation=Mutation)