# Session Management & Activity Monitoring Implementation Plan

## Overview
This document outlines the implementation of Session Management Dashboard and Activity Monitoring features for SkillSync.

---

## 🎯 **Features to Implement**

### **1. User-Facing Session Management Dashboard**
**What Users Can Do:**
- ✅ View all active sessions (devices where they're logged in)
- ✅ See device details (type, browser, OS)
- ✅ See location (city, country based on IP)
- ✅ See last activity time
- ✅ See if device is trusted
- ✅ Identify current session
- ✅ Revoke any session (remote logout)
- ✅ Revoke all sessions except current

**User Interface:**
```
Account Settings → Security → Active Sessions

📱 iPhone 13 Pro - Safari
   📍 New York, United States
   🕐 Active now (Current Session)
   🔐 Trusted Device
   [Revoke Access]

💻 Windows PC - Chrome  
   📍 Los Angeles, United States
   🕐 Last active: 2 hours ago
   🔐 Trusted Device
   [Revoke Access]
```

### **2. Admin Activity Monitoring Dashboard**
**What Admins Can See:**
- ✅ Recent security events system-wide
- ✅ Failed login attempts
- ✅ Suspicious login patterns
- ✅ Super admin activity log
- ✅ User session statistics
- ✅ Geographic login distribution
- ✅ Device type analytics

**Admin Interface:**
```
Admin Dashboard → Security Monitoring

RECENT SECURITY EVENTS:
⚠️ Suspicious Login - john@example.com from Russia
✅ Super Admin Login - admin@skillsync.com (OTP verified)
🔒 Failed Login Attempts - jane@example.com (3 attempts)
📱 New Device Trust - mike@example.com
```

---

## 🗄️ **Database Models**

### **Model 1: UserSession**

**Purpose:** Track active sessions with JWT refresh tokens

```python
# auth/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from helpers.generate_short_id import generate_short_id

User = get_user_model()

class UserSession(models.Model):
    """
    Track active user sessions linked to JWT refresh tokens.
    Each refresh token = one active session on one device.
    """
    
    id = models.CharField(
        max_length=10,
        primary_key=True,
        default=generate_short_id,
        editable=False
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    
    # Session identification
    refresh_token_jti = models.CharField(
        max_length=255,
        unique=True,
        help_text="JWT ID (jti) of the refresh token"
    )
    
    # Device information
    device_fingerprint = models.CharField(
        max_length=64,
        help_text="Device fingerprint hash"
    )
    device_name = models.CharField(
        max_length=255,
        help_text="Human-readable device name (e.g., Chrome on Windows)"
    )
    device_type = models.CharField(
        max_length=20,
        choices=[
            ('desktop', 'Desktop'),
            ('mobile', 'Mobile'),
            ('tablet', 'Tablet'),
            ('unknown', 'Unknown'),
        ],
        default='unknown'
    )
    browser = models.CharField(max_length=100, blank=True)
    os = models.CharField(max_length=100, blank=True)
    
    # Location information
    ip_address = models.GenericIPAddressField()
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True
    )
    
    # Session tracking
    is_current = models.BooleanField(
        default=False,
        help_text="True if this is the current session"
    )
    is_trusted_device = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'user_sessions'
        ordering = ['-last_activity']
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'
        indexes = [
            models.Index(fields=['user', 'revoked_at', 'expires_at']),
            models.Index(fields=['refresh_token_jti']),
            models.Index(fields=['user', 'is_current']),
        ]
    
    def __str__(self):
        return f"{self.device_name} - {self.user.email}"
    
    def is_active(self):
        """Check if session is still active (not revoked and not expired)"""
        return (
            self.revoked_at is None and 
            timezone.now() < self.expires_at
        )
    
    def revoke(self):
        """Revoke this session"""
        self.revoked_at = timezone.now()
        self.save()
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])
    
    @staticmethod
    def create_session(user, refresh_token_jti, device_info, ip_address, expires_at):
        """
        Create a new session record.
        
        Args:
            user: User instance
            refresh_token_jti: JWT ID from refresh token
            device_info: Dict with device information
            ip_address: Client IP address
            expires_at: Session expiry datetime
        """
        from otps.models import TrustedDevice
        
        device_fingerprint = TrustedDevice.generate_device_fingerprint(
            ip_address, 
            device_info.get('user_agent', '')
        )
        
        # Check if device is trusted
        is_trusted = TrustedDevice.is_device_trusted(user, device_fingerprint)
        
        # Parse device info
        device_name = device_info.get('device_name') or TrustedDevice._parse_device_name(
            device_info.get('user_agent', '')
        )
        
        # Geo-locate IP (placeholder - implement with API)
        location = UserSession._geolocate_ip(ip_address)
        
        session = UserSession.objects.create(
            user=user,
            refresh_token_jti=refresh_token_jti,
            device_fingerprint=device_fingerprint,
            device_name=device_name,
            device_type=device_info.get('device_type', 'unknown'),
            browser=device_info.get('browser', ''),
            os=device_info.get('os', ''),
            ip_address=ip_address,
            country=location.get('country', ''),
            city=location.get('city', ''),
            latitude=location.get('latitude'),
            longitude=location.get('longitude'),
            is_trusted_device=is_trusted,
            expires_at=expires_at,
        )
        
        return session
    
    @staticmethod
    def _geolocate_ip(ip_address):
        """
        Get location from IP address.
        
        TODO: Implement using services like:
        - ipapi.co (free tier: 30k requests/month)
        - ipgeolocation.io
        - MaxMind GeoIP2
        
        For now, returns placeholder.
        """
        # Placeholder implementation
        return {
            'country': 'Unknown',
            'city': 'Unknown',
            'latitude': None,
            'longitude': None
        }
    
    @staticmethod
    def get_user_active_sessions(user):
        """Get all active sessions for a user"""
        return UserSession.objects.filter(
            user=user,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now()
        ).order_by('-last_activity')
    
    @staticmethod
    def revoke_all_sessions_except(user, current_session_id):
        """Revoke all sessions except the current one"""
        UserSession.objects.filter(
            user=user,
            revoked_at__isnull=True
        ).exclude(
            id=current_session_id
        ).update(
            revoked_at=timezone.now()
        )
    
    @staticmethod
    def cleanup_expired_sessions():
        """Delete expired and revoked sessions older than 30 days"""
        cutoff_date = timezone.now() - timedelta(days=30)
        
        expired_sessions = UserSession.objects.filter(
            models.Q(expires_at__lt=timezone.now()) |
            models.Q(revoked_at__lt=cutoff_date)
        )
        
        count = expired_sessions.count()
        expired_sessions.delete()
        return count
```

### **Model 2: LoginHistory**

**Purpose:** Audit log of all login attempts (success and failures)

```python
# auth/models.py

class LoginHistory(models.Model):
    """
    Audit log of all login attempts.
    Tracks both successful and failed login attempts for security monitoring.
    """
    
    id = models.CharField(
        max_length=10,
        primary_key=True,
        default=generate_short_id,
        editable=False
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='login_history',
        null=True,  # Can be null for failed attempts with invalid email
        blank=True
    )
    email = models.EmailField(
        help_text="Email used in login attempt"
    )
    
    # Login result
    success = models.BooleanField(
        help_text="True if login was successful"
    )
    failure_reason = models.CharField(
        max_length=255,
        blank=True,
        help_text="Reason for login failure"
    )
    
    # Device and location
    device_fingerprint = models.CharField(max_length=64, blank=True)
    device_name = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField()
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Security flags
    otp_required = models.BooleanField(default=False)
    otp_verified = models.BooleanField(default=False)
    is_suspicious = models.BooleanField(
        default=False,
        help_text="Flagged as suspicious by security checks"
    )
    suspicious_reason = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    session = models.ForeignKey(
        UserSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='login_records'
    )
    
    class Meta:
        db_table = 'login_history'
        ordering = ['-created_at']
        verbose_name = 'Login History'
        verbose_name_plural = 'Login Histories'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['email', 'success', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
            models.Index(fields=['is_suspicious', 'created_at']),
        ]
    
    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{self.email} - {status} - {self.created_at}"
    
    @staticmethod
    def log_login_attempt(email, success, device_info, ip_address, **kwargs):
        """
        Log a login attempt.
        
        Args:
            email: Email used in login
            success: Whether login was successful
            device_info: Device information dict
            ip_address: Client IP
            **kwargs: Additional fields (user, failure_reason, etc.)
        """
        from otps.models import TrustedDevice
        
        device_fingerprint = TrustedDevice.generate_device_fingerprint(
            ip_address,
            device_info.get('user_agent', '')
        )
        
        device_name = TrustedDevice._parse_device_name(
            device_info.get('user_agent', '')
        )
        
        location = UserSession._geolocate_ip(ip_address)
        
        # Check for suspicious activity
        is_suspicious, suspicious_reason = LoginHistory._check_suspicious(
            email, ip_address, success
        )
        
        return LoginHistory.objects.create(
            email=email,
            success=success,
            device_fingerprint=device_fingerprint,
            device_name=device_name,
            ip_address=ip_address,
            country=location.get('country', ''),
            city=location.get('city', ''),
            user_agent=device_info.get('user_agent', ''),
            is_suspicious=is_suspicious,
            suspicious_reason=suspicious_reason,
            **kwargs
        )
    
    @staticmethod
    def _check_suspicious(email, ip_address, success):
        """
        Check if login attempt is suspicious.
        
        Returns:
            tuple: (is_suspicious bool, reason string)
        """
        # Check for multiple failed attempts
        recent_failures = LoginHistory.objects.filter(
            email=email,
            success=False,
            created_at__gte=timezone.now() - timedelta(minutes=15)
        ).count()
        
        if recent_failures >= 3:
            return True, f"Multiple failed login attempts ({recent_failures})"
        
        # Check for login from unusual location
        if success:
            try:
                user = User.objects.get(email=email)
                recent_locations = LoginHistory.objects.filter(
                    user=user,
                    success=True,
                    created_at__gte=timezone.now() - timedelta(days=30)
                ).values_list('country', flat=True).distinct()
                
                location = UserSession._geolocate_ip(ip_address)
                current_country = location.get('country', '')
                
                if current_country and current_country not in recent_locations:
                    return True, f"Login from unusual location: {current_country}"
            except User.DoesNotExist:
                pass
        
        return False, ""
    
    @staticmethod
    def get_recent_failures(email, minutes=15):
        """Get count of recent failed login attempts"""
        return LoginHistory.objects.filter(
            email=email,
            success=False,
            created_at__gte=timezone.now() - timedelta(minutes=minutes)
        ).count()
    
    @staticmethod
    def cleanup_old_records(days=90):
        """Delete login history older than specified days"""
        cutoff_date = timezone.now() - timedelta(days=days)
        old_records = LoginHistory.objects.filter(created_at__lt=cutoff_date)
        count = old_records.count()
        old_records.delete()
        return count
```

### **Model 3: SecurityEvent**

**Purpose:** Track security-related events for admin monitoring

```python
# auth/models.py

class SecurityEvent(models.Model):
    """
    Track security events for monitoring and audit trails.
    Used by admins to monitor system security.
    """
    
    EVENT_TYPES = [
        ('login_success', 'Successful Login'),
        ('login_failure', 'Failed Login'),
        ('otp_sent', 'OTP Sent'),
        ('otp_verified', 'OTP Verified'),
        ('otp_failed', 'OTP Verification Failed'),
        ('session_revoked', 'Session Revoked'),
        ('device_trusted', 'Device Trusted'),
        ('device_revoked', 'Device Trust Revoked'),
        ('password_changed', 'Password Changed'),
        ('account_locked', 'Account Locked'),
        ('account_unlocked', 'Account Unlocked'),
        ('suspicious_activity', 'Suspicious Activity Detected'),
        ('admin_action', 'Admin Action'),
    ]
    
    SEVERITY_LEVELS = [
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]
    
    id = models.CharField(
        max_length=10,
        primary_key=True,
        default=generate_short_id,
        editable=False
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='security_events',
        null=True,
        blank=True
    )
    event_type = models.CharField(
        max_length=50,
        choices=EVENT_TYPES
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_LEVELS,
        default='info'
    )
    
    # Event details
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device_name = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    
    # Additional context
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional event metadata"
    )
    
    # Admin review
    reviewed = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_security_events'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'security_events'
        ordering = ['-created_at']
        verbose_name = 'Security Event'
        verbose_name_plural = 'Security Events'
        indexes = [
            models.Index(fields=['user', 'event_type', 'created_at']),
            models.Index(fields=['severity', 'reviewed', 'created_at']),
            models.Index(fields=['event_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.user.email if self.user else 'System'}"
    
    @staticmethod
    def log_event(event_type, user=None, severity='info', description='', **kwargs):
        """
        Log a security event.
        
        Args:
            event_type: Type of event (from EVENT_TYPES choices)
            user: User instance (optional)
            severity: Severity level (from SEVERITY_LEVELS)
            description: Event description
            **kwargs: Additional fields (ip_address, metadata, etc.)
        """
        return SecurityEvent.objects.create(
            user=user,
            event_type=event_type,
            severity=severity,
            description=description,
            **kwargs
        )
    
    @staticmethod
    def get_unreviewed_critical_events():
        """Get unreviewed critical security events"""
        return SecurityEvent.objects.filter(
            severity='critical',
            reviewed=False
        ).order_by('-created_at')
    
    @staticmethod
    def get_recent_events(hours=24):
        """Get security events from last N hours"""
        cutoff = timezone.now() - timedelta(hours=hours)
        return SecurityEvent.objects.filter(
            created_at__gte=cutoff
        ).order_by('-created_at')
    
    def mark_reviewed(self, admin_user):
        """Mark event as reviewed by admin"""
        self.reviewed = True
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.save()
```

---

## 🔌 **GraphQL API Endpoints**

### **User Session Management APIs**

```python
# auth/query.py - Add these queries

@strawberry.type
class AuthQuery:
    
    @strawberry.field
    async def my_active_sessions(self, info) -> List[UserSessionType]:
        """Get current user's active sessions"""
        user = info.context.request.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        sessions = await sync_to_async(list)(
            UserSession.get_user_active_sessions(user)
        )
        return sessions
    
    @strawberry.field
    async def my_login_history(
        self, 
        info, 
        limit: int = 20
    ) -> List[LoginHistoryType]:
        """Get current user's login history"""
        user = info.context.request.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        history = await sync_to_async(list)(
            LoginHistory.objects.filter(user=user)[:limit]
        )
        return history
```

```python
# auth/mutation.py - Add these mutations

@strawberry.mutation
async def revoke_session(self, session_id: str) -> RevokeSessionPayload:
    """Revoke a specific session"""
    user = info.context.request.user
    if not user.is_authenticated:
        return RevokeSessionPayload(
            success=False,
            message="Authentication required"
        )
    
    try:
        session = await sync_to_async(UserSession.objects.get)(
            id=session_id,
            user=user
        )
        
        session.revoke()
        
        # Log security event
        SecurityEvent.log_event(
            event_type='session_revoked',
            user=user,
            severity='info',
            description=f"Session revoked: {session.device_name}",
            metadata={'session_id': session_id}
        )
        
        return RevokeSessionPayload(
            success=True,
            message="Session revoked successfully"
        )
    except UserSession.DoesNotExist:
        return RevokeSessionPayload(
            success=False,
            message="Session not found"
        )

@strawberry.mutation
async def revoke_all_sessions_except_current(self, info) -> RevokeSessionPayload:
    """Revoke all sessions except the current one"""
    user = info.context.request.user
    if not user.is_authenticated:
        return RevokeSessionPayload(
            success=False,
            message="Authentication required"
        )
    
    # Get current session ID from refresh token
    refresh_token = info.context.request.COOKIES.get('refresh_token')
    if not refresh_token:
        return RevokeSessionPayload(
            success=False,
            message="No active session found"
        )
    
    try:
        token = RefreshToken(refresh_token)
        current_jti = token['jti']
        
        current_session = await sync_to_async(UserSession.objects.get)(
            refresh_token_jti=current_jti,
            user=user
        )
        
        UserSession.revoke_all_sessions_except(user, current_session.id)
        
        # Log security event
        SecurityEvent.log_event(
            event_type='session_revoked',
            user=user,
            severity='info',
            description="All sessions revoked except current"
        )
        
        return RevokeSessionPayload(
            success=True,
            message="All other sessions revoked successfully"
        )
    except Exception as e:
        return RevokeSessionPayload(
            success=False,
            message=f"Failed to revoke sessions: {str(e)}"
        )
```

### **Admin Monitoring APIs**

```python
# admin/query.py - Add these admin-only queries

@strawberry.field
async def security_events(
    self,
    info,
    severity: Optional[str] = None,
    unreviewed_only: bool = False,
    limit: int = 50
) -> List[SecurityEventType]:
    """Get security events (admin only)"""
    user = info.context.request.user
    if not user.is_authenticated or user.role not in ['admin', 'super_admin']:
        raise Exception("Admin access required")
    
    queryset = SecurityEvent.objects.all()
    
    if severity:
        queryset = queryset.filter(severity=severity)
    
    if unreviewed_only:
        queryset = queryset.filter(reviewed=False)
    
    events = await sync_to_async(list)(queryset[:limit])
    return events

@strawberry.field
async def login_statistics(
    self,
    info,
    days: int = 7
) -> LoginStatisticsType:
    """Get login statistics (admin only)"""
    user = info.context.request.user
    if not user.is_authenticated or user.role not in ['admin', 'super_admin']:
        raise Exception("Admin access required")
    
    cutoff = timezone.now() - timedelta(days=days)
    
    total_logins = await sync_to_async(LoginHistory.objects.filter(
        created_at__gte=cutoff
    ).count)()
    
    successful_logins = await sync_to_async(LoginHistory.objects.filter(
        created_at__gte=cutoff,
        success=True
    ).count)()
    
    failed_logins = total_logins - successful_logins
    
    suspicious_attempts = await sync_to_async(LoginHistory.objects.filter(
        created_at__gte=cutoff,
        is_suspicious=True
    ).count)()
    
    return LoginStatisticsType(
        total_logins=total_logins,
        successful_logins=successful_logins,
        failed_logins=failed_logins,
        suspicious_attempts=suspicious_attempts,
        date_range_days=days
    )
```

---

## 📱 **Frontend Components**

### **User Session Management Page**

```tsx
// app/account/security/sessions/page.tsx

'use client';

import { useQuery, useMutation } from '@apollo/client';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Smartphone, Monitor, Tablet, MapPin, Clock, Shield, X } from 'lucide-react';

const MY_SESSIONS_QUERY = gql`
  query MyActiveSessions {
    auth {
      myActiveSessions {
        id
        deviceName
        deviceType
        browser
        os
        city
        country
        isCurrent
        isTrustedDevice
        lastActivity
        createdAt
      }
    }
  }
`;

const REVOKE_SESSION_MUTATION = gql`
  mutation RevokeSession($sessionId: String!) {
    auth {
      revokeSession(sessionId: $sessionId) {
        success
        message
      }
    }
  }
`;

export default function SessionsPage() {
  const { data, loading, refetch } = useQuery(MY_SESSIONS_QUERY);
  const [revokeSession] = useMutation(REVOKE_SESSION_MUTATION);

  const handleRevoke = async (sessionId: string) => {
    if (confirm('Are you sure you want to revoke this session?')) {
      await revokeSession({ variables: { sessionId } });
      refetch();
    }
  };

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Active Sessions</h1>
      
      <div className="space-y-4">
        {data?.auth?.myActiveSessions?.map((session) => (
          <Card key={session.id}>
            <CardContent className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-4">
                  {/* Device Icon */}
                  <div className="p-3 bg-accent/10 rounded-lg">
                    {session.deviceType === 'mobile' && <Smartphone className="h-6 w-6" />}
                    {session.deviceType === 'tablet' && <Tablet className="h-6 w-6" />}
                    {session.deviceType === 'desktop' && <Monitor className="h-6 w-6" />}
                  </div>
                  
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      <h3 className="font-semibold">{session.deviceName}</h3>
                      {session.isCurrent && (
                        <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                          Current Session
                        </span>
                      )}
                    </div>
                    
                    <div className="text-sm text-muted-foreground space-y-1">
                      <div className="flex items-center space-x-1">
                        <MapPin className="h-4 w-4" />
                        <span>{session.city}, {session.country}</span>
                      </div>
                      
                      <div className="flex items-center space-x-1">
                        <Clock className="h-4 w-4" />
                        <span>
                          {session.isCurrent 
                            ? 'Active now' 
                            : `Last active ${formatTimeAgo(session.lastActivity)}`
                          }
                        </span>
                      </div>
                      
                      {session.isTrustedDevice && (
                        <div className="flex items-center space-x-1 text-green-600">
                          <Shield className="h-4 w-4" />
                          <span>Trusted Device</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
                
                {!session.isCurrent && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRevoke(session.id)}
                  >
                    <X className="h-4 w-4 mr-1" />
                    Revoke
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
```

---

## 🚀 **Implementation Timeline**

### **Phase 3A: Database & Backend (2-3 days)**
1. ✅ Create models (UserSession, LoginHistory, SecurityEvent)
2. ✅ Run migrations
3. ✅ Update login mutation to create UserSession
4. ✅ Update logout mutation to revoke UserSession
5. ✅ Add session tracking to token refresh
6. ✅ Add GraphQL queries/mutations

### **Phase 3B: Frontend UI (2-3 days)**
1. ✅ Create Session Management page
2. ✅ Create Login History page
3. ✅ Add security alerts
4. ✅ Test session revocation

### **Phase 3C: Admin Dashboard (2-3 days)**
1. ✅ Create Security Monitoring dashboard
2. ✅ Add event filtering and search
3. ✅ Add statistics charts
4. ✅ Add real-time alerts

### **Phase 3D: IP Geolocation (1 day)**
1. ✅ Integrate IP geolocation API
2. ✅ Add location caching
3. ✅ Test location accuracy

---

## 🎯 **Benefits**

### **For Users:**
- 🔒 Better security control
- 👀 Visibility into account access
- 🚨 Quick response to suspicious activity
- 📱 Remote logout capability

### **For Admins:**
- 🔍 System-wide security monitoring
- ⚠️ Early threat detection
- 📊 Login analytics
- 🛡️ Compliance audit trails

### **For Business:**
- 🏆 Enterprise-grade security
- ✅ Compliance readiness
- 📈 User trust
- 🎖️ Competitive advantage

---

## 🔐 **Security Considerations**

1. **Session Hijacking Prevention:**
   - Tie sessions to device fingerprints
   - Validate on every refresh
   - Auto-revoke on suspicious activity

2. **Privacy:**
   - Only store necessary location data
   - GDPR-compliant data retention
   - User control over data

3. **Performance:**
   - Index all query fields
   - Implement caching for locations
   - Auto-cleanup old records

4. **Rate Limiting:**
   - Limit session queries
   - Prevent session enumeration
   - Throttle revocation attempts

---

## 📚 **Related Documentation**

- JWT Authentication Architecture
- Trusted Device Management
- OTP System Implementation
- Security Best Practices

