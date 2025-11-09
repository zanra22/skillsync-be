"""
Quick Integration Test - All 4 Learning Styles

This script tests that lesson generation works for all learning styles.
Run from: skillsync-be/ directory

Usage:
    python test_lesson_generation.py
"""

import os
import sys
import asyncio
import json
import logging
from datetime import datetime

# Setup Django before importing anything else
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')

import django
django.setup()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the lesson generation service
from helpers.ai_lesson_service import LessonGenerationService, LessonRequest


async def test_all_learning_styles():
    """Test lesson generation for all 4 learning styles"""

    logger.info("=" * 80)
    logger.info("LESSON GENERATION - ALL LEARNING STYLES TEST")
    logger.info("=" * 80)

    # Initialize service
    logger.info("Initializing LessonGenerationService...")
    service = LessonGenerationService()

    # Minimal user profile for testing
    user_profile = {
        'time_commitment': '3-5',
        'learning_pace': 'moderate',
        'current_experience_level': 'beginner',
        'role': 'student',
        'goals': [
            {'skill_name': 'Python', 'target_skill_level': 'intermediate'},
        ]
    }

    # Test data for each learning style
    test_cases = [
        {
            'learning_style': 'hands_on',
            'title': 'Python Variables and Data Types',
            'description': 'Hands-on lesson with coding exercises'
        },
        {
            'learning_style': 'video',
            'title': 'Introduction to Functions',
            'description': 'Video lesson with study guide'
        },
        {
            'learning_style': 'reading',
            'title': 'Control Flow and Loops',
            'description': 'Reading lesson with diagrams'
        },
        {
            'learning_style': 'mixed',
            'title': 'Working with Lists',
            'description': 'Mixed lesson with text, exercises, and visuals'
        }
    ]

    results = {
        'test_date': datetime.now().isoformat(),
        'total_tests': len(test_cases),
        'passed': 0,
        'failed': 0,
        'results': []
    }

    try:
        for i, test_case in enumerate(test_cases, 1):
            logger.info("")
            logger.info(f"TEST {i}/{len(test_cases)}: {test_case['learning_style'].upper()}")
            logger.info(f"Topic: {test_case['title']}")
            logger.info("-" * 80)

            try:
                # Create request
                request = LessonRequest(
                    step_title=test_case['title'],
                    lesson_number=1,
                    learning_style=test_case['learning_style'],
                    user_profile=user_profile,
                    difficulty='beginner',
                    industry='Technology',
                    category='python',
                    programming_language='python',
                    enable_research=False  # Disable research for faster testing
                )

                # Generate lesson
                logger.info(f"Generating {test_case['learning_style']} lesson...")
                lesson = await service.generate_lesson(request)

                if not lesson:
                    raise Exception("Lesson generation returned None")

                # Validate basic structure
                if not isinstance(lesson, dict):
                    raise Exception(f"Lesson must be dict, got {type(lesson)}")

                if 'type' not in lesson and 'lesson_type' not in lesson:
                    raise Exception("Lesson missing 'type' or 'lesson_type' field")

                # Check for required fields
                required_fields = ['title', 'summary']
                for field in required_fields:
                    if field not in lesson:
                        logger.warning(f"  Warning: Missing field: {field}")

                # Log success
                lesson_type = lesson.get('type') or lesson.get('lesson_type')
                logger.info(f"✅ SUCCESS: {test_case['learning_style']}")
                logger.info(f"   Type: {lesson_type}")
                logger.info(f"   Title: {lesson.get('title', 'N/A')}")
                logger.info(f"   Fields: {', '.join(list(lesson.keys())[:5])}...")

                results['results'].append({
                    'learning_style': test_case['learning_style'],
                    'status': 'PASSED',
                    'title': lesson.get('title', 'N/A'),
                    'error': None
                })
                results['passed'] += 1

            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ FAILED: {test_case['learning_style']}")
                logger.error(f"   Error: {error_msg}")

                results['results'].append({
                    'learning_style': test_case['learning_style'],
                    'status': 'FAILED',
                    'title': test_case['title'],
                    'error': error_msg
                })
                results['failed'] += 1

        # Cleanup
        logger.info("")
        logger.info("Cleaning up resources...")
        await service.cleanup()

    except Exception as e:
        logger.error(f"FATAL ERROR: {e}")
        results['fatal_error'] = str(e)
        raise

    finally:
        # Print summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total Tests: {results['total_tests']}")
        logger.info(f"Passed: {results['passed']}")
        logger.info(f"Failed: {results['failed']}")

        if results['failed'] == 0:
            logger.info("")
            logger.info("All tests passed!")
        else:
            logger.info("")
            logger.info("Some tests failed - see details above")

        logger.info("=" * 80)


if __name__ == '__main__':
    asyncio.run(test_all_learning_styles())
