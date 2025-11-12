"""
Pytest configuration for Django and async tests

Handles:
- Django settings initialization
- Async test support
- Mock fixtures
"""

import pytest
import django
import os
import sys
import asyncio

# Try to import pytest_asyncio, but don't fail if not available
try:
    import pytest_asyncio
    HAS_ASYNCIO = True
except ImportError:
    HAS_ASYNCIO = False

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def pytest_configure():
    """Configure pytest for Django tests"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')

    try:
        django.setup()
    except RuntimeError:
        # Already configured
        pass


@pytest.fixture(scope="session")
def django_db_setup():
    """Configure Django test database"""
    pass


# Only define asyncio fixture if pytest-asyncio is available
if HAS_ASYNCIO:
    @pytest_asyncio.fixture(scope="function")
    async def event_loop():
        """Create event loop for async tests"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        yield loop
        loop.close()
else:
    @pytest.fixture(scope="function")
    def event_loop():
        """Create event loop for async tests (fallback without pytest-asyncio)"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        yield loop
        loop.close()


@pytest.fixture
def mock_api_keys(monkeypatch):
    """Mock API keys for testing"""
    monkeypatch.setenv('GITHUB_API_TOKEN', 'mock_github_token')
    monkeypatch.setenv('YOUTUBE_API_KEY', 'mock_youtube_key')
    monkeypatch.setenv('GROQ_API_KEY', 'mock_groq_key')
    monkeypatch.setenv('OPENROUTER_API_KEY', 'mock_openrouter_key')
    return {
        'GITHUB_API_TOKEN': 'mock_github_token',
        'YOUTUBE_API_KEY': 'mock_youtube_key',
        'GROQ_API_KEY': 'mock_groq_key',
        'OPENROUTER_API_KEY': 'mock_openrouter_key',
    }


