import strawberry
import strawberry_django
from typing import Optional
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.contrib.sessions.models import Session
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from ninja_jwt.tokens import RefreshToken, AccessToken

from .types import LoginInput, SignupInput, LoginPayload, SignupPayload, LogoutPayload, TokenRefreshPayload
from .secure_utils import SecureTokenManager
from users.types import UserType

User = get_user_model()

@strawberry.type
class AuthMutation:
    @strawberry.mutation
    async def login(self, info, input: LoginInput) -> LoginPayload:
        """Authenticate user with email and password"""
        try:
            # Authenticate user
            user = await sync_to_async(authenticate)(
                request=info.context.request,
                username=input.email,  # Using email as username
                password=input.password
            )
            
            if not user:
                return LoginPayload(
                    success=False,
                    message="Invalid email or password"
                )
            
            # Check if user account is active
            if not user.is_active:
                return LoginPayload(
                    success=False,
                    message="Your account has been deactivated. Please contact support."
                )
            
            # Check account status
            if hasattr(user, 'account_status'):
                if user.account_status == 'suspended':
                    return LoginPayload(
                        success=False,
                        message="Your account has been suspended. Please contact support."
                    )
                elif user.account_status == 'banned':
                    return LoginPayload(
                        success=False,
                        message="Your account has been banned."
                    )
                elif user.account_status == 'pending':
                    return LoginPayload(
                        success=False,
                        message="Your account is pending verification. Please check your email."
                    )
            
            # Login the user (optional for JWT-based auth)
            await sync_to_async(login)(info.context.request, user)
            
            # Update last login
            user.last_login = timezone.now()
            user.is_sign_in = True
            await sync_to_async(user.save)(update_fields=['last_login', 'is_sign_in'])
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            # Set refresh token as HTTP-only cookie with enhanced security
            response = info.context.response
            if response:
                SecureTokenManager.set_secure_jwt_cookies(
                    response, str(access_token), str(refresh), info.context.request
                )
            
            # Return access token in response, refresh token will be set as HTTP-only cookie
            return LoginPayload(
                success=True,
                message="Login successful",
                user=user,
                access_token=str(access_token),
                expires_in=int(settings.NINJA_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
            )
            
        except Exception as e:
            return LoginPayload(
                success=False,
                message=f"Login failed: {str(e)}"
            )
    
    @strawberry.mutation
    async def sign_up(self, info, input: SignupInput) -> SignupPayload:
        """Register a new user account"""
        try:
            # Check if user already exists
            existing_user = await sync_to_async(User.objects.filter(email=input.email).exists)()
            if existing_user:
                return SignupPayload(
                    success=False,
                    message="A user with this email already exists"
                )
            
            # Validate terms acceptance
            if not input.accept_terms:
                return SignupPayload(
                    success=False,
                    message="You must accept the terms and conditions"
                )
            
            # Validate password length
            if len(input.password) < 8:
                return SignupPayload(
                    success=False,
                    message="Password must be at least 8 characters long"
                )
            
            # Create username from first and last name
            username = f"{input.first_name.lower()}{input.last_name.lower()}".replace(" ", "")
            
            # Ensure username is unique
            original_username = username
            counter = 1
            while await sync_to_async(User.objects.filter(username=username).exists)():
                username = f"{original_username}{counter}"
                counter += 1
            
            # Create new user
            user = await sync_to_async(User.objects.create_user)(
                email=input.email,
                username=username,
                password=input.password,
                first_name=input.first_name,
                last_name=input.last_name
            )
            
            # Set user as pending verification
            if hasattr(user, 'account_status'):
                user.account_status = 'pending'
                await sync_to_async(user.save)(update_fields=['account_status'])
            
            # TODO: Send verification email here
            # await send_verification_email(user)
            
            return SignupPayload(
                success=True,
                message="Account created successfully! Please check your email to verify your account.",
                user=user
            )
            
        except Exception as e:
            return SignupPayload(
                success=False,
                message=f"Signup failed: {str(e)}"
            )
    
    @strawberry.mutation
    async def refresh_token(self, info, refresh_token: Optional[str] = None) -> TokenRefreshPayload:
        """Refresh access token using refresh token from cookies with enhanced security"""
        try:
            # Validate client fingerprint first
            if not SecureTokenManager.validate_fingerprint(info.context.request):
                return TokenRefreshPayload(
                    success=False,
                    message="Security validation failed - potential session hijacking detected"
                )
            
            # Try to get refresh token from parameter first, then from cookies
            token_to_use = refresh_token
            if not token_to_use and hasattr(info.context, 'request'):
                token_to_use = info.context.request.COOKIES.get('refresh_token')
            
            if not token_to_use:
                return TokenRefreshPayload(
                    success=False,
                    message="No refresh token provided"
                )
            
            refresh = RefreshToken(token_to_use)
            
            # Get user from token
            user = await sync_to_async(User.objects.get)(id=refresh['user_id'])
            
            if not user.is_active:
                return TokenRefreshPayload(
                    success=False,
                    message="User account is inactive"
                )
            
            # Generate new tokens (rotation)
            new_refresh = RefreshToken.for_user(user)
            new_access_token = new_refresh.access_token
            
            # Blacklist old refresh token
            try:
                # Use sync_to_async for the blacklist operation
                blacklist_func = sync_to_async(lambda: refresh.blacklist())
                await blacklist_func()
            except Exception:
                pass  # Token might already be blacklisted
            
            # Set new cookies with enhanced security
            response = info.context.response
            if response:
                SecureTokenManager.set_secure_jwt_cookies(
                    response, str(new_access_token), str(new_refresh), info.context.request
                )
            
            return TokenRefreshPayload(
                success=True,
                message="Token refreshed successfully",
                access_token=str(new_access_token),
                expires_in=int(settings.NINJA_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
            )
            
        except Exception as e:
            return TokenRefreshPayload(
                success=False,
                message=f"Token refresh failed: {str(e)}"
            )
    
    @strawberry.mutation
    async def logout(self, info, refresh_token: Optional[str] = None) -> LogoutPayload:
        """Logout the current user and clear JWT cookies"""
        try:
            user = info.context.request.user
            
            if user.is_authenticated:
                # Update user sign-in status
                if hasattr(user, 'is_sign_in'):
                    user.is_sign_in = False
                    await sync_to_async(user.save)(update_fields=['is_sign_in'])
                
                # Try to blacklist refresh token from parameter or cookies
                token_to_blacklist = refresh_token
                if not token_to_blacklist and hasattr(info.context, 'request'):
                    token_to_blacklist = info.context.request.COOKIES.get('refresh_token')
                
                if token_to_blacklist:
                    try:
                        token = RefreshToken(token_to_blacklist)
                        # Use sync_to_async for the blacklist operation
                        blacklist_func = sync_to_async(lambda: token.blacklist())
                        await blacklist_func()
                    except Exception:
                        pass  # Token might already be invalid
                
                # Logout the user from session
                await sync_to_async(logout)(info.context.request)
                
                # Clear JWT cookies with enhanced security
                response = info.context.response
                if response:
                    SecureTokenManager.clear_secure_cookies(response)
                
                return LogoutPayload(
                    success=True,
                    message="Logout successful"
                )
            else:
                return LogoutPayload(
                    success=False,
                    message="User is not authenticated"
                )
                
        except Exception as e:
            return LogoutPayload(
                success=False,
                message=f"Logout failed: {str(e)}"
            )
    
    @strawberry.mutation
    async def change_password(
        self, 
        info, 
        current_password: str, 
        new_password: str
    ) -> LoginPayload:
        """Change password for authenticated user"""
        try:
            user = info.context.request.user
            
            if not user.is_authenticated:
                return LoginPayload(
                    success=False,
                    message="Authentication required"
                )
            
            # Verify current password
            if not await sync_to_async(user.check_password)(current_password):
                return LoginPayload(
                    success=False,
                    message="Current password is incorrect"
                )
            
            # Validate new password
            if len(new_password) < 8:
                return LoginPayload(
                    success=False,
                    message="New password must be at least 8 characters long"
                )
            
            # Set new password
            await sync_to_async(user.set_password)(new_password)
            await sync_to_async(user.save)()
            
            return LoginPayload(
                success=True,
                message="Password changed successfully",
                user=user
            )
            
        except Exception as e:
            return LoginPayload(
                success=False,
                message=f"Password change failed: {str(e)}"
            )
    
    @strawberry.mutation
    async def request_password_reset(self, email: str) -> LogoutPayload:
        """Request password reset for given email"""
        try:
            user = await sync_to_async(User.objects.get)(email=email)
            
            # Generate reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Create reset link (you'll need to adjust the domain)
            reset_link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"
            
            # Send email (you'll need to configure email settings)
            await sync_to_async(send_mail)(
                subject="Password Reset Request",
                message=f"Click the link to reset your password: {reset_link}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            
            return LogoutPayload(
                success=True,
                message="Password reset email sent successfully"
            )
            
        except User.DoesNotExist:
            # Don't reveal if email exists or not for security
            return LogoutPayload(
                success=True,
                message="If the email exists, a password reset link has been sent"
            )
        except Exception as e:
            return LogoutPayload(
                success=False,
                message="Failed to send password reset email"
            )
    
    @strawberry.mutation
    async def reset_password(
        self, 
        uid: str, 
        token: str, 
        new_password: str
    ) -> LoginPayload:
        """Reset password using token from email"""
        try:
            # Decode uid
            user_id = force_str(urlsafe_base64_decode(uid))
            user = await sync_to_async(User.objects.get)(pk=user_id)
            
            # Verify token
            if not default_token_generator.check_token(user, token):
                return LoginPayload(
                    success=False,
                    message="Invalid or expired reset token"
                )
            
            # Validate new password
            if len(new_password) < 8:
                return LoginPayload(
                    success=False,
                    message="Password must be at least 8 characters long"
                )
            
            # Set new password
            await sync_to_async(user.set_password)(new_password)
            await sync_to_async(user.save)()
            
            return LoginPayload(
                success=True,
                message="Password reset successful",
                user=user
            )
            
        except (User.DoesNotExist, ValueError, TypeError):
            return LoginPayload(
                success=False,
                message="Invalid reset link"
            )
        except Exception as e:
            return LoginPayload(
                success=False,
                message=f"Password reset failed: {str(e)}"
            )
