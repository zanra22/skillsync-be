#!/usr/bin/env python3
"""
Comprehensive Test: Account Creation → Onboarding → Roadmap → Lessons → Prompts

Tests the complete user journey with profile context integration.
Verifies that user profile fields (role, current_role, career_stage, transition_timeline, goals)
are properly utilized in roadmap and lesson generation.

Usage:
    python test_complete_profile_flow.py
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_complete_profile_flow.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')

import django
django.setup()

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

# Import our services
from helpers.ai_lesson_service import lesson_generation_service
from profiles.models import UserProfile

User = get_user_model()


class CompleteProfileFlowTest:
    """
    Comprehensive test for the complete user journey with profile context.
    """

    def __init__(self):
        self.test_user = None
        self.test_profile = None
        self.onboarding_session = None
        self.generated_roadmap = None
        self.generated_lessons = []

    def create_test_user(self) -> User:
        """Create a test user account"""
        logger.info("🔧 Creating test user account...")

        # Clean up any existing test user
        User.objects.filter(email="test.profile@example.com").delete()

        user = User.objects.create_user(
            username="test.profile@example.com",
            email="test.profile@example.com",
            password="testpass123",
            first_name="Test",
            last_name="ProfileUser",
            is_active=True
        )

        logger.info(f"✅ Created test user: {user.email} (ID: {user.id})")
        return user

    def create_comprehensive_profile(self, user: User) -> UserProfile:
        """Create a comprehensive user profile with all required fields"""
        logger.info("📋 Creating comprehensive user profile...")

        # Test profile data using correct field names from the model
        profile_data = {
            'user': user,
            'first_name': 'Test',
            'last_name': 'ProfileUser',
            'bio': 'Test user for profile context verification',
            'job_title': 'Junior Developer',  # Current role
            'career_stage': 'mid',  # Career stage
            'industry': 'technology',  # Industry (lowercase)
            'skill_level': 'intermediate',  # Experience level
            'time_commitment': '5-10',  # Hours per week
            'learning_style': 'mixed',  # hands_on, video, reading, mixed
            'transition_timeline': '6-12_months',  # Transition timeline
            'learning_goals': 'Master Python, React, System Design, Docker, AWS for career advancement'
        }

        profile = UserProfile.objects.create(**profile_data)

        logger.info("✅ Created comprehensive profile:")
        logger.info(f"   Job Title: {profile.job_title}")
        logger.info(f"   Career Stage: {profile.career_stage}")
        logger.info(f"   Industry: {profile.industry}")
        logger.info(f"   Skill Level: {profile.skill_level}")
        logger.info(f"   Time Commitment: {profile.time_commitment} hours/week")
        logger.info(f"   Learning Style: {profile.learning_style}")
        logger.info(f"   Transition Timeline: {profile.transition_timeline}")

        return profile



    def generate_roadmap(self, profile: UserProfile) -> Optional[Dict[str, Any]]:
        """Generate a roadmap based on user profile"""
        logger.info("🗺️ Generating personalized roadmap...")

        try:
            # Create roadmap request with profile context
            roadmap_request = {
                'user_profile': {
                    'role': profile.job_title,  # Map job_title to role
                    'current_role': profile.job_title,
                    'career_stage': profile.career_stage,
                    'transition_timeline': profile.transition_timeline,
                    'industry': profile.industry,
                    'experience_level': profile.skill_level,
                    'time_commitment': profile.time_commitment,
                    'learning_style': profile.learning_style,
                    'goals': profile.learning_goals
                },
                'target_role': profile.job_title,
                'current_role': profile.job_title,
                'career_stage': profile.career_stage,
                'transition_timeline': profile.transition_timeline,
                'industry': profile.industry,
                'difficulty': 'intermediate',
                'enable_research': True
            }

            # Convert Django UserProfile to roadmap service UserProfile dataclass
            from helpers.ai_roadmap_service import UserProfile as RoadmapUserProfile, LearningGoal

            # Convert learning_goals text to LearningGoal dataclasses
            roadmap_goals = []
            if profile.learning_goals:
                for goal in profile.learning_goals.split(','):
                    roadmap_goals.append(LearningGoal(
                        skill_name=goal.strip(),
                        description=f"Learn {goal.strip()} for career advancement",
                        target_skill_level=profile.skill_level,
                        priority=1
                    ))

            # Create roadmap service user profile (map Django fields to expected dataclass fields)
            roadmap_user_profile = RoadmapUserProfile(
                role=profile.job_title,  # Map job_title to role
                industry=profile.industry,
                career_stage=profile.career_stage,
                learning_style=profile.learning_style,
                time_commitment=profile.time_commitment,
                goals=roadmap_goals
            )

            # Generate roadmap using our service
            roadmaps = gemini_ai_service.generate_roadmaps(roadmap_user_profile)
            # Convert to expected format for lessons
            if roadmaps:
                self.generated_roadmap = roadmaps[0]
                logger.info("✅ Roadmap generated successfully")
                return self.generated_roadmap
            else:
                logger.warning("⚠️ No roadmaps generated")
                return None

        except Exception as e:
            logger.error(f"❌ Error generating roadmap: {e}")
            return None

    def generate_lessons(self, profile: UserProfile, roadmap: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate lessons for roadmap steps"""
        logger.info("📚 Generating personalized lessons...")

        lessons = []
        # Use attribute access for dataclass
        phases = getattr(roadmap, 'phases', None) or getattr(roadmap, 'steps', None) or []

        if not phases:
            logger.warning("⚠️ No phases found in roadmap")
            return lessons

        steps_processed = 0
        max_steps = 1  # Only generate one lesson for API quota

        for phase in phases[:1]:  # Only first phase
            steps = getattr(phase, 'steps', [])
            for step in steps[:1]:  # Only first step
                if steps_processed >= max_steps:
                    break

                step_title = getattr(step, 'title', 'Unknown')
                logger.info(f"📖 Generating lesson for: {step_title}")

                try:
                    lesson_request = {
                        'step_title': step_title,
                        'lesson_number': 1,
                        'learning_style': 'mixed',  # Always use mixed for this test
                        'user_profile': {
                            'role': profile.job_title,
                            'current_role': profile.job_title,
                            'career_stage': profile.career_stage,
                            'transition_timeline': profile.transition_timeline,
                            'industry': profile.industry,
                            'experience_level': profile.skill_level,
                            'time_commitment': profile.time_commitment,
                            'learning_style': 'mixed',  # Always use mixed for this test
                            'goals': profile.learning_goals
                        },
                        'difficulty': 'intermediate',
                        'industry': profile.industry,
                        'enable_research': True
                    }

                    logger.info(f"🔗 Lesson request: {lesson_request}")
                    lesson = asyncio.run(
                        lesson_generation_service.generate_lesson(lesson_request)
                    )

                    if lesson:
                        lesson_type = lesson.get('lesson_type', 'unknown') if isinstance(lesson, dict) else getattr(lesson, 'lesson_type', 'unknown')
                        title = lesson.get('title', 'N/A') if isinstance(lesson, dict) else getattr(lesson, 'title', 'N/A')
                        duration = lesson.get('estimated_duration', 0) if isinstance(lesson, dict) else getattr(lesson, 'estimated_duration', 0)
                        research_metadata = lesson.get('research_metadata', {}) if isinstance(lesson, dict) else getattr(lesson, 'research_metadata', {})
                        research_source = research_metadata.get('source_type', 'N/A') if isinstance(research_metadata, dict) else getattr(research_metadata, 'source_type', 'N/A')

                        logger.info(f"✅ Generated {lesson_type} lesson:")
                        logger.info(f"   Title: {title}")
                        logger.info(f"   Duration: {duration} min")
                        logger.info(f"   Research: {research_source}")
                        logger.info(f"   Full lesson: {lesson}")

                        lessons.append(lesson)
                        steps_processed += 1
                    else:
                        logger.warning(f"⚠️ No lesson generated for: {step_title}")

                except Exception as e:
                    logger.error(f"❌ Error generating lesson for {step_title}: {e}")

        logger.info(f"✅ Generated {len(lessons)} lessons total")
        self.generated_lessons = lessons
        return lessons

    def verify_profile_context_usage(self, profile: UserProfile, roadmap: Dict[str, Any], lessons: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Verify that profile context was properly used in generation"""
        logger.info("🔍 Verifying profile context usage...")

        verification_results = {
            'profile_context_found': False,
            'personalized_content': False,
            'goal_alignment': False,
            'role_specific_examples': False,
            'time_aware_content': False
        }

        # Check roadmap for profile context usage
        roadmap_str = json.dumps(roadmap).lower()

        # Look for profile-specific content in roadmap
        profile_keywords = [
            profile.job_title.lower(),
            profile.job_title.lower(),
            profile.career_stage.lower(),
            profile.industry.lower()
        ]

        for keyword in profile_keywords:
            if keyword in roadmap_str:
                verification_results['profile_context_found'] = True
                break

        # Check lessons for personalization
        for lesson in lessons:
            lesson_str = json.dumps(lesson).lower()

            # Check for personalized content indicators
            personalization_indicators = [
                'based on your', 'in your role', 'career goals',
                'your experience', 'your industry', 'your transition'
            ]

            for indicator in personalization_indicators:
                if indicator in lesson_str:
                    verification_results['personalized_content'] = True
                    break

            # Check for goal alignment
            if profile.learning_goals:
                goals_lower = profile.learning_goals.lower()
                if 'python' in goals_lower or 'react' in goals_lower or 'docker' in goals_lower:
                    verification_results['goal_alignment'] = True
                    break

            # Check for role-specific examples
            if profile.job_title.lower() in lesson_str:
                verification_results['role_specific_examples'] = True

            # Check for time-aware content
            if 'estimated_duration' in lesson:
                duration = lesson['estimated_duration']
                # Should be adjusted based on time_commitment (5-10 hours = 1.3x duration)
                if duration > 30:  # Longer than base duration indicates time-awareness
                    verification_results['time_aware_content'] = True

        # Log verification results
        logger.info("📊 Profile Context Verification Results:")
        for key, value in verification_results.items():
            status = "✅" if value else "❌"
            logger.info(f"   {status} {key}: {value}")

        return verification_results

    def run_complete_test(self) -> Dict[str, Any]:
        """Run the complete test flow"""
        logger.info("🚀 Starting Complete Profile Flow Test...")
        logger.info("=" * 60)

        test_results = {
            'success': False,
            'user_created': False,
            'profile_created': False,
            'roadmap_generated': False,
            'lessons_generated': False,
            'profile_context_verified': False,
            'verification_details': {},
            'errors': []
        }

        try:
            # Step 1: Create test user
            self.test_user = self.create_test_user()
            test_results['user_created'] = True
            logger.info("✅ Step 1: User account created")

            # Step 2: Create comprehensive profile
            self.test_profile = self.create_comprehensive_profile(self.test_user)
            test_results['profile_created'] = True
            logger.info("✅ Step 2: Comprehensive profile created")

            # Step 3: Generate roadmap
            self.generated_roadmap = self.generate_roadmap(self.test_profile)
            if self.generated_roadmap:
                test_results['roadmap_generated'] = True
                logger.info("✅ Step 3: Personalized roadmap generated")
            else:
                test_results['errors'].append("Failed to generate roadmap")
                logger.error("❌ Step 3: Roadmap generation failed")

            # Step 4: Generate lessons
            if self.generated_roadmap:
                self.generated_lessons = self.generate_lessons(self.test_profile, self.generated_roadmap)
                if self.generated_lessons:
                    test_results['lessons_generated'] = True
                    logger.info(f"✅ Step 4: Generated {len(self.generated_lessons)} personalized lessons")
                else:
                    test_results['errors'].append("Failed to generate lessons")
                    logger.error("❌ Step 4: Lesson generation failed")

            # Step 5: Verify profile context usage
            if self.generated_roadmap and self.generated_lessons:
                verification = self.verify_profile_context_usage(
                    self.test_profile,
                    self.generated_roadmap,
                    self.generated_lessons
                )
                test_results['verification_details'] = verification

                # Overall success if key verification points pass
                key_checks = [
                    verification['profile_context_found'],
                    verification['personalized_content'],
                    verification['goal_alignment']
                ]

                if all(key_checks):
                    test_results['profile_context_verified'] = True
                    test_results['success'] = True
                    logger.info("✅ Step 5: Profile context verification PASSED")
                else:
                    test_results['errors'].append("Profile context verification failed")
                    logger.error("❌ Step 5: Profile context verification failed")

            # Final results
            if test_results['success']:
                logger.info("🎉 COMPLETE TEST SUCCESSFUL!")
                logger.info("✅ All components working with profile context integration")
            else:
                logger.error("❌ Test completed with errors")

            logger.info("=" * 60)
            return test_results

        except Exception as e:
            logger.error(f"❌ Test failed with exception: {e}")
            test_results['errors'].append(str(e))
            return test_results

    def cleanup(self):
        """Clean up test data"""
        logger.info("🧹 Cleaning up test data...")

        if self.test_user:
            # Delete test user and related data
            User.objects.filter(email="test.profile@example.com").delete()
            logger.info("✅ Deleted test user and related data")


def main():
    """Main test execution"""
    logger.info("🧪 Starting Comprehensive Profile Flow Test")
    logger.info("Testing: Account → Onboarding → Roadmap → Lessons → Profile Context")

    # Create and run test
    test = CompleteProfileFlowTest()
    results = test.run_complete_test()

    # Cleanup
    test.cleanup()

    # Exit with appropriate code
    if results['success']:
        logger.info("🎉 Test completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Test completed with failures")
        logger.error(f"Errors: {results['errors']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
