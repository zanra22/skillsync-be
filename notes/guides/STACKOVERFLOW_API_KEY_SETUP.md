# Stack Exchange API Key Setup Guide

**Date**: October 10, 2025  
**Purpose**: Add Stack Overflow API key for better quota management  
**Status**: OPTIONAL - System works fine without it

---

## 🎯 Why Add an API Key?

### What It Does:
✅ **Increases daily quota**: 10,000 → 10,300 requests/day  
✅ **Separate from IP quota**: Your app gets its own allocation  
✅ **Better for production**: Shows you're a registered application  
✅ **Required for OAuth**: Needed if you want OAuth access tokens later

### What It DOESN'T Do:
❌ **Bypass current IP ban**: You still need to wait 19 hours  
❌ **Prevent IP throttles**: Still limited to 30 req/sec per IP  
❌ **Give unlimited requests**: Still capped at 10,300/day  

---

## 📝 Step-by-Step Setup (5 Minutes)

### Step 1: Register Your Application

1. **Go to**: https://stackapps.com/apps/oauth/register

2. **Fill in the form**:
   ```
   Application Name: SkillSync Learning Platform
   
   Description: 
   Educational platform that generates programming lessons using 
   Stack Overflow Q&A, GitHub examples, and other quality sources.
   
   OAuth Domain: localhost (for development)
   or: yourdomain.com (for production)
   
   Application Website: 
   https://github.com/zanra22/skillsync-be
   or: https://yourdomain.com
   ```

3. **Submit** and get your **API Key** (long string like `U4DMV*8nvpm3EOpvf69Rxw((`)

---

### Step 2: Add to Environment Variables

**File**: `.env`

```env
# Stack Overflow API (OPTIONAL - increases quota)
STACKOVERFLOW_API_KEY=your_actual_key_here
```

**Example**:
```env
STACKOVERFLOW_API_KEY=U4DMV*8nvpm3EOpvf69Rxw((
```

---

### Step 3: Verify It's Working

**Code already updated!** The service will automatically use the key if present:

```python
# helpers/multi_source_research.py (ALREADY DONE)
self.stackoverflow_key = os.getenv('STACKOVERFLOW_API_KEY')
self.stackoverflow_service = StackOverflowAPIService(api_key=self.stackoverflow_key)
```

---

### Step 4: Test After IP Ban Expires

**After October 11, 2025** (when IP ban expires):

```bash
cd skillsync-be
python test_stackoverflow_fix.py
```

**Expected output with API key**:
```
✅ SUCCESS! Got 3 results
📊 Using API key: U4DMV*8nvpm... (registered app)

Sample result:
   Title: What does the "yield" keyword do in Python?
   Score: 12,847 votes
   Accepted: ✓
   Answers: 15
```

---

## 🔐 Future Enhancement: OAuth Access Token (RECOMMENDED)

If you want **complete independence from IP throttles**:

### Benefits:
- ✅ **Separate quota per user** (10,000 req/day per user/app pair)
- ✅ **NOT affected by IP bans** (critical!)
- ✅ **Up to 5 quotas per user** (can authenticate multiple users)
- ✅ **Production-grade solution** (what big apps use)

### How It Works:
1. User authenticates via OAuth 2.0
2. You get an `access_token`
3. Pass token with each request
4. Your app has separate quota from IP-based limits

### Implementation Guide:

**1. Update your app registration**:
   - Enable OAuth 2.0
   - Set redirect URI: `https://yourdomain.com/oauth/callback`
   - Get `client_id` and `client_secret`

**2. Implement OAuth flow** (simplified for backend-only):
   ```python
   # Get access token (one-time setup)
   # Visit: https://stackoverflow.com/oauth/dialog?client_id=YOUR_ID&scope=read_inbox&redirect_uri=YOUR_URI
   # User approves → Get code → Exchange for access_token
   
   # Then use token in requests
   params['access_token'] = os.getenv('STACKOVERFLOW_ACCESS_TOKEN')
   ```

**3. Add to `.env`**:
   ```env
   STACKOVERFLOW_CLIENT_ID=your_client_id
   STACKOVERFLOW_CLIENT_SECRET=your_client_secret
   STACKOVERFLOW_ACCESS_TOKEN=your_access_token_here
   ```

**4. Update service**:
   ```python
   def __init__(self, api_key=None, access_token=None):
       self.api_key = api_key
       self.access_token = access_token  # Separate quota!
   
   # In requests:
   if self.access_token:
       params['access_token'] = self.access_token  # Use OAuth token
   elif self.api_key:
       params['key'] = self.api_key  # Fallback to API key
   ```

---

## 📊 Comparison: No Key vs API Key vs OAuth

| Feature | No Key | API Key | OAuth Token |
|---------|--------|---------|-------------|
| **Daily Quota** | 10,000 | 10,300 | 10,000 per user |
| **Quota Type** | IP-shared | App-specific | User/app-specific |
| **IP Throttle** | ❌ Affected | ❌ Affected | ✅ **NOT affected** |
| **Setup Time** | 0 min | 5 min | 30 min |
| **Complexity** | Easy | Easy | Medium |
| **Best For** | Development | Production | High-traffic apps |

---

## 🎯 My Recommendation

### For Now (Development):
1. ✅ **Add API key** (5 minutes, good practice)
2. ⏳ **Wait for IP ban to expire** (19 hours)
3. ✅ **System works fine without SO** (4 other sources)

### For Production (Future):
1. 🔐 **Implement OAuth access token** (prevents IP issues)
2. 📊 **Monitor quota usage** (track daily limits)
3. 🔄 **Handle token refresh** (tokens expire, need rotation)

---

## ✅ Current Status

**Code Updated**: ✅ Ready to accept API key  
**Your Action**: Add `STACKOVERFLOW_API_KEY` to `.env` when you get it  
**IP Ban**: Still active until Oct 11 (~19 hours)  
**System Status**: ✅ Works perfectly without SO (4 sources operational)

---

## 📝 Quick Checklist

- [ ] Register app at stackapps.com
- [ ] Get API key from registration
- [ ] Add `STACKOVERFLOW_API_KEY=your_key` to `.env`
- [ ] Wait for IP ban to expire (Oct 11)
- [ ] Test with `python test_stackoverflow_fix.py`
- [ ] Verify key is being used in requests

**Optional (Future)**:
- [ ] Enable OAuth in app settings
- [ ] Get client_id and client_secret
- [ ] Implement OAuth flow
- [ ] Test with access_token

---

**Next**: Wait for IP ban to expire, then your API key will work automatically! 🚀
