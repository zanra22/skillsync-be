"""
Custom GraphQL view with JWT cookie support
"""
from strawberry.django.views import AsyncGraphQLView
from django.http import HttpResponse
import json

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
    
    def get_context(self, request, response=None):
        """Override context to include response for cookie handling"""
        context = super().get_context(request, response)
        # Add a cookie response handler to context
        context['response'] = CookieResponse()
        return context
    
    async def dispatch(self, request, *args, **kwargs):
        """Override dispatch to handle response cookies"""
        # Store context for later cookie application
        self._context = self.get_context(request)
        
        # Get the original response
        response = await super().dispatch(request, *args, **kwargs)
        
        # Apply cookies from context to actual response
        cookie_response = self._context.get('response')
        if cookie_response and hasattr(cookie_response, 'cookies'):
            for cookie in cookie_response.cookies:
                response.set_cookie(**cookie)
        
        return response
