import strawberry
import strawberry_django
from typing import List, Optional
from django.contrib.auth import get_user_model
from users.types import UserType
from profiles.models import UserProfile

User = get_user_model()

# Admin-specific user type that combines User and Profile data
@strawberry.type
class AdminUserDetailType:
    """Comprehensive user data for admin dashboard operations"""
    # User model fields
    id: str
    email: str
    username: str
    role: str
    account_status: str
    is_premium: bool
    is_active: bool
    is_suspended: bool
    is_blocked: bool
    is_email_verified: bool
    date_joined: str
    last_login: Optional[str]
    created_at: str
    updated_at: str
    
    # Profile fields (optional since profile might not exist)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    phone_number: Optional[str] = None
    location: Optional[str] = None
    skill_level: Optional[str] = None
    career_stage: Optional[str] = None
    industry: Optional[str] = None
    
    # Computed admin-specific fields
    display_name: str
    account_age_days: int
    is_newly_registered: bool

@strawberry.type
class UserStatsType:
    """User statistics for dashboard metrics"""
    total_users: int
    active_users: int
    instructor_users: int
    newly_registered_users: int
    suspended_users: int
    blocked_users: int
    email_verified_users: int
    premium_users: int
    last_updated: str

@strawberry.type
class PaginatedUsersType:
    """Paginated user results with metadata"""
    users: List[AdminUserDetailType]
    total_count: int
    total_pages: int
    current_page: int
    page_size: int
    has_next: bool
    has_previous: bool

@strawberry.type
class UserGrowthMetricsType:
    """User growth analytics over time"""
    period_days: int
    daily_registrations: List['DailyRegistrationStatsType']
    role_distribution: List['RoleStatsType']
    status_distribution: List['StatusStatsType']
    monthly_growth: List['MonthlyGrowthStatsType']
    generated_at: str

@strawberry.type
class DailyRegistrationStatsType:
    """Daily registration statistics"""
    date: str
    count: int
    cumulative_count: int

@strawberry.type
class RoleStatsType:
    """Role distribution statistics"""
    role: str
    count: int
    percentage: float

@strawberry.type
class StatusStatsType:
    """Account status distribution statistics"""
    status: str
    count: int
    percentage: float

@strawberry.type
class MonthlyGrowthStatsType:
    """Monthly growth statistics"""
    month: str
    total_users: int
    new_registrations: int
    growth_rate: float

# Input types for filtering and pagination
@strawberry.input
class UserFilterInput:
    """Input type for filtering users"""
    search: Optional[str] = None
    role: Optional[str] = None
    account_status: Optional[str] = None
    is_active: Optional[bool] = None
    is_premium: Optional[bool] = None
    is_email_verified: Optional[bool] = None
    date_joined_after: Optional[str] = None
    date_joined_before: Optional[str] = None

@strawberry.input
class PaginationInput:
    """Input type for pagination"""
    page: int = 1
    page_size: int = 20
    sort_by: Optional[str] = "date_joined"
    sort_order: Optional[str] = "desc"

# Admin-specific input types for mutations
@strawberry.input
class AdminUserUpdateInput:
    """Admin-only user account updates"""
    email: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None
    account_status: Optional[str] = None
    is_active: Optional[bool] = None
    is_suspended: Optional[bool] = None
    is_blocked: Optional[bool] = None
    is_premium: Optional[bool] = None

@strawberry.input
class AdminUserProfileUpdateInput:
    """Admin-only user profile updates"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    phone_number: Optional[str] = None
    location: Optional[str] = None
    skill_level: Optional[str] = None
    career_stage: Optional[str] = None
    industry: Optional[str] = None

@strawberry.type
class AdminUserMutationResult:
    """Result type for admin user mutations"""
    success: bool
    message: str
    user: Optional[AdminUserDetailType] = None
