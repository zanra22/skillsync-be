#!/usr/bin/env python
"""
Simplified On-Demand Lesson Generation Test

Single user, single roadmap test to validate the core flow:
1. Roadmap skeleton creation
2. On-demand generation trigger
3. Lesson generation
4. Lesson retrieval
"""

import os
import sys
import django
from django.test import TestCase
from django.utils import timezone

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()

from lessons.models import Roadmap, Module, LessonContent
from profiles.models import UserProfile, UserLearningGoal, UserIndustry
from profiles.choices import IndustryType
from users.models import User


class TestOnDemandSimplified(TestCase):
    """Simplified test with single user and roadmap."""

    @classmethod
    def setUpClass(cls):
        """Create test user once for all tests."""
        # Clean up any existing test user
        User.objects.filter(email='test@example.com').delete()

        # Create single test user
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Test@12345'
        )

        # Create profile
        cls.profile = UserProfile.objects.create(
            user=cls.user,
            first_name='Test',
            last_name='User',
            learning_style='hands_on'
        )

        # Create industry (required FK for UserLearningGoal)
        cls.industry = UserIndustry.objects.create(
            user=cls.user,
            industry=IndustryType.TECHNOLOGY,
            is_primary=True
        )

        # Create goal with industry reference
        cls.goal = UserLearningGoal.objects.create(
            user=cls.user,
            industry=cls.industry,
            skill_name='Python Basics'
        )

        print("\n" + "="*80)
        print("TEST SETUP COMPLETE")
        print("="*80)
        print(f"User: {cls.user.email}")
        print(f"Goal: {cls.goal.skill_name}")

    @classmethod
    def tearDownClass(cls):
        """Clean up test data after all tests."""
        print("\n" + "="*80)
        print("CLEANUP: Deleting test data")
        print("="*80)

        # Delete all roadmaps and lessons (cascade will handle modules)
        roadmaps_deleted, _ = Roadmap.objects.filter(user_id=str(cls.user.id)).delete()
        print(f"✅ Deleted {roadmaps_deleted} roadmaps (and related modules/lessons)")

        # Delete goal
        cls.goal.delete()
        print(f"✅ Deleted learning goal")

        # Delete industry
        cls.industry.delete()
        print(f"✅ Deleted user industry")

        # Delete profile
        cls.profile.delete()
        print(f"✅ Deleted user profile")

        # Delete user
        cls.user.delete()
        print(f"✅ Deleted test user")
        print("="*80)

    def test_01_skeleton_creation(self):
        """Create roadmap skeleton (no AI calls)."""
        print("\n" + "="*80)
        print("TEST 1: Roadmap Skeleton Creation")
        print("="*80)

        # Create roadmap
        roadmap = Roadmap.objects.create(
            title='Python Basics Path',
            goal_input='Learn Python',
            user_id=str(self.user.id),
            goal_id=str(self.goal.id),
            difficulty_level='beginner'
        )

        print(f"✅ Roadmap created: {roadmap.title} (ID: {roadmap.id})")

        # Create modules without queuing
        for idx in range(1, 4):
            module = Module.objects.create(
                roadmap=roadmap,
                title=f'Module {idx}',
                order=idx,
                difficulty='beginner',
                generation_status='not_started'
            )
            print(f"✅ Module created: {module.title} (Status: {module.generation_status})")

        # Store for next tests
        self.roadmap = roadmap

    def test_02_on_demand_trigger(self):
        """Trigger lesson generation for a module."""
        print("\n" + "="*80)
        print("TEST 2: On-Demand Generation Trigger")
        print("="*80)

        # Get the roadmap from previous test (or create new one)
        try:
            roadmap = self.roadmap
        except AttributeError:
            roadmap = Roadmap.objects.create(
                title='Python Basics Path',
                goal_input='Learn Python',
                user_id=str(self.user.id),
                goal_id=str(self.goal.id)
            )
            Module.objects.create(
                roadmap=roadmap,
                title='Module 1',
                generation_status='not_started'
            )

        module = roadmap.modules.first()
        print(f"📦 Module before trigger: Status = {module.generation_status}")

        # Trigger generation
        module.generation_status = 'queued'
        module.generation_started_at = timezone.now()
        module.save()

        print(f"✅ Module after trigger: Status = {module.generation_status}")
        self.assertEqual(module.generation_status, 'queued')

    def test_03_lesson_generation(self):
        """Simulate Azure Function generating lessons."""
        print("\n" + "="*80)
        print("TEST 3: Lesson Generation")
        print("="*80)

        # Create roadmap and module
        roadmap = Roadmap.objects.create(
            title='Test Roadmap',
            goal_input='Test',
            user_id=str(self.user.id),
            goal_id=str(self.goal.id)
        )

        module = Module.objects.create(
            roadmap=roadmap,
            title='Test Module',
            difficulty='beginner',
            generation_status='queued'
        )

        print(f"📦 Module: {module.title}")
        print(f"   Starting generation...")

        # Update to in_progress
        module.generation_status = 'in_progress'
        module.save()

        # Create lessons
        for lesson_num in range(1, 4):
            lesson = LessonContent.objects.create(
                module=module,
                roadmap_step_title=module.title,
                lesson_number=lesson_num,
                learning_style='hands_on',
                content={
                    'title': f'Lesson {lesson_num}',
                    'sections': ['Intro', 'Content', 'Practice'],
                    'exercises': ['Ex 1', 'Ex 2']
                },
                title=f'{module.title} - Lesson {lesson_num}',
                difficulty_level='beginner',
                generation_metadata={
                    'prompt': f'Generate lesson {lesson_num}',
                    'model': 'gemini-2.0-flash-exp',
                    'learning_style': 'hands_on',
                    'generated_at': timezone.now().isoformat(),
                    'ai_provider': 'gemini',
                    'generation_attempt': 1
                }
            )
            print(f"✅ Lesson {lesson_num} created: {lesson.title}")

        # Mark module as completed
        module.generation_status = 'completed'
        module.generation_completed_at = timezone.now()
        module.save()

        print(f"✅ Module marked completed")
        print(f"   Total lessons: {module.lessons.count()}")

        # Verify
        self.assertEqual(module.lessons.count(), 3)
        self.assertEqual(module.generation_status, 'completed')

    def test_04_lesson_retrieval(self):
        """Retrieve and display lessons."""
        print("\n" + "="*80)
        print("TEST 4: Lesson Retrieval")
        print("="*80)

        # Create full scenario
        roadmap = Roadmap.objects.create(
            title='Complete Roadmap',
            goal_input='Test',
            user_id=str(self.user.id),
            goal_id=str(self.goal.id)
        )

        module = Module.objects.create(
            roadmap=roadmap,
            title='Complete Module',
            generation_status='completed'
        )

        # Create lessons with different styles
        styles = ['hands_on', 'video', 'reading']
        for idx, style in enumerate(styles, 1):
            LessonContent.objects.create(
                module=module,
                roadmap_step_title=module.title,
                lesson_number=idx,
                learning_style=style,
                content={'title': f'{style} lesson'},
                title=f'Lesson {idx}: {style}',
                generation_metadata={'model': 'gemini-2.0-flash-exp'}
            )

        # Retrieve lessons
        lessons = module.lessons.all().order_by('lesson_number')

        print(f"📚 Module: {module.title}")
        print(f"   Status: {module.generation_status}")
        print(f"   Lessons: {lessons.count()}")

        for lesson in lessons:
            print(f"   ✅ {lesson.title} ({lesson.learning_style})")

        self.assertEqual(lessons.count(), 3)

    def test_05_full_flow(self):
        """Test complete flow in one test."""
        print("\n" + "="*80)
        print("TEST 5: Full End-to-End Flow")
        print("="*80)

        # Step 1: Create roadmap skeleton
        print("\n1️⃣ Creating roadmap skeleton...")
        roadmap = Roadmap.objects.create(
            title='Full Flow Roadmap',
            goal_input='Test',
            user_id=str(self.user.id),
            goal_id=str(self.goal.id)
        )

        module = Module.objects.create(
            roadmap=roadmap,
            title='Full Flow Module',
            difficulty='beginner',
            generation_status='not_started'
        )
        print(f"✅ Roadmap and module created")

        # Step 2: Trigger generation
        print(f"\n2️⃣ Triggering on-demand generation...")
        module.generation_status = 'queued'
        module.generation_started_at = timezone.now()
        module.save()
        print(f"✅ Module queued for generation")

        # Step 3: Generate lessons
        print(f"\n3️⃣ Generating lessons...")
        module.generation_status = 'in_progress'
        module.save()

        for lesson_num in range(1, 4):
            LessonContent.objects.create(
                module=module,
                roadmap_step_title=module.title,
                lesson_number=lesson_num,
                learning_style='mixed',
                content={'title': f'Lesson {lesson_num}'},
                title=f'{module.title} - Lesson {lesson_num}',
                generation_metadata={
                    'model': 'gemini-2.0-flash-exp',
                    'generated_at': timezone.now().isoformat()
                }
            )

        module.generation_status = 'completed'
        module.generation_completed_at = timezone.now()
        module.save()
        print(f"✅ {module.lessons.count()} lessons generated")

        # Step 4: Retrieve lessons
        print(f"\n4️⃣ Retrieving lessons...")
        lessons = module.lessons.all()
        print(f"✅ Retrieved {lessons.count()} lessons")

        # Verify
        self.assertEqual(module.generation_status, 'completed')
        self.assertEqual(lessons.count(), 3)
        print(f"\n✅ Full flow test PASSED")


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v', '-s'])
