from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from .schema import schema
from strawberry.django.views import AsyncGraphQLView
from users.views import complete_onboarding

# Create the GraphQL view with CSRF exemption
graphql_view = csrf_exempt(AsyncGraphQLView.as_view(schema=schema))

urlpatterns = [
    # GraphQL endpoint
    path("", graphql_view, name="graphql"),
    
    # REST API endpoints
    path("onboarding/complete/", complete_onboarding, name="complete_onboarding"),
]