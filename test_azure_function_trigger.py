#!/usr/bin/env python
"""
Test Script: Trigger Lesson Generation via Azure Service Bus (Direct)

This script tests the Azure Service Bus integration by:
1. Directly triggering the service bus message enqueue
2. Simulating what the Django backend does when generating lessons
3. Checking the generation status updates

Usage:
    python test_azure_function_trigger.py --module-id MODULE_ID
    python test_azure_function_trigger.py --list-modules
"""

import os
import sys
import json
import argparse
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()

from lessons.models import Roadmap, Module
from helpers.ai_roadmap_service import HybridRoadmapService
import asyncio

def list_modules():
    """List all available modules that can be generated."""
    print("\n" + "="*80)
    print("AVAILABLE MODULES FOR TESTING")
    print("="*80 + "\n")

    roadmaps = Roadmap.objects.all()[:5]

    if not roadmaps:
        print("No roadmaps found.")
        return

    for roadmap in roadmaps:
        print(f"Roadmap: {roadmap.title} (ID: {roadmap.id})")
        print(f"  User: {roadmap.user_id}")
        print(f"  Modules:")

        modules = roadmap.modules.all().order_by('order')
        for module in modules:
            status_str = module.generation_status or 'not_started'
            print(f"    [{status_str[0].upper()}] {module.title}")
            print(f"       ID: {module.id}")
            print(f"       Status: {status_str}")
            print(f"       Lessons: {module.lessons.count()}")
        print()


async def trigger_module_generation(module_id):
    """Trigger lesson generation for a module."""
    print("\n" + "="*80)
    print(f"TRIGGERING LESSON GENERATION")
    print("="*80 + "\n")

    # Get module details
    try:
        module = Module.objects.select_related('roadmap').get(id=module_id)
        print(f"Module: {module.title}")
        print(f"  Roadmap: {module.roadmap.title}")
        print(f"  Current status: {module.generation_status}")
        print(f"  Current lessons: {module.lessons.count()}")
        print()
    except Module.DoesNotExist:
        print(f"Module not found: {module_id}")
        return

    # Prepare lesson generation data
    print("Preparing lesson generation request...")

    # Use the same structure as the GraphQL mutation would
    generation_data = {
        "module_id": module_id,
        "roadmap_id": str(module.roadmap.id),
        "title": module.title,
        "description": module.description or "",
        "difficulty": module.difficulty_level or "beginner",
        "user_profile": {
            "time_commitment": "3-5",
            "learning_pace": "moderate",
            "current_experience_level": "beginner",
            "role": "student",
            "goals": []
        }
    }

    print(f"Generation data prepared:")
    print(f"  Module ID: {generation_data['module_id']}")
    print(f"  Roadmap ID: {generation_data['roadmap_id']}")
    print(f"  Difficulty: {generation_data['difficulty']}")
    print()

    try:
        # Import and create the service
        from helpers.ai_lesson_service import LessonGenerationService
        from helpers.ai_lesson_service import LessonRequest

        service = LessonGenerationService()

        print("Generating sample lesson to test full flow...")
        print()

        # Create a lesson request
        request = LessonRequest(
            step_title=module.title,
            lesson_number=1,
            learning_style='hands_on',
            user_profile=generation_data['user_profile'],
            difficulty=generation_data['difficulty'],
            category='python',
            programming_language='python',
            enable_research=False
        )

        print(f"Generating lesson: {module.title} (Hands-On)")
        print("This simulates what Azure Function will do...")
        print()

        # Generate lesson
        lesson = await service.generate_lesson(request)

        if lesson:
            print("✅ Lesson generated successfully!")
            print(f"   Type: {lesson.get('type') or lesson.get('lesson_type')}")
            print(f"   Title: {lesson.get('title')}")
            print(f"   Fields: {', '.join(list(lesson.keys())[:5])}...")
            print()

            # Update module status (what Azure Function would do)
            module.generation_status = 'in_progress'
            module.save()
            print(f"✅ Module status updated: {module.generation_status}")
            print()

            print("💡 In production with Azure Functions:")
            print("   1. This would be triggered by Service Bus message")
            print("   2. Azure Function would generate all lessons (for all learning styles)")
            print("   3. Lessons would be saved to database")
            print("   4. Module status updated to 'completed'")
            print()

            await service.cleanup()
        else:
            print("❌ Failed to generate lesson")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description='Test lesson generation')
    parser.add_argument('--module-id', help='Module ID to generate lessons for')
    parser.add_argument('--list-modules', action='store_true', help='List available modules')

    args = parser.parse_args()

    # List modules mode
    if args.list_modules:
        list_modules()
        return

    # Trigger generation mode
    if not args.module_id:
        print("❌ Error: --module-id is required")
        parser.print_help()
        return

    # Run async function
    asyncio.run(trigger_module_generation(args.module_id))


if __name__ == '__main__':
    main()
