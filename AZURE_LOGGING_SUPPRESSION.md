# Suppress Noisy Azure Application Insights Logs

## Problem

Azure Application Insights SDK logs HTTP request/response headers to stdout during server startup, cluttering the logs with infrastructure noise:

```
Request URL: 'https://southeastasia-1.in.applicationinsights.azure.com//v2.1/track'
Request method: 'POST'
Request headers:
    'Content-Type': 'application/json'
    [20 more header lines...]
Response status: 200
Response headers:
    [20 more header lines...]
```

This makes it impossible to track application logs (YouTube search, research, lesson generation).

## Solution

Set these environment variables in Azure App Service Configuration:

### Method 1: Azure Portal
1. Go to App Service → Configuration → Application Settings
2. Add the following environment variables:

| Name | Value |
|------|-------|
| `PYTHONWARNINGS` | `ignore` |
| `AZURE_SDK_LOG_LEVEL` | `CRITICAL` |
| `OPENCENSUS_TRACE_SAMPLER` | `ProbabilitySampler(rate=0.0)` |
| `APPLICATIONINSIGHTS_LOGGING_LEVEL` | `CRITICAL` |

### Method 2: Azure CLI

```bash
# Set via Azure CLI
az webapp config appsettings set \
  --resource-group <resource-group> \
  --name skillsync-graphql \
  --settings \
    PYTHONWARNINGS=ignore \
    AZURE_SDK_LOG_LEVEL=CRITICAL \
    APPLICATIONINSIGHTS_LOGGING_LEVEL=CRITICAL
```

### Method 3: Bicep/ARM Template

```bicep
appSettings: [
  {
    name: 'PYTHONWARNINGS'
    value: 'ignore'
  }
  {
    name: 'AZURE_SDK_LOG_LEVEL'
    value: 'CRITICAL'
  }
  {
    name: 'APPLICATIONINSIGHTS_LOGGING_LEVEL'
    value: 'CRITICAL'
  }
]
```

## Expected Result

After setting these environment variables and restarting the app:

**Before:**
- 100+ lines of Application Insights HTTP headers per request
- Impossible to see application logs
- Server startup takes 30+ seconds just to print logs

**After:**
- Only application logs visible
- Clean log stream showing:
  - YouTube video search
  - Research execution  
  - Lesson generation status
  - Errors and failures
  
## Why This Works

- `PYTHONWARNINGS=ignore` - Suppresses Python warnings
- `AZURE_SDK_LOG_LEVEL=CRITICAL` - Sets Azure SDK logging to only critical level (no DEBUG/INFO)
- `APPLICATIONINSIGHTS_LOGGING_LEVEL=CRITICAL` - Sets Application Insights to critical only
- The filter in `core/settings/prod.py` suppresses remaining urllib3/azure loggers at the Django level

## Additional Notes

- These settings only affect Azure App Service
- Local development logging is still controlled by `core/settings/dev.py` (DEBUG level for YouTube/research/lessons)
- The `core/settings/prod.py` logger configuration provides redundant filtering as a failsafe
- If Application Insights logs are still appearing after these changes, check if there's a custom Application Insights configuration in the Azure App Service

## Testing

After applying these settings:

1. Restart the App Service
2. Check logs: `az webapp log tail --resource-group <rg> --name skillsync-graphql`
3. Trigger a lesson generation via the GraphQL API
4. Verify you see:
   - `[search_and_rank]` logs
   - `[has_transcript]` logs  
   - `[LessonGen]` logs
5. Verify you DON'T see:
   - `Request URL:` headers
   - `Request method:` lines
   - `Response headers:` sections
