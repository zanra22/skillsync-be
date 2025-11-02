# Quick Reference Guide

## Running Tests

### Quick Test (5 seconds)
```bash
cd skillsync-be
source .venv/Scripts/activate
pytest tests/test_on_demand_simple.py -v -s
```

### AI Test (78 seconds)
```bash
cd skillsync-be
source .venv/Scripts/activate
pytest tests/test_ai_with_realistic_onboarding.py -v -s
```

### Both Tests
```bash
pytest tests/test_on_demand_simple.py tests/test_ai_with_realistic_onboarding.py -v -s
```

---

## Student Profile Used in Tests

```
Email: student@example.com
Career Stage: STUDENT
Skill Level: BEGINNER
Learning Style: MIXED
Industry: TECHNOLOGY
Time Commitment: 3-5 hours/week
Goal: Master the basics of Python for Career Development
Priority: 1 (highest)
```

---

## Key Model Fields

### UserProfile
```python
career_stage = 'student'           # STUDENT, ENTRY_LEVEL, SENIOR_LEVEL, etc.
skill_level = 'beginner'           # BEGINNER, INTERMEDIATE, EXPERT
learning_style = 'mixed'           # hands_on, video, reading, mixed
time_commitment = '3-5'            # 1-3, 3-5, 5-10, 10+
```

### UserLearningGoal
```python
skill_name = 'Python Basics'       # What to learn
description = '...'                # Why it matters
target_skill_level = 'beginner'    # Where to get to
current_skill_level = 'beginner'   # Where starting from
priority = 1                       # 1=highest, 5=lowest (INTEGER!)
```

### UserIndustry
```python
industry = 'technology'            # From IndustryType choices
is_primary = True                  # Mark primary industry
```

---

## Common Fixes

### Priority Must Be Integer
❌ Wrong: `priority='high'`
✅ Right: `priority=1`

### Career Stage Values
```python
CareerStage.STUDENT          # For student
CareerStage.ENTRY_LEVEL      # For junior professional
CareerStage.SENIOR_LEVEL     # For experienced pro
```

### Skill Level Values
```python
SkillLevel.BEGINNER          # Start here
SkillLevel.INTERMEDIATE      # In between
SkillLevel.EXPERT            # Advanced
```

### Learning Style Values
```python
'hands_on'   # Coding exercises
'video'      # YouTube tutorials
'reading'    # Documentation + articles
'mixed'      # All three combined
```

---

## Database Relationships

```
User
  ↓
  └─ UserProfile (1:1) - personal info
       ↓
       └─ UserIndustry (1:M) - industry choices
            ↓
            └─ UserLearningGoal (1:M) - specific skills
```

---

## AI Generation Fallback Chain

```
Try: DeepSeek V3.1
  ↓ fails
Try: Groq Llama 3.3
  ↓ fails
Try: Gemini 2.0 Flash
  ↓ fails
Return error
```

---

## Rate Limiting

| Service | Limit | Interval |
|---------|-------|----------|
| DeepSeek | 20/min | 3 seconds |
| Gemini | 15/min | 4 seconds |
| Groq | 14,400/day | unlimited |

---

## Module Status Flow

```
not_started → queued → in_progress → completed
                    ↘         ↓        ↓
                       failed ← ← ← ← ←
```

---

## JSONB Metadata

Stored in `LessonContent.generation_metadata`:

```python
{
    'prompt': 'The prompt used',
    'model': 'gemini-2.0-flash-exp',
    'learning_style': 'hands_on',
    'career_stage': 'student',
    'skill_level': 'beginner',
    'generated_at': '2025-10-30T14:30:00Z',
    'ai_provider': 'gemini',
    'generation_attempt': 1
}
```

---

## GraphQL Mutations

### Generate Lessons On-Demand
```graphql
mutation {
  generateModuleLessons(moduleId: "abc123") {
    id
    title
    generationStatus
    lessons {
      id
      title
      content
    }
  }
}
```

---

## REST Endpoints

### Check Module Generation Status
```
GET /api/modules/{module_id}/generation-status/

Response:
{
  "id": "abc123",
  "title": "Python Variables",
  "status": "in_progress",
  "started_at": "2025-10-30T14:30:00Z",
  "lessons_count": 0,
  "error": null
}
```

---

## Azure Service Bus

### Configuration
- Namespace: `skillsync.servicebus.windows.net`
- Connection: In `.env` as `AZURE_SERVICE_BUS_CONNECTION_STRING`
- Queues needed: `module-generation`, `lesson-generation`

### Message Format
```json
{
  "module_id": "abc123xyz",
  "roadmap_id": "def456uvw",
  "title": "Python Variables and Data Types",
  "difficulty": "beginner",
  "user_profile": {
    "learning_style": "mixed",
    "career_stage": "student",
    "skill_level": "beginner"
  },
  "idempotency_key": "...",
  "timestamp": "2025-10-30T14:30:00.000Z"
}
```

---

## Documentation Files

| File | Purpose |
|------|---------|
| `TESTING_SUMMARY.md` | Test results and coverage |
| `ONBOARDING_DATA_REFERENCE.md` | Data structure guide |
| `AZURE_SERVICE_BUS_VALIDATION.md` | Setup and deployment |
| `COMPLETION_SUMMARY.md` | Project completion overview |
| `QUICK_REFERENCE.md` | This file |

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Priority field error | Use integer (1-5), not string |
| Industry not found | Create UserIndustry first |
| Queue not found | Create queues in Azure |
| 429 errors | Rate limited - wait 60 seconds |
| Event loop closed | Cleanup async resources |

---

## Environment Variables

```bash
# API Keys
GEMINI_API_KEY=your_key
GROQ_API_KEY=your_key
OPENROUTER_API_KEY=your_key
YOUTUBE_API_KEY=your_key
GITHUB_TOKEN=your_token

# Azure Service Bus
AZURE_SERVICE_BUS_CONNECTION_STRING=your_connection_string

# Database
DEV_DB_NAME=skillsync-dev
DEV_DB_USER=skillsync
DEV_DB_PASSWORD=your_password
DEV_DB_HOST=skillsync-db.postgres.database.azure.com
```

---

## Useful Commands

```bash
# Run tests
pytest tests/test_on_demand_simple.py -v -s

# Run with coverage
pytest tests/ --cov=lessons --cov=profiles

# Check migrations
python manage.py showmigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Open Django shell
python manage.py shell

# Run development server
python manage.py runserver --settings=core.settings.dev

# GraphQL playground
# Visit: http://localhost:8000/graphql/
```

---

## Test Results Summary

```
test_on_demand_simple.py               PASS (5/5 tests, 5.0s)
test_ai_with_realistic_onboarding.py   PASS (5/5 tests, 78.0s)
───────────────────────────────────────────────────────────────
TOTAL                                  PASS (10/10 tests, 83.0s)
```

---

## Next Steps Checklist

- [ ] Run tests locally to verify setup
- [ ] Implement `generateModuleLessons` in frontend
- [ ] Add loading state in lesson view
- [ ] Create Service Bus queues
- [ ] Deploy Azure Functions
- [ ] Test end-to-end with real messages
- [ ] Monitor and optimize

---

## Resources

- Test file: `tests/test_ai_with_realistic_onboarding.py`
- Models: `lessons/models.py`, `profiles/models.py`
- AI Services: `helpers/ai_lesson_service.py`
- Mutations: `lessons/mutation.py`
- Azure Functions: `azure_functions/module_orchestrator/`

---

**Created**: October 30, 2025
**Status**: ✅ Ready for Integration
