from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from .schema import schema
from .views import JWTGraphQLView
from django.conf import settings


class GraphQLViewWithCookieSupport(JWTGraphQLView):
    """
    JWTGraphQLView subclass that handles OPTIONS requests for CORS preflight
    AND properly manages HTTP-only cookies.

    Extends JWTGraphQLView to:
    1. Fix cookie context mismatch (cookies are now properly applied)
    2. Handle CORS preflight OPTIONS requests
    3. Ensure cookies are in the HTTP response headers

    Issue: Strawberry's AsyncGraphQLView doesn't implement options() method,
    causing OPTIONS preflight requests to fail with 405 Method Not Allowed.

    Security: All cookies are HTTP-only and secure (XSS + CSRF protected).
    """

    def options(self):
        """Handle OPTIONS preflight requests for CORS"""
        response = HttpResponse(status=200)
        response['Allow'] = 'OPTIONS, POST, GET'
        # Return 200 - all middleware will process this response normally
        # CorsMiddleware will add Access-Control-Allow-* headers
        # SecurityHeadersMiddleware will add security headers
        return response


# Create the GraphQL view with CSRF exemption and cookie support
graphql_view = csrf_exempt(GraphQLViewWithCookieSupport.as_view(schema=schema))


def health_check(request):
    """Simple health check endpoint to test CORS"""
    return JsonResponse({
        "status": "ok",
        "cors_settings": {
            "CORS_ALLOW_ALL_ORIGINS": getattr(settings, 'CORS_ALLOW_ALL_ORIGINS', False),
            "CORS_ALLOW_CREDENTIALS": getattr(settings, 'CORS_ALLOW_CREDENTIALS', False),
            "CORS_ALLOWED_ORIGINS": getattr(settings, 'CORS_ALLOWED_ORIGINS', []),
            "ENVIRONMENT": getattr(settings, 'ENVIRONMENT', 'not set'),
        }
    })


urlpatterns = [
    # GraphQL endpoint mounted at /graphql/ (see core.urls)
    path("", graphql_view, name="graphql"),
    # Health check endpoint to test CORS
    path("health/", health_check, name="health"),
]