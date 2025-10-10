import strawberry
import strawberry_django
from typing import Optional
from django.contrib.auth import authenticate  # Only for credential validation, not session management
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from .custom_tokens import CustomRefreshToken as RefreshToken, CustomAccessToken as AccessToken

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
            
            # NOTE: Pure JWT authentication - no Django session management needed
            # We only use authenticate() for credential validation, not login() for sessions
            
            # Update last login and sign-in status
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
            
            # Create username from email (temporary until names are provided in onboarding)
            username = input.email.split('@')[0].lower().replace('.', '_')
            
            # Ensure username is unique
            original_username = username
            counter = 1
            while await sync_to_async(User.objects.filter(username=username).exists)():
                username = f"{original_username}{counter}"
                counter += 1
            
            # Create new user without names (will be collected during onboarding)
            user = await sync_to_async(User.objects.create_user)(
                email=input.email,
                username=username,
                password=input.password,
                first_name="",  # Empty initially, filled during onboarding
                last_name=""    # Empty initially, filled during onboarding
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
            print("\n" + "="*80)
            print("🔄 TOKEN REFRESH MUTATION CALLED")
            print("="*80)
            
            # Validate client fingerprint first (skip in development)
            from django.conf import settings
            if settings.DEBUG:
                print("🔧 Development mode: Skipping fingerprint validation for token refresh")
            elif not SecureTokenManager.validate_fingerprint(info.context.request):
                print("❌ Fingerprint validation FAILED")
                return TokenRefreshPayload(
                    success=False,
                    message="Security validation failed - potential session hijacking detected"
                )
            
            # Try to get refresh token from parameter first, then from cookies
            token_to_use = refresh_token
            if not token_to_use and hasattr(info.context, 'request'):
                token_to_use = info.context.request.COOKIES.get('refresh_token')
                if token_to_use:
                    print(f"📦 Retrieved refresh_token from cookie: {token_to_use[:30]}...")
                else:
                    print(f"❌ No refresh_token in cookies")
                    print(f"🍪 Available cookies: {list(info.context.request.COOKIES.keys())}")
            
            if not token_to_use:
                print("❌ No refresh token provided (neither parameter nor cookie)")
                return TokenRefreshPayload(
                    success=False,
                    message="No refresh token provided"
                )
            
            print(f"✅ Validating refresh token (length: {len(token_to_use)})")
            refresh = RefreshToken(token_to_use)
            print(f"✅ Refresh token validated successfully")
            
            # Get user from token
            user = await sync_to_async(User.objects.get)(id=refresh['user_id'])
            print(f"👤 User retrieved: {user.email} (id={user.id}, is_active={user.is_active})")
            
            if not user.is_active:
                print(f"❌ User account is INACTIVE")
                return TokenRefreshPayload(
                    success=False,
                    message="User account is inactive"
                )
            
            # Determine remember_me by checking the existing token's lifetime BEFORE generating new tokens
            # The refresh token payload contains 'exp' claim which tells us the expiry
            token_exp = refresh.get('exp', 0)  # Unix timestamp (integer)
            
            # Get current time as Unix timestamp (integer)
            import time
            current_time = int(time.time())
            
            # Calculate time remaining in seconds
            time_remaining = token_exp - current_time
            
            # If token has more than 1 day remaining and was issued with long lifetime, it's a persistent login
            # Session tokens: 7 days default
            # Persistent tokens: 30 days with Remember Me
            # Threshold: If > 10 days remaining, definitely persistent; if < 10 days, could be session
            remember_me = time_remaining > (10 * 24 * 60 * 60)  # More than 10 days = persistent
            
            if remember_me:
                print(f"🔄 Token refresh: Detected PERSISTENT login (remember_me=True)")
                print(f"   Time remaining: {time_remaining / 86400:.1f} days")
            else:
                print(f"🔄 Token refresh: Detected SESSION login (remember_me=False)")
                print(f"   Time remaining: {time_remaining / 86400:.1f} days ({time_remaining / 3600:.1f} hours)")
            
            # Generate new tokens (rotation) with the same remember_me setting
            print(f"🔄 Generating new tokens for user: {user.email} (remember_me={remember_me})")
            new_refresh = RefreshToken.for_user(user, remember_me=remember_me)
            new_access_token = new_refresh.access_token
            print(f"✅ New tokens generated with lifetime: {(new_refresh.get('exp', 0) - current_time) / 86400:.1f} days")
            
            # Blacklist old refresh token
            try:
                # Use sync_to_async for the blacklist operation
                # Note: ninja-jwt's RefreshToken.blacklist() requires simplejwt.token_blacklist app
                # Check if blacklist is available
                if hasattr(refresh, 'blacklist'):
                    blacklist_func = sync_to_async(lambda: refresh.blacklist())
                    await blacklist_func()
                    print(f"✅ Old refresh token blacklisted")
                else:
                    # Fallback: Add to OutstandingToken/BlacklistedToken manually
                    from ninja_jwt.settings import api_settings
                    if 'ninja_jwt.token_blacklist' in settings.INSTALLED_APPS:
                        from ninja_jwt.token_blacklist.models import OutstandingToken, BlacklistedToken
                        # Get the jti (JWT ID) from the token
                        jti = refresh.get(api_settings.JTI_CLAIM)
                        if jti:
                            try:
                                token_obj = await sync_to_async(OutstandingToken.objects.get)(jti=jti)
                                await sync_to_async(BlacklistedToken.objects.get_or_create)(token=token_obj)
                                print(f"✅ Old refresh token blacklisted (manual)")
                            except OutstandingToken.DoesNotExist:
                                print(f"⚠️ Token not found in OutstandingToken table")
                    else:
                        print(f"⚠️ Token blacklist app not installed - token rotation without blacklist")
            except Exception as e:
                print(f"⚠️ Token blacklist failed (may already be blacklisted): {str(e)}")
                pass  # Token might already be blacklisted
            
            # Set new cookies with enhanced security
            # remember_me was already determined above based on old token lifetime
            response = info.context.response
            if response:
                SecureTokenManager.set_secure_jwt_cookies(
                    response, str(new_access_token), str(new_refresh), info.context.request,
                    remember_me=remember_me  # Use the remember_me value determined earlier
                )
                print(f"✅ Cookies set successfully with remember_me={remember_me}")
            
            print(f"✅ Token refresh SUCCESSFUL for user: {user.email}")
            print("="*80 + "\n")
            
            return TokenRefreshPayload(
                success=True,
                message="Token refreshed successfully",
                access_token=str(new_access_token),
                expires_in=int(settings.NINJA_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
            )
            
        except Exception as e:
            print(f"❌ TOKEN REFRESH FAILED: {type(e).__name__}: {str(e)}")
            import traceback
            print(f"📋 Full traceback:\n{traceback.format_exc()}")
            print("="*80 + "\n")
            return TokenRefreshPayload(
                success=False,
                message=f"Token refresh failed: {str(e)}"
            )
    
    @strawberry.mutation
    async def logout(self, info, refresh_token: Optional[str] = None) -> LogoutPayload:
        """Logout the current user and clear JWT cookies"""
        try:
            user = info.context.request.user
            
            # Try to get user from JWT token if Django session user is not authenticated
            if not user.is_authenticated:
                # Try to extract user from refresh_token cookie
                token_to_check = refresh_token
                if not token_to_check and hasattr(info.context, 'request'):
                    token_to_check = info.context.request.COOKIES.get('refresh_token')
                
                if token_to_check:
                    try:
                        token = RefreshToken(token_to_check)
                        user_id = token.get('user_id')
                        if user_id:
                            user = await sync_to_async(User.objects.get)(id=user_id)
                            print(f"🔓 User extracted from JWT token: {user.email}")
                    except Exception as e:
                        print(f"⚠️ Could not extract user from token: {str(e)}")
            
            if user.is_authenticated:
                print(f"🔓 Authenticated user logout: {user.email}")
                
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
                        # Check if blacklist method is available
                        if hasattr(token, 'blacklist'):
                            blacklist_func = sync_to_async(lambda: token.blacklist())
                            await blacklist_func()
                            print(f"✅ Refresh token blacklisted for user: {user.email}")
                        else:
                            print(f"⚠️ Token blacklist not available (will rely on cookie clearing)")
                    except Exception as e:
                        print(f"⚠️ Token blacklist failed: {str(e)}")
                        pass  # Token might already be invalid
                
                # NOTE: We use pure JWT auth, NOT Django sessions
                # No need to call Django's logout() - we manage auth via JWT cookies only
                print(f"✅ JWT logout completed for user: {user.email}")
            else:
                # User not authenticated in Django session and no valid JWT token
                print(f"⚠️ Logout called for unauthenticated user (will still clear cookies)")
            
            # ✅ ALWAYS clear cookies regardless of authentication status
            # This handles stale cookie cleanup when session has expired
            response = info.context.response
            if response:
                SecureTokenManager.clear_secure_cookies(response)
                print(f"✅ Cookies cleared successfully")
            
            return LogoutPayload(
                success=True,
                message="Logout successful"
            )
                
        except Exception as e:
            print(f"❌ Logout error: {str(e)}")
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
