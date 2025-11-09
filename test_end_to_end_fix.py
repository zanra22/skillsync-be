#!/usr/bin/env python
"""
Test end-to-end lesson generation with request key validation fix.
This script:
1. Resets module DZ6oiQhY94 status to 'not_started'
2. Deletes old request keys
3. Gets fresh access token via OTP
4. Triggers lesson generation mutation
5. Validates request key is created correctly
"""
import os
import sys
import asyncio
import json
import requests
from datetime import datetime
from asgiref.sync import sync_to_async

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.prod')
import django
django.setup()

from django.contrib.auth import get_user_model
from lessons.models import Module, LessonGenerationRequest
from otps.models import OTP
import hashlib

User = get_user_model()

# Configuration
MODULE_ID = 'pSE5ee5co6'
DJANGO_URL = 'https://api.skillsync.studio/graphql/'
USER_EMAIL = 'arnazdj69@gmail.com'

def print_step(message):
    """Print a step message"""
    print(f"\n[*] {message}")

def print_success(message):
    """Print a success message"""
    print(f"[OK] {message}")

def print_error(message):
    """Print an error message"""
    print(f"[X] {message}")

def print_info(message):
    """Print info message"""
    print(f"[INFO] {message}")

async def reset_module():
    """Reset module status to not_started and clean up request keys"""
    print_step("Resetting module status")

    try:
        module = await Module.objects.aget(id=MODULE_ID)
        print_info(f"Current status: {module.generation_status}")

        # Reset to not_started
        module.generation_status = 'not_started'
        module.generation_error = None
        module.generation_job_id = None
        module.generation_started_at = None
        module.generation_completed_at = None
        await module.asave()

        print_success(f"Module {MODULE_ID} reset to 'not_started'")
    except Module.DoesNotExist:
        print_error(f"Module {MODULE_ID} not found")
        return False

    # Delete old request keys
    print_step("Cleaning up old request keys")
    deleted_count = await LessonGenerationRequest.objects.filter(
        module_id=MODULE_ID
    ).adelete()

    if deleted_count[0] > 0:
        print_success(f"Deleted {deleted_count[0]} old request keys")
    else:
        print_info("No old request keys found")

    return True

async def get_access_token():
    """Get a valid access token via OTP"""
    print_step("Getting access token")

    try:
        user = await User.objects.aget(email=USER_EMAIL)
        print_info(f"Found user: {user.email}")
    except User.DoesNotExist:
        print_error(f"User {USER_EMAIL} not found")
        return None

    # Create OTP (sync method, use sync_to_async)
    try:
        otp, plain_code = await sync_to_async(OTP.create_otp)(user, purpose='signin', expiry_minutes=10)
        print_info(f"Created OTP: {plain_code}")
    except Exception as e:
        print_error(f"Failed to create OTP: {e}")
        return None

    # Verify OTP and get tokens
    mutation = """
    mutation VerifyOTP($input: VerifyOTPInput!) {
        otps {
            verifyOtp(input: $input) {
                success
                message
                accessToken
                user {
                    id
                    email
                }
            }
        }
    }
    """

    variables = {
        "input": {
            "email": USER_EMAIL,
            "code": plain_code,
            "purpose": "signin",
            "rememberMe": False,
            "trustDevice": False
        }
    }

    try:
        response = requests.post(
            DJANGO_URL,
            json={'query': mutation, 'variables': variables},
            timeout=60
        )
    except requests.exceptions.Timeout:
        print_error(f"OTP verification request timed out (10s)")
        return None
    except requests.exceptions.ConnectionError as e:
        print_error(f"Failed to connect to API: {e}")
        return None

    if response.status_code != 200:
        print_error(f"OTP verification failed: {response.status_code}")
        print_error(f"Response: {response.text}")
        return None

    data = response.json()

    if 'errors' in data:
        print_error(f"GraphQL error: {data['errors']}")
        return None

    result = data['data']['otps']['verifyOtp']

    if not result.get('success', False):
        print_error(f"OTP verification failed: {result.get('message')}")
        return None

    access_token = result.get('accessToken')
    if not access_token:
        print_error("No access token returned from OTP verification")
        return None

    print_success(f"Got access token")

    return access_token

async def trigger_lesson_generation(access_token):
    """Trigger lesson generation via GraphQL mutation"""
    print_step("Triggering lesson generation")

    # Get user
    user = await User.objects.aget(email=USER_EMAIL)
    print_info(f"User ID: {user.id}")

    # GraphQL mutation
    mutation = """
    mutation GenerateModuleLessons($moduleId: String!) {
        lessons {
            generateModuleLessons(moduleId: $moduleId) {
                id
                title
                generationStatus
                generationError
                generationJobId
            }
        }
    }
    """

    variables = {"moduleId": MODULE_ID}
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            DJANGO_URL,
            json={'query': mutation, 'variables': variables},
            headers=headers,
            timeout=60
        )
    except requests.exceptions.Timeout:
        print_error(f"Lesson generation request timed out (10s)")
        return False
    except requests.exceptions.ConnectionError as e:
        print_error(f"Failed to connect to API: {e}")
        return False

    if response.status_code != 200:
        print_error(f"Mutation failed: {response.status_code}")
        print_error(f"Response: {response.text}")
        return False

    data = response.json()

    if 'errors' in data:
        print_error(f"GraphQL error: {data['errors']}")
        return False

    result = data['data']['lessons']['generateModuleLessons']

    print_success(f"Mutation succeeded")
    print_info(f"Module ID: {result['id']}")
    print_info(f"Module Title: {result['title']}")
    print_info(f"Generation Status: {result['generationStatus']}")

    if result.get('generationError'):
        print_error(f"Generation Error: {result['generationError']}")

    return True

async def verify_request_key():
    """Verify that the request key was created correctly"""
    print_step("Verifying request key in database")

    # Get user
    user = await User.objects.aget(email=USER_EMAIL)

    # Check for request key
    try:
        req_key = await LessonGenerationRequest.objects.filter(
            module_id=MODULE_ID,
            user_id=str(user.id)
        ).afirst()

        if not req_key:
            print_error("No request key found for this module and user")
            return False

        print_success(f"Request key found")
        print_info(f"  Key: {req_key.request_key}")
        print_info(f"  User ID: {req_key.user_id}")
        print_info(f"  Module ID: {req_key.module_id}")
        print_info(f"  Created at: {req_key.created_at}")

        # Verify user_id is not 'None' string
        if req_key.user_id == 'None' or req_key.user_id == str(None):
            print_error("CRITICAL BUG: user_id is the string 'None'")
            return False

        if req_key.user_id != str(user.id):
            print_error(f"CRITICAL BUG: user_id mismatch. Expected {user.id}, got {req_key.user_id}")
            return False

        print_success("Request key validation passed - user_id is correct")
        return True

    except Exception as e:
        print_error(f"Error querying request key: {e}")
        return False

async def check_module_status():
    """Check the current module status"""
    print_step("Checking module status")

    try:
        module = await Module.objects.aget(id=MODULE_ID)
        print_info(f"Module: {module.title}")
        print_info(f"  ID: {module.id}")
        print_info(f"  Status: {module.generation_status}")
        print_info(f"  Job ID: {module.generation_job_id}")
        print_info(f"  Error: {module.generation_error}")
        print_info(f"  Lessons: {await module.lessons.acount()}")

        return True
    except Exception as e:
        print_error(f"Error checking module status: {e}")
        return False

async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("TEST: End-to-End Lesson Generation with Request Key Validation Fix")
    print("="*80)

    # Step 1: Reset module
    if not await reset_module():
        print_error("Failed to reset module")
        return False

    # Step 2: Get access token
    access_token = await get_access_token()
    if not access_token:
        print_error("Failed to get access token")
        return False

    # Step 3: Trigger lesson generation
    if not await trigger_lesson_generation(access_token):
        print_error("Failed to trigger lesson generation")
        return False

    # Step 4: Verify request key was created correctly
    if not await verify_request_key():
        print_error("Request key verification failed")
        return False

    # Step 5: Check module status
    if not await check_module_status():
        print_error("Failed to check module status")
        return False

    print("\n" + "="*80)
    print("TEST COMPLETE: All steps passed successfully!")
    print("="*80)
    print("\nNow waiting for Azure Function to process the message...")
    print("Check Azure Function logs to see if lesson generation completes.")
    print("\nExpected Azure Function behavior:")
    print("  1. Pick up message from Service Bus queue")
    print("  2. Validate request key from headers")
    print("  3. Generate lessons")
    print("  4. Update module status to 'completed'")
    print("\n" + "="*80)

    return True

if __name__ == '__main__':
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
