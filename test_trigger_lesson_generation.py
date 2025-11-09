#!/usr/bin/env python
"""
Test Script: Trigger Lesson Generation via GraphQL

This script triggers the generateModuleLessons mutation to test:
1. Django backend enqueuing messages to Azure Service Bus
2. Azure Function receiving and processing messages
3. Full end-to-end lesson generation flow

Usage:
    python test_trigger_lesson_generation.py --module-id MODULE_ID --access-token TOKEN
    python test_trigger_lesson_generation.py --list-modules  # List available modules
"""

import os
import sys
import json
import argparse
import requests
import django
from datetime import datetime

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()

from lessons.models import Roadmap, Module
from users.models import User


def list_modules(user_email=None):
    """List all available modules that can be generated."""
    print("\n" + "="*80)
    print("AVAILABLE MODULES FOR LESSON GENERATION")
    print("="*80 + "\n")

    # Filter by user if provided
    if user_email:
        try:
            user = User.objects.get(email=user_email)
            roadmaps = Roadmap.objects.filter(user_id=str(user.id))
            print(f"Filtering for user: {user.email}\n")
        except User.DoesNotExist:
            print(f"User not found: {user_email}")
            return
    else:
        roadmaps = Roadmap.objects.all()[:10]  # Limit to recent 10

    if not roadmaps:
        print("No roadmaps found.")
        return

    for roadmap in roadmaps:
        print(f"Roadmap: {roadmap.title} (ID: {roadmap.id})")
        print(f"  User: {roadmap.user_id}")
        print(f"  Modules:")

        modules = roadmap.modules.all().order_by('order')
        for module in modules:
            status_emoji = {
                'not_started': '[_]',
                'queued': '[*]',
                'in_progress': '[>]',
                'completed': '[OK]',
                'failed': '[X]'
            }.get(module.generation_status, '[?]')

            print(f"    {status_emoji} {module.title}")
            print(f"       ID: {module.id}")
            print(f"       Status: {module.generation_status}")
            print(f"       Lessons: {module.lessons.count()}")
        print()


def get_access_token_from_login(email, password, api_url):
    """Login and get access token."""
    print(f"\n🔑 Logging in as {email}...")

    login_mutation = """
    mutation Login($input: LoginInput!) {
        auth {
            login(input: $input) {
                success
                message
                accessToken
                user {
                    id
                    email
                    role
                }
            }
        }
    }
    """

    response = requests.post(
        api_url,
        json={
            'query': login_mutation,
            'variables': {
                'input': {
                    'email': email,
                    'password': password
                }
            }
        },
        headers={'Content-Type': 'application/json'}
    )

    if response.status_code == 200:
        try:
            result = response.json()
        except Exception as e:
            print(f"[X] Failed to parse response: {e}")
            print(f"Response text: {response.text[:500]}")
            return None

        print(f"📡 Response: {json.dumps(result, indent=2)}")

        if result and result.get('data', {}).get('auth', {}).get('login', {}).get('success'):
            token = result['data']['auth']['login']['accessToken']
            print(f"[OK] Login successful! Token obtained.")
            return token
        else:
            message = result.get('data', {}).get('auth', {}).get('login', {}).get('message') if result else 'No response data'
            print(f"[X] Login failed: {message}")
            if result and 'errors' in result:
                print(f"GraphQL errors: {result['errors']}")
    else:
        print(f"[X] Login request failed: {response.status_code}")
        print(f"Response: {response.text[:500]}")

    return None


def trigger_lesson_generation(module_id, access_token, api_url):
    """Trigger lesson generation for a module."""
    print("\n" + "="*80)
    print(f"TRIGGERING LESSON GENERATION")
    print("="*80 + "\n")

    # Get module details
    try:
        module = Module.objects.select_related('roadmap').get(id=module_id)
        print(f"📦 Module: {module.title}")
        print(f"   Roadmap: {module.roadmap.title}")
        print(f"   Current status: {module.generation_status}")
        print(f"   Current lessons: {module.lessons.count()}")
        print()
    except Module.DoesNotExist:
        print(f"[X] Module not found: {module_id}")
        return

    # GraphQL mutation
    graphql_mutation = """
    mutation GenerateModuleLessons($moduleId: String!) {
        lessons {
            generateModuleLessons(moduleId: $moduleId) {
                id
                title
                generationStatus
                generationError
            }
        }
    }
    """

    print(f"🚀 Calling GraphQL API...")
    print(f"   URL: {api_url}")
    print(f"   Module ID: {module_id}")
    print()

    response = requests.post(
        api_url,
        json={
            'query': graphql_mutation,
            'variables': {'moduleId': module_id}
        },
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        },
        timeout=30
    )

    print(f"📡 Response status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()

        if 'errors' in result:
            print(f"\n[X] GraphQL Errors:")
            for error in result['errors']:
                print(f"   {error.get('message')}")
            return

        data = result.get('data', {}).get('lessons', {}).get('generateModuleLessons')

        if data:
            print(f"\n[OK] Mutation successful!")
            print(f"   Module ID: {data['id']}")
            print(f"   Title: {data['title']}")
            print(f"   New status: {data['generationStatus']}")
            if data.get('generationError'):
                print(f"   Error: {data['generationError']}")

            print(f"\n💡 What happens next:")
            print(f"   1. Message enqueued to Azure Service Bus (lesson-generation queue)")
            print(f"   2. Azure Function will pick up the message")
            print(f"   3. Lessons will be generated in the background")
            print(f"   4. Module status will update: queued → in_progress → completed")
            print(f"\n📊 Monitor progress:")
            print(f"   - App Service logs: Django backend logs")
            print(f"   - Function App logs: Azure Function processing logs")
            print(f"   - Service Bus: Check queue messages")
        else:
            print(f"\n[!] No data in response:")
            print(json.dumps(result, indent=2))
    else:
        print(f"\n[X] Request failed: {response.status_code}")
        print(response.text[:500])


def main():
    parser = argparse.ArgumentParser(description='Trigger lesson generation for a module')
    parser.add_argument('--module-id', help='Module ID to generate lessons for')
    parser.add_argument('--access-token', help='JWT access token for authentication')
    parser.add_argument('--email', help='Email for login (alternative to access-token)')
    parser.add_argument('--password', help='Password for login (alternative to access-token)')
    parser.add_argument('--list-modules', action='store_true', help='List available modules')
    parser.add_argument('--user-email', help='Filter modules by user email')
    parser.add_argument('--api-url', default='http://localhost:8000/graphql/',
                        help='GraphQL API URL (default: http://localhost:8000/graphql/)')

    args = parser.parse_args()

    # List modules mode
    if args.list_modules:
        list_modules(args.user_email)
        return

    # Trigger generation mode
    if not args.module_id:
        print("[X] Error: --module-id is required")
        parser.print_help()
        return

    # Get access token
    access_token = args.access_token

    if not access_token and args.email and args.password:
        access_token = get_access_token_from_login(args.email, args.password, args.api_url)

    if not access_token:
        print("[X] Error: Authentication required")
        print("   Provide either:")
        print("   1. --access-token TOKEN")
        print("   2. --email EMAIL --password PASSWORD")
        return

    # Trigger generation
    trigger_lesson_generation(args.module_id, access_token, args.api_url)


if __name__ == '__main__':
    main()
