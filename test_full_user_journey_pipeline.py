#!/usr/bin/env python3
# NOTE: Do NOT close the default asyncio event loop manually on Windows.
# Closing the loop here leads to Proactor/transport finalizer errors like
# "RuntimeError: Event loop is closed" when async transports are GC'd.
import asyncio
"""
Full User Journey Pipeline Test - October 20, 2025

Covers the entire backend flow:
- User creation
- Onboarding/profile creation
- Roadmap generation (personalized)
- Lesson generation for each roadmap step ("mixed" approach, hybrid AI)
- Full logging at every stage
- Cleans up test user/data at the end

Usage:
    python test_full_user_journey_pipeline.py
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_full_user_journey_pipeline.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')

import django
django.setup()

from asgiref.sync import sync_to_async

from django.contrib.auth import get_user_model
from profiles.models import UserProfile
from helpers.ai_roadmap_service import hybrid_roadmap_service, UserProfile as RoadmapUserProfile, LearningGoal
from helpers.ai_lesson_service import LessonGenerationService, LessonRequest

User = get_user_model()

class FullUserJourneyPipelineTest:
    def __init__(self):
        self.test_user = None
        self.test_profile = None
        self.generated_roadmap = None
        self.generated_lessons = []
        self.lesson_service = LessonGenerationService()

    def create_test_user(self):
        logger.info("🔧 Creating test user account...")
        User.objects.filter(email="test.pipeline@example.com").delete()
        user = User.objects.create_user(
            username="test.pipeline@example.com",
            email="test.pipeline@example.com",
            password="testpass123",
            first_name="Test",
            last_name="PipelineUser",
            is_active=True
        )
        logger.info(f"✅ Created test user: {user.email} (ID: {user.id})")
        return user

    def create_comprehensive_profile(self, user):
        logger.info("📋 Creating comprehensive user profile...")
        profile_data = {
            'user': user,
            'first_name': 'Test',
            'last_name': 'PipelineUser',
            'bio': 'Test user for full pipeline verification',
            'job_title': 'Junior Developer',
            'career_stage': 'mid',
            'industry': 'technology',
            'skill_level': 'intermediate',
            'time_commitment': '5-10',
            'learning_style': 'mixed',
            'transition_timeline': '6-12_months',
            'learning_goals': 'Master Python for career advancement'
        }
        profile = UserProfile.objects.create(**profile_data)
        logger.info(f"✅ Created profile for user: {user.email}")
        return profile

    async def generate_full_roadmap_modules_lessons(self, profile):
        logger.info("🗺️ Generating full roadmap -> modules -> lessons using hybrid_roadmap_service...")
        from helpers.ai_roadmap_service import LearningGoal, UserProfile as RoadmapUserProfile, hybrid_roadmap_service

        integrated_goal = LearningGoal(
            skill_name=profile.learning_goals.strip(),
            description=f"Master {profile.learning_goals.strip()} (integrated roadmap)",
            target_skill_level=profile.skill_level,
            priority=1
        )
        roadmap_user_profile = RoadmapUserProfile(
            role=profile.job_title,
            industry=profile.industry,
            career_stage=profile.career_stage,
            learning_style=profile.learning_style,
            time_commitment=profile.time_commitment,
            goals=[integrated_goal]
        )
        # Call the new full generation method directly (async)
        roadmap_obj, modules, lessons_by_module = await hybrid_roadmap_service.generate_full_roadmap_modules_lessons(roadmap_user_profile)
        if roadmap_obj:
            logger.info(f"✅ Roadmap ready: {roadmap_obj.title} (ID: {roadmap_obj.id})")
        else:
            logger.error("❌ No roadmap generated/fetched")
        logger.info(f"📦 Modules count: {len(modules)}")
        for module in modules:
            logger.info(f"   Module: {module.title} (ID: {module.id})")
            lessons = lessons_by_module.get(module.id, [])
            logger.info(f"      Lessons count: {len(lessons)}")
            for lesson in lessons:
                logger.info(f"         Lesson: {lesson.title} (ID: {lesson.id})")
        self.generated_roadmap = roadmap_obj
        self.generated_modules = modules
        self.generated_lessons_by_module = lessons_by_module
        return roadmap_obj, modules, lessons_by_module

    async def generate_lessons_for_roadmap(self, profile, roadmap, max_steps=None):
        logger.info("📚 Generating lessons for roadmap steps (mixed approach)...")
        lessons = []
        # Support both 'steps' (dict) and 'phases' (dataclass)
        steps = getattr(roadmap, 'steps', None) or getattr(roadmap, 'phases', None) or []
        total_steps = len(steps)
        steps_to_process = total_steps if max_steps is None else min(max_steps, total_steps)
        print(f"\n================ LESSON GENERATION =================\n")
        for idx, step in enumerate(steps[:steps_to_process], 1):
            step_title = step.title if hasattr(step, 'title') else step.get('title', f'Step {idx}')
            print(f"\n--------------------------------------------------")
            print(f"  LESSON {idx}/{steps_to_process}: {step_title}")
            print(f"--------------------------------------------------\n")
            lesson_request = LessonRequest(
                step_title=step_title,
                lesson_number=idx,
                learning_style='mixed',
                user_profile={
                    'role': profile.job_title,
                    'current_role': profile.job_title,
                    'career_stage': profile.career_stage,
                    'transition_timeline': profile.transition_timeline,
                    'industry': profile.industry,
                    'experience_level': profile.skill_level,
                    'time_commitment': profile.time_commitment,
                    'learning_style': 'mixed',
                    'goals': profile.learning_goals
                },
                difficulty='intermediate',
                category=None,
                programming_language=None,
                enable_research=True
            )
            try:
                lesson = await self.lesson_service.generate_lesson(lesson_request)
                if lesson:
                    # Print summary of lesson components
                    lesson_type = lesson.get('lesson_type', lesson.get('type', 'unknown')) if isinstance(lesson, dict) else getattr(lesson, 'lesson_type', 'unknown')
                    title = lesson.get('title', 'N/A') if isinstance(lesson, dict) else getattr(lesson, 'title', 'N/A')
                    duration = lesson.get('estimated_duration', 0) if isinstance(lesson, dict) else getattr(lesson, 'estimated_duration', 0)
                    research_metadata = lesson.get('research_metadata', {}) if isinstance(lesson, dict) else getattr(lesson, 'research_metadata', {})
                    research_source = research_metadata.get('source_type', 'N/A') if isinstance(research_metadata, dict) else getattr(research_metadata, 'source_type', 'N/A')
                    print(f"✅ Lesson generated: {title}")
                    print(f"   Type: {lesson_type}")
                    print(f"   Duration: {duration} min")
                    print(f"   Research Source: {research_source}")
                    # Print components
                    components = []
                    if lesson.get('exercises') and len(lesson['exercises']) > 0:
                        components.append('hands-on')
                    if lesson.get('video') or lesson.get('video_summary'):
                        components.append('video')
                    if ('text_content' in lesson and lesson['text_content']) or \
                       ('key_concepts' in lesson and lesson['key_concepts']) or \
                       ('text_introduction' in lesson and lesson['text_introduction']) or \
                       ('summary' in lesson and lesson['summary']):
                        components.append('reading')
                    print(f"   Components: {', '.join(components) if components else 'none'}")
                    if lesson.get('is_fallback', False):
                        print(f"   ⚠️  Fallback content used (AI unavailable)")
                    print(f"   Full lesson object: {json.dumps(lesson, indent=2, ensure_ascii=False)[:1000]}...\n")
                    lessons.append(lesson)
                else:
                    print(f"❌ No lesson generated for: {step_title}")
            except Exception as e:
                print(f"❌ Error generating lesson for {step_title}: {e}")
        print(f"\n================ END LESSON GENERATION ================\n")
        logger.info(f"✅ Generated {len(lessons)} lessons total")
        self.generated_lessons = lessons
        return lessons

    async def cleanup(self):
        import asyncio
        logger.info("🧹 Cleaning up test data...")
        # Properly close async clients to avoid 'Event loop is closed' warnings
        if hasattr(self, 'lesson_service') and self.lesson_service:
            try:
                await self.lesson_service.cleanup()
            except Exception as e:
                logger.warning(f"Lesson service cleanup error: {e}")
        # Add similar cleanup for other async services if needed
        if self.test_user:
            await asyncio.to_thread(User.objects.filter(email="test.pipeline@example.com").delete)
            logger.info("✅ Deleted test user and related data")
        # Close any lingering Django DB connections to avoid server-side connection issues
        try:
            from django import db
            db.connections.close_all()
            logger.debug("🔌 Closed Django DB connections")
        except Exception as e:
            logger.debug(f"⚠️ Error closing DB connections: {e}")
        
        # Cancel any remaining asyncio tasks (best-effort) to avoid Proactor transport finalizer
        try:
            current = asyncio.current_task()
            pending = [t for t in asyncio.all_tasks() if t is not current]
            if pending:
                logger.debug(f"🧯 Cancelling {len(pending)} pending asyncio tasks")
                for t in pending:
                    t.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
                # Give OS a moment to close any underlying transports
                await asyncio.sleep(0.05)
        except Exception as e:
            logger.debug(f"⚠️ Error while cancelling pending tasks: {e}")


    async def run_full_pipeline(self):
        logger.info("🚀 Starting Full User Journey Pipeline Test...")
        results = {
            'success': False,
            'user_created': False,
            'profile_created': False,
            'roadmap_generated': False,
            'lessons_generated': False,
            'errors': []
        }
        try:
            # Use sync_to_async for Django ORM calls
            self.test_user = await sync_to_async(self.create_test_user)()
            results['user_created'] = True
            self.test_profile = await sync_to_async(self.create_comprehensive_profile)(self.test_user)
            results['profile_created'] = True
            roadmap_obj, modules, lessons_by_module = await self.generate_full_roadmap_modules_lessons(self.test_profile)
            if roadmap_obj:
                results['roadmap_generated'] = True
                results['modules_generated'] = len(modules) > 0
                results['lessons_generated'] = any(len(lessons) > 0 for lessons in lessons_by_module.values())
                results['success'] = True
            else:
                results['errors'].append("Failed to generate roadmap/modules/lessons")
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            results['errors'].append(str(e))
        finally:
            await self.cleanup()
        return results

def main():
    logger.info("🧪 Starting Full User Journey Pipeline Test")
    test = FullUserJourneyPipelineTest()
    results = asyncio.run(test.run_full_pipeline())
    if results['success']:
        logger.info("🎉 Test completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Test completed with failures")
        logger.error(f"Errors: {results['errors']}")
        sys.exit(1)

if __name__ == "__main__":
    main()
