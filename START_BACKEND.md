# Starting the Backend Development Server

## Quick Start (Copy & Paste)

### Windows (PowerShell or CMD)

```bash
cd e:\Projects\skillsync-latest\skillsync-be
.venv\Scripts\activate
python manage.py runserver --settings=core.settings.dev
```

### Linux/Mac

```bash
cd skillsync-latest/skillsync-be
source .venv/bin/activate
python manage.py runserver --settings=core.settings.dev
```

---

## What You Should See

```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
October 30, 2025 - 14:30:00
Django version 5.2.6, using settings 'core.settings.dev'
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK (Windows) or CTRL-C (Mac/Linux).
```

---

## Verify Backend is Running

### In Browser
Visit these URLs:

1. **GraphQL Playground**: http://127.0.0.1:8000/graphql/
2. **Admin Panel**: http://127.0.0.1:8000/admin/

### In Terminal (Linux/Mac)
```bash
curl http://127.0.0.1:8000/graphql/
```

### Using Python
```python
import requests
response = requests.get('http://127.0.0.1:8000/graphql/')
print(response.status_code)  # Should be 200 or 400 (not 404)
```

---

## Test the GraphQL Endpoint

In GraphQL Playground, run:

```graphql
query {
  __schema {
    types {
      name
    }
  }
}
```

**Expected Result**: List of GraphQL types (should see 50+ types)

---

## Common Issues

### Issue: "Port 8000 already in use"

```bash
# Find what's using port 8000
netstat -ano | findstr :8000  # Windows
lsof -i :8000                  # Mac/Linux

# Kill the process
taskkill /PID <PID> /F         # Windows
kill -9 <PID>                  # Mac/Linux

# Or use different port
python manage.py runserver 8001 --settings=core.settings.dev
```

### Issue: "ModuleNotFoundError: No module named 'core'"

```bash
# Make sure you're in the right directory
cd skillsync-be

# Make sure venv is activated
source .venv/Scripts/activate  # Windows
source .venv/bin/activate      # Linux/Mac

# Try running again
python manage.py runserver --settings=core.settings.dev
```

### Issue: "Environment variables not loaded"

Make sure `.env` file exists in `skillsync-be/` directory and contains:

```
GEMINI_API_KEY=your_key
GROQ_API_KEY=your_key
OPENROUTER_API_KEY=your_key
YOUTUBE_API_KEY=your_key
GITHUB_TOKEN=your_token
AZURE_SERVICE_BUS_CONNECTION_STRING=your_string
```

---

## Useful Commands

### Access Django Shell
```bash
python manage.py shell --settings=core.settings.dev
```

### Run Tests
```bash
# All tests
pytest tests/ -v

# Specific test
pytest tests/test_ai_with_realistic_onboarding.py -v

# With minimal output
pytest tests/ -q
```

### Check Database
```bash
python manage.py migrate --settings=core.settings.dev
python manage.py migrate --settings=core.settings.dev --plan  # Preview
```

### Create Superuser
```bash
python manage.py createsuperuser --settings=core.settings.dev
```

---

## Configuration Files

Important files used by backend:

```
skillsync-be/
├── .env                        # API keys (ignored by git)
├── core/
│   ├── settings/
│   │   ├── base.py            # Base settings
│   │   ├── dev.py             # Development overrides
│   │   └── prod.py            # Production overrides
│   └── urls.py                # URL routing
├── manage.py                   # Django management
└── requirements.txt            # Python dependencies
```

---

## Stopping the Server

**Windows**:
- Press `CTRL + C` in the terminal

**Mac/Linux**:
- Press `CTRL + C` in the terminal

Or kill the process:
```bash
# Windows
taskkill /IM python.exe /F

# Mac/Linux
pkill -f "python manage.py runserver"
```

---

## Next: Start Frontend

Once backend is running, open a new terminal and run:

```bash
cd e:\Projects\skillsync-latest\skillsync-fe
npm run dev
```

This will start the frontend on http://localhost:3000

---

**Status**: Backend Ready ✅
