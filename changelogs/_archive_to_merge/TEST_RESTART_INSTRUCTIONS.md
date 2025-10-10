# 🔄 Restart Servers & Test Instructions

## 🐛 Problem Fixed

The middleware was looking for `auth-token` cookie (removed in Phase 1), causing redirects even after successful OTP verification.

## ✅ Solution Applied

**Backend now sets 3 types of cookies:**
1. `refresh_token` - HTTP-only (secure, JavaScript can't access)
2. `client_fp` / `fp_hash` - HTTP-only (device fingerprinting)
3. **`user-role`** - NOT HTTP-only (middleware can read it) ← **NEW**

This allows Next.js middleware to check authentication while keeping tokens secure.

---

## 🚀 Step 1: Restart Backend Server

**In the terminal where Django is running:**

```powershell
# Press CTRL+BREAK or CTRL+C to stop the server
# Then restart:
python manage.py runserver
```

**Expected log:**
```
System check identified no issues (0 silenced).
October 08, 2025 - XX:XX:XX
Django version 5.2.6, using settings 'core.settings'
Starting development server at http://127.0.0.1:8000/
```

---

## 🚀 Step 2: Frontend Already Running

Frontend should auto-reload with Hot Module Replacement (HMR).

If not, restart manually:
```powershell
# In skillsync-fe directory
bun dev
```

---

## 🧪 Step 3: Test Authentication

### **Clear Browser Data First** (IMPORTANT!)

1. Open DevTools (F12)
2. Go to **Application** → **Storage**
3. Click **"Clear site data"** button
4. **OR** Go to **Cookies** → Delete all localhost cookies manually

---

### **Test A: Login & OTP Verification**

1. Go to: http://localhost:3000/auth/login

2. **Login:**
   - Email: arnazdj69@gmail.com
   - Password: [your password]
   - **UNCHECK** ❌ "Remember Me" (for first test)
   - Click **Login**

3. **Check backend logs** (should show):
   ```
   🔐 Setting SESSION cookies (browser close = logout)
   Email sent successfully to arnazdj69@gmail.com...
   OTP email sent successfully...
   ```

4. **Enter OTP** from email/console

5. **Check backend logs after OTP** (should show):
   ```
   DEBUG: Verifying OTP for email=arnazdj69@gmail.com, purpose=signin
   DEBUG: Verification result: success=True
   🔐 Setting SESSION cookies (browser close = logout)
   ✅ Tokens generated for arnazdj69@gmail.com after OTP verification
   🔑 Set user-role cookie: learner    ← **NEW LOG**
   ```

6. **Expected Result:**
   - ✅ **Redirected to /user-dashboard** (NOT back to signin!)
   - ✅ Console shows: "🔐 Storing access token in memory only (secure)"
   - ✅ Console shows: "🚀 Redirecting based on role: learner"

---

### **Test B: Check Cookies**

Open DevTools → **Application** → **Cookies** → **http://localhost:3000**

**Expected cookies:**
```
✅ refresh_token
   - Value: [long JWT string]
   - HttpOnly: ✓ (checkmark)
   - Expires/Max-Age: Session (no date for remember_me=false)
   
✅ client_fp
   - Value: [hash string]
   - HttpOnly: ✓
   
✅ fp_hash
   - Value: [hash string]
   - HttpOnly: ✓
   
✅ user-role    ← **NEW COOKIE**
   - Value: learner
   - HttpOnly: ✗ (NO checkmark - middleware can read it)
   - Expires/Max-Age: Session

❌ NO "auth-token" cookie (correctly removed)
❌ NO "access_token" cookie (correctly in memory only)
```

---

### **Test C: Middleware Logs**

Check **frontend terminal** for middleware logs:

**Should NOW show:**
```javascript
🔍 Middleware Debug: {
  pathname: '/user-dashboard',
  authToken: false,  // Still false (no auth-token cookie)
  userRole: 'learner',  ← **NOW PRESENT!**
  roleSource: 'cookie',
  userRoleFromCookie: 'learner',  ← **NOW PRESENT!**
  hasAuthCookie: false,
  hasRoleCookie: true,  ← **NOW TRUE!**
  allCookies: {
    refresh_token: '[HttpOnly]',  // Can't see value (HTTP-only)
    user-role: 'learner',  ← **CAN SEE THIS!**
    csrftoken: '...',
    sessionid: '...'
  }
}

✅ Access granted to protected route: { pathname: '/user-dashboard', userRole: 'learner' }
```

**No more:**
```
❌ Unauthenticated access to protected route, redirecting to signin
```

---

### **Test D: Remember Me (Session Cookie)**

1. **Close ALL browser windows completely**
2. **Reopen browser**
3. Go to: http://localhost:3000

**Expected Result:**
- ❌ **NOT logged in** (redirected to login page)
- ✅ Session cookies were deleted when browser closed

---

### **Test E: Remember Me (Persistent Cookie)**

1. **Login again** with **Remember Me CHECKED** ✅

2. **Check backend logs:**
   ```
   🔐 Setting PERSISTENT cookies (Remember Me): 30 days  ← **SHOULD SAY THIS**
   ✅ Tokens generated...
   🔑 Set user-role cookie: learner
   ```

3. **Check cookies:**
   ```
   ✅ refresh_token: Expires = [Date 30 days from now]
   ✅ user-role: Expires = [Date 30 days from now]
   ```

4. **Close ALL browser windows**

5. **Reopen browser** → Go to: http://localhost:3000

**Expected Result:**
- ✅ **STILL logged in** (redirected to /user-dashboard)
- ✅ Persistent cookies survived browser restart
- ✅ Console shows: "✅ Session restored successfully"

---

### **Test F: Logout**

1. Click **Logout** button

2. **Check backend logs:**
   ```
   🚪 Logout mutation called
   🧹 Clearing all authentication cookies
   ```

3. **Check cookies in DevTools:**
   ```
   ❌ ALL cookies deleted:
      - refresh_token: GONE
      - client_fp: GONE
      - fp_hash: GONE
      - user-role: GONE  ← **SHOULD BE DELETED**
   ```

4. **Try accessing /user-dashboard:**
   - ❌ Redirected to /signin (not authenticated)

---

## 🎯 Success Criteria

| Test | Expected Result | Status |
|------|-----------------|--------|
| Login + OTP → Redirect to dashboard | ✅ No redirect loop | ⬜ |
| Cookies set correctly | ✅ refresh_token (HTTP-only) + user-role (readable) | ⬜ |
| Middleware sees user-role | ✅ userRole: 'learner' in logs | ⬜ |
| Remember Me OFF → Browser close | ❌ Must login again | ⬜ |
| Remember Me ON → Browser close | ✅ Still logged in | ⬜ |
| Logout clears all cookies | ✅ All auth cookies deleted | ⬜ |

---

## 🐛 Troubleshooting

### **Still redirected to signin after OTP?**

**Check backend logs for:**
```
🔑 Set user-role cookie: learner
```

If **NOT present**, restart backend server again.

---

### **Middleware still can't see user-role?**

**Check frontend middleware logs:**
```javascript
allCookies: {
  user-role: 'learner'  ← **MUST BE HERE**
}
```

If **NOT present**:
1. Clear all browser cookies
2. Restart backend
3. Login again

---

### **Access token not in console?**

**Check frontend console for:**
```
✅ OTP API response: { success: true, accessToken: "eyJ...", user: {...} }
```

If **accessToken is undefined**:
- Backend OTP mutation didn't return token
- Check backend logs for errors
- Verify OTP mutation includes `access_token` field

---

## 📊 What Changed

### **Backend (auth/secure_utils.py)**
```python
# NEW: Set user-role cookie (NOT HTTP-only, for middleware)
response.set_cookie(
    'user-role',
    user_role,
    max_age=max_age,  # Same as refresh_token
    httponly=False,  # 🔑 Allow middleware to read
    secure=not settings.DEBUG,
    samesite='Strict',
    path='/',
)
```

### **Backend (otps/mutation.py)**
```python
# NEW: Generate tokens during OTP verification for signin
if input.purpose == 'signin':
    refresh = CustomRefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    
    SecureTokenManager.set_secure_jwt_cookies(
        response=info.context.response,
        access_token=access_token,
        refresh_token=str(refresh),
        request=info.context.request,
        remember_me=False  # Default to session cookie
    )
```

### **Frontend (context/AuthContext.tsx)**
```typescript
// NEW: Use access token from OTP response (don't call signin again)
if (authState.pendingPurpose === 'signin' && response.accessToken) {
    setAuthState(prev => ({
        ...prev,
        user: response.user as any,
        accessToken: response.accessToken || null,  // From OTP response
        isAuthenticated: true,
        isLoading: false,
        tokenExpiresAt: expiresAt,
        isRedirecting: true,
    }));
    // Role-based redirect
    redirectBasedOnRole(response.user);
}
```

---

## ✅ Final Checklist Before Testing

- [ ] Backend server restarted
- [ ] Frontend server running (auto-reloaded)
- [ ] Browser cookies cleared
- [ ] Email/console ready for OTP codes
- [ ] DevTools open (Application + Console tabs)
- [ ] Backend terminal visible (watch for logs)
- [ ] Frontend terminal visible (watch for middleware logs)

---

**Ready to test!** Follow Test A → Test B → Test C → Test D → Test E → Test F in order.

Good luck! 🚀
