"""
Authentication utilities for JWT token handling
"""
from django.http import JsonResponse
from django.conf import settings
from datetime import datetime, timedelta

def set_jwt_cookies(response, access_token, refresh_token):
    """
    Set JWT tokens as HTTP-only cookies for security
    """
    # Set access token cookie (shorter expiration)
    response.set_cookie(
        'access_token',
        access_token,
        max_age=settings.NINJA_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds(),
        httponly=True,  # Prevents XSS attacks
        secure=not settings.DEBUG,  # HTTPS only in production
        samesite='Lax'  # CSRF protection
    )
    
    # Set refresh token cookie (longer expiration)
    response.set_cookie(
        'refresh_token', 
        refresh_token,
        max_age=settings.NINJA_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds(),
        httponly=True,  # Prevents XSS attacks
        secure=not settings.DEBUG,  # HTTPS only in production
        samesite='Lax'  # CSRF protection
    )
    
    return response

def clear_jwt_cookies(response):
    """
    Clear JWT cookies on logout
    """
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    return response

def get_tokens_from_cookies(request):
    """
    Extract JWT tokens from HTTP-only cookies
    """
    access_token = request.COOKIES.get('access_token')
    refresh_token = request.COOKIES.get('refresh_token')
    return access_token, refresh_token
