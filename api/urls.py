from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from .schema import schema
from strawberry.django.views import AsyncGraphQLView


# GraphQL view with CSRF exemption
base_graphql_view = AsyncGraphQLView.as_view(schema=schema)


@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def graphql_view(request):
    """GraphQL endpoint that handles CORS preflight (OPTIONS) requests"""
    if request.method == "OPTIONS":
        # Handle CORS preflight - return empty response
        # CORS headers will be added by CorsMiddleware
        return HttpResponse()
    else:
        # Delegate to Strawberry for GET/POST
        return base_graphql_view(request)


urlpatterns = [
    # GraphQL endpoint mounted at /graphql/ (see core.urls)
    path("", graphql_view, name="graphql"),
]