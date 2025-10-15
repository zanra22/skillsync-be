# Token Blacklist Setup - October 15, 2025

## 🔐 Issue: Token Blacklist Not Enabled

**Warning Message**: 
```
⚠️ Token blacklist app not installed - token rotation without blacklist
```

---

## 🔍 What is Token Blacklisting?

### Purpose
When a refresh token is rotated (replaced with a new one), the **old token should be invalidated** (blacklisted) to prevent replay attacks.

**Without Blacklisting**:
- ❌ Old refresh tokens remain valid even after rotation
- ❌ If an attacker steals an old token, they can still use it
- ❌ Token rotation provides no security benefit

**With Blacklisting**:
- ✅ Old refresh tokens are immediately invalidated
- ✅ Stolen old tokens become useless
- ✅ Token rotation provides real security

---

## 🔧 Fix Applied

### 1. **Added Token Blacklist App to INSTALLED_APPS**

**File**: `skillsync-be/core/settings/base.py`

**OLD**:
```python
INSTALLED_APPS = [
    # ...
    "ninja_jwt",
    "strawberry.django",
    # ...
]
```

**NEW**:
```python
INSTALLED_APPS = [
    # ...
    "ninja_jwt",
    "ninja_jwt.token_blacklist",  # ✅ Token blacklist for security (rotation)
    "strawberry.django",
    # ...
]
```

---

## 🚀 Required Steps to Complete Setup

### Step 1: Run Migrations
The token blacklist app needs database tables to store blacklisted tokens.

```powershell
# Navigate to backend
cd skillsync-be

# Run migrations to create blacklist tables
python manage.py migrate
```

**Expected Output**:
```
Operations to perform:
  Apply all migrations: ...
Running migrations:
  Applying ninja_jwt.token_blacklist.0001_initial... OK
  Applying ninja_jwt.token_blacklist.0002_auto... OK
```

---

## 📊 What Tables Are Created

### Database Tables

1. **`ninja_jwt_token_blacklist_outstandingtoken`**
   - Stores all issued refresh tokens
   - Tracks token JTI (JWT ID), user, expiry, etc.

2. **`ninja_jwt_token_blacklist_blacklistedtoken`**
   - Stores blacklisted (invalidated) tokens
   - Links to OutstandingToken table
   - Prevents reuse of old tokens

---

## 🔍 How It Works

### Token Rotation Flow (With Blacklisting)

```python
# User requests token refresh
1. Backend receives refresh token from HTTP-only cookie
2. Backend validates token
3. Backend generates NEW refresh + access tokens
4. Backend blacklists OLD refresh token ✅
5. Backend sets NEW tokens in cookies
6. Backend returns NEW access token

# If attacker tries to use OLD token
7. Backend checks blacklist
8. Token is blacklisted ✅
9. Request denied with 401 Unauthorized
```

### Code (auth/mutation.py - Lines 361-386)

```python
# Blacklist old refresh token
try:
    if hasattr(refresh, 'blacklist'):
        blacklist_func = sync_to_async(lambda: refresh.blacklist())
        await blacklist_func()
        print(f"✅ Old refresh token blacklisted")
    else:
        # Manual blacklist using token_blacklist app
        if 'ninja_jwt.token_blacklist' in settings.INSTALLED_APPS:
            from ninja_jwt.token_blacklist.models import OutstandingToken, BlacklistedToken
            jti = refresh.get(api_settings.JTI_CLAIM)
            if jti:
                token_obj = await sync_to_async(OutstandingToken.objects.get)(jti=jti)
                await sync_to_async(BlacklistedToken.objects.get_or_create)(token=token_obj)
                print(f"✅ Old refresh token blacklisted (manual)")
except Exception as e:
    print(f"⚠️ Token blacklist failed: {str(e)}")
```

---

## 🧪 Testing

### Test 1: Verify Blacklist Tables Created
```powershell
# After running migrations
python manage.py dbshell

# In PostgreSQL shell
\dt ninja_jwt_token_blacklist*

# Expected output:
#  ninja_jwt_token_blacklist_outstandingtoken
#  ninja_jwt_token_blacklist_blacklistedtoken
```

### Test 2: Verify Token Rotation Blacklists Old Token
```
1. Login (get refresh token)
2. Wait 1 minute
3. Call refresh mutation (get new tokens)
4. Check logs for: "✅ Old refresh token blacklisted"
5. Try using old refresh token → Should fail with 401
```

### Test 3: Check Console Output
After running migrations and restarting server:
- ❌ Should NOT see: "⚠️ Token blacklist app not installed"
- ✅ Should see: "✅ Old refresh token blacklisted"

---

## 🔐 Security Benefits

### Before Fix (No Blacklisting)
```
Time    Event                           Security Risk
----------------------------------------------------------
T0      User gets refresh token         ✅ Secure
T1      Token rotated, new token issued ⚠️ Old token still valid!
T2      Attacker steals old token       ❌ VULNERABLE
T3      Attacker uses old token         ❌ SUCCESS (token works!)
```

### After Fix (With Blacklisting)
```
Time    Event                           Security Status
----------------------------------------------------------
T0      User gets refresh token         ✅ Secure
T1      Token rotated, new token issued ✅ Old token blacklisted
T2      Attacker steals old token       ⚠️ Token stolen
T3      Attacker uses old token         ✅ BLOCKED (token blacklisted!)
```

---

## 📝 Configuration Verification

### Check NINJA_JWT Settings

File: `config/security.py` or `core/settings/base.py`

Should have:
```python
NINJA_JWT = {
    'ROTATE_REFRESH_TOKENS': True,          # ✅ Must be True
    'BLACKLIST_AFTER_ROTATION': True,       # ✅ Must be True
    'UPDATE_LAST_LOGIN': True,
    # ... other settings
}
```

These settings tell ninja-jwt to:
1. Generate a new refresh token on each refresh (rotation)
2. Blacklist the old refresh token automatically

---

## ⚠️ Important Notes

### 1. Database Cleanup
Over time, the blacklist tables will grow. You should periodically clean up expired tokens:

```python
# Cleanup script (run weekly)
from django.core.management import call_command
from ninja_jwt.token_blacklist.management.commands import flushexpiredtokens

call_command('flushexpiredtokens')
```

### 2. Token Lifetime
- **Access tokens**: 5 minutes (short-lived, not blacklisted)
- **Refresh tokens**: 7-30 days (long-lived, must be blacklisted)

Only refresh tokens need blacklisting because:
- Access tokens expire quickly (5 min)
- Refresh tokens live longer (up to 30 days)
- Refresh tokens can generate new access tokens

### 3. Performance
- Blacklist check adds ~1ms per token refresh
- Negligible impact on performance
- Critical for security

---

## ✅ Completion Checklist

- [x] Added `ninja_jwt.token_blacklist` to INSTALLED_APPS
- [ ] Run `python manage.py migrate` (PENDING - USER MUST DO)
- [ ] Verify blacklist tables created (PENDING)
- [ ] Test token rotation (PENDING)
- [ ] Verify old tokens are blacklisted (PENDING)
- [ ] Confirm warning message disappears (PENDING)

---

## 🚀 Next Steps for User

**YOU NEED TO RUN THIS COMMAND**:
```powershell
# In skillsync-be directory
python manage.py migrate
```

This will create the necessary database tables for token blacklisting.

After migration, restart your Django server and the warning should disappear!

---

**Date**: October 15, 2025  
**Issue Type**: Security configuration  
**Severity**: MEDIUM (security enhancement)  
**Resolution**: Added token blacklist app to INSTALLED_APPS  
**Action Required**: Run migrations to create blacklist tables  

---

*Token blacklisting is a critical security feature that prevents replay attacks with stolen refresh tokens.*
