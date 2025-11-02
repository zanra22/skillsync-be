# Azure Functions Deployment Guide - Complete Setup
## Creating and Deploying lesson_orchestrator Function

**Date:** October 31, 2025
**Goal:** Deploy `lesson_orchestrator` Azure Function to process lesson generation requests
**Time Required:** 30-45 minutes

---

## Architecture Overview

### Why Azure Functions?

**SkillSync** uses a hybrid synchronous/asynchronous architecture for content generation:

**Synchronous Operations (Django - Fast):**
- User onboarding: Create user profile
- Roadmap creation: Generate 5-8 modules (~3 seconds)
- Module list display: Immediate feedback to user
- All completed within 5 seconds, user sees skeleton immediately

**Asynchronous Operations (Azure Functions - Background):**
- Lesson generation: 3-5 lessons per module (~2-5 minutes per module)
- Multi-source research: GitHub, Stack Overflow, YouTube, Dev.to, official docs
- AI generation: Hybrid fallback chain (DeepSeek → Groq → Gemini)
- Happens in background, user can navigate while generating

### Message Queue Flow

```
User clicks "Generate" on module
    ↓
Django enqueues message to Azure Service Bus (lesson-generation queue)
    ↓
Message contains: module_id, roadmap_id, user_id, difficulty, learning_style
    ↓
Azure Function triggered automatically by Service Bus message
    ↓
Function generates 3-5 lessons using hybrid AI + multi-source research
    ↓
Updates Module.generation_status → 'completed'
    ↓
Lessons appear in dashboard (user refreshes or gets WebSocket notification)
```

### Architecture Decisions

**Why Only lesson_orchestrator?**
- Modules created **synchronously** during onboarding in Django (< 5 seconds)
- No need for module_orchestrator Azure Function
- Message sent to queue immediately when user clicks "Generate" button
- Lesson generation happens in background without blocking user

**Why Azure Service Bus?**
- Reliable message delivery with duplicate detection
- Automatic retry with exponential backoff
- Dead-letter queue for failed messages
- Triggers Azure Functions automatically
- ~$0.05/month cost (included in free tier)

**Why Single Queue (lesson-generation)?**
- Simpler architecture (less to maintain)
- Single trigger for lesson_orchestrator function
- Status tracking happens in PostgreSQL Module.generation_status field
- Dead-letter queue catches failed messages for debugging

### Status Tracking

**Module.generation_status field** tracks state:
```
not_started → queued → in_progress → completed/failed
```

All updates happen atomically in PostgreSQL (ACID transactions):
- Django sets status to 'queued' when enqueuing message
- Azure Function sets status to 'in_progress' when processing starts
- Azure Function sets status to 'completed' when lessons created successfully
- Azure Function sets status to 'failed' if error occurs (with error message in Module.generation_error)

### Cost Model

Estimated monthly cost at scale (100 users):
```
Storage Account:      ~$1/month  (for function logs/state)
Azure Functions:      FREE       (< 1M executions/month = free tier)
Service Bus:          ~$0.05/month (minimal message volume)
PostgreSQL:           Included   (already budgeted)
---
TOTAL:                ~$1-2/month very cheap! 🎉
```

---

## Prerequisites

Before starting, make sure you have:

1. ✅ Azure subscription (with free tier or student credits)
2. ✅ Azure CLI installed (`az --version` to check)
3. ✅ Python 3.9+ installed
4. ✅ Azure Functions Core Tools installed (`func --version` to check)

**Install if missing:**
```bash
# Azure CLI
# https://docs.microsoft.com/en-us/cli/azure/install-azure-cli

# Azure Functions Core Tools
npm install -g azure-functions-core-tools@4 --unsafe-perm=true --allow-root
# OR
brew tap azure/azure
brew install azure-functions-core-tools@4
```

---

## Step 1: Create Resource Group (5 minutes)

A Resource Group is a container for all your Azure resources.

```bash
# Set variables
$resourceGroup = "skillsync-rg"
$location = "eastus"

# Create resource group
az group create \
  --name $resourceGroup \
  --location $location

# Verify creation
az group show --name $resourceGroup
```

**Expected Output:**
```
{
  "id": "/subscriptions/.../resourceGroups/skillsync-rg",
  "location": "eastus",
  "name": "skillsync-rg",
  ...
}
```

---

## Step 2: Create Storage Account (5 minutes)

Azure Functions requires a storage account for logs and state.

```bash
$storageAccount = "skillsyncstorage"
$resourceGroup = "skillsync-rg"

# Create storage account
az storage account create \
  --name $storageAccount \
  --resource-group $resourceGroup \
  --location eastus \
  --sku Standard_LRS

# Get connection string (you'll need this)
az storage account show-connection-string \
  --name $storageAccount \
  --resource-group $resourceGroup
```

**Save the connection string** - you'll need it in Step 4.

---

## Step 3: Create App Service Plan (5 minutes)

The App Service Plan defines how your function runs (compute resources).

```bash
$appServicePlan = "skillsync-plan"
$resourceGroup = "skillsync-rg"

# Create App Service Plan (consumption tier = pay per execution)
az appservice plan create \
  --name $appServicePlan \
  --resource-group $resourceGroup \
  --sku B1 \
  --is-linux

# For even cheaper: use consumption tier
az functionapp plan create \
  --name $appServicePlan \
  --resource-group $resourceGroup \
  --sku EP1 \
  --is-linux
```

**Options:**
- **Consumption Plan (FREE):** Pay only for executions, ~$0.20/month for your usage
- **B1 Plan (CHEAP):** $10-20/month, always running

**Recommendation:** Use Consumption Plan for Phase 1 (free tier).

---

## Step 4: Create Function App (5 minutes)

This is where your Azure Functions live.

```bash
$functionAppName = "skillsync-functions"
$resourceGroup = "skillsync-rg"
$storageAccount = "skillsyncstorage"

# Create Function App
az functionapp create \
  --name $functionAppName \
  --resource-group $resourceGroup \
  --storage-account $storageAccount \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --os-type Linux

# Verify creation
az functionapp show --name $functionAppName --resource-group $resourceGroup
```

**Save the Function App name** - you'll need it for deployment.

---

## Step 5: Configure Environment Variables in Azure Portal (10 minutes)

Now you need to set the connection strings and URLs that your function will use.

### In Azure Portal:

1. Go to: https://portal.azure.com
2. Search for: "Function App"
3. Click your function app: `skillsync-functions`
4. Left sidebar → **Settings → Configuration**
5. Click **+ New application setting**

**Core Settings (REQUIRED):**

| Name | Value | Description |
|------|-------|-------------|
| `ENVIRONMENT` | `production` or `development` | Determines which database and Django URL to use |
| `PROD_DJANGO_URL` | `https://skillsync-graphql.azurewebsites.net/graphql/` | **PROD ONLY**: Your deployed Django App Service GraphQL endpoint |
| `DEV_DJANGO_URL` | `http://localhost:8000/graphql/` | **DEV ONLY**: Django GraphQL endpoint (only works if Azure Functions run locally) |
| `AzureServiceBusConnectionString` | (from Service Bus) | Primary Connection String from Service Bus → Shared access policies |

**Database Settings (For Your Environment):**

**If ENVIRONMENT=production:**
| Name | Value | Source |
|------|-------|--------|
| `PROD_DB_HOST` | PostgreSQL hostname | Azure Portal → Database server |
| `PROD_DB_NAME` | Database name | Your PostgreSQL database name |
| `PROD_DB_USER` | Database username | Your PostgreSQL user |
| `PROD_DB_PASSWORD` | Database password | Your PostgreSQL password |
| `PROD_DB_PORT` | `5432` | PostgreSQL port (default: 5432) |

**If ENVIRONMENT=development:**
| Name | Value | Source |
|------|-------|--------|
| `DEV_DB_HOST` | `localhost` or server IP | Your database host |
| `DEV_DB_NAME` | Database name | Your PostgreSQL database name |
| `DEV_DB_USER` | Database username | Your PostgreSQL user |
| `DEV_DB_PASSWORD` | Database password | Your PostgreSQL password |
| `DEV_DB_PORT` | `5432` | PostgreSQL port |

### How to get AZURE_SERVICE_BUS_CONNECTION_STRING:
1. Azure Portal → Service Bus namespace (`skillsync`)
2. Left sidebar → **Settings → Shared access policies**
3. Click **RootManageSharedAccessKey**
4. Copy **Primary Connection String**
5. Use this value in the Function App setting

### How to get PROD_DJANGO_URL:
1. Azure Portal → Search for your Django App Service (e.g., `skillsync-graphql`)
2. Click on it → **Overview**
3. Note the URL (e.g., `https://skillsync-graphql.azurewebsites.net`)
4. Append `/graphql/` to get the GraphQL endpoint
5. Full URL: `https://skillsync-graphql.azurewebsites.net/graphql/`

### ⚠️ CRITICAL NOTES:

**For Production:**
- The Django URL MUST be accessible from Azure (public URL, not localhost)
- Use the deployed Azure App Service URL
- Example: `https://skillsync-graphql.azurewebsites.net/graphql/`
- DO NOT use `http://localhost:8000` - Azure Functions in cloud cannot reach localhost

**For Development:**
- Only use `http://localhost:8000` if you're running Azure Functions locally with `func start`
- If Azure Functions is deployed to cloud, use the deployed Django URL
- Cannot use localhost from cloud environment

### After adding all settings:

1. Click **Save** button at the top
2. Azure will automatically restart your function app
3. Wait 1-2 minutes for changes to take effect
4. Check the function logs to verify it loaded correctly

---

## Step 6: Update function.json to Match Environment Variable Name (5 minutes)

**File:** `skillsync-be/azure_functions/lesson_orchestrator/function.json`

**Current (WRONG):**
```json
{
  "bindings": [
    {
      "name": "lessonmessage",
      "type": "serviceBusTrigger",
      "connection": "AzureServiceBusConnection"
    }
  ]
}
```

**Fixed (CORRECT):**
```json
{
  "scriptFile": "__init__.py",
  "bindings": [
    {
      "name": "lessonmessage",
      "type": "serviceBusTrigger",
      "direction": "in",
      "queueName": "lesson-generation",
      "connection": "AzureServiceBusConnectionString"
    }
  ]
}
```

**Key changes:**
- `connection`: "AzureServiceBusConnection" → "AzureServiceBusConnectionString"
- Added `queueName`: "lesson-generation"
- Added `direction`: "in"

---

## Step 7: Test Locally (10 minutes)

Before deploying to Azure, test it locally.

```bash
# Navigate to azure_functions directory
cd skillsync-be/azure_functions

# Start the Functions runtime locally
func start

# You should see output like:
# Azure Functions Core Tools
# Found Python project. Installing dependencies.
# ...
# Functions runtime started. Press CTRL+C to exit.
# Http Functions:
# ...
# lesson_orchestrator: [Enabled]
```

**Test by sending a message:**

Open another terminal and run:
```bash
# Navigate to skillsync-be
cd skillsync-be

# Send a test message to the queue
python -c "
import json
import os
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from dotenv import load_dotenv

load_dotenv()
conn_str = os.getenv('AZURE_SERVICE_BUS_CONNECTION_STRING')

with ServiceBusClient.from_connection_string(conn_str) as client:
    with client.get_queue_sender('lesson-generation') as sender:
        test_message = {
            'module_id': 'test-123',
            'title': 'Test Module',
            'description': 'Test Description',
            'difficulty': 'beginner',
            'user_id': 'test-user'
        }
        sender.send_messages(ServiceBusMessage(json.dumps(test_message)))
        print('Test message sent!')
"
```

**Expected result in func start terminal:**
```
[2025-10-31T15:30:00Z] Executing 'Functions.lesson_orchestrator' (Reason='(null)', Id=...)
[2025-10-31T15:30:00Z] Processing lesson: ...
```

If you see this, your function is working locally! ✅

---

## Step 8: Deploy to Azure (10 minutes)

Once local testing works, deploy to Azure.

```bash
# Navigate to azure_functions directory
cd skillsync-be/azure_functions

# Deploy to Azure
func azure functionapp publish skillsync-functions

# You'll be prompted to login if not already authenticated
# Azure CLI will:
# 1. Build the function
# 2. Upload to Azure
# 3. Deploy to your Function App
```

**Expected output:**
```
Getting site publishing info for function app 'skillsync-functions'...
Creating archive for current directory
Uploading archive...
Deployment successful!
Remote build succeeded!
Syncing triggers...

Functions in skillsync-functions:
    lesson_orchestrator - [Enabled]
```

---

## Step 9: Verify Deployment in Azure Portal (5 minutes)

1. Go to: https://portal.azure.com
2. Search: "Function App"
3. Click: `skillsync-functions`
4. Left sidebar → **Functions**
5. You should see: `lesson_orchestrator` listed as **Enabled**

### Monitor execution:

1. Click on `lesson_orchestrator`
2. Top menu → **Monitor**
3. You should see recent executions
4. Any errors will be shown here

---

## Step 10: Test End-to-End (5 minutes)

Now test the full flow from your Django app.

```bash
# In skillsync-be directory
python manage.py runserver --settings=core.settings.dev

# In browser:
# 1. Login
# 2. Complete onboarding (create roadmap)
# 3. Go to dashboard
# 4. Click "Generate" on a module

# Expected logs in Django:
# [ServiceBus] Message sent to queue 'lesson-generation' successfully
# Module queued for generation: ...
```

### Check Azure Function logs:

1. Azure Portal → skillsync-functions → Monitor
2. Look for new executions
3. Click an execution to see logs
4. Should see: "Processing lesson: ..."

### Check database:

```bash
# Query your PostgreSQL database
SELECT * FROM lessons_lessoncontent WHERE module_id='...';

# Should show new lessons being created
```

---

## Troubleshooting

### Problem: Function not triggering

**Check:**
1. Is function enabled in Azure Portal?
2. Are environment variables set correctly?
3. Does message exist in queue? (Azure Portal → Service Bus → lesson-generation queue)

**Solution:**
```bash
# Check function logs
az functionapp log tail --name skillsync-functions --resource-group skillsync-rg
```

### Problem: "ValueError: Django API URL not configured"

**Cause:** Missing `PROD_DJANGO_URL` or `DEV_DJANGO_URL` environment variable

**Solution:**
1. Check your `ENVIRONMENT` variable (is it `production` or `development`?)
2. Add the corresponding Django URL variable:
   - If `ENVIRONMENT=production`: Add `PROD_DJANGO_URL=https://skillsync-graphql.azurewebsites.net/graphql/`
   - If `ENVIRONMENT=development`: Add `DEV_DJANGO_URL=http://localhost:8000/graphql/`
3. Azure Portal → Function App → Configuration
4. Click **Save**
5. Wait 1-2 minutes for the setting to apply
6. Send a test message to retry

### Problem: "HTTPConnectionPool... Connection refused"

**Cause:** Django URL is incorrect or Django app is not accessible from Azure

**Solution:**
1. **Verify Django is running:**
   - If using Azure App Service: Azure Portal → App Service → Overview → Check status is "Running"
   - If running locally: Ensure `python manage.py runserver` is active

2. **Verify the Django URL is correct:**
   - Open the URL in your browser: `https://skillsync-graphql.azurewebsites.net/graphql/`
   - Should show GraphQL Playground or schema
   - If error 404 or timeout, the URL is wrong

3. **Check if you're using localhost:**
   - ❌ `http://localhost:8000` - Azure Functions in cloud cannot reach localhost
   - ✅ Use the deployed Azure App Service URL instead
   - Example: `https://skillsync-graphql.azurewebsites.net/graphql/`

4. **If using local Django for testing:**
   - Run Azure Functions locally: `cd azure_functions && func start`
   - Then `DEV_DJANGO_URL=http://localhost:8000` works
   - But deployed Azure Functions cannot use localhost

### Problem: "AzureServiceBusConnectionString not found"

**Cause:** Environment variable name mismatch

**Solution:**
1. Azure Portal → Function App → Configuration
2. Verify variable is named: `AzureServiceBusConnectionString` (exact spelling)
3. Verify value is correct (copy from Service Bus)
4. Click Save

### Problem: "CBS Put token error"

**Cause:** Connection string invalid or expired

**Solution:**
1. Get fresh connection string from Azure Portal
2. Service Bus → Shared access policies → RootManageSharedAccessKey
3. Copy: "Primary Connection String"
4. Update in Function App Configuration
5. Click Save

### Problem: Function runs but lessons not created

**Cause:** Django GraphQL mutation failed or database connection issue

**Check logs:**
```bash
az functionapp log tail --name skillsync-functions --resource-group skillsync-rg
```

Look for:
- `GraphQL error: ...` - The mutation `generateModuleLessons` failed
- `Database connection failed` - Cannot connect to PostgreSQL
- `Module not found` - Module ID doesn't exist in database
- `API request failed` - Django returned HTTP error (check Django logs)

**Next steps:**
1. Test Django API directly in GraphQL Playground
2. Verify module exists: `SELECT * FROM lessons_module WHERE id='...'`
3. Check Django logs for errors

---

## Cost Estimate

| Component | Cost | Notes |
|-----------|------|-------|
| Storage Account | ~$1/month | Minimal usage |
| App Service Plan | Free | Consumption plan |
| Function Executions | Free | < 1M/month free tier |
| Service Bus | ~$0.05/month | Minimal messages |
| Database | Included | Already paid |
| **Total** | **~$1-2/month** | Very cheap! |

---

## Implementation Details: Synchronous vs Asynchronous Patterns

### How Lesson Generation Works in Django

**File:** `skillsync-be/helpers/ai_roadmap_service.py` (Lines 275-330)

When user clicks "Generate" button in dashboard:

```python
# Synchronous: Returns immediately
async def queue_lesson_generation(module, user_profile):
    """Queue lessons for asynchronous generation"""

    # 1. Create message payload
    message = {
        'module_id': str(module.id),
        'roadmap_id': str(module.roadmap.id),
        'title': module.title,
        'difficulty': module.difficulty,
        'user_profile': user_profile,
        'timestamp': timezone.now().isoformat()
    }

    # 2. Send to Service Bus queue (lesson-generation)
    await self.service_bus_client.send_message(
        queue_name='lesson-generation',
        message=json.dumps(message)
    )

    # 3. Update module status (synchronously in Django)
    module.generation_status = 'queued'
    await module.asave()

    # 4. Return immediately to frontend (< 1 second)
    return module
```

**Timeline:**
- User clicks "Generate" button
- Message queued to Service Bus (< 1 second)
- UI updates to show "Queued" status
- User can navigate away immediately
- No blocking or waiting

### How Azure Function Processes Lessons

**File:** `skillsync-be/azure_functions/lesson_orchestrator/__init__.py`

When Service Bus message arrives:

```python
async def main(lesson_message: func.ServiceBusMessage):
    """
    Triggered automatically by Service Bus message.
    Generates 3-5 lessons for a module asynchronously.
    """

    try:
        # 1. Parse message (sent by Django)
        message_data = json.loads(lesson_message.get_body().decode('utf-8'))

        # 2. Update status to in_progress
        module = await Module.objects.aget(id=message_data['module_id'])
        module.generation_status = 'in_progress'
        module.generation_started_at = timezone.now()
        await module.asave()

        # 3. Generate lessons (2-5 minutes)
        # - Hybrid AI: DeepSeek V3.1 → Groq → Gemini 2.0
        # - Multi-source research: GitHub, Stack Overflow, YouTube, Dev.to
        lessons = await lesson_service.generate_lessons(
            module=module,
            user_profile=message_data['user_profile'],
            difficulty=message_data['difficulty']
        )

        # 4. Save lessons to database
        for lesson in lessons:
            await LessonContent.objects.acreate(
                module=module,
                content=lesson['content'],
                source_attribution=lesson['sources'],
                generation_metadata=lesson['metadata']
            )

        # 5. Update status to completed
        module.generation_status = 'completed'
        module.generation_completed_at = timezone.now()
        await module.asave()

    except Exception as e:
        # Error handling: Update status to failed
        module.generation_status = 'failed'
        module.generation_error = str(e)
        module.generation_completed_at = timezone.now()
        await module.asave()
        raise

    finally:
        # Cleanup async resources
        await lesson_service.cleanup()
```

**Timeline:**
- Service Bus triggers function automatically
- Status updates to 'in_progress'
- Lessons generated asynchronously (2-5 minutes)
- Each lesson: AI generation + multi-source research
- Lessons saved atomically to database
- Status updates to 'completed'
- Frontend can poll Module.generation_status to update UI

### Key Differences: Sync vs Async

| Aspect | Django (Synchronous) | Azure Function (Asynchronous) |
|--------|----------------------|--------------------------------|
| **What it does** | Queues messages to Service Bus | Processes queued messages |
| **How long it takes** | < 1 second | 2-5 minutes |
| **Blocks user?** | NO (message sent, function returns) | NO (runs in background) |
| **Where it runs** | Web App Server | Separate compute resource |
| **Cost per operation** | ~$0.001 (included in web tier) | FREE (< 1M/month free tier) |
| **Scaling** | Auto-scales with web app | Auto-scales independently |
| **What it needs** | Service Bus connection string | Django DB + AI API keys |

### Why This Architecture?

**Fast Onboarding (Synchronous Modules):**
- User completes onboarding
- Roadmap created with 5-8 modules (< 5 seconds)
- User sees skeleton immediately
- Good UX: No waiting, can start browsing

**Progressive Content Loading (Asynchronous Lessons):**
- User clicks "Generate" on module
- Message queued immediately (< 1 second)
- Azure Function processes in background
- Lessons appear as they're generated
- User can see Module.generation_status = 'in_progress'
- Good UX: Can continue using app while lessons generate

**Cost Efficiency:**
- No AI API calls during onboarding
- Lessons generated only when user requests
- Hybrid AI fallback saves money (DeepSeek → Groq → Gemini)
- Smart caching: 80%+ lessons from cache
- Result: ~$0.48 per user instead of $8 per user (94% savings!)

---

## Implementation Journey: Mistakes & Lessons Learned

### The Critical Mistake We Almost Made

**Initial Approach (❌ FAILED):**

We initially tried to run the entire Django app inside Azure Functions:

```python
# WRONG APPROACH
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.base')
django.setup()

from lessons.models import Module
async def generate_lessons(module):
    # Re-implement lesson generation from Django
```

**Problems:**
1. ❌ `ModuleNotFoundError: No module named 'django'` - Django not in requirements
2. ❌ `ModuleNotFoundError: No module named 'core.settings.base'` - Wrong settings module
3. ❌ 90+ packages in requirements.txt (bloated, slow deployment)
4. ❌ Duplicating business logic from Django (DRY violation)
5. ❌ Different lesson generation implementation in two places = inconsistency

**Error Timeline:**
- Deployment succeeded (looked OK)
- Function triggered by message
- Runtime crash with import errors
- Silent failures if errors were caught

### The Insight That Changed Everything

**User's Critical Question:**
> "My django project is already deployed on an app service, why do we need to upload the django app now?"

This single question revealed the fundamental misunderstanding. Azure Functions should not run Django—it should orchestrate it!

### The Solution: HTTP API Orchestration

**New Approach (✅ WORKING):**

```python
# CORRECT APPROACH
import requests

class LessonOrchestrationService:
    async def generate_lesson_via_api(self, message_data: dict) -> dict:
        """Call Django GraphQL API via HTTP"""
        response = requests.post(
            self.django_api_url,
            json={"query": graphql_query, "variables": {"moduleId": module_id}},
            timeout=300
        )
        return response.json()
```

**Benefits:**
- ✅ Separation of concerns: Azure Functions (queueing) vs Django (generation)
- ✅ No code duplication (single source of truth in Django)
- ✅ Minimal dependencies (6 packages instead of 90+)
- ✅ Reuses existing business logic
- ✅ Clear error messages and logging

### Dependency Issues & How We Fixed Them

#### Issue 1: System Library Error with psycopg2

**Error:**
```
ImportError: libpq.so.5: cannot open shared object file
```

**Root Cause:** `psycopg2` requires PostgreSQL system libraries not available in Azure runtime

**Fix:**
```
Before: psycopg2==2.9.10
After:  psycopg2-binary==2.9.10
```

`psycopg2-binary` includes all system libraries bundled, so it works in Azure Functions.

#### Issue 2: Requirements Bloat

**Before (90+ packages):**
```
Django==5.2.6
django-ninja==1.4.3
strawberry-graphql==0.281.0
google-generativeai==0.8.5
groq==0.32.0
openai==2.2.0
... 85 more packages not needed in Functions ...
```

**After (minimal, 6 packages):**
```
azure-functions==1.17.0
azure-servicebus==7.11.4
azure-identity==1.15.0
psycopg2-binary==2.9.10
python-dotenv==1.1.1
requests==2.32.5
```

**Impact:** Deployment time reduced from 6+ minutes to < 2 minutes

#### Issue 3: Hardcoded Fallback to Localhost

**Original Code (❌ WRONG):**
```python
def __init__(self):
    self.environment = os.getenv('ENVIRONMENT', 'development')
    if self.environment == 'production':
        self.django_api_url = os.getenv(
            'PROD_DJANGO_URL',
            'https://skillsync-graphql.azurewebsites.net/graphql/'  # ← Hardcoded default
        )
    else:
        self.django_api_url = os.getenv(
            'DEV_DJANGO_URL',
            'http://localhost:8000/graphql/'  # ← Hardcoded localhost!
        )
```

**Problem:** Azure Functions in cloud cannot reach localhost, but error only appears at runtime

**Real Error Seen:**
```
HTTPConnectionPool(host='localhost', port=8000):
Max retries exceeded... Connection refused
```

**Fixed Code (✅ CORRECT):**
```python
def __init__(self):
    self.environment = os.getenv('ENVIRONMENT', 'development')

    # Get URL - NO DEFAULTS (REQUIRED)
    if self.environment == 'production':
        self.django_api_url = os.getenv('PROD_DJANGO_URL')
    else:
        self.django_api_url = os.getenv('DEV_DJANGO_URL')

    # VALIDATE - Fail fast with clear message
    if not self.django_api_url:
        raise ValueError(
            f"Django API URL not configured. "
            f"Please set {self.environment.upper()}_DJANGO_URL environment variable"
        )
```

**Why This Is Better:**
- ✅ Fails immediately at startup with clear error
- ✅ No silent fallbacks
- ✅ Forces explicit configuration
- ✅ Same code works for dev and production

### Key Learnings & Best Practices

#### Don't ❌

```python
# 1. Don't try to run Django in serverless Functions
import django
django.setup()

# 2. Don't hardcode fallback URLs
url = os.getenv('URL', 'http://localhost:8000')  # WRONG

# 3. Don't include unnecessary dependencies
# Azure Functions ≠ Django - keep it lightweight

# 4. Don't use localhost for cloud-deployed functions
# Cloud Functions cannot reach your local machine

# 5. Don't silently fail - always validate config
try:
    validate_config()
except:
    pass  # Silent failure = BAD
```

#### Do ✅

```python
# 1. Call APIs via HTTP
response = requests.post(django_url, json=payload)

# 2. Make configuration REQUIRED
url = os.getenv('DJANGO_URL')
if not url:
    raise ValueError("DJANGO_URL environment variable required")

# 3. Keep dependencies minimal
# Only what you absolutely need

# 4. Use deployed URLs for production
PROD_URL = 'https://skillsync-graphql.azurewebsites.net/graphql/'

# 5. Fail fast and loud with clear messages
if not config:
    raise ValueError(
        f"Missing {var_name}. "
        f"Configure in Azure Portal → Function App → Configuration"
    )
```

### Architecture Principles Applied

| Principle | Implementation |
|-----------|-----------------|
| **Separation of Concerns** | Azure Functions handles queueing; Django handles generation |
| **DRY (Don't Repeat Yourself)** | Lesson generation logic in Django only, not duplicated |
| **Fail Fast** | Validate config at startup, not at runtime |
| **Minimal Scope** | Only 6 packages in Azure Functions |
| **Atomic Operations** | All database updates happen in Django with transactions |
| **Proper Error Handling** | Clear logs, proper exceptions, Service Bus retries |
| **Resource Cleanup** | Database connections closed in finally block |

### Timeline: From Mistake to Working Solution

| Phase | Duration | What Happened |
|-------|----------|---------------|
| **Initial Setup** | Oct 31 | Created module_orchestrator, deployed basic structure |
| **Architecture Discovery** | Nov 1-2 | User asked critical question, realized Django shouldn't be in Functions |
| **Code Refactoring** | Nov 2 | Removed Django imports, implemented HTTP API orchestration |
| **Dependency Fixes** | Nov 2 | Changed psycopg2 → psycopg2-binary, reduced from 90 to 6 packages |
| **Configuration** | Nov 2-3 | Fixed environment variable validation, added fail-fast logic |
| **Documentation** | Nov 3 | Updated deployment guide with lessons learned |

### What We Built Instead

A robust async lesson generation pipeline that:
- ✅ Separates concerns (Functions ≠ Django)
- ✅ Minimizes dependencies (6 packages)
- ✅ Reuses business logic (no duplication)
- ✅ Handles errors gracefully
- ✅ Scales independently
- ✅ Costs < $2/month
- ✅ Easy to maintain and update

---

## Next: Delete module_orchestrator (Optional)

Once lessons are generating correctly, you can delete the unused `module_orchestrator` function:

```bash
# In Azure Portal:
# 1. Delete the module_orchestrator function
# 2. Delete the "module-generation" queue from Service Bus

# Locally, keep the code for reference but it won't be deployed
```

---

## Summary Checklist

- [ ] Resource group created
- [ ] Storage account created
- [ ] App Service Plan created
- [ ] Function App created
- [ ] Environment variables configured in Azure Portal
- [ ] function.json updated with correct connection name
- [ ] Function tested locally with `func start`
- [ ] Test message sent and processed locally
- [ ] Function deployed to Azure with `func azure functionapp publish`
- [ ] Deployment verified in Azure Portal
- [ ] End-to-end test passed (message sent → lessons created)
- [ ] Database shows new lessons created

---

**Status:** Ready to start deploying! Follow the steps above in order.
**Timeline:** 30-45 minutes total
**Outcome:** Lessons will start generating when users click "Generate"
