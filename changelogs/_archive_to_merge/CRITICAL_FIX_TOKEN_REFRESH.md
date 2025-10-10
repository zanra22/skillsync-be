# 🎯 CRITICAL FIX: Token Refresh Overwrites Remember Me Cookies

## Problem Identified

From your logs, I found the **root cause** of why Remember Me cookies revert to session cookies:

### The Issue
1. **OTP Verification** sets 30-day cookies correctly ✅
   ```
   🔐 Setting PERSISTENT cookies (Remember Me): 30 days
   ✅ Tokens generated for arnazdj69@gmail.com after OTP verification (remember_me=True)
   ```

2. **BUT** immediately after, `checkExistingSession()` calls `refreshToken()` ❌
   ```
   🔧 Development mode: Skipping fingerprint validation for token refresh
   🔐 Setting SESSION cookies (browser close = logout)  ← OVERWRITES 30-day cookies!
   ```

3. Result: Persistent cookies get **overwritten** with session cookies

---

## Root Cause

**File**: `skillsync-be/auth/mutation.py`  
**Mutation**: `refresh_token`  
**Line**: ~221

The `refresh_token` mutation was calling `set_secure_jwt_cookies()` **without** the `remember_me` parameter, so it defaulted to `False` (session cookies).

**Old Code:**
```python
SecureTokenManager.set_secure_jwt_cookies(
    response, str(new_access_token), str(new_refresh), info.context.request
    # ❌ Missing remember_me parameter - defaults to False!
)
```

---

## Solution Applied

### Fix 1: Preserve Remember Me Setting During Token Refresh

Updated `refresh_token` mutation to **detect** if the original token was persistent or session-based:

**Logic:**
- Check the refresh token's expiry time
- If expiry > 7 days remaining → It's a persistent token (Remember Me ON)
- If expiry < 7 days remaining → It's a session token (Remember Me OFF)
- Preserve the same setting when issuing new tokens

**New Code:**
```python
# Determine remember_me by checking the existing refresh token's lifetime
token_exp = refresh.get('exp', 0)
current_time = refresh.current_time
time_remaining = token_exp - current_time

# If token has more than 7 days remaining, it's a persistent login
if time_remaining > (7 * 24 * 60 * 60):  # More than 7 days
    remember_me = True
    print(f"🔄 Token refresh: Preserving PERSISTENT cookie setting (remember_me=True)")
else:
    remember_me = False
    print(f"🔄 Token refresh: Preserving SESSION cookie setting (remember_me=False)")

SecureTokenManager.set_secure_jwt_cookies(
    response, str(new_access_token), str(new_refresh), info.context.request,
    remember_me=remember_me  # ✅ Preserve the Remember Me setting
)
```

**Files Modified:**
- `skillsync-be/auth/mutation.py` (lines 215-245)

---

### Fix 2: Enhanced Logout Logging

Added detailed logging to track cookie clearing:

**Backend Logging:**
```python
print(f"🔓 Clearing cookies for user: {user.email}")
SecureTokenManager.clear_secure_cookies(response)
print(f"✅ Cookies cleared successfully")
```

**Cookie Clearing Logging:**
```python
print(f"🧹 Clearing {len(cookies_to_clear)} cookies...")
for cookie_name in cookies_to_clear:
    print(f"  🗑️ Deleting cookie: {cookie_name} (domain={domain})")
    response.delete_cookie(...)
```

**Files Modified:**
- `skillsync-be/auth/mutation.py` (lines 268-271)
- `skillsync-be/auth/secure_utils.py` (lines 111-115)

---

## Testing Instructions

### Step 1: Restart Backend
```powershell
cd e:\Projects\skillsync-latest\skillsync-be

# Stop current server (Ctrl+C)

# Start Django server
python manage.py runserver
```

**Important:** Keep backend terminal visible to see logs!

---

### Step 2: Clear Browser & Test Remember Me ON

1. **Clear everything:**
   - DevTools → Application → Clear site data
   - Close all windows → Reopen

2. **Login with Remember Me ON:**
   - Go to `http://localhost:3000/signin`
   - Email: `arnazdj69@gmail.com`
   - Password: your password
   - **CHECK** Remember Me ✅
   - Click "Sign In"

3. **Verify OTP**

4. **Check Backend Logs - Should see:**
   ```
   🔐 Setting PERSISTENT cookies (Remember Me): 30 days
   ✅ Tokens generated for arnazdj69@gmail.com after OTP verification (remember_me=True)
   
   🔧 Development mode: Skipping fingerprint validation for token refresh
   🔄 Token refresh: Preserving PERSISTENT cookie setting (remember_me=True)  ← ✅ NEW!
   🔐 Setting PERSISTENT cookies (Remember Me): 30 days  ← ✅ Should be persistent!
   ```

5. **Check Cookies:**
   - DevTools → Application → Cookies
   - `refresh_token` → Expires should show **~30 days from now**
   - Should NOT say "Session"

---

### Step 3: Test Browser Close (Remember Me ON)

1. **Close ALL browser windows** (completely exit browser)
2. **Reopen browser**
3. Go to `http://localhost:3000/dashboard`

**Expected:**
- ✅ Should still be logged in
- ✅ Dashboard loads immediately
- ✅ Console shows "Session restored from HTTP-only cookie"

---

### Step 4: Test Logout

1. Click "Logout" button

**Expected Backend Logs:**
```
🔓 Clearing cookies for user: arnazdj69@gmail.com
🧹 Clearing 6 cookies...
  🗑️ Deleting cookie: refresh_token (domain=localhost)
  🗑️ Deleting cookie: client_fp (domain=localhost)
  🗑️ Deleting cookie: fp_hash (domain=localhost)
  🗑️ Deleting cookie: access_token (domain=localhost)
  🗑️ Deleting cookie: auth-token (domain=localhost)
  🗑️ Deleting cookie: user-role (domain=localhost)
✅ Cookies cleared successfully
```

**Expected Frontend:**
- Redirects to `/signin` immediately
- Can access signin page (no redirect loop)

**Expected Cookies:**
- DevTools → Cookies should show **NO auth cookies**
- `refresh_token`, `client_fp`, `fp_hash` should all be gone

---

### Step 5: Test Remember Me OFF

1. **Clear browser data again**
2. **Login WITHOUT Remember Me:**
   - Uncheck Remember Me ❌
   - Complete login + OTP

**Expected Backend Logs:**
```
🔐 Setting SESSION cookies (browser close = logout)
✅ Tokens generated for arnazdj69@gmail.com after OTP verification (remember_me=False)

🔄 Token refresh: Preserving SESSION cookie setting (remember_me=False)  ← ✅ NEW!
🔐 Setting SESSION cookies (browser close = logout)  ← ✅ Should be session!
```

**Expected Cookies:**
- `refresh_token` → Expires: **Session**

**Test Browser Close:**
- Close all windows → Reopen
- Should be logged out ✅

---

## Expected Results Summary

| Test | Before Fix | After Fix |
|------|-----------|-----------|
| Remember Me ON → OTP | 30 days | 30 days ✅ |
| Remember Me ON → Token Refresh | Session ❌ | 30 days ✅ |
| Remember Me ON → Browser Close | Logged out ❌ | Logged in ✅ |
| Remember Me OFF → OTP | Session ✅ | Session ✅ |
| Remember Me OFF → Token Refresh | Session ✅ | Session ✅ |
| Remember Me OFF → Browser Close | Logged out ✅ | Logged out ✅ |
| Logout → Cookies Cleared | Some remain ❌ | All cleared ✅ |
| Logout → Access Signin | Redirect loop ❌ | Can access ✅ |

---

## Key Backend Log Changes

### Before Fix:
```
🔐 Setting PERSISTENT cookies (Remember Me): 30 days  ← OTP verification
✅ Tokens generated (remember_me=True)

🔧 Development mode: Skipping fingerprint validation
🔐 Setting SESSION cookies (browser close = logout)  ← ❌ Token refresh overwrites!
```

### After Fix:
```
🔐 Setting PERSISTENT cookies (Remember Me): 30 days  ← OTP verification
✅ Tokens generated (remember_me=True)

🔧 Development mode: Skipping fingerprint validation
🔄 Token refresh: Preserving PERSISTENT cookie setting (remember_me=True)  ← ✅ NEW!
🔐 Setting PERSISTENT cookies (Remember Me): 30 days  ← ✅ Preserves setting!
```

---

## What This Fix Does

1. **Token Rotation Preserves Remember Me:**
   - When access token expires and needs refresh
   - New tokens maintain the same cookie duration as original
   - Persistent stays persistent, session stays session

2. **No More Overwriting:**
   - Token refresh no longer defaults to session cookies
   - Checks original token's expiry to determine setting
   - Applies same setting to new tokens

3. **Better Logging:**
   - Shows exactly when cookies are persistent vs session
   - Shows cookie deletion process
   - Makes debugging much easier

---

## Files Changed

### Backend
1. **`skillsync-be/auth/mutation.py`**
   - Lines 215-245: Token refresh now preserves remember_me
   - Lines 268-271: Enhanced logout logging

2. **`skillsync-be/auth/secure_utils.py`**
   - Lines 111-130: Cookie clearing with detailed logging

---

## Next Steps

1. **Restart backend server** (see Step 1 above)
2. **Test Remember Me ON** (see Step 2-3 above)
3. **Test Logout** (see Step 4 above)
4. **Test Remember Me OFF** (see Step 5 above)
5. **Report results** with backend logs

This should **finally** fix the Remember Me issue! The token refresh was the culprit all along. 🎯

---

*Fix Applied: October 8, 2025*  
*Issue: Token refresh overwrites persistent cookies with session cookies*  
*Solution: Detect and preserve original remember_me setting during token rotation*
