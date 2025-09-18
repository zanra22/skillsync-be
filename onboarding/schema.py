import strawberry
from .query import OnboardingQuery
from .mutation import OnboardingMutation


@strawberry.type
class OnboardingSchema:
    """
    GraphQL schema for onboarding operations
    """
    query: OnboardingQuery
    mutation: OnboardingMutation
