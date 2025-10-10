# 🏗️ Django Project Structure - SkillSync

## ⚠️ CRITICAL: Settings Path

### ✅ CORRECT Django Settings Path
```python
# Use this in ALL test scripts, Django setup, and imports
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
```

### ❌ COMMON MISTAKES (DO NOT USE)
```python
# ❌ WRONG - 'config' is NOT the Django project root
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

# ❌ WRONG - Missing the settings package
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# ❌ WRONG - 'skillsync' is not the project name
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skillsync.settings')

# ❌ WRONG - No top-level settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
```

---

## 📂 Project Structure

```
skillsync-be/
├─ core/                        # 🎯 Django project root (NOT 'config')
│  ├─ settings/                 # Settings package
│  │  ├─ __init__.py            # Main settings (imports from base)
│  │  ├─ base.py                # Base settings (shared config)
│  │  ├─ dev.py                 # Development settings
│  │  └─ production.py          # Production settings
│  ├─ urls.py                   # Root URL configuration
│  ├─ wsgi.py                   # WSGI application
│  ├─ asgi.py                   # ASGI application
│  └─ __init__.py
│
├─ config/                      # 🔧 App-level config (NOT Django settings!)
│  ├─ security.py               # JWT, CORS, security settings
│  ├─ constants.py              # Application constants
│  └─ __init__.py
│
├─ api/                         # 🍓 Strawberry GraphQL schema
│  ├─ schema.py                 # Root Query/Mutation
│  ├─ middleware.py             # GraphQL middleware
│  └─ views.py                  # GraphQL view
│
├─ auth/                        # 🔐 Authentication app
│  ├─ mutation.py               # Login, logout, refresh mutations
│  ├─ query.py                  # Auth queries
│  ├─ types.py                  # GraphQL types
│  ├─ models.py                 # Auth models
│  ├─ secure_utils.py           # SecureTokenManager (cookies)
│  └─ custom_tokens.py          # JWT tokens with role claims
│
├─ users/                       # 👥 User management app
├─ profiles/                    # 📋 User profiles app
├─ onboarding/                  # 🚀 Onboarding flow app
├─ lessons/                     # 📚 Lesson management app
├─ otps/                        # 🔢 OTP verification app
│
├─ helpers/                     # 🛠️ Shared utilities
│  ├─ ai_lesson_service.py      # Lesson generation service
│  ├─ multi_source_research.py  # Multi-source research engine
│  ├─ github_api.py             # GitHub API integration
│  ├─ stackoverflow_api.py      # Stack Overflow API
│  ├─ devto_api.py              # Dev.to API
│  ├─ official_docs_scraper.py  # Official docs scraper
│  └─ youtube_quality_ranker.py # YouTube video ranking
│
├─ manage.py                    # Django management script
├─ requirements.txt             # Python dependencies
├─ .env                         # Environment variables (DO NOT COMMIT)
└─ .env.example                 # Environment variables template
```

---

## 🔧 Settings Environment Variables

### Development (.env)
```env
# Django Settings
DJANGO_SETTINGS_MODULE=core.settings.dev  # Used by manage.py

# API Keys
GEMINI_API_KEY=your_key_here
YOUTUBE_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
GITHUB_TOKEN=ghp_your_token_here
UNSPLASH_ACCESS_KEY=your_key_here

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/skillsync

# Security
SECRET_KEY=your_secret_key
DEBUG=True
```

---

## 📝 Test Script Template

### ✅ CORRECT Test Script Structure
```python
"""
Your Test Script Name

Description of what this test does.

Author: SkillSync Team
Date: October 10, 2025
"""

import os
import sys
import django

# ✅ CRITICAL: Use correct Django settings path
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()

# Now import Django models/services (after django.setup()!)
from helpers.ai_lesson_service import LessonGenerationService
from lessons.models import LessonContent
from users.models import User

def test_something():
    """Your test function"""
    # Your test code here
    pass

if __name__ == "__main__":
    test_something()
```

---

## 📋 Common Django Commands

### Running Django
```powershell
# Start development server
python manage.py runserver

# Run migrations
python manage.py migrate

# Create migrations
python manage.py makemigrations

# Create superuser
python manage.py createsuperuser

# Django shell
python manage.py shell

# Run tests
python manage.py test
```

### Custom Test Scripts
```powershell
# Run test scripts (they handle Django setup internally)
python test_lesson_generation.py
python test_language_detection.py
python test_onboarding_to_lessons.py
python test_smart_caching.py
```

---

## 🎯 Key Differences: `core/` vs `config/`

| Folder | Purpose | Contains | Import Path |
|--------|---------|----------|-------------|
| **`core/`** | Django project root | settings/, urls.py, wsgi.py, asgi.py | `DJANGO_SETTINGS_MODULE='core.settings.dev'` |
| **`config/`** | App-level config | security.py, constants.py | `from config.security import JWT_SETTINGS` |

### Examples:

**Django Settings** (lives in `core/`):
```python
# core/settings/dev.py
DEBUG = True
DATABASES = {...}
INSTALLED_APPS = [...]
```

**App Config** (lives in `config/`):
```python
# config/security.py
JWT_SETTINGS = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
}

# config/constants.py
DEFAULT_LESSON_DURATION = 45  # minutes
```

---

## 🚨 Troubleshooting

### Error: `ModuleNotFoundError: No module named 'config.settings'`

**Cause**: Using wrong Django settings path

**Solution**:
```python
# ❌ WRONG
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

# ✅ CORRECT
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
```

### Error: `ModuleNotFoundError: No module named 'core.settings'`

**Cause**: Missing the `.dev` or `.base` suffix

**Solution**:
```python
# ❌ WRONG
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# ✅ CORRECT
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
```

### Error: `django.core.exceptions.ImproperlyConfigured: Requested setting X`

**Cause**: Called Django functions before `django.setup()`

**Solution**:
```python
# ✅ CORRECT order
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()  # MUST come before Django imports

# NOW you can import Django stuff
from lessons.models import LessonContent
```

---

## 📚 Reference Files

For more information, check these files:
- `core/settings/base.py` - Base Django settings
- `core/settings/dev.py` - Development settings
- `config/security.py` - Security configuration (JWT, CORS)
- `manage.py` - Django management script (see line 11)
- `.github/copilot-instructions.md` - AI assistant instructions

---

## ✅ Quick Checklist

When creating a new test script or Django setup:

- [ ] Import: `import os, sys, django`
- [ ] Set env: `os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')`
- [ ] Setup: `django.setup()`
- [ ] Then import Django models/services
- [ ] NOT before: `from lessons.models import LessonContent` (will fail!)

---

*Last Updated: October 10, 2025*  
*Django Version: 4.x*  
*Settings Path: `core.settings.dev` (ALWAYS)*
