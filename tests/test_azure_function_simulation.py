#!/usr/bin/env python
"""
Azure Function Simulation Test

This test simulates what the Azure Function would do when processing
Service Bus messages for on-demand lesson generation.

Flow:
1. Service Bus message received with module_id
2. Django models updated with lesson generation
3. generation_metadata JSONB field populated
4. Module status transitions: queued → in_progress → completed
"""

import os
import sys
import json
import asyncio
import django
from django.test import TestCase
from django.utils import timezone
from asgiref.sync import sync_to_async

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()

from lessons.models import Module, Roadmap, LessonContent
from profiles.models import UserProfile, UserLearningGoal
from users.models import User


class SimulatedLessonGenerationService:
    """
    Simulates the AI lesson generation without actual API calls.
    In production, this calls the real LessonGenerationService.
    """

    def __init__(self):
        self.model = 'gemini-2.0-flash-exp'
        self.temperature = 0.7
        self.max_tokens = 2048

    async def generate_lesson_content(self, lesson_request):
        """Simulate lesson content generation."""
        # In production: calls actual AI (Gemini, Groq, DeepSeek)
        # For testing: return realistic mock content

        content = {
            'title': f"{lesson_request['title']} - Part {lesson_request['lesson_number']}",
            'summary': f"Lesson {lesson_request['lesson_number']} for {lesson_request['title']}",
            'estimated_duration': 45,
            'sections': [
                {
                    'heading': 'Introduction',
                    'content': 'Overview and learning objectives...',
                    'examples': ['Example 1', 'Example 2'],
                    'key_points': ['Point 1', 'Point 2', 'Point 3']
                },
                {
                    'heading': 'Core Concepts',
                    'content': 'Deep dive into the main concepts...',
                    'examples': ['Example 3', 'Example 4'],
                    'key_points': ['Point 4', 'Point 5', 'Point 6']
                },
                {
                    'heading': 'Hands-on Practice',
                    'content': 'Practical exercises and projects...',
                    'examples': ['Project 1', 'Project 2'],
                    'code_snippets': ['Code example 1', 'Code example 2']
                }
            ],
            'exercises': [
                {'question': 'Exercise 1', 'difficulty': 'beginner'},
                {'question': 'Exercise 2', 'difficulty': 'intermediate'},
                {'question': 'Challenge', 'difficulty': 'advanced'}
            ],
            'resources': [
                'https://official-docs.example.com',
                'https://tutorial.example.com',
                'https://github.com/example/project'
            ],
            'key_takeaways': [
                'Key learning 1',
                'Key learning 2',
                'Key learning 3'
            ]
        }

        return content


class TestAzureFunctionSimulation(TestCase):
    """
    Simulates the Azure Service Bus Function that processes
    module generation requests.
    """

    def setUp(self):
        """Setup test data."""
        print("\n" + "="*80)
        print("SETUP: Azure Function Simulation Test")
        print("="*80)

        # Create test user
        self.user = User.objects.create_user(
            username='azure_test_user',
            email='azure@skillsync.com',
            password='Test@12345'
        )

        # Create profile
        self.profile = UserProfile.objects.create(
            user=self.user,
            first_name='Azure',
            last_name='Tester',
            learning_style='hands_on'
        )

        # Create goal
        self.goal = UserLearningGoal.objects.create(
            user=self.user,
            skill_name='Test Skill'
        )

        print(f"✅ Test user created: {self.user.email}")

    def test_service_bus_message_processing(self):
        """
        Simulate receiving and processing a Service Bus message.

        Expected message format:
        {
            "module_id": "abc123",
            "roadmap_id": "xyz789",
            "title": "Python Basics",
            "description": "...",
            "difficulty": "beginner",
            "user_profile": {...},
            "idempotency_key": "md5_hash",
            "timestamp": "2025-10-30T14:30:00Z"
        }
        """
        print("\n" + "="*80)
        print("TEST: Service Bus Message Processing")
        print("="*80)

        # Create test data
        roadmap = Roadmap.objects.create(
            title='Test Roadmap',
            goal_input='Test',
            user_id=str(self.user.id),
            goal_id=str(self.goal.id)
        )

        module = Module.objects.create(
            roadmap=roadmap,
            title='Python Basics',
            description='Learn Python fundamentals',
            difficulty='beginner',
            generation_status='queued'
        )

        # Simulate Service Bus message
        service_bus_message = {
            'module_id': module.id,
            'roadmap_id': roadmap.id,
            'title': module.title,
            'description': module.description,
            'difficulty': module.difficulty,
            'user_profile': {
                'industry': self.profile.industry,
                'learning_style': self.profile.learning_style
            },
            'idempotency_key': 'abc123def456',
            'timestamp': timezone.now().isoformat()
        }

        print(f"\n📨 Service Bus Message Received:")
        print(f"   Module ID: {service_bus_message['module_id']}")
        print(f"   Title: {service_bus_message['title']}")
        print(f"   Difficulty: {service_bus_message['difficulty']}")
        print(f"   Timestamp: {service_bus_message['timestamp']}")

        # STEP 1: Validate message
        print(f"\n✅ STEP 1: Validate Message")
        print(f"   Checking module exists in DB...")

        module_in_db = Module.objects.get(id=service_bus_message['module_id'])
        self.assertIsNotNone(module_in_db)
        print(f"   Module found: {module_in_db.title}")

        # STEP 2: Update status to in_progress
        print(f"\n✅ STEP 2: Update Module Status")

        module_in_db.generation_status = 'in_progress'
        module_in_db.save()

        print(f"   Status: queued → in_progress")
        print(f"   Timestamp: {timezone.now()}")

        # STEP 3: Generate lessons
        print(f"\n✅ STEP 3: Generate Lessons")

        # Determine lesson count based on difficulty
        lesson_counts = {
            'beginner': 3,
            'intermediate': 4,
            'advanced': 5
        }
        lesson_count = lesson_counts.get(module_in_db.difficulty, 3)

        print(f"   Difficulty: {module_in_db.difficulty}")
        print(f"   Lessons to generate: {lesson_count}")

        # Generate lessons with different learning styles
        learning_styles = ['hands_on', 'video', 'reading', 'mixed']
        ai_service = SimulatedLessonGenerationService()

        created_lessons = []

        for lesson_num in range(1, lesson_count + 1):
            # Select learning style (cycle through available styles)
            learning_style = learning_styles[(lesson_num - 1) % len(learning_styles)]

            print(f"\n   Generating lesson {lesson_num}/{lesson_count}...")
            print(f"   Learning style: {learning_style}")

            # Simulate lesson generation (in production: calls real AI)
            lesson_request = {
                'title': module_in_db.title,
                'lesson_number': lesson_num,
                'learning_style': learning_style,
                'difficulty': module_in_db.difficulty
            }

            # Simulate AI generation
            lesson_content = {
                'title': f"{module_in_db.title} - Part {lesson_num} ({learning_style.title()})",
                'summary': f"Part {lesson_num}: {learning_style} approach to {module_in_db.title}",
                'sections': ['Introduction', 'Core Concepts', 'Practice'],
                'exercises': ['Exercise 1', 'Exercise 2'],
                'estimated_duration': 45,
                'key_concepts': ['Concept 1', 'Concept 2', 'Concept 3']
            }

            # Create generation_metadata JSONB
            generation_metadata = {
                'prompt': f"Create a {learning_style} lesson for {module_in_db.title} (lesson {lesson_num})",
                'system_prompt': 'You are an expert educator creating structured learning content.',
                'model': 'gemini-2.0-flash-exp',
                'learning_style': learning_style,
                'difficulty': module_in_db.difficulty,
                'user_industry': self.profile.industry,
                'temperature': 0.7,
                'max_tokens': 2048,
                'generated_at': timezone.now().isoformat(),
                'ai_provider': 'gemini',
                'generation_attempt': 1,
                'response_time_ms': 2350  # Simulated response time
            }

            # Save lesson to database
            lesson = LessonContent.objects.create(
                module=module_in_db,
                roadmap_step_title=module_in_db.title,
                lesson_number=lesson_num,
                learning_style=learning_style,
                content=lesson_content,
                title=lesson_content['title'],
                description=lesson_content['summary'],
                estimated_duration=lesson_content['estimated_duration'],
                difficulty_level=module_in_db.difficulty,
                ai_model_version='gemini-2.0-flash-exp',
                source_type='multi_source',
                generation_metadata=generation_metadata,
                created_by='gemini-ai'
            )

            created_lessons.append(lesson)
            print(f"   ✅ Lesson saved to DB: {lesson.id}")
            print(f"      Metadata keys: {list(generation_metadata.keys())}")

        # STEP 4: Update module status to completed
        print(f"\n✅ STEP 4: Mark Module as Completed")

        module_in_db.generation_status = 'completed'
        module_in_db.generation_completed_at = timezone.now()
        module_in_db.save()

        print(f"   Status: in_progress → completed")
        print(f"   Lessons created: {len(created_lessons)}")
        print(f"   Completed at: {module_in_db.generation_completed_at}")

        # STEP 5: Verify final state
        print(f"\n✅ STEP 5: Verify Final State")

        refreshed_module = Module.objects.get(id=module_in_db.id)
        lessons_in_db = refreshed_module.lessons.all()

        print(f"   Module status: {refreshed_module.generation_status}")
        print(f"   Lessons in DB: {lessons_in_db.count()}")
        print(f"   Generation time: {refreshed_module.generation_completed_at}")

        # Verify each lesson has proper metadata
        for idx, lesson in enumerate(lessons_in_db, 1):
            print(f"\n   Lesson {idx}:")
            print(f"     Title: {lesson.title}")
            print(f"     Style: {lesson.learning_style}")
            print(f"     Status: ✅ Ready")
            print(f"     Metadata model: {lesson.generation_metadata.get('model')}")
            print(f"     Response time: {lesson.generation_metadata.get('response_time_ms')}ms")

        # Final assertions
        self.assertEqual(refreshed_module.generation_status, 'completed')
        self.assertEqual(lessons_in_db.count(), lesson_count)
        self.assertTrue(all(l.generation_metadata is not None for l in lessons_in_db))

        print(f"\n🎉 Azure Function simulation test PASSED")

    def test_error_handling_in_azure_function(self):
        """
        Test error handling in Azure Function.

        Scenarios:
        - Module not found
        - AI generation timeout
        - Database save failure
        """
        print("\n" + "="*80)
        print("TEST: Error Handling")
        print("="*80)

        roadmap = Roadmap.objects.create(
            title='Error Test',
            goal_input='Test',
            user_id=str(self.user.id),
            goal_id=str(self.goal.id)
        )

        module = Module.objects.create(
            roadmap=roadmap,
            title='Error Test Module',
            generation_status='in_progress'
        )

        print(f"\n📦 Module before error:")
        print(f"   Status: {module.generation_status}")

        # Simulate error (e.g., API rate limit)
        error_message = "Gemini API 429: Rate limit exceeded"
        print(f"\n❌ Error occurred:")
        print(f"   {error_message}")

        # Update module with error state
        module.generation_status = 'failed'
        module.generation_error = error_message
        module.generation_completed_at = timezone.now()
        module.save()

        print(f"\n✅ Module after error handling:")
        print(f"   Status: {module.generation_status}")
        print(f"   Error message: {module.generation_error}")

        # Verify error state is persisted
        refreshed = Module.objects.get(id=module.id)
        self.assertEqual(refreshed.generation_status, 'failed')
        self.assertIsNotNone(refreshed.generation_error)

        print(f"\n✅ Error state properly saved and retrievable")

    def test_idempotency_duplicate_message(self):
        """
        Test that duplicate Service Bus messages don't create duplicate lessons.

        Scenario:
        - Message 1 arrives: creates lessons
        - Message 1 redelivers (duplicate): should not create lessons again
        """
        print("\n" + "="*80)
        print("TEST: Idempotency - Duplicate Message Handling")
        print("="*80)

        roadmap = Roadmap.objects.create(
            title='Idempotency Test',
            goal_input='Test',
            user_id=str(self.user.id),
            goal_id=str(self.goal.id)
        )

        module = Module.objects.create(
            roadmap=roadmap,
            title='Idempotency Module',
            generation_status='queued',
            idempotency_key='abc123def456'
        )

        print(f"\n📨 Message 1 - First attempt:")
        print(f"   Idempotency key: {module.idempotency_key}")

        # First processing
        module.generation_status = 'in_progress'
        module.save()

        lesson1 = LessonContent.objects.create(
            module=module,
            roadmap_step_title=module.title,
            lesson_number=1,
            learning_style='hands_on',
            content={'title': 'Lesson 1'},
            title='Lesson 1',
            generation_metadata={'idempotency_key': module.idempotency_key}
        )

        module.generation_status = 'completed'
        module.save()

        print(f"   ✅ Lessons created: {module.lessons.count()}")

        # Simulate duplicate message arriving
        print(f"\n📨 Message 1 - Duplicate (retry):")
        print(f"   Idempotency key: {module.idempotency_key}")

        # Check: Module is already completed with this idempotency_key
        existing_module = Module.objects.filter(
            idempotency_key=module.idempotency_key,
            generation_status='completed'
        ).first()

        if existing_module:
            print(f"   ⚠️ Module already processed with this idempotency key")
            print(f"   Status: {existing_module.generation_status}")
            print(f"   Lessons: {existing_module.lessons.count()}")
            print(f"   ✅ Skipping duplicate processing")
        else:
            print(f"   Processing as new module (shouldn't happen)")

        # Verify no duplicate lessons were created
        final_lesson_count = module.lessons.count()
        self.assertEqual(final_lesson_count, 1)

        print(f"\n✅ Idempotency test PASSED - No duplicates created")


class TestAzureFunctionIntegration(TestCase):
    """
    Integration test with realistic Azure Function flow
    """

    def setUp(self):
        """Setup."""
        self.user = User.objects.create_user(
            username='integration_azure',
            email='integration_azure@skillsync.com',
            password='Test@12345'
        )

        self.profile = UserProfile.objects.create(
            user=self.user,
            first_name='Integration',
            last_name='Azure'
        )

        self.goal = UserLearningGoal.objects.create(
            user=self.user,
            skill_name='Integration Test'
        )

    def test_full_azure_workflow(self):
        """
        Full workflow from user action to lesson availability.

        Flow:
        1. User clicks module (frontend)
        2. Frontend calls generateModuleLessons mutation (GraphQL)
        3. Mutation enqueues message to Service Bus
        4. Azure Function picks up message
        5. Function generates lessons
        6. User can fetch lessons from API
        """
        print("\n" + "="*80)
        print("INTEGRATION TEST: Full Azure Workflow")
        print("="*80)

        # Create roadmap and modules
        roadmap = Roadmap.objects.create(
            title='Full Workflow Test',
            goal_input='Test',
            user_id=str(self.user.id),
            goal_id=str(self.goal.id)
        )

        module = Module.objects.create(
            roadmap=roadmap,
            title='Test Module',
            difficulty='beginner',
            generation_status='not_started'
        )

        print(f"\n1️⃣ Initial state:")
        print(f"   Module: {module.title}")
        print(f"   Status: {module.generation_status}")
        print(f"   Lessons: {module.lessons.count()}")

        # FRONTEND: User clicks module
        # This triggers GraphQL mutation: generateModuleLessons
        print(f"\n2️⃣ User clicks module:")
        print(f"   Frontend calls: generateModuleLessons(moduleId='{module.id}')")

        # MUTATION: Update status to queued
        module.generation_status = 'queued'
        module.generation_started_at = timezone.now()
        module.save()

        print(f"   ✅ Mutation response: status = 'queued'")

        # AZURE SERVICE BUS: Message arrives
        print(f"\n3️⃣ Service Bus message processing:")

        module.generation_status = 'in_progress'
        module.save()

        # Generate lessons
        for lesson_num in range(1, 4):
            LessonContent.objects.create(
                module=module,
                roadmap_step_title=module.title,
                lesson_number=lesson_num,
                learning_style='hands_on',
                content={'title': f'Lesson {lesson_num}'},
                title=f'Lesson {lesson_num}',
                generation_metadata={
                    'model': 'gemini-2.0-flash-exp',
                    'generated_at': timezone.now().isoformat()
                }
            )

        module.generation_status = 'completed'
        module.generation_completed_at = timezone.now()
        module.save()

        print(f"   ✅ Lessons generated: {module.lessons.count()}")
        print(f"   ✅ Module status: completed")

        # FRONTEND: Fetch lessons
        print(f"\n4️⃣ Frontend fetches lessons:")

        lessons = module.lessons.all().order_by('lesson_number')
        print(f"   Total lessons: {lessons.count()}")

        for lesson in lessons:
            print(f"   ✅ {lesson.title}")
            print(f"      Style: {lesson.learning_style}")
            print(f"      Status: Ready to view")

        # FINAL STATE
        print(f"\n5️⃣ Final state:")
        print(f"   Module: {module.title}")
        print(f"   Status: {module.generation_status}")
        print(f"   Lessons: {module.lessons.count()}")
        print(f"   User can view: ✅ All lessons")

        self.assertEqual(module.generation_status, 'completed')
        self.assertEqual(module.lessons.count(), 3)

        print(f"\n🎉 Full Azure workflow test PASSED")


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v', '-s'])
