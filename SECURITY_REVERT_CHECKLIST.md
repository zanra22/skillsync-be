# ⚠️ SECURITY REVERT CHECKLIST

**CRITICAL: This document tracks temporary security changes made for development testing.**

**YOU MUST REVERT THESE CHANGES BEFORE PRODUCTION LAUNCH!**

---

## 🎯 Purpose

These changes were made to allow testing from `localhost:3000` (frontend) against Azure production backend without hitting security validation errors. They temporarily relax device fingerprint validation for development origins.

---

## 📋 Changes Made (TO BE REVERTED)

### 1. ✅ Added ALLOW_DEV_CORS Flag

**File**: `config/constants.py`

**Lines Added** (around line 14-16):
```python
# ⚠️ TEMPORARY: Allow development CORS testing against production backend
# TODO: REMOVE BEFORE PRODUCTION LAUNCH - See SECURITY_REVERT_CHECKLIST.md
ALLOW_DEV_CORS = os.getenv("ALLOW_DEV_CORS", "false").lower() == "true"
```

**Action to Revert**:
- [ ] **DELETE** the entire `ALLOW_DEV_CORS` variable and comments
- [ ] Remove import from `core/settings/base.py` (line 6)
- [ ] Remove assignment in `core/settings/base.py` (line 15)
- [ ] Remove print statement in `core/settings/base.py` (line 22)

---

### 2. ✅ Modified Fingerprint Validation Logic

**File**: `auth/mutation.py`

**Lines Modified** (around line 285-315):
```python
# ⚠️ TEMPORARY: Check if dev CORS is enabled and request is from localhost
request_origin = info.context.request.META.get('HTTP_ORIGIN', '')
is_localhost_request = 'localhost' in request_origin or '127.0.0.1' in request_origin
skip_validation = settings.DEBUG or (settings.ALLOW_DEV_CORS and is_localhost_request)
```

**Action to Revert**:
- [ ] **REPLACE** the entire validation block with the original simple check:
```python
# Validate client fingerprint first (skip in development)
from django.conf import settings
if settings.DEBUG:
    print("🔧 Development mode: Skipping fingerprint validation for token refresh")
elif not SecureTokenManager.validate_fingerprint(info.context.request):
    print("❌ Fingerprint validation FAILED")
    return TokenRefreshPayload(
        success=False,
        message="Security validation failed - potential session hijacking detected"
    )
```

**Note**: The improved logging and cookie checking logic CAN BE KEPT - it improves security by distinguishing "missing cookies" from "hijacking". Only remove the `ALLOW_DEV_CORS` bypass logic.

---

### 3. ✅ Azure Environment Variable

**Location**: Azure App Service → Configuration → Application Settings

**Variable Added**:
- Name: `ALLOW_DEV_CORS`
- Value: `true`

**Action to Revert**:
- [ ] Go to Azure Portal
- [ ] Navigate to your App Service
- [ ] Go to Configuration → Application Settings
- [ ] **DELETE** the `ALLOW_DEV_CORS` setting
- [ ] **SAVE** the configuration
- [ ] **RESTART** the app service

---

## 🔒 Security Guarantees After Revert

After reverting these changes:

✅ **Device Fingerprinting**: Fully enforced in production
✅ **Session Hijacking Detection**: Active for all real users
✅ **SameSite Cookies**: `Strict` mode in production
✅ **HTTP-Only Cookies**: All authentication cookies protected from XSS
✅ **CSRF Protection**: Full protection with Strict cookies

---

## 🧪 Testing After Revert

### Test 1: Production Security (with real domain)

1. Deploy frontend to production domain (e.g., `https://skillsync.studio`)
2. Login from production frontend → production backend
3. Verify refresh token works
4. **Change User-Agent** manually and try refresh → Should fail with "hijacking detected"
5. **Clear cookies** and try refresh → Should fail with "missing cookies"

### Test 2: Cross-Origin Block (with localhost)

1. Try to access from `localhost:3000` → Azure backend
2. Should see security validation errors (expected behavior)
3. This confirms security is enforced

---

## 📝 Debug Logging (SAFE TO KEEP)

The following debug logging was added and **can be kept** in production:

**File**: `auth/secure_utils.py` (lines 100-107)
```python
# Debug logging in validate_fingerprint()
print(f"🔍 Fingerprint Validation:")
print(f"   Stored hash: {stored_fp_hash[:20] if stored_fp_hash else 'None'}...")
# ...
```

**File**: `auth/secure_utils.py` (lines 100-107)
```python
# Debug logging in set_secure_cookies()
print(f"✅ Set authentication cookies:")
# ...
```

**Why it's safe**: These logs help monitor security in production and can be useful for debugging real issues. They don't expose sensitive data (only truncated hashes).

---

## ✅ Revert Checklist Summary

Before production launch, complete ALL of these:

- [ ] **Remove** `ALLOW_DEV_CORS` from `config/constants.py`
- [ ] **Remove** `ALLOW_DEV_CORS` import and usage from `core/settings/base.py`
- [ ] **Restore** simple fingerprint validation in `auth/mutation.py` (remove localhost bypass)
- [ ] **Delete** `ALLOW_DEV_CORS` from Azure App Service configuration
- [ ] **Restart** Azure App Service
- [ ] **Test** security with production domain
- [ ] **Test** that localhost is blocked (confirming security works)
- [ ] **Delete this file** (`SECURITY_REVERT_CHECKLIST.md`) after completing all steps

---

## 🚀 Alternative: Use Local Backend for Development

**Recommended Approach** (avoids needing these temporary changes):

1. Run Django backend locally: `python manage.py runserver --settings=core.settings.dev`
2. Frontend connects to `http://localhost:8000`
3. All security checks work naturally because it's truly in `DEBUG=True` mode
4. No need to relax production security

**When to use Azure backend**:
- Testing actual production environment
- Testing deployment
- **Always revert these changes after testing!**

---

## 📅 Revert By Date

**Target Date**: Before production launch (or within 7 days of creating this file)
**Created**: [Auto-generated on commit]
**Last Updated**: [Auto-generated on commit]

---

## ⚠️ DO NOT IGNORE THIS FILE

Failing to revert these changes will leave your production environment vulnerable to:
- Cross-origin session hijacking
- Weakened device fingerprinting
- Bypassed security validation from localhost origins

**Set a reminder now to revert these changes!**
