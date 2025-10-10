"""
Custom JWT token classes that include user role
"""
from ninja_jwt.tokens import AccessToken, RefreshToken
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomAccessToken(AccessToken):
    """Custom access token that includes user role in payload"""
    
    @classmethod
    def for_user(cls, user):
        """
        Returns an authorization token for the given user that will be provided
        after authenticating the user's credentials, and includes user role.
        """
        token = super().for_user(user)
        
        # Add user role to token payload
        token['role'] = user.role if hasattr(user, 'role') else 'learner'
        token['user_role'] = user.role if hasattr(user, 'role') else 'learner'  # Alternative claim name
        
        # Add other useful claims
        token['email'] = user.email
        token['is_staff'] = user.is_staff
        token['is_superuser'] = user.is_superuser
        
        return token


class CustomRefreshToken(RefreshToken):
    """Custom refresh token that includes user role in payload"""
    
    @classmethod
    def for_user(cls, user, remember_me=False):
        """
        Returns a refresh token for the given user that includes role information.
        
        Args:
            user: The user object
            remember_me: If True, use extended lifetime (30 days). If False, use default (7 days).
        """
        token = super().for_user(user)
        
        # Override token lifetime based on remember_me flag
        if remember_me:
            from django.conf import settings
            from datetime import timedelta
            # Set extended lifetime for Remember Me
            lifetime = settings.NINJA_JWT.get('REFRESH_TOKEN_LIFETIME_REMEMBER', timedelta(days=30))
            token.set_exp(lifetime=lifetime)
        
        # Add user role to refresh token payload (for consistency)
        token['role'] = user.role if hasattr(user, 'role') else 'learner'
        token['user_role'] = user.role if hasattr(user, 'role') else 'learner'
        token['email'] = user.email
        
        return token