# core/settings/prod.py
# Deployment: Retry after Azure 409 conflict
from .base import *
from config.constants import DATABASE_CONFIG, FRONTEND_URL, CORS_ALLOWED_ORIGINS_CONFIG
import os

DEBUG = False

ALLOWED_HOSTS = ['.azurewebsites.net', '127.0.0.1', 'localhost', '.skillsync.studio']

# FRONTEND_URL is already resolved based on ENVIRONMENT in constants.py
print(f"Production FRONTEND_URL: {FRONTEND_URL}")
print('production checkpoint')

DATABASES = {
    "default": DATABASE_CONFIG,
}

print(f"Production DATABASES: {DATABASES}")

# Azure Key Vault - Read YouTube Service Account Credentials
# Reads the service account JSON from Azure Key Vault for YouTube OAuth2 authentication
try:
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
    import json

    KEYVAULT_URL = os.getenv('AZURE_KEYVAULT_URL')
    print(f"[DEBUG] AZURE_KEYVAULT_URL env var: {KEYVAULT_URL}")

    if KEYVAULT_URL:
        try:
            print("[DEBUG] Attempting to create DefaultAzureCredential...")
            credential = DefaultAzureCredential()
            print("[DEBUG] Creating SecretClient...")
            secret_client = SecretClient(vault_url=KEYVAULT_URL, credential=credential)

            # Retrieve YouTube service account JSON from Key Vault
            print("[DEBUG] Retrieving 'youtube-service-account-json' secret from Key Vault...")
            youtube_secret = secret_client.get_secret("youtube-service-account-json")
            if youtube_secret:
                # The secret contains the JSON content as a string
                secret_value = youtube_secret.value
                print(f"[DEBUG] Secret value (first 100 chars): {secret_value[:100]}")

                # Handle potential escaping issues
                try:
                    YOUTUBE_SERVICE_ACCOUNT = json.loads(secret_value)
                    print("[OK] Loaded YouTube service account from Azure Key Vault")
                except json.JSONDecodeError as json_err:
                    # Try unescaping if it's been double-escaped
                    try:
                        print(f"[DEBUG] JSON parse failed: {json_err}, attempting to unescape...")
                        unescaped = secret_value.encode().decode('unicode_escape')
                        YOUTUBE_SERVICE_ACCOUNT = json.loads(unescaped)
                        print("[OK] Loaded YouTube service account from Azure Key Vault (after unescaping)")
                    except Exception as e2:
                        print(f"[WARN] Failed to parse even after unescaping: {e2}")
                        YOUTUBE_SERVICE_ACCOUNT = None
            else:
                print("[WARN] youtube-service-account-json not found in Key Vault")
                YOUTUBE_SERVICE_ACCOUNT = None
        except Exception as e:
            print(f"[WARN] Failed to load YouTube service account from Key Vault: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            YOUTUBE_SERVICE_ACCOUNT = None
    else:
        print("[WARN] AZURE_KEYVAULT_URL not set - YouTube service account will not be loaded from Key Vault")
        YOUTUBE_SERVICE_ACCOUNT = None

except ImportError as e:
    # Azure SDK not available (shouldn't happen in production)
    print(f"[WARN] Azure SDK ImportError - YouTube service account authentication disabled: {e}")
    YOUTUBE_SERVICE_ACCOUNT = None

# CRITICAL FIX: Remove CORS_ALLOWED_ORIGINS from globals in production
# This ensures django-cors-headers respects CORS_ALLOW_ALL_ORIGINS = True
# CORS_ALLOWED_ORIGINS comes from 'from .base import *', so we must delete it from globals()
# not locals() to actually remove it from the settings module namespace
if CORS_ALLOW_ALL_ORIGINS:
    if 'CORS_ALLOWED_ORIGINS' in globals():
        del globals()['CORS_ALLOWED_ORIGINS']
    print("Production: CORS_ALLOWED_ORIGINS removed from globals to enable CORS_ALLOW_ALL_ORIGINS = True")
print(f"Production CORS_ALLOW_ALL_ORIGINS: {CORS_ALLOW_ALL_ORIGINS}")
if 'CORS_ALLOWED_ORIGINS' in globals():
    print(f"Production CORS_ALLOWED_ORIGINS: {globals()['CORS_ALLOWED_ORIGINS']}")
else:
    print("Production: CORS_ALLOWED_ORIGINS not in globals (allowing all origins)")