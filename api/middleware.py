"""
GraphQL authentication middleware for JWT tokens
"""
from ninja_jwt.tokens import UntypedToken, AccessToken
from ninja_jwt.exceptions import InvalidToken, TokenError
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model

User = get_user_model()

class JWTAuthMiddleware:
    """Middleware to authenticate users from JWT tokens in GraphQL requests"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Initialize user as anonymous
        request.user = AnonymousUser()
        
        # Try to get token from Authorization header first (preferred for API)
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        token = None
        
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        elif 'access_token' in request.COOKIES:
            # Fallback to cookie if no Authorization header
            token = request.COOKIES.get('access_token')
        
        if token:
            try:
                # Validate the token
                UntypedToken(token)
                
                # Get user from token
                access_token = AccessToken(token)
                user_id = access_token['user_id']
                
                # Set the user on the request
                try:
                    request.user = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    request.user = AnonymousUser()
                    
            except (InvalidToken, TokenError, KeyError):
                request.user = AnonymousUser()
        
        response = self.get_response(request)
        return response
