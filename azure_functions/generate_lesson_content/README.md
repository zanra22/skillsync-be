# Azure Function: Generate Lesson Content (On-Demand)

## Overview

This Azure Function generates full content for a single lesson skeleton on-demand.

**Flow:**
1. Frontend/Backend triggers Azure Function with `lesson_id` and `user_id`
2. Azure Function calls Django GraphQL mutation: `generateLessonContent`
3. Django generates full lesson content (exercises, videos, etc.)
4. Lesson status updated: `pending` → `generating` → `completed`
5. Azure Function returns success response

## Local Testing

### Prerequisites

1. **Azure Functions Core Tools** installed
   ```bash
   npm install -g azure-functions-core-tools@4 --unsafe-perm true
   ```

2. **Django backend running**
   ```bash
   cd skillsync-be
   python manage.py runserver
   ```

3. **Lesson skeletons created** (run onboarding first)
   ```bash
   python test_full_ondemand_flow.py
   ```

### Step 1: Start Azure Functions

```bash
cd skillsync-be/azure_functions
func start
```

You should see:
```
Functions:
    generate_lesson_content: [POST] http://localhost:7071/api/generate_lesson_content
```

### Step 2: Run Test Script

In a **new terminal**:

```bash
cd skillsync-be
python test_azure_lesson_generation.py
```

The test will:
1. Find a lesson with `status='pending'`
2. Call the Azure Function
3. Verify the lesson was updated with full content

### Expected Output

```
🧪 TESTING AZURE FUNCTION: Generate Lesson Content
================================================================================
🔍 Finding a pending lesson...
✅ Found pending lesson:
   ID: abc123
   Title: Understanding Python Basics
   Module: Python Fundamentals
   User: user_xyz

🚀 Testing Azure Function...
   URL: http://localhost:7071/api/generate_lesson_content
   Payload: {
     "lesson_id": "abc123",
     "user_id": "user_xyz"
   }

📡 Calling Azure Function...
   Status Code: 200

✅ Azure Function Response:
   Success: True
   Lesson ID: abc123
   Title: Understanding Python Basics
   Status: completed
   Content Size: 9568 chars

🔍 Verifying lesson was updated...
   Status: completed
   Content Size: 9568 chars
   Content Keys: ['quiz', 'type', 'title', 'summary', 'exercises', ...]

✅ Lesson successfully updated!

================================================================================
✅ AZURE FUNCTION TEST PASSED!
================================================================================
```

## Manual Testing (cURL)

```bash
curl -X POST http://localhost:7071/api/generate_lesson_content \
  -H "Content-Type: application/json" \
  -d '{
    "lesson_id": "YOUR_LESSON_ID",
    "user_id": "YOUR_USER_ID"
  }'
```

## Deployment

### Azure Portal

1. Create Azure Function App (Python 3.10)
2. Configure environment variables:
   - `DEV_DJANGO_URL` or `PROD_DJANGO_URL`
   - `ENVIRONMENT` (development/production)
3. Deploy:
   ```bash
   cd azure_functions
   func azure functionapp publish YOUR_FUNCTION_APP_NAME
   ```

### Environment Variables

**Development:**
- `DEV_DJANGO_URL`: `http://localhost:8000`
- `ENVIRONMENT`: `development`

**Production:**
- `PROD_DJANGO_URL`: `https://api.skillsync.studio`
- `ENVIRONMENT`: `production`

## Troubleshooting

### Connection Error

```
❌ Connection Error!
   Could not connect to Azure Function at http://localhost:7071/api/generate_lesson_content
```

**Solution:** Make sure Azure Functions is running (`func start`)

### No Pending Lessons

```
❌ No pending lessons found
💡 Run test_full_ondemand_flow.py first to create lesson skeletons
```

**Solution:** Run the onboarding test to create lesson skeletons

### GraphQL Error

```
❌ GraphQL error: Authentication required
```

**Solution:** Check that `X-User-Id` header is being sent correctly

## Architecture

```
┌─────────────┐      HTTP POST      ┌──────────────────┐
│   Frontend  │ ───────────────────▶│ Azure Function   │
│  (or Test)  │  {lesson_id, user}  │ (generate_lesson)│
└─────────────┘                     └──────────────────┘
                                             │
                                             │ GraphQL
                                             ▼
                                    ┌──────────────────┐
                                    │ Django Backend   │
                                    │ (mutation)       │
                                    └──────────────────┘
                                             │
                                             │ Generate
                                             ▼
                                    ┌──────────────────┐
                                    │ AI Services      │
                                    │ (Groq/Gemini)    │
                                    └──────────────────┘
                                             │
                                             │ Save
                                             ▼
                                    ┌──────────────────┐
                                    │ PostgreSQL DB    │
                                    │ (lesson content) │
                                    └──────────────────┘
```

## Benefits

✅ **Async Processing** - Doesn't block the main Django app  
✅ **Scalable** - Azure Functions auto-scale based on demand  
✅ **Isolated** - Failures don't affect other lessons  
✅ **Cost-Effective** - Only pay for actual generation time  
✅ **Fast UX** - User sees roadmap immediately, lessons generate on-demand
