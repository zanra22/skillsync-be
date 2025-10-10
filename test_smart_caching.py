"""
Test Smart Caching System

This script tests the complete lesson caching flow:
1. First request: Generate lesson → Save to database (CACHE MISS)
2. Second request: Fetch from database (CACHE HIT)
3. Verify: Database has lessons, cache hit rate working

Expected Results:
- First call: ~20 seconds, $0.002 cost, saves to database
- Second call: ~0.1 seconds, $0 cost, fetches from cache
- Database: Contains saved lessons with correct cache_key

Author: SkillSync Team
Date: October 9, 2025
"""

import os
import sys
import django
import asyncio
import time
import hashlib
from datetime import datetime
from asgiref.sync import sync_to_async

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()

from lessons.models import LessonContent
from lessons.types import GetOrGenerateLessonInput
from lessons.query import LessonsQuery
from django.contrib.auth import get_user_model

User = get_user_model()


class MockInfo:
    """Mock GraphQL info object for testing"""
    class MockRequest:
        def __init__(self):
            self.user = None  # Will be set later in async context
    
    def __init__(self):
        self.context = type('Context', (), {'request': self.MockRequest()})()


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_section(text):
    """Print formatted section"""
    print(f"\n{'─' * 80}")
    print(f"  {text}")
    print(f"{'─' * 80}")


async def get_or_create_test_user():
    """Get or create test user (async)"""
    try:
        user = await sync_to_async(User.objects.get)(email='test@skillsync.com')
    except User.DoesNotExist:
        user = await sync_to_async(User.objects.create_user)(
            email='test@skillsync.com',
            password='testpass123',
            role='learner'
        )
    return user


async def test_caching_system():
    """Test complete caching flow"""
    
    print_header("🧪 SMART CACHING SYSTEM TEST")
    print(f"Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Setup test user
    print_section("👤 Setting up test user")
    test_user = await get_or_create_test_user()
    print(f"✅ Test user ready: {test_user.email}")
    
    # Test data
    test_cases = [
        {
            'step_title': 'Python Variables',
            'learning_style': 'mixed',
            'lesson_number': 1
        },
        {
            'step_title': 'JavaScript Functions',
            'learning_style': 'hands_on',
            'lesson_number': 1
        }
    ]
    
    lessons_query = LessonsQuery()
    mock_info = MockInfo()
    mock_info.context.request.user = test_user  # Set the user
    
    # Track statistics
    stats = {
        'total_requests': 0,
        'cache_hits': 0,
        'cache_misses': 0,
        'total_time': 0,
        'lessons_in_db_before': 0,
        'lessons_in_db_after': 0
    }
    
    # Check initial database state
    print_section("📊 Initial Database State")
    stats['lessons_in_db_before'] = await sync_to_async(LessonContent.objects.count)()
    print(f"Lessons in database: {stats['lessons_in_db_before']}")
    
    # Test each case
    for i, test_case in enumerate(test_cases, 1):
        print_header(f"Test Case {i}: {test_case['step_title']}")
        
        # Calculate expected cache key
        cache_string = f"{test_case['step_title']}:{test_case['lesson_number']}:{test_case['learning_style']}"
        expected_cache_key = hashlib.md5(cache_string.encode()).hexdigest()
        print(f"\n📌 Test Parameters:")
        print(f"   Topic: {test_case['step_title']}")
        print(f"   Style: {test_case['learning_style']}")
        print(f"   Lesson #: {test_case['lesson_number']}")
        print(f"   Expected Cache Key: {expected_cache_key}")
        
        # Create input
        lesson_input = GetOrGenerateLessonInput(
            step_title=test_case['step_title'],
            lesson_number=test_case['lesson_number'],
            learning_style=test_case['learning_style']
        )
        
        # First request (should be CACHE MISS)
        print_section("🔍 Request #1: Should be CACHE MISS (Generate)")
        start_time = time.time()
        
        result1 = await lessons_query.get_or_generate_lesson(mock_info, lesson_input)
        
        elapsed1 = time.time() - start_time
        stats['total_requests'] += 1
        stats['total_time'] += elapsed1
        
        print(f"\n✅ Request #1 Complete:")
        print(f"   Success: {result1.success}")
        print(f"   Message: {result1.message}")
        print(f"   Was Cached: {result1.was_cached}")
        print(f"   Time: {elapsed1:.2f} seconds")
        
        if result1.lesson:
            print(f"   Lesson ID: {result1.lesson.id}")
            print(f"   Title: {result1.lesson.title}")
            print(f"   Cache Key: {result1.lesson.cache_key}")
            print(f"   Learning Style: {result1.lesson.learning_style}")
            
            # Verify it's a cache miss
            if result1.was_cached:
                print(f"   ⚠️ WARNING: Should be cache miss but was cached!")
                stats['cache_hits'] += 1
            else:
                print(f"   ✅ CORRECT: Cache miss (generated new lesson)")
                stats['cache_misses'] += 1
        else:
            print(f"   ❌ ERROR: No lesson returned!")
        
        # Wait a moment
        await asyncio.sleep(1)
        
        # Second request (should be CACHE HIT)
        print_section("🔍 Request #2: Should be CACHE HIT (Fetch)")
        start_time = time.time()
        
        result2 = await lessons_query.get_or_generate_lesson(mock_info, lesson_input)
        
        elapsed2 = time.time() - start_time
        stats['total_requests'] += 1
        stats['total_time'] += elapsed2
        
        print(f"\n✅ Request #2 Complete:")
        print(f"   Success: {result2.success}")
        print(f"   Message: {result2.message}")
        print(f"   Was Cached: {result2.was_cached}")
        print(f"   Time: {elapsed2:.2f} seconds")
        
        if result2.lesson:
            print(f"   Lesson ID: {result2.lesson.id}")
            print(f"   Same as Request #1: {result1.lesson.id == result2.lesson.id if result1.lesson else False}")
            
            # Verify it's a cache hit
            if result2.was_cached:
                print(f"   ✅ CORRECT: Cache hit (fetched from database)")
                print(f"   💰 Cost Savings: $0.002 (would have cost AI generation)")
                print(f"   ⚡ Speed Up: {elapsed1 / elapsed2:.1f}x faster")
                stats['cache_hits'] += 1
            else:
                print(f"   ⚠️ WARNING: Should be cache hit but generated new!")
                stats['cache_misses'] += 1
        else:
            print(f"   ❌ ERROR: No lesson returned!")
        
        # Verify database
        print_section("💾 Database Verification")
        lessons_with_key = await sync_to_async(list)(
            LessonContent.objects.filter(cache_key=expected_cache_key)
        )
        count = len(lessons_with_key)
        print(f"   Lessons with cache_key '{expected_cache_key}': {count}")
        
        if count > 0:
            print(f"   ✅ CORRECT: Lesson saved to database")
            for lesson in lessons_with_key:
                print(f"      - ID: {lesson.id}, Upvotes: {lesson.upvotes}, Views: {lesson.view_count}")
        else:
            print(f"   ❌ ERROR: No lessons found with this cache_key!")
    
    # Final database state
    print_header("📊 Final Statistics")
    stats['lessons_in_db_after'] = await sync_to_async(LessonContent.objects.count)()
    
    print(f"\n📈 Database:")
    print(f"   Before: {stats['lessons_in_db_before']} lessons")
    print(f"   After: {stats['lessons_in_db_after']} lessons")
    print(f"   New Lessons: {stats['lessons_in_db_after'] - stats['lessons_in_db_before']}")
    
    print(f"\n📊 Caching Performance:")
    print(f"   Total Requests: {stats['total_requests']}")
    print(f"   Cache Hits: {stats['cache_hits']}")
    print(f"   Cache Misses: {stats['cache_misses']}")
    
    if stats['total_requests'] > 0:
        hit_rate = (stats['cache_hits'] / stats['total_requests']) * 100
        print(f"   Cache Hit Rate: {hit_rate:.1f}%")
        print(f"   Expected Hit Rate: 50% (since we test each topic twice)")
    
    avg_time = stats['total_time'] / stats['total_requests']
    print(f"\n⏱️ Performance:")
    print(f"   Total Time: {stats['total_time']:.2f} seconds")
    print(f"   Average Time: {avg_time:.2f} seconds")
    
    # Cost calculation
    estimated_cost = stats['cache_misses'] * 0.002
    saved_cost = stats['cache_hits'] * 0.002
    print(f"\n💰 Cost Analysis:")
    print(f"   Actual Cost: ${estimated_cost:.4f} ({stats['cache_misses']} generations)")
    print(f"   Saved Cost: ${saved_cost:.4f} ({stats['cache_hits']} cached)")
    print(f"   Savings: {(saved_cost / (estimated_cost + saved_cost) * 100) if (estimated_cost + saved_cost) > 0 else 0:.1f}%")
    
    # Success criteria
    print_header("✅ Test Results")
    
    success = True
    issues = []
    
    # Check if new lessons were created
    if stats['lessons_in_db_after'] <= stats['lessons_in_db_before']:
        success = False
        issues.append("❌ No new lessons were created in database")
    else:
        print("✅ New lessons successfully saved to database")
    
    # Check cache hit rate
    if stats['cache_hits'] == 0:
        success = False
        issues.append("❌ No cache hits detected (caching not working)")
    else:
        print(f"✅ Caching working ({stats['cache_hits']} cache hits)")
    
    # Check cache miss rate
    if stats['cache_misses'] == 0:
        success = False
        issues.append("❌ No cache misses (should generate at least once)")
    else:
        print(f"✅ Generation working ({stats['cache_misses']} new lessons)")
    
    if success:
        print("\n🎉 ALL TESTS PASSED!")
        print("\n✨ Smart Caching System is working perfectly!")
        print("   - Lessons are saved to database ✅")
        print("   - Cache hits are detected ✅")
        print("   - Cost savings confirmed ✅")
    else:
        print("\n⚠️ TESTS FAILED!")
        print("\nIssues found:")
        for issue in issues:
            print(f"   {issue}")
    
    return success


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("  SMART CACHING TEST - Phase 1 Implementation")
    print("  Testing: Database persistence + Smart caching")
    print("=" * 80)
    
    try:
        success = asyncio.run(test_caching_system())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
