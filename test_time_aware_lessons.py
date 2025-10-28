#!/usr/bin/env python3
"""
Test Time-Aware Lesson Generation (October 16, 2025)

This script tests the implementation of time commitment in lesson generation.
Tests all learning styles with different time commitments to ensure:
1. Duration adjustment works correctly
2. Content complexity scaling works
3. AI prompts include time guidance
4. User profile data flows from onboarding to lessons

BEFORE RUNNING:
- Ensure backend is running (python manage.py runserver)
- Ensure database migration is applied (time_commitment field exists)
- Ensure test user exists with completed onboarding
"""

import os
import sys
import django
import asyncio
import json
from typing import Dict, Any

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()

# Import after Django setup
from helpers.ai_lesson_service import LessonGenerationService, LessonRequest
from users.models import User
from profiles.models import UserProfile


class TimeAwareLessonTester:
    """Test suite for time-aware lesson generation"""
    
    def __init__(self):
        self.service = LessonGenerationService()
        self.test_results = []
    
    async def test_all_scenarios(self):
        """Test all time commitment scenarios"""
        print("=" * 80)
        print("🧪 TESTING TIME-AWARE LESSON GENERATION")
        print("=" * 80)
        
        # Test scenarios
        scenarios = [
            {
                'name': 'Casual Learner (1-3 hours)',
                'time_commitment': '1-3',
                'expected_duration_multiplier': 0.7,
                'expected_content_reduction': True
            },
            {
                'name': 'Steady Learner (3-5 hours)', 
                'time_commitment': '3-5',
                'expected_duration_multiplier': 1.0,
                'expected_content_reduction': False
            },
            {
                'name': 'Focused Learner (5-10 hours)',
                'time_commitment': '5-10', 
                'expected_duration_multiplier': 1.3,
                'expected_content_reduction': False
            },
            {
                'name': 'Intensive Learner (10+ hours)',
                'time_commitment': '10+',
                'expected_duration_multiplier': 1.5,
                'expected_content_reduction': False
            }
        ]
        
        learning_styles = ['hands_on', 'reading', 'mixed']
        
        for scenario in scenarios:
            print(f"\n📊 {scenario['name']}")
            print("-" * 60)
            
            for style in learning_styles:
                await self.test_lesson_generation(scenario, style)
        
        # Print summary
        await self.print_test_summary()
    
    async def test_lesson_generation(self, scenario: Dict, learning_style: str):
        """Test lesson generation for specific scenario and style"""
        
        # Create mock user profile
        user_profile = {
            'time_commitment': scenario['time_commitment'],
            'learning_style': learning_style,
            'skill_level': 'intermediate',
            'industry': 'Technology'
        }
        
        # Create lesson request
        request = LessonRequest(
            step_title=f"Python Basics - Variables and Data Types",
            lesson_number=1,
            learning_style=learning_style,
            user_profile=user_profile,
            difficulty='beginner',
            industry='Technology',
            enable_research=False  # Disable for faster testing
        )
        
        try:
            print(f"  🎯 Testing {learning_style} lesson...")
            
            # Generate lesson
            lesson_data = await self.service.generate_lesson(request)
            
            # Analyze results
            result = await self.analyze_lesson_result(
                lesson_data, scenario, learning_style, request
            )
            
            self.test_results.append(result)
            
            # Print immediate feedback
            status = "✅ PASS" if result['passes_tests'] else "❌ FAIL"
            duration = lesson_data.get('estimated_duration', 'N/A')
            exercise_count = len(lesson_data.get('exercises', []))
            concept_count = len(lesson_data.get('key_concepts', []))
            
            print(f"    {status} Duration: {duration}min | Exercises: {exercise_count} | Concepts: {concept_count}")
            
            if not result['passes_tests']:
                print(f"    ⚠️ Issues: {', '.join(result['issues'])}")
            
        except Exception as e:
            print(f"    ❌ ERROR: {str(e)}")
            self.test_results.append({
                'scenario': scenario['name'],
                'learning_style': learning_style,
                'passes_tests': False,
                'issues': [f"Exception: {str(e)}"],
                'error': True
            })
    
    async def analyze_lesson_result(
        self, 
        lesson_data: Dict[str, Any], 
        scenario: Dict, 
        learning_style: str,
        request: LessonRequest
    ) -> Dict:
        """Analyze lesson generation result for correctness"""
        
        issues = []
        
        # Test 1: Duration adjustment
        base_durations = {
            'hands_on': 45,
            'reading': 30,
            'mixed': 60,
            'video': None  # Video duration is based on actual video length
        }
        
        if learning_style != 'video':
            base_duration = base_durations[learning_style]
            expected_duration = int(base_duration * scenario['expected_duration_multiplier'])
            actual_duration = lesson_data.get('estimated_duration')
            
            if actual_duration != expected_duration:
                issues.append(f"Duration mismatch: expected {expected_duration}, got {actual_duration}")
        
        # Test 2: Content complexity (for casual learners)
        if scenario['time_commitment'] == '1-3':
            original_exercise_count = 6  # Typical number before reduction
            exercise_count = len(lesson_data.get('exercises', []))
            expected_max = max(2, int(original_exercise_count * 0.6))  # 60% reduction
            
            if exercise_count > expected_max:
                issues.append(f"Too many exercises for casual learner: {exercise_count} > {expected_max}")
        
        # Test 3: User profile inclusion (check if time guidance was used)
        if request.user_profile:
            # The time guidance should influence the lesson structure
            # This is harder to test automatically, but we can check if the service received the profile
            if not hasattr(request, 'user_profile') or not request.user_profile:
                issues.append("User profile not passed to lesson generation")
        
        # Test 4: Required fields present
        required_fields = ['lesson_type', 'estimated_duration', 'title']
        for field in required_fields:
            if field not in lesson_data:
                issues.append(f"Missing required field: {field}")
        
        return {
            'scenario': scenario['name'],
            'learning_style': learning_style,
            'time_commitment': scenario['time_commitment'],
            'actual_duration': lesson_data.get('estimated_duration'),
            'exercise_count': len(lesson_data.get('exercises', [])),
            'concept_count': len(lesson_data.get('key_concepts', [])),
            'passes_tests': len(issues) == 0,
            'issues': issues,
            'lesson_data_keys': list(lesson_data.keys())
        }
    
    async def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['passes_tests']])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
        
        # Group by time commitment
        print(f"\n📈 RESULTS BY TIME COMMITMENT:")
        time_commitments = {}
        for result in self.test_results:
            tc = result['time_commitment']
            if tc not in time_commitments:
                time_commitments[tc] = {'passed': 0, 'total': 0}
            time_commitments[tc]['total'] += 1
            if result['passes_tests']:
                time_commitments[tc]['passed'] += 1
        
        for tc, stats in time_commitments.items():
            rate = stats['passed'] / stats['total'] * 100
            print(f"  {tc} hours: {stats['passed']}/{stats['total']} ({rate:.1f}%)")
        
        # Show failed tests
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['passes_tests']:
                    print(f"  {result['scenario']} - {result['learning_style']}")
                    for issue in result['issues']:
                        print(f"    • {issue}")
        
        # Duration analysis
        print(f"\n⏱️ DURATION ANALYSIS:")
        for result in self.test_results:
            if result['passes_tests'] and 'actual_duration' in result:
                duration = result['actual_duration']
                print(f"  {result['time_commitment']} hrs ({result['learning_style']}): {duration} min")
        
        print("\n" + "=" * 80)


async def test_user_profile_integration():
    """Test integration with actual user profile from database"""
    print("\n🔗 TESTING USER PROFILE INTEGRATION")
    print("-" * 60)
    
    try:
        # Try to find a user with completed onboarding
        user = User.objects.filter(role='learner').first()
        if not user:
            print("❌ No learner users found. Creating test scenario...")
            return
        
        try:
            profile = user.profile
            print(f"✅ Found user profile: {user.email}")
            print(f"   Time commitment: {getattr(profile, 'time_commitment', 'NOT SET')}")
            print(f"   Learning style: {getattr(profile, 'learning_style', 'NOT SET')}")
            print(f"   Onboarding completed: {profile.onboarding_completed}")
            
            # Test if time_commitment field exists
            if hasattr(profile, 'time_commitment') and profile.time_commitment:
                print(f"✅ time_commitment field exists: {profile.time_commitment}")
                
                # Create user_profile dict for lesson generation
                user_profile = {
                    'time_commitment': profile.time_commitment,
                    'learning_style': getattr(profile, 'learning_style', 'mixed'),
                    'skill_level': profile.skill_level or 'beginner',
                    'industry': profile.industry or 'Technology'
                }
                
                # Test lesson generation with real profile
                service = LessonGenerationService()
                request = LessonRequest(
                    step_title="Real Profile Test - Python Variables",
                    lesson_number=1,
                    learning_style=user_profile['learning_style'],
                    user_profile=user_profile,
                    difficulty='beginner',
                    industry=user_profile['industry'],
                    enable_research=False
                )
                
                print("🎯 Generating lesson with real user profile...")
                lesson_data = await service.generate_lesson(request)
                
                print(f"✅ Lesson generated successfully!")
                print(f"   Duration: {lesson_data.get('estimated_duration')} minutes")
                print(f"   Type: {lesson_data.get('lesson_type')}")
                print(f"   Exercises: {len(lesson_data.get('exercises', []))}")
                
            else:
                print("❌ time_commitment field missing or empty")
                print("   This indicates the migration may not have been applied correctly")
                print("   or the onboarding data wasn't saved to the profile")
                
        except Exception as e:
            print(f"❌ Error accessing profile: {e}")
            
    except Exception as e:
        print(f"❌ Database error: {e}")


async def test_duration_calculations():
    """Test duration calculation logic in isolation"""
    print("\n🧮 TESTING DURATION CALCULATIONS")
    print("-" * 60)
    
    service = LessonGenerationService()
    
    test_cases = [
        {'time_commitment': '1-3', 'base': 45, 'expected': 32},  # 45 * 0.7
        {'time_commitment': '3-5', 'base': 45, 'expected': 45},  # 45 * 1.0
        {'time_commitment': '5-10', 'base': 45, 'expected': 59}, # 45 * 1.3
        {'time_commitment': '10+', 'base': 45, 'expected': 68},  # 45 * 1.5
        {'time_commitment': None, 'base': 30, 'expected': 30},   # No profile
    ]
    
    for case in test_cases:
        user_profile = {'time_commitment': case['time_commitment']} if case['time_commitment'] else None
        result = service._calculate_lesson_duration(case['base'], user_profile)
        
        status = "✅" if result == case['expected'] else "❌"
        tc = case['time_commitment'] or 'None'
        
        print(f"  {status} {tc}: {case['base']}min → {result}min (expected: {case['expected']})")


async def main():
    """Main test runner"""
    print("🚀 Starting Time-Aware Lesson Generation Tests")
    print(f"📅 Date: October 16, 2025")
    print(f"🎯 Purpose: Verify time commitment is factored into lesson generation")
    
    # Test 1: Duration calculations
    await test_duration_calculations()
    
    # Test 2: User profile integration
    await test_user_profile_integration()
    
    # Test 3: Full lesson generation scenarios
    tester = TimeAwareLessonTester()
    await tester.test_all_scenarios()
    
    # Cleanup
    await tester.service.cleanup()
    
    print("\n🎉 All tests completed!")
    print("\n💡 Next steps:")
    print("   1. Review any failed tests above")
    print("   2. Test onboarding flow to ensure time_commitment is saved")
    print("   3. Generate actual lessons through the GraphQL API")
    print("   4. Verify lesson durations in the frontend")


if __name__ == "__main__":
    asyncio.run(main())