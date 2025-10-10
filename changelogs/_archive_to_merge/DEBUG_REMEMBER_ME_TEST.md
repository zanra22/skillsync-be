# 🐛 Debug Remember Me - Test Instructions

## Overview
We've added comprehensive logging to trace the Remember Me flag through the entire flow. This will help us identify where the value is getting lost.

---

## Changes Made

### 1. Frontend Logging (AuthContext.tsx)
Added detailed logging in `verifyOTP` function:
- `🔍 Raw pending-login data` - Shows the raw sessionStorage value
- `📝 Retrieved rememberMe from pending login` - Shows parsed rememberMe value and type
- `📦 Full login data` - Shows entire login object
- `🚀 Calling verifyOTP with rememberMe` - Shows value being passed to API

### 2. API Logging (otp.tsx)
Added GraphQL variables logging:
- `🔍 OTP API - verifyOTP variables` - Shows complete GraphQL mutation variables including rememberMe

### 3. Backend Logging (otps/mutation.py)
Added debug logging in verify_otp mutation:
- `🔍 DEBUG: input.remember_me` - Shows the value received from GraphQL
- `🔍 DEBUG: remember_me_value after check` - Shows the value after None check
- `✅ Tokens generated` - Shows final rememberMe value used for cookies

### 4. Logout Fix
Changed from `window.location.href` to `window.location.replace('/signin')`:
- Forces immediate navigation
- Clears browser history entry (prevents back button issues)
- Ensures middleware sees cleared cookies

---

## Test Procedure

### Step 1: Restart Servers

**Backend:**
```powershell
cd e:\Projects\skillsync-latest\skillsync-be
python manage.py runserver
```

**Frontend:**
```powershell
cd e:\Projects\skillsync-latest\skillsync-fe
bun dev
```

---

### Step 2: Clear Everything

1. Open Browser DevTools (F12)
2. Application tab → Storage → Clear site data
3. Close DevTools
4. Close ALL browser windows
5. Reopen browser

---

### Step 3: Test Remember Me ON

1. Go to `http://localhost:3000/signin`
2. Enter credentials:
   - Email: `arnazdj69@gmail.com`
   - Password: Your password
   - **CHECK** Remember Me ✅

3. Click "Sign In"

### Expected Console Output (Frontend):

```javascript
🔐 Starting login process... { email: "arnazdj69@gmail.com", rememberMe: true }
🔑 Validating credentials...
✅ Credentials valid, checking if OTP required...
📱 OTP required, sending OTP...
💾 Storing pending login credentials...
💾 Stored pending login data
```

4. **Check sessionStorage NOW**:
   - DevTools → Application → Session Storage → http://localhost:3000
   - Find `pending-login`
   - Should show: `{"email":"arnazdj69@gmail.com","password":"***","rememberMe":true}`
   - ✅ **Verify `rememberMe: true` is stored**

5. Enter OTP code
6. Click "Verify"

### Expected Console Output (Frontend - OTP Verification):

```javascript
🔐 Starting OTP verification... { email: "arnazdj69@gmail.com", purpose: "signin" }
🔍 Raw pending-login data: {"email":"arnazdj69@gmail.com","password":"***","rememberMe":true}
📝 Retrieved rememberMe from pending login: true Type: boolean
📦 Full login data: { email: "...", password: "...", rememberMe: true }
🚀 Calling verifyOTP with rememberMe: true
🔍 OTP API - verifyOTP variables: {
  "input": {
    "code": "123456",
    "email": "arnazdj69@gmail.com",
    "purpose": "signin",
    "trustDevice": false,
    "rememberMe": true  ← ✅ Should be true
  },
  "deviceInfo": { ... }
}
✅ OTP API response: { success: true, ... }
```

### Expected Backend Output:

```
🔍 DEBUG: input.remember_me = True, type = <class 'bool'>
🔍 DEBUG: remember_me_value after check = True, type = <class 'bool'>
✅ Tokens generated for arnazdj69@gmail.com after OTP verification (remember_me=True)
```

### Expected Cookies (After OTP):

Open DevTools → Application → Cookies → http://localhost:3000

```
✅ refresh_token:
   - HttpOnly: ✓
   - Expires: ~30 days from now (e.g., Nov 7, 2025 10:30:45 AM)
   
✅ client_fp:
   - HttpOnly: ✓
   - Expires: ~30 days from now
   
✅ fp_hash:
   - HttpOnly: ✓
   - Expires: ~30 days from now
```

---

### Step 4: Test Logout

1. Click "Logout" button

### Expected Console Output:

```javascript
🚪 Logging out...
✅ Backend logout successful
🧹 Auth state cleared
🔄 Forcing full page reload to signin...
```

### Expected Result:
- Should navigate to `/signin` immediately
- DevTools → Cookies should show NO auth cookies
- Should be able to access signin page (not redirected)

---

### Step 5: Test Remember Me OFF

1. Go to `http://localhost:3000/signin`
2. Enter credentials
3. **UNCHECK** Remember Me ❌
4. Click "Sign In"

### Expected sessionStorage:
```json
{"email":"arnazdj69@gmail.com","password":"***","rememberMe":false}
```

5. Enter OTP → Verify

### Expected Console Output:

```javascript
📝 Retrieved rememberMe from pending login: false Type: boolean
🚀 Calling verifyOTP with rememberMe: false
🔍 OTP API - verifyOTP variables: {
  "input": { ..., "rememberMe": false }  ← ✅ Should be false
}
```

### Expected Backend Output:

```
🔍 DEBUG: input.remember_me = False, type = <class 'bool'>
🔍 DEBUG: remember_me_value after check = False, type = <class 'bool'>
✅ Tokens generated for arnazdj69@gmail.com after OTP verification (remember_me=False)
```

### Expected Cookies (After OTP):

```
✅ refresh_token:
   - HttpOnly: ✓
   - Expires: Session  ← ✅ Should say "Session"
   
✅ client_fp:
   - HttpOnly: ✓
   - Expires: Session
   
✅ fp_hash:
   - HttpOnly: ✓
   - Expires: Session
```

---

## Troubleshooting Guide

### Issue 1: sessionStorage shows `rememberMe: undefined`

**Diagnosis:**
The login form isn't passing the checkbox value correctly.

**Check:**
1. DevTools → Application → Session Storage
2. Look at `pending-login` value
3. If `rememberMe` is missing or `undefined`, the form has an issue

**Solution:**
Check `signin/page.tsx` form submission - ensure checkbox value is being read.

---

### Issue 2: Frontend shows `rememberMe: true` but backend receives `False`

**Diagnosis:**
GraphQL variable not being passed or type mismatch.

**Check Frontend Console:**
```javascript
🔍 OTP API - verifyOTP variables: { "input": { "rememberMe": ??? } }
```

**Check Backend Console:**
```
🔍 DEBUG: input.remember_me = ???
```

**Solution:**
- If frontend shows `true` but backend shows `False`: GraphQL schema issue
- Check `otps/types.py` - ensure `remember_me: Optional[bool] = False` exists
- Check GraphQL query - ensure `rememberMe` field is included in mutation

---

### Issue 3: Cookies set BEFORE OTP verification

**Diagnosis:**
Initial login mutation is setting cookies when it shouldn't.

**Expected:**
- **Before OTP**: NO refresh_token cookie (or expired one)
- **After OTP**: Fresh refresh_token with correct expiry

**If cookies exist before OTP:**
This means the initial `login` mutation is setting cookies. This is actually by design for non-OTP flows, but they should be overwritten by OTP verification with the correct `remember_me` setting.

**Check:**
1. Before entering OTP: Check cookies → Should have session cookies from login
2. After entering OTP: Check cookies → Should be updated with correct expiry based on Remember Me

---

### Issue 4: After logout, cannot access signin page

**Diagnosis:**
Middleware still sees old cookies or redirect loop.

**Check Middleware Logs:**
```javascript
🔍 Middleware: { 
  pathname: "/signin", 
  isAuthenticated: ???,  ← Should be false after logout
  hasRefreshToken: ???,  ← Should be false after logout
  allCookies: [...]      ← Should NOT include refresh_token
}
```

**If `hasRefreshToken: true` after logout:**
- Backend didn't clear cookies properly
- Check backend `clear_secure_cookies()` includes `domain='localhost'`

**If middleware redirects `/signin` → `/`:**
- Middleware sees user as authenticated
- Force a hard refresh: Ctrl+Shift+R
- Manually delete cookies and try again

---

## Expected Test Results Summary

| Scenario | sessionStorage rememberMe | GraphQL rememberMe | Backend input.remember_me | Cookie Expires |
|----------|--------------------------|-------------------|--------------------------|----------------|
| Remember Me ON | `true` | `true` | `True` | ~30 days |
| Remember Me OFF | `false` | `false` | `False` | Session |

---

## What to Report

If issues persist, please provide:

### 1. Frontend Console Logs
Copy entire console output starting from login click until dashboard redirect:
```
🔐 Starting login process...
... (all logs)
🚀 Redirecting based on role...
```

### 2. Backend Console Logs
Copy backend output during OTP verification:
```
🔍 DEBUG: input.remember_me = ???
🔍 DEBUG: remember_me_value after check = ???
✅ Tokens generated for ...
```

### 3. sessionStorage Content
DevTools → Application → Session Storage → `pending-login`:
```json
{ "email": "...", "password": "...", "rememberMe": ??? }
```

### 4. Cookies Before OTP
DevTools → Application → Cookies (before entering OTP code):
```
refresh_token: Expires = ???
```

### 5. Cookies After OTP
DevTools → Application → Cookies (after OTP verification):
```
refresh_token: Expires = ???
```

---

*Test Guide Created: October 8, 2025*  
*Purpose: Debug Remember Me flag propagation*  
*Expected Duration: 5-10 minutes*
