from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from .schema import schema
from strawberry.django.views import AsyncGraphQLView


# Create the GraphQL view with CSRF exemption
# CorsMiddleware will handle OPTIONS requests automatically
graphql_view = csrf_exempt(AsyncGraphQLView.as_view(schema=schema))


urlpatterns = [
    # GraphQL endpoint mounted at /graphql/ (see core.urls)
    path("", graphql_view, name="graphql"),
]