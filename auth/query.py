import strawberry
import strawberry_django
from typing import List, Optional
from users.types import UserType
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.conf import settings

User = get_user_model()

@strawberry.type
class AuthQuery:
    
    @strawberry.field
    async def me(self, info) -> Optional[UserType]:
        """Get the currently authenticated user"""
        user = info.context.request.user
        if user.is_authenticated:
            return await sync_to_async(lambda: user)()
        return None
    
    @strawberry.field
    async def current_user(self, info) -> Optional[UserType]:
        """Alias for 'me' query - get the currently authenticated user"""
        return await self.me(info)
    
    @strawberry.field
    async def is_authenticated(self, info) -> bool:
        """Check if the current user is authenticated"""
        user = info.context.request.user
        return user.is_authenticated if user else False
    
    @strawberry.field
    async def user_permissions(self, info) -> List[str]:
        """Get the current user's permissions"""
        user = info.context.request.user
        if not user.is_authenticated:
            return []
        
        permissions = []
        
        # Role-based permissions
        if await sync_to_async(lambda: user.is_mentor())():
            permissions.extend(['can_mentor', 'can_view_mentee_profiles'])
        
        if await sync_to_async(lambda: user.is_admin())():
            permissions.extend(['can_moderate', 'can_manage_users', 'can_view_analytics'])
        
        if await sync_to_async(lambda: user.can_create_content())():
            permissions.append('can_create_content')
        
        if await sync_to_async(lambda: user.can_moderate())():
            permissions.append('can_moderate_content')
        
        if await sync_to_async(lambda: user.is_premium_user())():
            permissions.extend(['can_access_premium_content', 'can_book_premium_mentors'])
        
        return permissions
    
    @strawberry.field
    async def user_role(self, info) -> Optional[str]:
        """Get the current user's role"""
        user = info.context.request.user
        if user.is_authenticated:
            return await sync_to_async(lambda: user.role)()
        return None
    
    @strawberry.field
    async def account_status(self, info) -> Optional[str]:
        """Get the current user's account status"""
        user = info.context.request.user
        if user.is_authenticated:
            return await sync_to_async(lambda: user.account_status)()
        return None
    
    @strawberry.field
    async def is_premium(self, info) -> bool:
        """Check if the current user has premium access"""
        user = info.context.request.user
        if not user.is_authenticated:
            return False
        return await sync_to_async(lambda: user.is_premium_user())()
    
    @strawberry.field
    async def session_info(self, info) -> Optional[str]:
        """Get session information for the current user"""
        user = info.context.request.user
        if not user.is_authenticated:
            return None
        
        session_key = info.context.request.session.session_key
        if session_key:
            try:
                session = await sync_to_async(Session.objects.get)(session_key=session_key)
                return f"Session expires: {session.expire_date}"
            except Session.DoesNotExist:
                return "No active session found"
        return "No session key available"
    
    @strawberry.field
    async def check_email_exists(self, email: str) -> bool:
        """Check if an email address is already registered"""
        return await sync_to_async(
            User.objects.filter(email=email).exists
        )()
    
    @strawberry.field
    async def check_username_exists(self, username: str) -> bool:
        """Check if a username is already taken"""
        return await sync_to_async(
            User.objects.filter(username=username).exists
        )()