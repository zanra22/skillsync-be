from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from .schema import schema
from strawberry.django.views import AsyncGraphQLView


class GraphQLViewWithOptionsSupport(AsyncGraphQLView):
    """
    AsyncGraphQLView subclass that handles OPTIONS requests for CORS preflight.

    Issue: Strawberry's AsyncGraphQLView doesn't implement options() method,
    causing OPTIONS preflight requests to fail with 405 Method Not Allowed.
    This breaks CORS because the preflight request never completes.

    Fix: Implement options() to return 200 OK. This allows:
    - CorsMiddleware to add CORS headers to the response
    - SecurityHeadersMiddleware to add security headers
    - The browser to complete the CORS preflight sequence

    Security: This doesn't bypass any security features. All middleware
    (rate limiting, security headers, JWT auth) still processes the response.
    """

    def options(self):
        """Handle OPTIONS preflight requests for CORS"""
        response = HttpResponse(status=200)
        response['Allow'] = 'OPTIONS, POST, GET'
        # Return 200 - all middleware will process this response normally
        # CorsMiddleware will add Access-Control-Allow-* headers
        # SecurityHeadersMiddleware will add security headers
        return response


# Create the GraphQL view with CSRF exemption
graphql_view = csrf_exempt(GraphQLViewWithOptionsSupport.as_view(schema=schema))


urlpatterns = [
    # GraphQL endpoint mounted at /graphql/ (see core.urls)
    path("", graphql_view, name="graphql"),
]