# Remember Me Feature - Testing Guide

## 🎯 Testing Objectives

Verify that:
1. ✅ Session cookies (remember_me=False) are deleted when browser closes
2. ✅ Persistent cookies (remember_me=True) survive browser restarts
3. ✅ Access tokens are stored in memory only (not in cookies/localStorage)
4. ✅ HTTP-only cookies cannot be accessed by JavaScript
5. ✅ Logout clears all cookies correctly
6. ✅ Token rotation works on refresh

---

## 🚀 Quick Testing Plan (5 Minutes)

### Test 1: Session Cookie (Remember Me = OFF)
**Time**: 2 minutes

```bash
1. Start both servers:
   # Terminal 1 - Backend
   cd skillsync-be
   python manage.py runserver

   # Terminal 2 - Frontend
   cd skillsync-fe
   bun dev

2. Open browser: http://localhost:3000/auth/login

3. Login WITHOUT checking "Remember Me"
   - Email: test@skillsync.com
   - Password: [your password]
   - Remember Me: UNCHECKED ❌

4. Check DevTools → Application → Cookies → localhost
   Expected:
   ✅ refresh_token: NO "Expires" field (session cookie)
   ✅ client_fp: NO "Expires" field
   ✅ fp_hash: NO "Expires" field
   ❌ NO "auth-token" cookie (removed in Phase 1)

5. Close ALL browser windows (Ctrl+Shift+W or close entirely)

6. Reopen browser → http://localhost:3000
   Expected:
   ❌ NOT logged in (redirected to login page)
   ✅ Session ended when browser closed
```

**Expected Result**: ✅ PASS - User must login again after browser close

---

### Test 2: Persistent Cookie (Remember Me = ON)
**Time**: 2 minutes

```bash
1. Open browser: http://localhost:3000/auth/login

2. Login WITH "Remember Me" checked
   - Email: test@skillsync.com
   - Password: [your password]
   - Remember Me: CHECKED ✅

3. Check DevTools → Application → Cookies → localhost
   Expected:
   ✅ refresh_token: "Expires" = ~30 days from now
   ✅ client_fp: "Expires" = ~30 days from now
   ✅ fp_hash: "Expires" = ~30 days from now

4. Check Console logs:
   Expected:
   ✅ "🔐 Setting PERSISTENT cookies: 30 days"

5. Close ALL browser windows

6. Reopen browser → http://localhost:3000
   Expected:
   ✅ Still logged in (session restored)
   ✅ Redirected to dashboard (no login required)
   ✅ Console shows: "✅ Session restored successfully"
```

**Expected Result**: ✅ PASS - User stays logged in after browser restart

---

### Test 3: Memory-Only Access Token
**Time**: 1 minute

```bash
1. Login successfully (with or without Remember Me)

2. Open DevTools → Console
   Type: document.cookie
   Expected:
   ❌ Should NOT show "auth-token" or "access_token"
   ✅ May show "refresh_token" BUT with [HttpOnly] indicator (cannot access value)

3. Type: localStorage.getItem('accessToken')
   Expected:
   ❌ null (not in localStorage)

4. Type: sessionStorage.getItem('accessToken')
   Expected:
   ❌ null (not in sessionStorage)

5. Check React DevTools → Components → AuthContext
   Expected:
   ✅ authState.accessToken: "eyJhbGciOiJI..." (in memory)
```

**Expected Result**: ✅ PASS - Access token ONLY in React state (memory)

---

## 🧪 Automated Backend Testing

### Test Script: `skillsync-be/test_remember_me.py`

**Already created in backend guide!** Run it:

```bash
cd skillsync-be
python test_remember_me.py
```

**Expected Output**:
```
🧪 Testing Remember Me Backend Implementation

✅ Using existing test user

🔑 Generated tokens:
   Access token (first 50 chars): eyJhbGciOiJIUzI1NiIs...
   Refresh token (first 50 chars): eyJhbGciOiJIUzI1NiIs...

📋 Test 1: Session Cookie (remember_me=False)
------------------------------------------------------------
🔐 Setting SESSION cookies (browser close = logout)
   Cookie max-age: None
   ✅ PASS: Session cookie (no max-age)

📋 Test 2: Persistent Cookie (remember_me=True)
------------------------------------------------------------
🔐 Setting PERSISTENT cookies: 30 days
   Cookie max-age: 2592000 seconds
   ✅ PASS: Persistent cookie (30 days)

📋 Test 3: Cookie Security Attributes
------------------------------------------------------------
   HttpOnly: True
   SameSite: Strict
   Path: /
   ✅ PASS: All security attributes correct

============================================================
🎉 Testing complete!
```

---

## 🔍 Detailed Testing Checklist

### ✅ Backend Tests

Run these tests to verify backend implementation:

```bash
cd skillsync-be

# Test 1: JWT authentication flow
python test_jwt_auth.py

# Test 2: Complete authentication flow
python test_complete_flow.py

# Test 3: Remember Me functionality (most important)
python test_remember_me.py

# Test 4: Run Django unit tests
python manage.py test auth
```

---

### ✅ Frontend Manual Tests

#### Test A: Cookie Inspection
```bash
1. Login with Remember Me = ON
2. Open DevTools → Application → Cookies
3. Verify each cookie:

refresh_token:
✅ Value: Long JWT string
✅ Domain: localhost
✅ Path: /
✅ Expires: ~30 days from now
✅ HttpOnly: ✓ (checkmark)
✅ Secure: ✓ (if HTTPS, otherwise -)
✅ SameSite: Strict

client_fp:
✅ Value: Random string (device fingerprint)
✅ HttpOnly: ✓
✅ Expires: ~30 days from now

fp_hash:
✅ Value: SHA-256 hash
✅ HttpOnly: ✓
✅ Expires: ~30 days from now

❌ auth-token: Should NOT exist (removed in Phase 1)
```

---

#### Test B: Session Restoration on Page Refresh
```bash
1. Login successfully (with or without Remember Me)
2. Navigate to any page (e.g., /dashboard)
3. Press F5 or Ctrl+R to refresh
4. Open DevTools → Console

Expected logs:
✅ "🔍 Checking for existing session..."
✅ "🔄 Refreshing access token..."
✅ "✅ Token refresh successful"
✅ "🔐 New access token stored in memory"

Expected behavior:
✅ Page reloads
✅ User stays logged in (no redirect)
✅ Same user data displayed

Check Network tab:
✅ POST request to /graphql/ (refreshToken mutation)
✅ Request includes cookies (refresh_token sent automatically)
✅ Response returns new accessToken
```

---

#### Test C: Logout Cookie Clearing
```bash
1. Login successfully
2. Verify cookies exist in DevTools
3. Click "Logout" button
4. Check DevTools → Application → Cookies

Expected:
✅ refresh_token: DELETED
✅ client_fp: DELETED
✅ fp_hash: DELETED
✅ All auth cookies cleared

Check Console:
✅ "🚪 Starting logout process..."
✅ "✅ Backend logout successful (cookies cleared by server)"
✅ "🧹 Frontend state cleared"

Try accessing protected route:
✅ Redirected to login page (401 Unauthorized)
```

---

#### Test D: Token Rotation on Refresh
```bash
1. Login successfully
2. Open DevTools → Application → Cookies
3. Copy refresh_token value (e.g., "eyJhbGci...")
4. Refresh page (F5)
5. Check refresh_token value again

Expected:
✅ refresh_token value CHANGED (new token)
✅ Old token was rotated (security)

Backend behavior:
✅ Old refresh token added to blacklist
✅ New refresh token generated
✅ New access token returned
```

---

#### Test E: XSS Protection Verification
```bash
1. Login successfully
2. Open DevTools → Console
3. Try to steal tokens (simulate XSS attack):

// Try to read access token from cookies
document.cookie.split('; ').find(row => row.startsWith('access_token='))
Expected: ❌ undefined (not in cookies)

// Try to read refresh token from cookies
document.cookie.split('; ').find(row => row.startsWith('refresh_token='))
Expected: ❌ undefined (HTTP-only, invisible to JS)

// Try to read from localStorage
localStorage.getItem('accessToken')
localStorage.getItem('refresh_token')
Expected: ❌ null (not stored there)

// Try to read from sessionStorage
sessionStorage.getItem('accessToken')
sessionStorage.getItem('refresh_token')
Expected: ❌ null (not stored there)

Result:
✅ No way for malicious JavaScript to steal tokens
✅ XSS attack cannot access authentication credentials
```

---

## 🎬 Video Recording Test (Recommended)

**Best practice**: Record your screen while testing for documentation.

```bash
1. Start screen recording (Windows: Win+G, Mac: Cmd+Shift+5)

2. Test Scenario 1: Session Cookie
   - Show login screen
   - Login WITHOUT Remember Me
   - Show DevTools cookies (no Expires field)
   - Close browser completely
   - Reopen browser
   - Show redirect to login (session ended)

3. Test Scenario 2: Persistent Cookie
   - Show login screen
   - Login WITH Remember Me
   - Show DevTools cookies (Expires ~30 days)
   - Close browser completely
   - Reopen browser
   - Show successful login restoration

4. Save recording as: remember_me_test_oct082025.mp4
```

---

## 🐛 Troubleshooting Common Issues

### Issue 1: "refresh_token cookie not found"
**Symptom**: Session restoration fails, user redirected to login

**Debug Steps**:
```bash
1. Check if backend is setting cookies:
   - Backend logs should show: "🔐 Setting SESSION/PERSISTENT cookies"
   - If not, check auth/mutation.py login function

2. Check CORS settings:
   - Frontend must use credentials: 'include' in fetch
   - Backend CORS_ALLOW_CREDENTIALS must be True
   - Backend CORS_ALLOWED_ORIGINS must include frontend URL

3. Check cookie domain:
   - Both frontend/backend on same domain (localhost)
   - Cookie path is '/' (not '/api' or other)
```

**Fix**:
```python
# Backend: config/settings/dev.py
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Frontend URL
]
```

---

### Issue 2: "Cookies visible in document.cookie"
**Symptom**: Can see refresh_token value in JavaScript

**Debug Steps**:
```bash
1. Check if HttpOnly flag is set:
   DevTools → Application → Cookies → Check "HttpOnly" column
   
2. If not HttpOnly:
   - Check auth/secure_utils.py set_secure_jwt_cookies()
   - Verify: httponly=True in response.set_cookie()

3. Verify cookies set by backend (not frontend):
   - Frontend should NEVER call document.cookie = 'refresh_token=...'
   - Only backend can create truly HTTP-only cookies
```

**Fix**:
```python
# Backend: auth/secure_utils.py
response.set_cookie(
    'refresh_token',
    refresh_token,
    httponly=True,  # ✅ CRITICAL
    secure=not settings.DEBUG,
    samesite='Strict',
    path='/',
)
```

---

### Issue 3: "Session cookie persists after browser close"
**Symptom**: User stays logged in even with Remember Me = OFF

**Debug Steps**:
```bash
1. Check cookie max_age value:
   DevTools → Application → Cookies → Check "Expires/Max-Age" column
   
2. If session cookie has Expires date:
   - Backend incorrectly setting max_age
   - Should be max_age=None (not 0, not empty string)

3. Check backend logs:
   - Should show: "🔐 Setting SESSION cookies (browser close = logout)"
   - If shows "PERSISTENT", remember_me flag not passed correctly
```

**Fix**:
```python
# Backend: auth/secure_utils.py
if remember_me:
    max_age = int(settings.NINJA_JWT['REFRESH_TOKEN_LIFETIME_REMEMBER'].total_seconds())
else:
    max_age = None  # ✅ CRITICAL: None = session cookie, NOT 0
```

---

### Issue 4: "Access token in localStorage"
**Symptom**: Security scan finds tokens in localStorage

**Debug Steps**:
```bash
1. Search codebase for localStorage.setItem:
   grep -r "localStorage.setItem.*[Tt]oken" skillsync-fe/

2. Check if old code still present:
   - Should be removed in Phase 1 (Oct 8, 2025)
   - Check AuthContext.tsx, signin.tsx, otp.tsx

3. Verify React state storage:
   - Only setAuthState({ accessToken: ... })
   - Never localStorage or sessionStorage
```

**Fix**: Remove any remaining localStorage calls:
```typescript
// ❌ REMOVE THIS
localStorage.setItem('accessToken', token);
localStorage.setItem('refreshToken', token);

// ✅ USE THIS
setAuthState(prev => ({ ...prev, accessToken: token }));
```

---

## 📊 Testing Checklist Summary

### Before Release:
- [ ] Backend test_remember_me.py passes (all 3 tests)
- [ ] Frontend login WITHOUT Remember Me → browser close → must re-login
- [ ] Frontend login WITH Remember Me → browser close → stays logged in
- [ ] Access token NOT in cookies/localStorage/sessionStorage (memory only)
- [ ] HTTP-only cookies NOT visible in document.cookie
- [ ] Logout clears all cookies (verify in DevTools)
- [ ] Session restoration works on page refresh (< 500ms)
- [ ] Token rotation works (refresh_token value changes on refresh)
- [ ] XSS protection verified (cannot steal tokens via JavaScript)
- [ ] CORS configured correctly (credentials included)
- [ ] Cookie attributes correct (HttpOnly, Secure in prod, SameSite=Strict)

### Performance:
- [ ] Login response time < 1 second
- [ ] Session restoration < 500ms
- [ ] Token refresh < 200ms
- [ ] Logout < 300ms

### Security:
- [ ] No tokens in browser DevTools → Storage section
- [ ] No tokens accessible via document.cookie
- [ ] Backend logs show secure cookie setting
- [ ] HTTPS enforced in production (Secure flag = true)

---

## 🎯 Quick Test Summary

**Fastest test (2 minutes)**:
```bash
1. Login WITHOUT Remember Me
2. Close browser completely
3. Reopen → Should NOT be logged in ✅

4. Login WITH Remember Me
5. Close browser completely
6. Reopen → Should STILL be logged in ✅
```

**That's it!** If those two scenarios pass, Remember Me is working correctly.

---

## 📝 Test Results Template

Copy this to document your test results:

```markdown
# Remember Me Test Results - October 8, 2025

## Environment
- Backend: Django 4.x (localhost:8000)
- Frontend: Next.js 15.5.2 (localhost:3000)
- Browser: [Chrome/Firefox/Safari] [version]
- OS: [Windows/Mac/Linux]

## Test 1: Session Cookie (Remember Me = OFF)
- [ ] Login successful
- [ ] Cookies set (no Expires field)
- [ ] Browser close → Session ended
- [ ] Reopen → Must login again
- **Result**: ✅ PASS / ❌ FAIL

## Test 2: Persistent Cookie (Remember Me = ON)
- [ ] Login successful
- [ ] Cookies set (Expires ~30 days)
- [ ] Browser close → Cookie persists
- [ ] Reopen → Session restored
- **Result**: ✅ PASS / ❌ FAIL

## Test 3: Memory-Only Access Token
- [ ] Access token NOT in document.cookie
- [ ] Access token NOT in localStorage
- [ ] Access token NOT in sessionStorage
- [ ] Access token ONLY in React state
- **Result**: ✅ PASS / ❌ FAIL

## Test 4: HTTP-Only Cookie Protection
- [ ] refresh_token has HttpOnly flag
- [ ] Cannot read refresh_token via JavaScript
- [ ] client_fp has HttpOnly flag
- [ ] fp_hash has HttpOnly flag
- **Result**: ✅ PASS / ❌ FAIL

## Test 5: Logout Cookie Clearing
- [ ] Logout successful
- [ ] All cookies deleted
- [ ] Access to protected route blocked
- [ ] Must login again
- **Result**: ✅ PASS / ❌ FAIL

## Overall Result
- **Total Tests**: 5
- **Passed**: [X]
- **Failed**: [X]
- **Status**: ✅ READY FOR PRODUCTION / ❌ NEEDS FIXES

## Notes
[Any observations, issues, or recommendations]

## Tested By
Name: [Your Name]
Date: October 8, 2025
Time: [Time]
```

---

*Testing Guide Created: October 8, 2025*  
*For: Remember Me Feature Verification*  
*Security Level: Enterprise-Grade*
