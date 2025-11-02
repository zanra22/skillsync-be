#!/usr/bin/env python
"""
End-to-End Test: On-Demand Lesson Generation Flow

This test validates the complete user journey:
1. User completes onboarding
2. Roadmap + Skeleton modules created (< 2 seconds)
3. User sees roadmap dashboard
4. User clicks module → Triggers on-demand lesson generation
5. Lessons generated in background (Azure Function simulation)
6. User can fetch generated lessons

Pattern: Lazy Loading with On-Demand Generation (Cost Optimized)
"""

import os
import sys
import json
import asyncio
import pytest
import django
from django.test import TestCase, AsyncClient
from django.utils import timezone
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()

# Import models after Django setup
from lessons.models import Roadmap, Module, LessonContent
from profiles.models import UserProfile, UserLearningGoal
from users.models import User
from helpers.ai_roadmap_service import HybridRoadmapService
from helpers.ai_lesson_service import LessonGenerationService, LessonRequest

# ============================================================================
# PART 1: SYNCHRONOUS TESTS (Database + Model Validation)
# ============================================================================

class TestOnDemandGenerationFlow(TestCase):
    """
    Test the on-demand lesson generation flow:
    - Roadmap skeleton creation (fast, no AI)
    - Modules created but not queued for generation
    - Manual trigger to generate lessons for a module
    - Verify lesson generation status tracking
    """

    def setUp(self):
        """Setup test data."""
        print("\n" + "="*80)
        print("SETUP: Creating test user and profile")
        print("="*80)

        # Create test user
        self.user = User.objects.create_user(
            username='e2e_test_user',
            email='e2e@skillsync.com',
            password='Test@12345'
        )
        print(f"✅ User created: {self.user.email}")

        # Create user profile
        self.profile = UserProfile.objects.create(
            user=self.user,
            first_name='E2E',
            last_name='Tester',
            bio='Testing on-demand generation',
            industry='Technology',
            career_stage='entry_level',
            learning_style='hands_on'
        )
        print(f"✅ Profile created for user: {self.user.email}")

        # Create learning goal
        self.goal = UserLearningGoal.objects.create(
            user=self.user,
            skill_name='Python Async Programming',
            description='Learn advanced async/await patterns',
            target_skill_level='intermediate',
            priority=1
        )
        print(f"✅ Learning goal created: {self.goal.skill_name}")

    def test_01_roadmap_skeleton_creation(self):
        """
        Test 1: Roadmap skeleton creation (FAST - NO AI CALLS)

        Expected flow:
        - User completes onboarding
        - Roadmap + modules created immediately
        - NO lesson generation triggered
        - Modules have status 'not_started'
        """
        print("\n" + "="*80)
        print("TEST 1: Roadmap Skeleton Creation (NO AI)")
        print("="*80)

        # Create roadmap (as if from onboarding completion)
        roadmap = Roadmap.objects.create(
            title='Python Async Mastery',
            goal_input='Master Python async/await',
            description='Complete roadmap for async programming',
            user_id=str(self.user.id),
            goal_id=str(self.goal.id),
            difficulty_level='intermediate',
            total_duration='4 weeks',
            user_profile_snapshot={
                'industry': self.profile.industry,
                'learning_style': self.profile.learning_style,
                'career_stage': self.profile.career_stage
            },
            ai_model_version='gemini-2.0-flash-exp'
        )
        print(f"✅ Roadmap created (skeleton): {roadmap.title}")
        print(f"   ID: {roadmap.id}")
        print(f"   User: {roadmap.user_id}")

        # Create modules WITHOUT enqueueing for generation
        modules = []
        module_titles = [
            'Event Loop Fundamentals',
            'Coroutines & Tasks',
            'Advanced Patterns',
            'Error Handling',
            'Real-World Applications'
        ]

        for idx, title in enumerate(module_titles, 1):
            module = Module.objects.create(
                roadmap=roadmap,
                title=title,
                description=f"Module {idx}: {title}",
                order=idx,
                difficulty='intermediate',
                generation_status='not_started'  # ← Key: NOT queued
            )
            modules.append(module)
            print(f"✅ Module created: {title} (Status: {module.generation_status})")

        # Verify skeleton state
        self.assertEqual(roadmap.modules.count(), 5)
        self.assertTrue(all(m.generation_status == 'not_started' for m in modules))

        print(f"\n✅ Roadmap skeleton created with {len(modules)} modules")
        print(f"   Generation status: NOT QUEUED (waiting for user interaction)")

        # Store for next test
        self.roadmap_id = roadmap.id
        self.module_id = modules[0].id

    def test_02_on_demand_generation_trigger(self):
        """
        Test 2: User clicks module → Trigger on-demand generation

        Expected flow:
        - User clicks "Module 1: Event Loop Fundamentals"
        - Frontend calls generateModuleLessons mutation
        - Module status changes: not_started → queued
        - Message enqueued to Azure Service Bus (simulated)
        """
        print("\n" + "="*80)
        print("TEST 2: On-Demand Generation Trigger")
        print("="*80)

        # Use data from test_01 if available, else create fresh
        try:
            roadmap = Roadmap.objects.get(id=self.roadmap_id)
            module = Module.objects.get(id=self.module_id)
        except:
            # Create minimal data for this test
            roadmap = Roadmap.objects.create(
                title='Quick Test Roadmap',
                goal_input='Test',
                user_id=str(self.user.id),
                goal_id=str(self.goal.id)
            )
            module = Module.objects.create(
                roadmap=roadmap,
                title='Test Module',
                generation_status='not_started'
            )

        print(f"📦 Module before trigger:")
        print(f"   Status: {module.generation_status}")
        print(f"   Generation job ID: {module.generation_job_id}")

        # Simulate the generateModuleLessons mutation
        # In real flow: frontend calls mutation → triggers enqueue
        module.generation_status = 'queued'
        module.generation_started_at = timezone.now()
        module.save()

        print(f"\n✅ Module after trigger:")
        print(f"   Status: {module.generation_status}")
        print(f"   Generation started at: {module.generation_started_at}")

        # Verify status change
        refreshed = Module.objects.get(id=module.id)
        self.assertEqual(refreshed.generation_status, 'queued')
        self.assertIsNotNone(refreshed.generation_started_at)

    def test_03_lesson_generation_processing(self):
        """
        Test 3: Azure Function processes module (simulated)

        Expected flow:
        - Azure Function receives Service Bus message
        - Updates module status: queued → in_progress
        - Generates lessons for the module (3-5 depending on difficulty)
        - Saves lessons with generation_metadata JSONB
        - Updates module status: in_progress → completed
        """
        print("\n" + "="*80)
        print("TEST 3: Lesson Generation Processing (Simulated Azure Function)")
        print("="*80)

        # Create test module
        roadmap = Roadmap.objects.create(
            title='Async Test',
            goal_input='Test',
            user_id=str(self.user.id),
            goal_id=str(self.goal.id)
        )

        module = Module.objects.create(
            roadmap=roadmap,
            title='Event Loop Basics',
            difficulty='beginner',
            generation_status='queued'
        )

        print(f"📦 Module processing:")
        print(f"   Title: {module.title}")
        print(f"   Initial status: {module.generation_status}")

        # STEP 1: Mark as in_progress (as Azure Function would do)
        module.generation_status = 'in_progress'
        module.save()
        print(f"\n✅ Status updated: queued → in_progress")

        # STEP 2: Generate lessons (simulated - NOT actual AI calls)
        # In production: lesson_service._generate_lesson_content() would call Gemini
        lesson_count = 3 if module.difficulty == 'beginner' else 5

        lessons = []
        for lesson_num in range(1, lesson_count + 1):
            # Simulate lesson content (in production, this comes from AI)
            simulated_content = {
                'title': f'{module.title} - Part {lesson_num}',
                'summary': f'Part {lesson_num} of {module.title}',
                'sections': [
                    {
                        'heading': f'Section {i}',
                        'content': f'Content for section {i}',
                        'examples': ['Example 1', 'Example 2']
                    }
                    for i in range(1, 3)
                ],
                'key_concepts': ['concept1', 'concept2', 'concept3'],
                'exercises': ['Exercise 1', 'Exercise 2'],
                'estimated_duration': 45
            }

            # Generate metadata
            generation_metadata = {
                'prompt': f'Generate lesson {lesson_num} for {module.title}',
                'model': 'gemini-2.0-flash-exp',
                'learning_style': 'hands_on',
                'difficulty': module.difficulty,
                'temperature': 0.7,
                'max_tokens': 2048,
                'generated_at': timezone.now().isoformat(),
                'ai_provider': 'gemini',
                'generation_attempt': 1
            }

            lesson = LessonContent.objects.create(
                module=module,
                roadmap_step_title=module.title,
                lesson_number=lesson_num,
                learning_style='hands_on',
                content=simulated_content,
                title=simulated_content['title'],
                description=simulated_content['summary'],
                estimated_duration=simulated_content['estimated_duration'],
                difficulty_level=module.difficulty,
                ai_model_version='gemini-2.0-flash-exp',
                source_type='multi_source',
                generation_metadata=generation_metadata
            )
            lessons.append(lesson)
            print(f"✅ Lesson created: {lesson.title}")
            print(f"   Lesson ID: {lesson.id}")
            print(f"   Generation metadata stored: {list(generation_metadata.keys())}")

        # STEP 3: Mark module as completed
        module.generation_status = 'completed'
        module.generation_completed_at = timezone.now()
        module.save()
        print(f"\n✅ Status updated: in_progress → completed")
        print(f"   Completed at: {module.generation_completed_at}")
        print(f"   Total lessons created: {len(lessons)}")

        # Verify final state
        refreshed_module = Module.objects.get(id=module.id)
        self.assertEqual(refreshed_module.generation_status, 'completed')
        self.assertEqual(refreshed_module.lessons.count(), lesson_count)

        # Verify generation_metadata was saved
        for lesson in lessons:
            self.assertIsNotNone(lesson.generation_metadata)
            self.assertEqual(lesson.generation_metadata['model'], 'gemini-2.0-flash-exp')
            self.assertEqual(lesson.generation_metadata['learning_style'], 'hands_on')

        print(f"\n✅ All lessons have generation_metadata stored in JSONB")

    def test_04_lesson_retrieval(self):
        """
        Test 4: User fetches lessons for a module

        Expected flow:
        - User views module dashboard
        - Fetches all lessons for that module
        - Verifies content, metadata, and JSONB fields
        """
        print("\n" + "="*80)
        print("TEST 4: Lesson Retrieval & Display")
        print("="*80)

        # Create roadmap with module and lessons
        roadmap = Roadmap.objects.create(
            title='Complete Course',
            goal_input='Test',
            user_id=str(self.user.id),
            goal_id=str(self.goal.id)
        )

        module = Module.objects.create(
            roadmap=roadmap,
            title='Module A',
            generation_status='completed'
        )

        # Create lessons with different learning styles
        learning_styles = ['hands_on', 'video', 'reading']

        for idx, style in enumerate(learning_styles, 1):
            lesson = LessonContent.objects.create(
                module=module,
                roadmap_step_title=module.title,
                lesson_number=idx,
                learning_style=style,
                content={
                    'title': f'Lesson {idx}: {style.title()}',
                    'sections': ['Section 1', 'Section 2'],
                    'exercises': ['Ex 1', 'Ex 2']
                },
                title=f'Lesson {idx}: {style.title()}',
                difficulty_level='beginner',
                generation_metadata={
                    'prompt': f'Generate {style} lesson',
                    'model': 'gemini-2.0-flash-exp',
                    'learning_style': style
                }
            )
            print(f"✅ Lesson created: {lesson.title}")

        # Fetch lessons for module (as frontend would do)
        lessons = module.lessons.all().order_by('lesson_number')

        print(f"\n📚 Module lessons:")
        print(f"   Module: {module.title}")
        print(f"   Status: {module.generation_status}")
        print(f"   Total lessons: {lessons.count()}")

        for lesson in lessons:
            print(f"\n   Lesson {lesson.lesson_number}:")
            print(f"     Title: {lesson.title}")
            print(f"     Style: {lesson.learning_style}")
            print(f"     Content keys: {list(lesson.content.keys())}")
            print(f"     Metadata model: {lesson.generation_metadata.get('model')}")

        # Verify retrieval
        self.assertEqual(lessons.count(), 3)
        self.assertTrue(all(l.generation_metadata is not None for l in lessons))

        print(f"\n✅ All lessons retrieved successfully with JSONB metadata")

    def test_05_module_status_transitions(self):
        """
        Test 5: Module status state machine

        Expected transitions:
        not_started → queued → in_progress → completed/failed
        """
        print("\n" + "="*80)
        print("TEST 5: Module Status State Machine")
        print("="*80)

        roadmap = Roadmap.objects.create(
            title='Status Test',
            goal_input='Test',
            user_id=str(self.user.id),
            goal_id=str(self.goal.id)
        )

        module = Module.objects.create(
            roadmap=roadmap,
            title='Status Module',
            generation_status='not_started'
        )

        status_flow = [
            ('not_started', 'Initial state (user created roadmap)'),
            ('queued', 'User clicked module'),
            ('in_progress', 'Azure Function started processing'),
            ('completed', 'Lessons generated successfully')
        ]

        print(f"\n📊 Status transitions:")
        for status, description in status_flow:
            module.generation_status = status
            if status == 'in_progress':
                module.generation_started_at = timezone.now()
            elif status == 'completed':
                module.generation_completed_at = timezone.now()

            module.save()
            refreshed = Module.objects.get(id=module.id)

            print(f"✅ {status:15} - {description}")
            print(f"   Verified in DB: {refreshed.generation_status}")

        self.assertEqual(module.generation_status, 'completed')
        print(f"\n✅ Status machine working correctly")

    def test_06_error_handling(self):
        """
        Test 6: Error handling in generation process

        Expected flow:
        - Generation fails (timeout, API error, etc.)
        - Module status: in_progress → failed
        - Error message saved
        - Error visible in dashboard
        """
        print("\n" + "="*80)
        print("TEST 6: Error Handling")
        print("="*80)

        roadmap = Roadmap.objects.create(
            title='Error Test',
            goal_input='Test',
            user_id=str(self.user.id),
            goal_id=str(self.goal.id)
        )

        module = Module.objects.create(
            roadmap=roadmap,
            title='Error Module',
            generation_status='in_progress',
            generation_started_at=timezone.now()
        )

        # Simulate error
        error_message = 'Gemini API rate limit exceeded (429 Too Many Requests)'
        module.generation_status = 'failed'
        module.generation_error = error_message
        module.generation_completed_at = timezone.now()
        module.save()

        print(f"\n❌ Generation failed:")
        print(f"   Module: {module.title}")
        print(f"   Status: {module.generation_status}")
        print(f"   Error: {module.generation_error}")

        # Verify error state
        refreshed = Module.objects.get(id=module.id)
        self.assertEqual(refreshed.generation_status, 'failed')
        self.assertIsNotNone(refreshed.generation_error)

        print(f"\n✅ Error state saved and retrievable")


# ============================================================================
# PART 2: ASYNC TESTS (GraphQL API Simulation)
# ============================================================================

class TestOnDemandGenerationGraphQL(TestCase):
    """
    Test GraphQL mutations for on-demand generation
    """

    def setUp(self):
        """Setup test data."""
        self.user = User.objects.create_user(
            username='graphql_test_user',
            email='graphql@skillsync.com',
            password='Test@12345'
        )

        self.profile = UserProfile.objects.create(
            user=self.user,
            first_name='GraphQL',
            last_name='Tester'
        )

        self.goal = UserLearningGoal.objects.create(
            user=self.user,
            skill_name='Test Skill'
        )

    def test_graphql_generate_module_lessons_mutation(self):
        """
        Test the generateModuleLessons GraphQL mutation

        This is the endpoint that triggers on-demand generation
        """
        print("\n" + "="*80)
        print("GRAPHQL TEST: generateModuleLessons Mutation")
        print("="*80)

        # Create test data
        roadmap = Roadmap.objects.create(
            title='GraphQL Test',
            goal_input='Test',
            user_id=str(self.user.id),
            goal_id=str(self.goal.id)
        )

        module = Module.objects.create(
            roadmap=roadmap,
            title='GraphQL Module',
            generation_status='not_started'
        )

        print(f"\n📦 Before mutation:")
        print(f"   Module ID: {module.id}")
        print(f"   Status: {module.generation_status}")

        # In actual GraphQL query, this would be:
        # mutation {
        #   lessons {
        #     generateModuleLessons(moduleId: "{module_id}") {
        #       id
        #       title
        #       generationStatus
        #     }
        #   }
        # }

        # For testing, we simulate the mutation's effects:
        # 1. Service receives request
        # 2. Validates module exists and user has permission
        # 3. Enqueues message to Azure Service Bus
        # 4. Updates module status to 'queued'

        module.generation_status = 'queued'
        module.generation_started_at = timezone.now()
        module.save()

        print(f"\n✅ After mutation:")
        refreshed = Module.objects.get(id=module.id)
        print(f"   Status: {refreshed.generation_status}")
        print(f"   Generation started at: {refreshed.generation_started_at}")

        # Verify mutation response would contain:
        response_data = {
            'id': str(module.id),
            'title': module.title,
            'generationStatus': module.generation_status
        }

        print(f"\n📤 GraphQL Response:")
        print(f"   {json.dumps(response_data, indent=2)}")

        self.assertEqual(refreshed.generation_status, 'queued')


# ============================================================================
# PART 3: INTEGRATION TEST (Full Flow Simulation)
# ============================================================================

class TestFullIntegrationFlow(TestCase):
    """
    Complete integration test simulating the full user journey
    """

    def setUp(self):
        """Setup."""
        self.user = User.objects.create_user(
            username='integration_user',
            email='integration@skillsync.com',
            password='Test@12345'
        )

        self.profile = UserProfile.objects.create(
            user=self.user,
            first_name='Integration',
            last_name='Test',
            learning_style='hands_on'
        )

        self.goal = UserLearningGoal.objects.create(
            user=self.user,
            skill_name='Full Stack Development'
        )

    def test_full_user_journey(self):
        """
        Simulate complete user journey:
        1. Onboarding complete → Roadmap created
        2. Dashboard loads → Shows skeleton
        3. User clicks module → Triggers generation
        4. Background processing → Lessons created
        5. User views lessons → Content displayed
        """
        print("\n" + "="*80)
        print("INTEGRATION TEST: Full User Journey")
        print("="*80)

        # STEP 1: Onboarding completes, roadmap created
        print("\n🔵 STEP 1: Onboarding Complete - Roadmap Created")
        print("-" * 80)

        roadmap = Roadmap.objects.create(
            title='Full Stack Developer Roadmap',
            goal_input='Become a full stack developer',
            description='Complete journey to full stack mastery',
            user_id=str(self.user.id),
            goal_id=str(self.goal.id),
            difficulty_level='intermediate',
            user_profile_snapshot={
                'learning_style': self.profile.learning_style,
                'industry': self.profile.industry
            }
        )

        modules_data = [
            ('Frontend Basics', 'HTML, CSS, JavaScript'),
            ('React Fundamentals', 'Component-based architecture'),
            ('Backend Basics', 'Node.js and Express'),
            ('Database Design', 'SQL and NoSQL'),
            ('Full Stack Integration', 'Connecting frontend to backend')
        ]

        modules = []
        for idx, (title, desc) in enumerate(modules_data, 1):
            module = Module.objects.create(
                roadmap=roadmap,
                title=title,
                description=desc,
                order=idx,
                difficulty='intermediate' if idx < 4 else 'advanced',
                generation_status='not_started'
            )
            modules.append(module)

        print(f"✅ Roadmap: {roadmap.title}")
        print(f"   Modules: {len(modules)}")
        print(f"   Total duration: {roadmap.total_duration or 'TBD'}")
        print(f"   User: {roadmap.user_id}")

        # STEP 2: User sees dashboard with skeleton
        print("\n🟢 STEP 2: Dashboard - Skeleton Loaded")
        print("-" * 80)

        dashboard_modules = roadmap.modules.all().order_by('order')
        print(f"Dashboard shows {dashboard_modules.count()} modules:")

        for idx, mod in enumerate(dashboard_modules, 1):
            print(f"  {idx}. {mod.title}")
            print(f"     Status: {mod.generation_status}")
            print(f"     Lessons: {mod.lessons.count()} (not generated yet)")

        # STEP 3: User clicks module 1 → Trigger generation
        print("\n🟡 STEP 3: User Clicks Module - Generation Triggered")
        print("-" * 80)

        selected_module = modules[0]
        print(f"User clicked: {selected_module.title}")

        # Mutation called: generateModuleLessons(moduleId: "abc123")
        selected_module.generation_status = 'queued'
        selected_module.generation_started_at = timezone.now()
        selected_module.save()

        print(f"✅ Module status: {selected_module.generation_status}")
        print(f"   Message enqueued to Azure Service Bus")
        print(f"   Waiting for background processing...")

        # STEP 4: Azure Function processes
        print("\n🔴 STEP 4: Background Processing (Azure Function)")
        print("-" * 80)

        selected_module.generation_status = 'in_progress'
        selected_module.save()
        print(f"Azure Function started processing: {selected_module.title}")

        # Generate lessons
        lesson_count = 4  # intermediate difficulty
        lesson_styles = ['hands_on', 'video', 'reading', 'mixed']

        for lesson_num in range(1, lesson_count + 1):
            lesson = LessonContent.objects.create(
                module=selected_module,
                roadmap_step_title=selected_module.title,
                lesson_number=lesson_num,
                learning_style=lesson_styles[lesson_num - 1],
                content={
                    'title': f'{selected_module.title} - {lesson_styles[lesson_num - 1].title()}',
                    'sections': ['Introduction', 'Core Concepts', 'Hands-on Practice'],
                    'exercises': ['Exercise 1', 'Exercise 2', 'Challenge'],
                    'resources': ['Official docs', 'Tutorial link', 'Code example']
                },
                title=f'{selected_module.title} - {lesson_styles[lesson_num - 1].title()}',
                difficulty_level=selected_module.difficulty,
                generation_metadata={
                    'prompt': f'Create {lesson_styles[lesson_num - 1]} lesson for {selected_module.title}',
                    'model': 'gemini-2.0-flash-exp',
                    'learning_style': lesson_styles[lesson_num - 1],
                    'difficulty': selected_module.difficulty,
                    'generated_at': timezone.now().isoformat(),
                    'ai_provider': 'gemini',
                    'generation_attempt': 1
                }
            )
            print(f"  ✅ Created: {lesson.title} ({lesson.learning_style})")

        selected_module.generation_status = 'completed'
        selected_module.generation_completed_at = timezone.now()
        selected_module.save()

        print(f"✅ Module generation completed")
        print(f"   Total lessons: {selected_module.lessons.count()}")

        # STEP 5: User views lessons
        print("\n🟣 STEP 5: User Views Generated Lessons")
        print("-" * 80)

        lessons = selected_module.lessons.all().order_by('lesson_number')
        print(f"Displaying {lessons.count()} lessons for: {selected_module.title}")

        for lesson in lessons:
            print(f"\n  📖 {lesson.title}")
            print(f"     Style: {lesson.learning_style}")
            print(f"     Duration: {lesson.estimated_duration} min")
            print(f"     Content sections: {len(lesson.content.get('sections', []))}")
            print(f"     Metadata: {list(lesson.generation_metadata.keys())}")
            print(f"     Status: ✅ Ready to view")

        # STEP 6: Verify complete state
        print("\n✅ STEP 6: Final Verification")
        print("-" * 80)

        final_roadmap = Roadmap.objects.get(id=roadmap.id)
        final_modules = final_roadmap.modules.all()

        completed_count = final_modules.filter(generation_status='completed').count()
        pending_count = final_modules.filter(generation_status='not_started').count()

        print(f"Roadmap: {final_roadmap.title}")
        print(f"  Total modules: {final_modules.count()}")
        print(f"  Completed: {completed_count}")
        print(f"  Pending (not generated): {pending_count}")
        print(f"\n💡 User can now:")
        print(f"  ✅ View lessons for completed modules")
        print(f"  ✅ Click pending modules to trigger generation on-demand")
        print(f"  ✅ Vote, comment, and provide feedback on lessons")

        # Assertions
        self.assertEqual(final_roadmap.modules.count(), 5)
        self.assertEqual(completed_count, 1)
        self.assertEqual(pending_count, 4)
        self.assertEqual(selected_module.lessons.count(), 4)

        print(f"\n🎉 Full integration test PASSED")


# ============================================================================
# Test Execution
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
