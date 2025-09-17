import strawberry
from typing import Optional
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from asgiref.sync import sync_to_async
from users.types import UserType
from .types import AdminUserDetailType, AdminUserUpdateInput, AdminUserMutationResult
from .query import convert_user_to_admin_detail

User = get_user_model()

@strawberry.type
class AdminMutation:
    
    @strawberry.mutation
    async def update_user(self, user_id: str, input: AdminUserUpdateInput) -> AdminUserMutationResult:
        """Update user information (admin only)"""
        try:
            @sync_to_async
            def update_user_sync():
                with transaction.atomic():
                    user = User.objects.get(id=user_id)
                    
                    # Update fields if provided
                    if input.email is not None:
                        if User.objects.filter(email=input.email).exclude(id=user_id).exists():
                            return AdminUserMutationResult(
                                success=False,
                                message="Email already exists"
                            )
                        user.email = input.email
                    
                    if input.username is not None:
                        if User.objects.filter(username=input.username).exclude(id=user_id).exists():
                            return AdminUserMutationResult(
                                success=False,
                                message="Username already exists"
                            )
                        user.username = input.username
                    
                    if input.role is not None:
                        user.role = input.role
                    
                    if input.account_status is not None:
                        user.account_status = input.account_status
                    
                    if input.is_active is not None:
                        user.is_active = input.is_active
                    
                    if input.is_suspended is not None:
                        user.is_suspended = input.is_suspended
                    
                    if input.is_blocked is not None:
                        user.is_blocked = input.is_blocked
                    
                    if input.is_premium is not None:
                        user.is_premium = input.is_premium
                    
                    user.full_clean()
                    user.save()
                    
                    return AdminUserMutationResult(
                        success=True,
                        message="User updated successfully",
                        user=convert_user_to_admin_detail(user)
                    )
            
            return await update_user_sync()
        
        except User.DoesNotExist:
            return AdminUserMutationResult(
                success=False,
                message="User not found"
            )
        except ValidationError as e:
            return AdminUserMutationResult(
                success=False,
                message=f"Validation error: {e}"
            )
        except Exception as e:
            return AdminUserMutationResult(
                success=False,
                message=f"Error updating user: {str(e)}"
            )
    
    @strawberry.mutation
    async def suspend_user(self, user_id: str, reason: Optional[str] = None) -> AdminUserMutationResult:
        """Suspend a user account"""
        try:
            @sync_to_async
            def suspend_user_sync():
                user = User.objects.get(id=user_id)
                user.is_suspended = True
                user.is_active = False
                user.save()
                
                message = "User suspended successfully"
                if reason:
                    message += f" - Reason: {reason}"
                
                return AdminUserMutationResult(
                    success=True,
                    message=message,
                    user=convert_user_to_admin_detail(user)
                )
            
            return await suspend_user_sync()
        
        except User.DoesNotExist:
            return AdminUserMutationResult(
                success=False,
                message="User not found"
            )
        except Exception as e:
            return AdminUserMutationResult(
                success=False,
                message=f"Error suspending user: {str(e)}"
            )
    
    @strawberry.mutation
    async def unsuspend_user(self, user_id: str) -> AdminUserMutationResult:
        """Unsuspend a user account"""
        try:
            @sync_to_async
            def unsuspend_user_sync():
                user = User.objects.get(id=user_id)
                user.is_suspended = False
                user.is_active = True
                user.save()
                
                return AdminUserMutationResult(
                    success=True,
                    message="User unsuspended successfully",
                    user=convert_user_to_admin_detail(user)
                )
            
            return await unsuspend_user_sync()
        
        except User.DoesNotExist:
            return AdminUserMutationResult(
                success=False,
                message="User not found"
            )
        except Exception as e:
            return AdminUserMutationResult(
                success=False,
                message=f"Error unsuspending user: {str(e)}"
            )
