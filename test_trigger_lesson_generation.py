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
import time
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
    """Login and get access token with OTP verification."""
    print(f"\n[K] Logging in as {email}...")

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

        print(f"[>>] Response: {json.dumps(result, indent=2)}")

        login_response = result.get('data', {}).get('auth', {}).get('login', {})

        # Check if OTP is required (accessToken is null but OTP message present)
        if not login_response.get('accessToken') and 'OTP' in login_response.get('message', ''):
            print(f"\n[i] OTP sent to {email}")
            otp_code = input("Enter OTP code: ").strip()

            # Verify OTP
            verify_otp_mutation = """
            mutation VerifyOTP($input: VerifyOTPInput!) {
                otps {
                    verifyOtp(input: $input) {
                        success
                        message
                        accessToken
                        user {
                            id
                            email
                            role
                        }
                        deviceTrusted
                    }
                }
            }
            """

            otp_response = requests.post(
                api_url,
                json={
                    'query': verify_otp_mutation,
                    'variables': {
                        'input': {
                            'email': email,
                            'code': otp_code,
                            'purpose': 'signin'
                        }
                    }
                },
                headers={'Content-Type': 'application/json'}
            )

            if otp_response.status_code == 200:
                otp_result = otp_response.json()
                print(f"[>>] OTP Response: {json.dumps(otp_result, indent=2)}")

                # Check for errors first
                if otp_result.get('errors'):
                    print(f"[X] GraphQL Errors: {otp_result['errors']}")
                    return None

                otp_login = otp_result.get('data', {}).get('otps', {}).get('verifyOtp', {})
                if otp_login.get('success'):
                    token = otp_login.get('accessToken')
                    print(f"[OK] OTP verified! Access token obtained.")
                    return token
                else:
                    print(f"[X] OTP verification failed: {otp_login.get('message')}")
            else:
                print(f"[X] OTP request failed: {otp_response.status_code}")

            return None

        # Check if token was returned directly (no OTP required)
        if login_response.get('success') and login_response.get('accessToken'):
            token = login_response.get('accessToken')
            print(f"[OK] Login successful! Token obtained.")
            return token
        else:
            message = login_response.get('message', 'No response data')
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
        timeout=10
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


def check_generation_status(module_id, api_url, max_attempts=60, poll_interval=5):
    """Poll module generation status until completed or timeout."""
    print(f"\n[POLL] Monitoring generation status (max {max_attempts} attempts)...")

    for attempt in range(1, max_attempts + 1):
        try:
            # Query module status via REST API
            response = requests.get(
                f"{api_url.replace('/graphql/', '/api/modules/')}{module_id}/status/",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                status = data.get('generation_status', 'unknown')
                error = data.get('generation_error', '')
                lessons = data.get('lessons_count', 0)

                print(f"[{attempt}/{max_attempts}] Status: {status} | Lessons: {lessons} | Error: {error[:60] if error else 'None'}")

                if status == 'completed':
                    print(f"[OK] Generation completed! {lessons} lessons created.")
                    return True
                elif status == 'failed':
                    print(f"[X] Generation failed: {error}")
                    return False
                elif status in ['queued', 'in_progress']:
                    if attempt < max_attempts:
                        time.sleep(poll_interval)
                        continue
            else:
                print(f"[{attempt}/{max_attempts}] Status check failed: {response.status_code}")
        except Exception as e:
            print(f"[{attempt}/{max_attempts}] Error checking status: {e}")

        if attempt < max_attempts:
            time.sleep(poll_interval)

    print(f"[X] Timeout: Generation did not complete in {max_attempts * poll_interval} seconds")
    return False


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
    parser.add_argument('--poll', action='store_true', help='Poll for completion after triggering')
    parser.add_argument('--timeout', type=int, default=300, help='Max seconds to wait for completion')

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

    # Poll for completion if requested
    if args.poll:
        max_polls = args.timeout // 5
        check_generation_status(args.module_id, args.api_url, max_attempts=max_polls, poll_interval=5)


if __name__ == '__main__':
    main()
