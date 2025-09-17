import strawberry
from typing import List, Optional
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta, date
from users.types import UserType
from profiles.models import UserProfile
from asgiref.sync import sync_to_async
from .types import (
    AdminUserDetailType, 
    UserStatsType, 
    PaginatedUsersType, 
    UserGrowthMetricsType,
    DailyRegistrationStatsType,
    RoleStatsType,
    StatusStatsType,
    MonthlyGrowthStatsType,
    UserFilterInput,
    PaginationInput
)

User = get_user_model()

def convert_user_to_admin_detail(user):
    """Helper function to convert User instance to AdminUserDetailType with profile data"""
    try:
        profile = user.profile
        first_name = profile.first_name
        last_name = profile.last_name
        bio = profile.bio
        job_title = profile.job_title
        company = profile.company
        phone_number = profile.phone_number
        location = profile.location
        skill_level = profile.skill_level
        career_stage = profile.career_stage
        industry = profile.industry
    except (UserProfile.DoesNotExist, AttributeError):
        # No profile exists for this user, use User model fields as fallback
        first_name = user.first_name or None
        last_name = user.last_name or None
        bio = None
        job_title = None
        company = None
        phone_number = None
        location = None
        skill_level = None
        career_stage = None
        industry = None
    
    # Calculate computed fields
    display_name = f"{first_name} {last_name}".strip() if first_name and last_name else user.username or user.email
    account_age_days = (timezone.now().date() - user.date_joined.date()).days
    is_newly_registered = account_age_days <= 30
    
    return AdminUserDetailType(
        id=user.id,
        email=user.email,
        username=user.username,
        role=user.role,
        account_status=user.account_status,
        is_premium=user.is_premium,
        is_active=user.is_active,
        is_suspended=user.is_suspended,
        is_blocked=user.is_blocked,
        is_email_verified=user.is_email_verified,
        date_joined=user.date_joined.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
        first_name=first_name,
        last_name=last_name,
        bio=bio,
        job_title=job_title,
        company=company,
        phone_number=phone_number,
        location=location,
        skill_level=skill_level,
        career_stage=career_stage,
        industry=industry,
        display_name=display_name,
        account_age_days=account_age_days,
        is_newly_registered=is_newly_registered,
    )

@strawberry.type
class AdminQuery:
    
    @strawberry.field
    async def user_stats(self, newly_registered_days: int = 30) -> UserStatsType:
        """Get comprehensive user statistics for admin dashboard"""
        now = timezone.now()
        cutoff_date = now - timedelta(days=newly_registered_days)
        
        # Calculate various user statistics using sync_to_async
        total_users = await sync_to_async(User.objects.count)()
        active_users = await sync_to_async(
            User.objects.filter(
                is_active=True, 
                is_suspended=False, 
                is_blocked=False
            ).count
        )()
        instructor_users = await sync_to_async(
            User.objects.filter(role="instructor").count
        )()
        newly_registered_users = await sync_to_async(
            User.objects.filter(date_joined__gte=cutoff_date).count
        )()
        suspended_users = await sync_to_async(
            User.objects.filter(is_suspended=True).count
        )()
        blocked_users = await sync_to_async(
            User.objects.filter(is_blocked=True).count
        )()
        email_verified_users = await sync_to_async(
            User.objects.filter(is_email_verified=True).count
        )()
        premium_users = await sync_to_async(
            User.objects.filter(is_premium=True).count
        )()
        
        return UserStatsType(
            total_users=total_users,
            active_users=active_users,
            instructor_users=instructor_users,
            newly_registered_users=newly_registered_users,
            suspended_users=suspended_users,
            blocked_users=blocked_users,
            email_verified_users=email_verified_users,
            premium_users=premium_users,
            last_updated=now.isoformat()
        )
    
    @strawberry.field
    async def paginated_users(
        self,
        filters: Optional[UserFilterInput] = None,
        pagination: Optional[PaginationInput] = None
    ) -> PaginatedUsersType:
        """Get paginated list of users with filtering and sorting"""
        
        # Build queryset with filters
        def build_queryset():
            queryset = User.objects.all()
            
            # Apply filters if provided
            if filters:
                if filters.search:
                    # Search in username, email, and profile names
                    search_q = Q(username__icontains=filters.search) | Q(email__icontains=filters.search)
                    # Also search in profile if available
                    try:
                        search_q |= Q(profile__first_name__icontains=filters.search) | Q(profile__last_name__icontains=filters.search)
                    except:
                        pass
                    queryset = queryset.filter(search_q)
                
                if filters.role:
                    queryset = queryset.filter(role=filters.role)
                
                if filters.account_status:
                    queryset = queryset.filter(account_status=filters.account_status)
                
                if filters.is_active is not None:
                    queryset = queryset.filter(is_active=filters.is_active)
                
                if filters.is_premium is not None:
                    queryset = queryset.filter(is_premium=filters.is_premium)
                
                if filters.is_email_verified is not None:
                    queryset = queryset.filter(is_email_verified=filters.is_email_verified)
                
                if filters.date_joined_after:
                    queryset = queryset.filter(date_joined__gte=filters.date_joined_after)
                
                if filters.date_joined_before:
                    queryset = queryset.filter(date_joined__lte=filters.date_joined_before)
            
            return queryset
        
        queryset = await sync_to_async(build_queryset)()
        
        # Apply pagination and sorting
        if pagination is None:
            pagination = PaginationInput()
        
        # Sorting
        sort_field = pagination.sort_by or "date_joined"
        if pagination.sort_order == "asc":
            queryset = queryset.order_by(sort_field)
        else:
            queryset = queryset.order_by(f"-{sort_field}")
        
        # Pagination calculation
        total_count = await sync_to_async(queryset.count)()
        page_size = max(1, min(pagination.page_size, 100))  # Limit page size to 100
        total_pages = (total_count + page_size - 1) // page_size
        current_page = max(1, pagination.page)
        offset = (current_page - 1) * page_size
        
        # Get users for current page
        users_list = await sync_to_async(list)(
            queryset.select_related('profile')[offset:offset + page_size]
        )
        
        # Convert to AdminUserDetailType
        admin_users = [convert_user_to_admin_detail(user) for user in users_list]
        
        return PaginatedUsersType(
            users=admin_users,
            total_count=total_count,
            total_pages=total_pages,
            current_page=current_page,
            page_size=page_size,
            has_next=current_page < total_pages,
            has_previous=current_page > 1
        )
    
    @strawberry.field
    async def user_by_id(self, user_id: str) -> Optional[AdminUserDetailType]:
        """Get a specific user by ID"""
        try:
            user = await sync_to_async(
                User.objects.select_related('profile').get
            )(id=user_id)
            return convert_user_to_admin_detail(user)
        except User.DoesNotExist:
            return None
    
    @strawberry.field
    def user_growth_metrics(self, period_days: int = 30) -> UserGrowthMetricsType:
        """Get user growth analytics for the specified period"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=period_days)
        
        # Daily registrations with cumulative count
        daily_registrations = []
        cumulative_count = User.objects.filter(date_joined__date__lt=start_date).count()
        
        current_date = start_date
        while current_date <= end_date:
            daily_count = User.objects.filter(date_joined__date=current_date).count()
            cumulative_count += daily_count
            daily_registrations.append(
                DailyRegistrationStatsType(
                    date=current_date.isoformat(),
                    count=daily_count,
                    cumulative_count=cumulative_count
                )
            )
            current_date += timedelta(days=1)
        
        # Role distribution
        total_users = User.objects.count()
        role_stats = User.objects.values('role').annotate(count=Count('role'))
        role_distribution = []
        for stat in role_stats:
            percentage = (stat['count'] / total_users * 100) if total_users > 0 else 0
            role_distribution.append(
                RoleStatsType(
                    role=stat['role'] or 'unknown',
                    count=stat['count'],
                    percentage=round(percentage, 2)
                )
            )
        
        # Status distribution
        status_distribution = []
        status_stats = User.objects.values('account_status').annotate(count=Count('account_status'))
        for stat in status_stats:
            percentage = (stat['count'] / total_users * 100) if total_users > 0 else 0
            status_distribution.append(
                StatusStatsType(
                    status=stat['account_status'] or 'unknown',
                    count=stat['count'],
                    percentage=round(percentage, 2)
                )
            )
        
        # Monthly growth (last 12 months)
        monthly_growth = []
        for i in range(12):
            month_start = (end_date.replace(day=1) - timedelta(days=i*30)).replace(day=1)
            month_end = (month_start + timedelta(days=31)).replace(day=1) - timedelta(days=1)
            
            total_users_month = User.objects.filter(date_joined__date__lte=month_end).count()
            new_registrations = User.objects.filter(
                date_joined__date__gte=month_start,
                date_joined__date__lte=month_end
            ).count()
            
            # Calculate growth rate
            prev_month_end = month_start - timedelta(days=1)
            prev_total = User.objects.filter(date_joined__date__lte=prev_month_end).count()
            growth_rate = ((total_users_month - prev_total) / prev_total * 100) if prev_total > 0 else 0
            
            monthly_growth.insert(0, MonthlyGrowthStatsType(
                month=month_start.strftime("%Y-%m"),
                total_users=total_users_month,
                new_registrations=new_registrations,
                growth_rate=round(growth_rate, 2)
            ))
        
        return UserGrowthMetricsType(
            period_days=period_days,
            daily_registrations=daily_registrations,
            role_distribution=role_distribution,
            status_distribution=status_distribution,
            monthly_growth=monthly_growth,
            generated_at=timezone.now().isoformat()
        )
