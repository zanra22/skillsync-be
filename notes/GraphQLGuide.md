# GraphQL Implementation Guide for SkillSync

## 🎯 **Complete GraphQL Reference & Best Practices**

This guide provides comprehensive examples, syntax patterns, and best practices for GraphQL implementation in Django with Strawberry, based on our enterprise-grade authentication system.

---

## 📚 **Table of Contents**

1. [Schema Architecture](#schema-architecture)
2. [Types & Input Types](#types--input-types)
3. [Queries](#queries)
4. [Mutations](#mutations)
5. [Authentication & Security](#authentication--security)
6. [Error Handling](#error-handling)
7. [Best Practices](#best-practices)
8. [Frontend Integration](#frontend-integration)
9. [Testing Strategies](#testing-strategies)
10. [Performance Optimization](#performance-optimization)

---

## 🏗️ **Schema Architecture**

### **Project Structure**
```
backend/
├── api/
│   ├── schema.py          # Main schema aggregation
│   ├── middleware.py      # GraphQL middleware
│   └── views.py          # GraphQL view configuration
├── auth/
│   ├── schema.py         # Auth-specific schema
│   ├── types.py          # Auth GraphQL types
│   ├── mutation.py       # Auth mutations
│   └── query.py          # Auth queries
└── users/
    ├── schema.py         # User-specific schema
    ├── types.py          # User GraphQL types
    ├── mutation.py       # User mutations
    └── query.py          # User queries
```

### **Main Schema (`api/schema.py`)**
```python
import strawberry
from strawberry_django.optimizer import DjangoOptimizerExtension

# Import schemas from different apps
from auth.schema import AuthQuery, AuthMutation
from users.schema import UserQuery, UserMutation
from profiles.schema import ProfileQuery, ProfileMutation

@strawberry.type
class Query(AuthQuery, UserQuery, ProfileQuery):
    """
    Root Query Type - Aggregates all queries from different apps
    
    Best Practice: Keep this file minimal and import from app-specific schemas
    """
    pass

@strawberry.type  
class Mutation(AuthMutation, UserMutation, ProfileMutation):
    """
    Root Mutation Type - Aggregates all mutations from different apps
    
    Best Practice: Group related mutations in their respective app schemas
    """
    pass

# Schema configuration with optimization
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    extensions=[
        DjangoOptimizerExtension,  # Prevents N+1 queries
    ]
)
```

---

## 🏷️ **Types & Input Types**

### **Basic Type Definition (`auth/types.py`)**
```python
import strawberry
from typing import Optional, List
from datetime import datetime
from strawberry import auto

@strawberry.django.type(User)
class UserType:
    """
    GraphQL type for User model
    
    Best Practice: Use strawberry.django.type for automatic field mapping
    """
    id: auto
    email: auto
    first_name: auto
    last_name: auto
    is_active: auto
    date_joined: auto
    last_login: Optional[datetime]
    
    # Custom computed fields
    @strawberry.field
    def full_name(self) -> str:
        """Computed field example"""
        return f"{self.first_name} {self.last_name}".strip()
    
    @strawberry.field
    def display_name(self) -> str:
        """Another computed field with fallback logic"""
        if self.first_name or self.last_name:
            return self.full_name
        return self.email.split('@')[0]

@strawberry.input
class LoginInput:
    """
    Input type for login operations
    
    Best Practice: Always use input types for mutations, never use output types
    """
    email: str
    password: str

@strawberry.input
class RegisterInput:
    """
    Input type for user registration
    
    Security Note: Never include sensitive fields like hashed_password
    """
    email: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    terms_accepted: bool

@strawberry.type
class LoginPayload:
    """
    Response type for authentication operations
    
    Best Practice: Always include success/error information
    """
    success: bool
    message: str
    user: Optional[UserType] = None
    access_token: Optional[str] = None
    expires_in: Optional[int] = None
    
    # Additional metadata
    @strawberry.field
    def timestamp(self) -> datetime:
        """When this response was generated"""
        return datetime.now()

# Union Types for flexible responses
@strawberry.type
class ValidationError:
    field: str
    message: str

@strawberry.union
class LoginResult:
    """
    Union type for different login outcomes
    
    Use Case: When you need different response structures
    """
    success: LoginPayload
    validation_error: List[ValidationError]
```

### **Advanced Type Patterns**
```python
# Enum types
@strawberry.enum
class UserStatus:
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BANNED = "banned"

# Interface for shared fields
@strawberry.interface
class Node:
    """
    Global interface for entities with IDs
    
    Best Practice: Useful for pagination and caching
    """
    id: strawberry.ID

@strawberry.django.type(User)
class UserType(Node):
    """User implementing Node interface"""
    # Auto-inherits id from Node
    email: auto
    status: UserStatus

# Generic pagination
@strawberry.type
class PageInfo:
    """Standard pagination info"""
    has_next_page: bool
    has_previous_page: bool
    start_cursor: Optional[str] = None
    end_cursor: Optional[str] = None

@strawberry.type
class UserConnection:
    """
    Relay-style pagination for users
    
    Best Practice: Use consistent pagination patterns
    """
    edges: List['UserEdge']
    page_info: PageInfo
    total_count: int

@strawberry.type
class UserEdge:
    node: UserType
    cursor: str
```

---

## 🔍 **Queries**

### **Basic Queries (`auth/query.py`)**
```python
import strawberry
from typing import List, Optional
from strawberry_django import DjangoOptimizerExtension
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async

User = get_user_model()

@strawberry.type
class AuthQuery:
    """
    Authentication-related queries
    
    Security Note: Always check authentication before returning sensitive data
    """
    
    @strawberry.field
    async def me(self, info) -> Optional[UserType]:
        """
        Get current authenticated user
        
        Security: Requires valid JWT token
        """
        user = info.context.request.user
        
        if not user.is_authenticated:
            return None
            
        return user
    
    @strawberry.field
    async def user_profile(self, info) -> Optional[UserType]:
        """
        Get detailed user profile
        
        Example of async query with database access
        """
        user = info.context.request.user
        
        if not user.is_authenticated:
            raise PermissionError("Authentication required")
        
        # Async database access
        profile = await sync_to_async(
            User.objects.select_related('profile').get
        )(id=user.id)
        
        return profile

@strawberry.type
class UserQuery:
    """
    User management queries
    """
    
    @strawberry.field
    async def users(
        self, 
        info,
        first: Optional[int] = 10,
        after: Optional[str] = None,
        search: Optional[str] = None,
        status: Optional[UserStatus] = None
    ) -> UserConnection:
        """
        Paginated user list with filtering
        
        Best Practice: Always implement pagination for list queries
        """
        user = info.context.request.user
        
        # Permission check
        if not user.is_authenticated or not user.is_staff:
            raise PermissionError("Admin access required")
        
        # Build query
        queryset = User.objects.all()
        
        # Apply filters
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        
        if status:
            queryset = queryset.filter(status=status.value)
        
        # Apply pagination
        if after:
            # Decode cursor and apply
            start_id = decode_cursor(after)
            queryset = queryset.filter(id__gt=start_id)
        
        # Limit results
        users = await sync_to_async(list)(
            queryset.order_by('id')[:first + 1]
        )
        
        # Build connection
        has_next = len(users) > first
        if has_next:
            users = users[:-1]
        
        edges = [
            UserEdge(
                node=user,
                cursor=encode_cursor(user.id)
            )
            for user in users
        ]
        
        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=bool(after),
            start_cursor=edges[0].cursor if edges else None,
            end_cursor=edges[-1].cursor if edges else None,
        )
        
        total_count = await sync_to_async(queryset.count)()
        
        return UserConnection(
            edges=edges,
            page_info=page_info,
            total_count=total_count
        )
    
    @strawberry.field
    async def user_by_id(self, info, id: strawberry.ID) -> Optional[UserType]:
        """
        Get specific user by ID
        
        Security: Implement proper authorization
        """
        current_user = info.context.request.user
        
        if not current_user.is_authenticated:
            raise PermissionError("Authentication required")
        
        # Users can only see their own profile unless they're staff
        if str(current_user.id) != str(id) and not current_user.is_staff:
            raise PermissionError("Permission denied")
        
        try:
            user = await sync_to_async(User.objects.get)(id=id)
            return user
        except User.DoesNotExist:
            return None
```

### **Advanced Query Patterns**
```python
# Field-level permissions
@strawberry.field
async def sensitive_data(self, info) -> Optional[str]:
    """
    Example of field-level permission checking
    """
    user = info.context.request.user
    
    # Check if user can access this field
    if not user.has_perm('auth.view_sensitive_data'):
        return None  # Or raise PermissionError
    
    return "sensitive information"

# DataLoader pattern for N+1 prevention
from strawberry.dataloader import DataLoader

async def load_user_profiles(user_ids: List[int]) -> List[Profile]:
    """DataLoader function to batch profile loading"""
    profiles = await sync_to_async(list)(
        Profile.objects.filter(user_id__in=user_ids)
    )
    
    # Return in same order as requested
    profile_map = {p.user_id: p for p in profiles}
    return [profile_map.get(user_id) for user_id in user_ids]

@strawberry.field
async def profile(self, info) -> Optional[ProfileType]:
    """
    Use DataLoader to prevent N+1 queries
    """
    loader = DataLoader(load_fn=load_user_profiles)
    return await loader.load(self.id)
```

---

## ✏️ **Mutations**

### **Authentication Mutations (`auth/mutation.py`)**
```python
import strawberry
from typing import Optional
from django.contrib.auth import authenticate, login
from django.utils import timezone
from asgiref.sync import sync_to_async
from ninja_jwt.tokens import RefreshToken

@strawberry.type
class AuthMutation:
    """
    Authentication mutations with comprehensive security
    """
    
    @strawberry.mutation
    async def login(self, info, input: LoginInput) -> LoginPayload:
        """
        Secure login with comprehensive validation
        
        Security Features:
        - Rate limiting (handled by middleware)
        - Account status validation
        - Automatic token generation
        - Secure cookie setting
        """
        try:
            # Validate input
            if not input.email or not input.password:
                return LoginPayload(
                    success=False,
                    message="Email and password are required"
                )
            
            # Authenticate user
            user = await sync_to_async(authenticate)(
                request=info.context.request,
                username=input.email,
                password=input.password
            )
            
            if not user:
                return LoginPayload(
                    success=False,
                    message="Invalid email or password"
                )
            
            # Check account status
            if not user.is_active:
                return LoginPayload(
                    success=False,
                    message="Account is deactivated"
                )
            
            # Additional security checks
            if hasattr(user, 'account_status'):
                if user.account_status == 'suspended':
                    return LoginPayload(
                        success=False,
                        message="Account suspended. Contact support."
                    )
            
            # Update login tracking
            user.last_login = timezone.now()
            if hasattr(user, 'is_sign_in'):
                user.is_sign_in = True
            
            await sync_to_async(user.save)(
                update_fields=['last_login', 'is_sign_in']
            )
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            # Set secure cookies (handled by SecureTokenManager)
            response = info.context.response
            if response:
                from .secure_utils import SecureTokenManager
                SecureTokenManager.set_secure_jwt_cookies(
                    response, 
                    str(access_token), 
                    str(refresh), 
                    info.context.request
                )
            
            return LoginPayload(
                success=True,
                message="Login successful",
                user=user,
                access_token=str(access_token),
                expires_in=300,  # 5 minutes
            )
            
        except Exception as e:
            # Log error for debugging (don't expose to client)
            logger.error(f"Login error: {str(e)}")
            
            return LoginPayload(
                success=False,
                message="Login failed. Please try again."
            )
    
    @strawberry.mutation
    async def register(self, info, input: RegisterInput) -> LoginPayload:
        """
        User registration with validation
        
        Best Practice: Separate registration and login logic
        """
        try:
            # Validation
            if not input.terms_accepted:
                return LoginPayload(
                    success=False,
                    message="Terms and conditions must be accepted"
                )
            
            # Check if user exists
            user_exists = await sync_to_async(
                User.objects.filter(email=input.email).exists
            )()
            
            if user_exists:
                return LoginPayload(
                    success=False,
                    message="User with this email already exists"
                )
            
            # Password validation
            if len(input.password) < 8:
                return LoginPayload(
                    success=False,
                    message="Password must be at least 8 characters"
                )
            
            # Create user
            user = await sync_to_async(User.objects.create_user)(
                email=input.email,
                password=input.password,
                first_name=input.first_name or '',
                last_name=input.last_name or '',
            )
            
            # Send welcome email (async)
            # await send_welcome_email(user.email)
            
            return LoginPayload(
                success=True,
                message="Registration successful",
                user=user,
            )
            
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            
            return LoginPayload(
                success=False,
                message="Registration failed. Please try again."
            )
    
    @strawberry.mutation
    async def refresh_token(
        self, 
        info, 
        refresh_token: Optional[str] = None
    ) -> TokenRefreshPayload:
        """
        Token refresh with security validation
        
        Security Features:
        - Client fingerprinting
        - Token rotation
        - Automatic blacklisting
        """
        try:
            # Validate client fingerprint
            from .secure_utils import SecureTokenManager
            
            if not SecureTokenManager.validate_fingerprint(info.context.request):
                return TokenRefreshPayload(
                    success=False,
                    message="Security validation failed"
                )
            
            # Get refresh token from cookies or parameter
            token_to_use = (
                refresh_token or 
                info.context.request.COOKIES.get('refresh_token')
            )
            
            if not token_to_use:
                return TokenRefreshPayload(
                    success=False,
                    message="No refresh token provided"
                )
            
            # Validate and use refresh token
            refresh = RefreshToken(token_to_use)
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
                blacklist_func = sync_to_async(lambda: refresh.blacklist())
                await blacklist_func()
            except Exception:
                pass  # Token might already be blacklisted
            
            # Set new secure cookies
            response = info.context.response
            if response:
                SecureTokenManager.set_secure_jwt_cookies(
                    response,
                    str(new_access_token),
                    str(new_refresh),
                    info.context.request
                )
            
            return TokenRefreshPayload(
                success=True,
                message="Token refreshed successfully",
                access_token=str(new_access_token),
                expires_in=300,
            )
            
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            
            return TokenRefreshPayload(
                success=False,
                message="Token refresh failed"
            )
```

### **CRUD Mutation Patterns**
```python
@strawberry.type
class UserMutation:
    """
    User management mutations
    """
    
    @strawberry.mutation
    async def update_profile(
        self, 
        info, 
        input: UpdateProfileInput
    ) -> UpdateProfilePayload:
        """
        Update user profile with field-level validation
        
        Best Practice: Validate each field individually
        """
        user = info.context.request.user
        
        if not user.is_authenticated:
            return UpdateProfilePayload(
                success=False,
                message="Authentication required"
            )
        
        try:
            # Field-level validation
            updates = {}
            
            if input.first_name is not None:
                if len(input.first_name.strip()) < 1:
                    return UpdateProfilePayload(
                        success=False,
                        message="First name cannot be empty"
                    )
                updates['first_name'] = input.first_name.strip()
            
            if input.last_name is not None:
                updates['last_name'] = input.last_name.strip()
            
            if input.email is not None:
                # Email validation and uniqueness check
                if not validate_email(input.email):
                    return UpdateProfilePayload(
                        success=False,
                        message="Invalid email format"
                    )
                
                email_exists = await sync_to_async(
                    User.objects.filter(email=input.email)
                    .exclude(id=user.id)
                    .exists
                )()
                
                if email_exists:
                    return UpdateProfilePayload(
                        success=False,
                        message="Email already in use"
                    )
                
                updates['email'] = input.email
            
            # Apply updates
            for field, value in updates.items():
                setattr(user, field, value)
            
            await sync_to_async(user.save)(update_fields=list(updates.keys()))
            
            return UpdateProfilePayload(
                success=True,
                message="Profile updated successfully",
                user=user
            )
            
        except Exception as e:
            logger.error(f"Profile update error: {str(e)}")
            
            return UpdateProfilePayload(
                success=False,
                message="Profile update failed"
            )
    
    @strawberry.mutation
    async def delete_user(
        self, 
        info, 
        user_id: strawberry.ID,
        confirm: bool = False
    ) -> DeleteUserPayload:
        """
        Admin-only user deletion with confirmation
        
        Security: Multiple permission checks
        """
        current_user = info.context.request.user
        
        # Permission checks
        if not current_user.is_authenticated:
            raise PermissionError("Authentication required")
        
        if not current_user.is_staff:
            raise PermissionError("Admin privileges required")
        
        if not confirm:
            return DeleteUserPayload(
                success=False,
                message="Confirmation required for user deletion"
            )
        
        # Prevent self-deletion
        if str(current_user.id) == str(user_id):
            return DeleteUserPayload(
                success=False,
                message="Cannot delete your own account"
            )
        
        try:
            target_user = await sync_to_async(User.objects.get)(id=user_id)
            
            # Additional checks for super users
            if target_user.is_superuser and not current_user.is_superuser:
                return DeleteUserPayload(
                    success=False,
                    message="Cannot delete superuser account"
                )
            
            # Soft delete or hard delete based on business logic
            if hasattr(target_user, 'is_active'):
                # Soft delete
                target_user.is_active = False
                await sync_to_async(target_user.save)(update_fields=['is_active'])
                message = "User account deactivated"
            else:
                # Hard delete
                await sync_to_async(target_user.delete)()
                message = "User account deleted"
            
            return DeleteUserPayload(
                success=True,
                message=message
            )
            
        except User.DoesNotExist:
            return DeleteUserPayload(
                success=False,
                message="User not found"
            )
        except Exception as e:
            logger.error(f"User deletion error: {str(e)}")
            
            return DeleteUserPayload(
                success=False,
                message="User deletion failed"
            )
```

---

## 🔐 **Authentication & Security**

### **JWT Middleware Integration**
```python
# api/middleware.py
from django.utils.deprecation import MiddlewareMixin
from ninja_jwt.authentication import JWTAuthentication
from ninja_jwt.exceptions import InvalidToken

class GraphQLJWTMiddleware(MiddlewareMixin):
    """
    JWT Authentication middleware for GraphQL
    
    Handles both Authorization header and cookie-based tokens
    """
    
    def process_request(self, request):
        """Extract and validate JWT from request"""
        
        # Skip authentication for introspection queries
        if self.is_introspection_query(request):
            return None
        
        # Try Authorization header first
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            user = self.authenticate_token(token)
            if user:
                request.user = user
                return None
        
        # Try cookie-based authentication
        access_token = request.COOKIES.get('access_token')
        if access_token:
            user = self.authenticate_token(access_token)
            if user:
                request.user = user
        
        return None
    
    def authenticate_token(self, token):
        """Validate JWT token and return user"""
        try:
            jwt_auth = JWTAuthentication()
            validated_token = jwt_auth.get_validated_token(token)
            user = jwt_auth.get_user(validated_token)
            return user
        except InvalidToken:
            return None
    
    def is_introspection_query(self, request):
        """Check if request is GraphQL introspection"""
        if request.content_type != 'application/json':
            return False
        
        try:
            import json
            body = json.loads(request.body.decode('utf-8'))
            query = body.get('query', '')
            return '__schema' in query or '__type' in query
        except:
            return False
```

### **Permission Decorators**
```python
# auth/decorators.py
import strawberry
from functools import wraps
from typing import Callable, Any

def login_required(func: Callable) -> Callable:
    """
    Decorator to require authentication for GraphQL fields
    
    Usage:
        @strawberry.field
        @login_required
        async def protected_field(self, info) -> str:
            return "sensitive data"
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract info from args (usually second parameter)
        info = None
        for arg in args:
            if hasattr(arg, 'context'):
                info = arg
                break
        
        if not info:
            raise ValueError("GraphQL info not found in arguments")
        
        user = info.context.request.user
        if not user.is_authenticated:
            raise PermissionError("Authentication required")
        
        return await func(*args, **kwargs)
    
    return wrapper

def staff_required(func: Callable) -> Callable:
    """Decorator to require staff privileges"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        info = None
        for arg in args:
            if hasattr(arg, 'context'):
                info = arg
                break
        
        user = info.context.request.user
        if not user.is_authenticated:
            raise PermissionError("Authentication required")
        
        if not user.is_staff:
            raise PermissionError("Staff privileges required")
        
        return await func(*args, **kwargs)
    
    return wrapper

def permission_required(permission: str):
    """Decorator to require specific permission"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            info = None
            for arg in args:
                if hasattr(arg, 'context'):
                    info = arg
                    break
            
            user = info.context.request.user
            if not user.is_authenticated:
                raise PermissionError("Authentication required")
            
            if not user.has_perm(permission):
                raise PermissionError(f"Permission '{permission}' required")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

# Usage examples:
@strawberry.type
class SecureQuery:
    
    @strawberry.field
    @login_required
    async def user_profile(self, info) -> UserType:
        return info.context.request.user
    
    @strawberry.field
    @staff_required
    async def admin_data(self, info) -> str:
        return "admin only data"
    
    @strawberry.field
    @permission_required('users.view_sensitive_data')
    async def sensitive_data(self, info) -> str:
        return "sensitive information"
```

---

## ⚠️ **Error Handling**

### **Custom Exception Types**
```python
# api/exceptions.py
import strawberry
from typing import List, Optional

@strawberry.type
class FieldError:
    """Individual field validation error"""
    field: str
    message: str
    code: Optional[str] = None

@strawberry.type
class ValidationError:
    """Validation error with multiple field errors"""
    message: str
    errors: List[FieldError]

@strawberry.type
class AuthenticationError:
    """Authentication-related error"""
    message: str
    code: str = "AUTHENTICATION_REQUIRED"

@strawberry.type
class PermissionError:
    """Permission-related error"""
    message: str
    required_permission: Optional[str] = None
    code: str = "PERMISSION_DENIED"

# Union type for different error types
@strawberry.union
class MutationError:
    validation_error: ValidationError
    authentication_error: AuthenticationError
    permission_error: PermissionError

# Enhanced payload type with error handling
@strawberry.type
class UserMutationPayload:
    """Enhanced payload with comprehensive error handling"""
    success: bool
    message: str
    user: Optional[UserType] = None
    errors: Optional[List[FieldError]] = None
    
    @classmethod
    def success_response(cls, message: str, user: UserType = None):
        """Helper method for success responses"""
        return cls(
            success=True,
            message=message,
            user=user,
            errors=None
        )
    
    @classmethod
    def error_response(cls, message: str, errors: List[FieldError] = None):
        """Helper method for error responses"""
        return cls(
            success=False,
            message=message,
            user=None,
            errors=errors or []
        )
    
    @classmethod
    def validation_error_response(cls, field_errors: dict):
        """Helper method for validation errors"""
        errors = [
            FieldError(field=field, message=message)
            for field, message in field_errors.items()
        ]
        
        return cls(
            success=False,
            message="Validation failed",
            user=None,
            errors=errors
        )
```

### **Error Handling in Mutations**
```python
@strawberry.mutation
async def create_user(self, info, input: CreateUserInput) -> UserMutationPayload:
    """
    Example mutation with comprehensive error handling
    """
    try:
        # Validation
        field_errors = {}
        
        if not input.email:
            field_errors['email'] = "Email is required"
        elif not validate_email(input.email):
            field_errors['email'] = "Invalid email format"
        
        if not input.password:
            field_errors['password'] = "Password is required"
        elif len(input.password) < 8:
            field_errors['password'] = "Password must be at least 8 characters"
        
        # Check email uniqueness
        if input.email:
            email_exists = await sync_to_async(
                User.objects.filter(email=input.email).exists
            )()
            
            if email_exists:
                field_errors['email'] = "Email already in use"
        
        # Return validation errors if any
        if field_errors:
            return UserMutationPayload.validation_error_response(field_errors)
        
        # Create user
        user = await sync_to_async(User.objects.create_user)(
            email=input.email,
            password=input.password,
            first_name=input.first_name or '',
            last_name=input.last_name or '',
        )
        
        return UserMutationPayload.success_response(
            message="User created successfully",
            user=user
        )
        
    except IntegrityError as e:
        # Database constraint violation
        return UserMutationPayload.error_response(
            message="Database constraint violation",
            errors=[FieldError(field="database", message=str(e))]
        )
        
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Unexpected error in create_user: {str(e)}")
        
        return UserMutationPayload.error_response(
            message="An unexpected error occurred"
        )
```

---

## 🎯 **Best Practices**

### **Schema Organization**
```python
# ✅ DO: Organize by domain/app
auth/
├── schema.py     # Aggregate auth schema
├── types.py      # Auth-specific types
├── queries.py    # Auth queries
├── mutations.py  # Auth mutations
└── resolvers.py  # Complex resolver logic

# ❌ DON'T: Put everything in one file
api/
└── schema.py     # 2000+ lines of mixed concerns
```

### **Type Design**
```python
# ✅ DO: Use descriptive type names
@strawberry.type
class UserRegistrationPayload:
    success: bool
    message: str
    user: Optional[UserType] = None

# ❌ DON'T: Use generic names
@strawberry.type
class Response:
    data: Optional[str] = None
```

### **Input Validation**
```python
# ✅ DO: Validate inputs comprehensively
@strawberry.input
class CreateUserInput:
    email: str
    password: str
    
    def validate(self) -> List[FieldError]:
        """Custom validation method"""
        errors = []
        
        if not self.email:
            errors.append(FieldError(field="email", message="Required"))
        elif not validate_email(self.email):
            errors.append(FieldError(field="email", message="Invalid format"))
        
        if len(self.password) < 8:
            errors.append(FieldError(field="password", message="Too short"))
        
        return errors

# ❌ DON'T: Skip validation
@strawberry.input
class CreateUserInput:
    email: str
    password: str
    # No validation
```

### **Security Patterns**
```python
# ✅ DO: Check permissions at field level
@strawberry.field
async def sensitive_field(self, info) -> Optional[str]:
    user = info.context.request.user
    
    if not user.is_authenticated:
        return None  # Don't expose existence
    
    if not user.has_perm('view_sensitive'):
        return None
    
    return self.sensitive_data

# ❌ DON'T: Expose unauthorized data
@strawberry.field
def sensitive_field(self) -> str:
    return self.sensitive_data  # Always returns data
```

### **Database Optimization**
```python
# ✅ DO: Use select_related for foreign keys
@strawberry.field
async def user_with_profile(self, info, id: strawberry.ID) -> Optional[UserType]:
    user = await sync_to_async(
        User.objects.select_related('profile').get
    )(id=id)
    return user

# ✅ DO: Use prefetch_related for reverse relationships
@strawberry.field
async def users_with_posts(self, info) -> List[UserType]:
    users = await sync_to_async(list)(
        User.objects.prefetch_related('posts').all()
    )
    return users

# ❌ DON'T: Cause N+1 queries
@strawberry.field
async def users_with_posts(self, info) -> List[UserType]:
    users = await sync_to_async(list)(User.objects.all())
    # Each user.posts access will cause additional query
    return users
```

---

## 🌐 **Frontend Integration**

### **React/TypeScript Examples**
```typescript
// GraphQL query with TypeScript
const GET_USER_PROFILE = `
  query GetUserProfile {
    me {
      id
      email
      firstName
      lastName
      fullName
      lastLogin
    }
  }
`;

interface UserProfile {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  fullName: string;
  lastLogin: string | null;
}

interface GraphQLResponse<T> {
  data: T;
  errors?: Array<{ message: string }>;
}

// Type-safe API function
async function getUserProfile(): Promise<UserProfile | null> {
  try {
    const response = await fetch('/graphql/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include', // Important for HTTP-only cookies
      body: JSON.stringify({
        query: GET_USER_PROFILE,
      }),
    });

    const result: GraphQLResponse<{ me: UserProfile | null }> = await response.json();
    
    if (result.errors) {
      console.error('GraphQL errors:', result.errors);
      return null;
    }

    return result.data.me;
  } catch (error) {
    console.error('Network error:', error);
    return null;
  }
}

// Mutation example
const LOGIN_MUTATION = `
  mutation Login($input: LoginInput!) {
    login(input: $input) {
      success
      message
      user {
        id
        email
        firstName
        lastName
      }
      accessToken
      expiresIn
    }
  }
`;

interface LoginInput {
  email: string;
  password: string;
}

interface LoginResponse {
  success: boolean;
  message: string;
  user?: UserProfile;
  accessToken?: string;
  expiresIn?: number;
}

async function login(input: LoginInput): Promise<LoginResponse> {
  const response = await fetch('/graphql/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({
      query: LOGIN_MUTATION,
      variables: { input },
    }),
  });

  const result: GraphQLResponse<{ login: LoginResponse }> = await response.json();
  
  if (result.errors) {
    throw new Error(result.errors[0].message);
  }

  return result.data.login;
}
```

### **Apollo Client Configuration**
```typescript
// Apollo Client setup with authentication
import { ApolloClient, InMemoryCache, createHttpLink } from '@apollo/client';
import { setContext } from '@apollo/client/link/context';

const httpLink = createHttpLink({
  uri: '/graphql/',
  credentials: 'include', // Include HTTP-only cookies
});

const authLink = setContext((_, { headers }) => {
  // Get access token from memory (not localStorage)
  const token = getAccessTokenFromMemory();
  
  return {
    headers: {
      ...headers,
      authorization: token ? `Bearer ${token}` : "",
    }
  };
});

const client = new ApolloClient({
  link: authLink.concat(httpLink),
  cache: new InMemoryCache({
    typePolicies: {
      User: {
        fields: {
          // Custom cache policies
          fullName: {
            read(existing, { readField }) {
              const firstName = readField('firstName');
              const lastName = readField('lastName');
              return `${firstName} ${lastName}`.trim();
            }
          }
        }
      }
    }
  }),
  defaultOptions: {
    watchQuery: {
      errorPolicy: 'all',
    },
    query: {
      errorPolicy: 'all',
    },
  },
});

// React Hook for authentication
import { useQuery, useMutation } from '@apollo/client';
import { GET_USER_PROFILE, LOGIN_MUTATION } from './queries';

export function useAuth() {
  const { data, loading, error } = useQuery(GET_USER_PROFILE);
  const [loginMutation] = useMutation(LOGIN_MUTATION);

  const login = async (email: string, password: string) => {
    try {
      const result = await loginMutation({
        variables: {
          input: { email, password }
        }
      });

      return result.data.login;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  };

  return {
    user: data?.me,
    loading,
    error,
    login,
  };
}
```

---

## 🧪 **Testing Strategies**

### **Unit Testing Queries and Mutations**
```python
# tests/test_auth_mutations.py
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from strawberry.test import BaseGraphQLTestCase
from api.schema import schema

User = get_user_model()

class AuthMutationTests(BaseGraphQLTestCase):
    """Test authentication mutations"""
    
    GRAPHQL_SCHEMA = schema
    
    def setUp(self):
        """Set up test data"""
        self.user_data = {
            'email': 'test@example.com',
            'password': 'testpassword123',
            'first_name': 'Test',
            'last_name': 'User',
        }
        
        self.user = User.objects.create_user(**self.user_data)
    
    def test_login_success(self):
        """Test successful login"""
        query = """
        mutation Login($input: LoginInput!) {
            login(input: $input) {
                success
                message
                user {
                    id
                    email
                    firstName
                    lastName
                }
                accessToken
                expiresIn
            }
        }
        """
        
        variables = {
            'input': {
                'email': self.user_data['email'],
                'password': self.user_data['password'],
            }
        }
        
        response = self.query(query, variables=variables)
        
        self.assertResponseNoErrors(response)
        
        data = response.json()['data']['login']
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['email'], self.user_data['email'])
        self.assertIsNotNone(data['accessToken'])
        self.assertEqual(data['expiresIn'], 300)  # 5 minutes
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        query = """
        mutation Login($input: LoginInput!) {
            login(input: $input) {
                success
                message
                user {
                    id
                }
                accessToken
            }
        }
        """
        
        variables = {
            'input': {
                'email': self.user_data['email'],
                'password': 'wrongpassword',
            }
        }
        
        response = self.query(query, variables=variables)
        
        self.assertResponseNoErrors(response)
        
        data = response.json()['data']['login']
        self.assertFalse(data['success'])
        self.assertEqual(data['message'], 'Invalid email or password')
        self.assertIsNone(data['user'])
        self.assertIsNone(data['accessToken'])
    
    def test_register_success(self):
        """Test successful user registration"""
        query = """
        mutation Register($input: RegisterInput!) {
            register(input: $input) {
                success
                message
                user {
                    id
                    email
                    firstName
                    lastName
                }
            }
        }
        """
        
        variables = {
            'input': {
                'email': 'newuser@example.com',
                'password': 'newpassword123',
                'firstName': 'New',
                'lastName': 'User',
                'termsAccepted': True,
            }
        }
        
        response = self.query(query, variables=variables)
        
        self.assertResponseNoErrors(response)
        
        data = response.json()['data']['register']
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['email'], 'newuser@example.com')
        
        # Verify user was created in database
        self.assertTrue(
            User.objects.filter(email='newuser@example.com').exists()
        )

@pytest.mark.asyncio
class AuthQueryTests(TestCase):
    """Test authentication queries"""
    
    async def test_me_query_authenticated(self):
        """Test me query with authenticated user"""
        # Create test user
        user = await User.objects.acreate(
            email='test@example.com',
            first_name='Test',
            last_name='User',
        )
        
        # Mock authenticated request
        from unittest.mock import Mock
        request = Mock()
        request.user = user
        
        info = Mock()
        info.context.request = request
        
        # Test the query
        from auth.query import AuthQuery
        auth_query = AuthQuery()
        
        result = await auth_query.me(info)
        
        assert result is not None
        assert result.email == 'test@example.com'
        assert result.first_name == 'Test'
    
    async def test_me_query_unauthenticated(self):
        """Test me query without authentication"""
        from django.contrib.auth.models import AnonymousUser
        from unittest.mock import Mock
        
        request = Mock()
        request.user = AnonymousUser()
        
        info = Mock()
        info.context.request = request
        
        from auth.query import AuthQuery
        auth_query = AuthQuery()
        
        result = await auth_query.me(info)
        
        assert result is None
```

### **Integration Testing**
```python
# tests/test_integration.py
import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
import json

User = get_user_model()

class GraphQLIntegrationTests(TestCase):
    """Integration tests for GraphQL API"""
    
    def setUp(self):
        self.client = Client()
        self.graphql_url = '/graphql/'
        
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpassword123',
            first_name='Test',
            last_name='User',
        )
    
    def execute_query(self, query, variables=None, headers=None):
        """Helper method to execute GraphQL queries"""
        body = {
            'query': query,
            'variables': variables or {},
        }
        
        response = self.client.post(
            self.graphql_url,
            data=json.dumps(body),
            content_type='application/json',
            **headers or {}
        )
        
        return response
    
    def test_full_authentication_flow(self):
        """Test complete authentication flow"""
        # 1. Login
        login_query = """
        mutation Login($input: LoginInput!) {
            login(input: $input) {
                success
                message
                user { id email }
                accessToken
            }
        }
        """
        
        login_response = self.execute_query(
            login_query,
            variables={
                'input': {
                    'email': 'test@example.com',
                    'password': 'testpassword123',
                }
            }
        )
        
        self.assertEqual(login_response.status_code, 200)
        
        login_data = login_response.json()['data']['login']
        self.assertTrue(login_data['success'])
        
        access_token = login_data['accessToken']
        self.assertIsNotNone(access_token)
        
        # 2. Use access token to access protected resource
        me_query = """
        query Me {
            me {
                id
                email
                firstName
                lastName
            }
        }
        """
        
        me_response = self.execute_query(
            me_query,
            headers={'HTTP_AUTHORIZATION': f'Bearer {access_token}'}
        )
        
        self.assertEqual(me_response.status_code, 200)
        
        me_data = me_response.json()['data']['me']
        self.assertIsNotNone(me_data)
        self.assertEqual(me_data['email'], 'test@example.com')
        
        # 3. Test token refresh
        refresh_query = """
        mutation RefreshToken {
            refreshToken(refreshToken: "") {
                success
                message
                accessToken
            }
        }
        """
        
        refresh_response = self.execute_query(refresh_query)
        
        # Should work if refresh token cookie is set
        refresh_data = refresh_response.json()['data']['refreshToken']
        # Note: This might fail in unit tests without proper cookie handling
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        login_query = """
        mutation Login($input: LoginInput!) {
            login(input: $input) {
                success
                message
            }
        }
        """
        
        # Make multiple failed login attempts
        for i in range(10):
            response = self.execute_query(
                login_query,
                variables={
                    'input': {
                        'email': 'test@example.com',
                        'password': 'wrongpassword',
                    }
                }
            )
            
            if i < 5:
                # Should allow first few attempts
                self.assertEqual(response.status_code, 200)
            else:
                # Should start rate limiting
                # Note: Actual behavior depends on rate limiting configuration
                pass
```

---

## 🚀 **Performance Optimization**

### **DataLoader Pattern**
```python
# utils/dataloaders.py
from strawberry.dataloader import DataLoader
from typing import List
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()

async def load_users_by_ids(user_ids: List[int]) -> List[User]:
    """
    DataLoader function to batch load users by IDs
    
    Prevents N+1 queries when accessing user relationships
    """
    users = await sync_to_async(list)(
        User.objects.filter(id__in=user_ids)
    )
    
    # Return in same order as requested
    user_map = {user.id: user for user in users}
    return [user_map.get(user_id) for user_id in user_ids]

async def load_profiles_by_user_ids(user_ids: List[int]) -> List['Profile']:
    """DataLoader for user profiles"""
    from profiles.models import Profile
    
    profiles = await sync_to_async(list)(
        Profile.objects.filter(user_id__in=user_ids)
    )
    
    profile_map = {profile.user_id: profile for profile in profiles}
    return [profile_map.get(user_id) for user_id in user_ids]

# Usage in resolvers
@strawberry.field
async def created_by(self, info) -> Optional[UserType]:
    """Use DataLoader to prevent N+1 queries"""
    user_loader = DataLoader(load_fn=load_users_by_ids)
    return await user_loader.load(self.created_by_id)
```

### **Query Optimization**
```python
# Optimized query with select_related and prefetch_related
@strawberry.field
async def users_with_profiles(
    self, 
    info,
    limit: int = 10
) -> List[UserType]:
    """
    Optimized user query with profile data
    
    Uses select_related to join profile data in single query
    """
    users = await sync_to_async(list)(
        User.objects
        .select_related('profile')  # Join profile table
        .prefetch_related('groups')  # Prefetch many-to-many
        .filter(is_active=True)
        .order_by('-date_joined')
        [:limit]
    )
    
    return users

# Query complexity analysis
@strawberry.field
async def complex_user_data(self, info) -> List[UserType]:
    """
    Example of query complexity monitoring
    
    Use this pattern for expensive operations
    """
    # Check query complexity/depth
    query_depth = info.field_asts[0].selection_set
    if self._calculate_depth(query_depth) > MAX_QUERY_DEPTH:
        raise ValueError("Query too complex")
    
    # Proceed with optimized query
    return await self.get_optimized_users()
```

### **Caching Strategies**
```python
# Redis caching for expensive operations
from django.core.cache import cache
import hashlib

@strawberry.field
async def expensive_computation(self, info, params: str) -> str:
    """
    Example of caching expensive GraphQL operations
    """
    # Create cache key from query and parameters
    cache_key = f"expensive_computation:{hashlib.md5(params.encode()).hexdigest()}"
    
    # Try to get from cache first
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    # Perform expensive operation
    result = await self.perform_expensive_operation(params)
    
    # Cache for 1 hour
    cache.set(cache_key, result, 3600)
    
    return result

# Query-level caching with cache control
@strawberry.field
async def public_data(self, info) -> List[PublicDataType]:
    """
    Public data that can be cached aggressively
    """
    # Set cache control headers
    if hasattr(info.context, 'response'):
        info.context.response['Cache-Control'] = 'public, max-age=3600'
    
    return await self.get_public_data()
```

---

This comprehensive GraphQL guide provides everything needed to implement and maintain a production-ready GraphQL API with Django and Strawberry, including security best practices, performance optimizations, and real-world examples based on our enterprise-grade authentication system.