from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from .schema import schema
from strawberry.django.views import AsyncGraphQLView


# GraphQL view class to handle both sync (OPTIONS) and async (POST/GET) requests
class GraphQLViewWithCORS(AsyncGraphQLView):
    """AsyncGraphQLView subclass that handles CORS preflight (OPTIONS) requests"""

    async def dispatch(self, request, *args, **kwargs):
        """Handle CORS preflight OPTIONS requests"""
        if request.method == "OPTIONS":
            # Return empty response for CORS preflight
            # CORS headers will be added by CorsMiddleware
            return HttpResponse()

        # Delegate to AsyncGraphQLView for POST/GET
        return await super().dispatch(request, *args, **kwargs)


# Create the view with CSRF exemption
graphql_view = csrf_exempt(GraphQLViewWithCORS.as_view(schema=schema))


urlpatterns = [
    # GraphQL endpoint mounted at /graphql/ (see core.urls)
    path("", graphql_view, name="graphql"),
]