from django.urls import path
from .schema import schema
from strawberry.django.views import AsyncGraphQLView

# Create the GraphQL view
graphql_view = AsyncGraphQLView.as_view(schema=schema)

urlpatterns = [
    path("graphql/", graphql_view, name="graphql"),
]