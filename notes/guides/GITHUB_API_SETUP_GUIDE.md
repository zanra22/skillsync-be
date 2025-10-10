# 🔧 GitHub API Setup Guide

## Why You Need This

**Current State**: ❌ 401 Unauthorized errors (no token)
- Limited to 60 requests/hour
- Missing code examples in multi-source research
- Can't search GitHub repositories

**With Token**: ✅ Full functionality
- **5,000 requests/hour** (83x more!)
- Access to code search API
- Better quality lessons with real production code

---

## 🚀 Quick Setup (2 Minutes)

### Step 1: Get Your GitHub Token

1. Go to: https://github.com/settings/tokens
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. Give it a name: `skillsync-github-api`
4. Set expiration: **90 days** (or "No expiration" for development)
5. Select scopes (permissions):
   - ✅ **`public_repo`** - Access public repositories (required)
   - ✅ **`read:org`** - Read organization data (optional, but recommended)
   - ✅ **`repo`** - Full control of private repositories (optional, only if searching private code)
6. Click **"Generate token"**
7. **COPY THE TOKEN IMMEDIATELY** (you won't see it again!)

### Step 2: Add Token to .env File

```bash
# Navigate to backend
cd E:\Projects\skillsync-latest\skillsync-be

# Edit .env file (or create if missing)
notepad .env
```

Add this line:
```env
GITHUB_TOKEN=ghp_your_token_here_1234567890abcdef
```

**Example**:
```env
# GitHub API Configuration
GITHUB_TOKEN=ghp_Xj8K3mPq9LrN2vWcY5tF7nBhG4sD6aE1

# Other API keys (existing)
GEMINI_API_KEY=...
YOUTUBE_API_KEY=...
GROQ_API_KEY=...
```

### Step 3: Restart Django Server

```powershell
# Stop current server (Ctrl+C)
# Then restart:
python manage.py runserver
```

You should see:
```
✅ GitHub API initialized with token (5000 requests/hour)
✓ Multi-Source Research Engine initialized with all services
```

---

## 📊 Verify It's Working

Run the test again:
```powershell
python test_lesson_generation.py
```

**Before (no token)**:
```
HTTP Request: GET https://api.github.com/search/code?... "HTTP/1.1 401 Unauthorized"
GitHub API authentication failed - check your token
```

**After (with token)**:
```
HTTP Request: GET https://api.github.com/search/code?... "HTTP/1.1 200 OK"
✓ Found 5 GitHub examples for: Python Variables
```

---

## 🔒 Security Best Practices

### ✅ DO:
- Store token in `.env` file (never commit to Git)
- Add `.env` to `.gitignore` (should already be there)
- Use token with minimal scopes (only `public_repo` for SkillSync)
- Set expiration date (90 days recommended)

### ❌ DON'T:
- Commit token to GitHub (public exposure = security breach)
- Share token in chat/email
- Use personal account token in production (create dedicated account)
- Give token `repo` scope unless you need private code search

---

## 🐛 Troubleshooting

### Issue: Still getting 401 errors

**Solution 1**: Check `.env` file format
```env
# ❌ WRONG (quotes around value)
GITHUB_TOKEN="ghp_..."

# ✅ CORRECT (no quotes)
GITHUB_TOKEN=ghp_...
```

**Solution 2**: Verify token hasn't expired
- Go to: https://github.com/settings/tokens
- Check "Expires" column
- Regenerate if expired

**Solution 3**: Check Django is reading .env
```python
# Test in Django shell
python manage.py shell

>>> import os
>>> from django.conf import settings
>>> os.getenv('GITHUB_TOKEN')
'ghp_...'  # Should show your token
```

### Issue: Rate limit still 60/hour

**Cause**: Token not being passed to API
**Solution**: Check `helpers/multi_source_research_engine.py`:
```python
# Line ~50 should show:
self.github_service = GitHubAPIService(api_token=github_token)
```

---

## 📈 Rate Limits Summary

| Authentication | Rate Limit | Search Requests | Best For |
|---------------|-----------|-----------------|----------|
| **No Token** | 60/hour | ❌ Blocked (401) | Testing only |
| **With Token** | 5,000/hour | ✅ 30/minute | Production |
| **GitHub App** | 15,000/hour | ✅ 100/minute | High-volume |

**SkillSync Usage**: With token = ~10-20 requests per lesson generation (plenty!)

---

## 🎯 What This Unlocks

With GitHub token, your lessons will include:

### Before (no token):
```
Research sources:
- ✓ Official docs: Python.org
- ✓ Stack Overflow: 5 answers
- ✓ Dev.to: 2 articles
- ❌ GitHub: Authentication failed
```

### After (with token):
```
Research sources:
- ✓ Official docs: Python.org
- ✓ Stack Overflow: 5 answers (13M views)
- ✓ GitHub: 5 code examples (Django, Flask, FastAPI)
- ✓ Dev.to: 2 articles (42 reactions)

✅ Research Quality Score: 85/100
```

**Real impact**: Better code examples, more accurate lessons, production-ready patterns!

---

## 📝 Next Steps After Setup

1. ✅ Get GitHub token
2. ✅ Add to `.env` file
3. ✅ Restart Django server
4. ✅ Run `python test_lesson_generation.py`
5. ✅ Verify you see: `✓ Found X GitHub examples`
6. 🎉 Ready for comprehensive testing!

---

*Setup time: 2 minutes*  
*Token cost: FREE (5K requests/hour)*  
*Security: Enterprise-grade with .env isolation*
