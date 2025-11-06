"""
Custom GraphQL view with JWT cookie support
"""
from strawberry.django.views import AsyncGraphQLView
from django.http import HttpResponse
from contextvars import ContextVar
import json

# Use contextvars for thread-safe, async-safe storage per request
_cookie_response_context: ContextVar = ContextVar('cookie_response', default=None)

class CookieResponse:
    """Helper class to store cookies that will be applied to the response"""
    def __init__(self):
        self.cookies = []

    def set_cookie(self, key, value, max_age=None, expires=None, path='/',
                   domain=None, secure=False, httponly=False, samesite='Lax'):
        """Store cookie data to be applied later"""
        self.cookies.append({
            'key': key,
            'value': value,
            'max_age': max_age,
            'expires': expires,
            'path': path,
            'domain': domain,
            'secure': secure,
            'httponly': httponly,
            'samesite': samesite
        })

    def delete_cookie(self, key, path='/', domain=None):
        """Store cookie deletion to be applied later"""
        self.cookies.append({
            'key': key,
            'value': '',
            'max_age': 0,
            'expires': 'Thu, 01 Jan 1970 00:00:00 GMT',
            'path': path,
            'domain': domain,
            'secure': False,
            'httponly': False,
            'samesite': 'Lax'
        })

class JWTGraphQLView(AsyncGraphQLView):
    """Custom GraphQL view that supports JWT cookie handling"""

    async def get_context(self, request, response=None):
        """Override context to include response for cookie handling"""
        context = await super().get_context(request, response)

        # 🔑 CRITICAL: Get or create CookieResponse in context var (thread-safe, async-safe)
        cookie_response = _cookie_response_context.get()
        if cookie_response is None:
            cookie_response = CookieResponse()
            _cookie_response_context.set(cookie_response)

        # 🔑 CRITICAL: Use attribute assignment, not dict assignment
        # StrawberryDjangoContext is an object, not a dict
        context.response = cookie_response
        return context

    async def dispatch(self, request, *args, **kwargs):
        """Override dispatch to handle response cookies"""
        # 🔑 CRITICAL: Create fresh CookieResponse for this request
        cookie_response = CookieResponse()
        token = _cookie_response_context.set(cookie_response)

        try:
            # Get the original response
            response = await super().dispatch(request, *args, **kwargs)

            # Apply cookies from context to actual response
            if cookie_response and hasattr(cookie_response, 'cookies'):
                for cookie in cookie_response.cookies:
                    print(f"🍪 Applying cookie from dispatch: {cookie['key']}", flush=True)
                    response.set_cookie(**cookie)

            return response
        finally:
            # 🔑 CRITICAL: Clean up after request
            _cookie_response_context.reset(token)
