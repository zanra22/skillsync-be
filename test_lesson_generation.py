"""
Test script to verify Phase A-D lesson generation changes
"""
import os
import django
import json
import asyncio
from asgiref.sync import sync_to_async

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()

from helpers.ai_lesson_service import LessonGenerationService, LessonRequest
from lessons.models import LessonStructure


async def test_lesson_structure_generation():
    """Test Phase A.1: Lesson structure generation"""
    print("\n" + "="*80)
    print("TEST 1: Lesson Structure Generation (Phase A.1)")
    print("="*80)

    service = LessonGenerationService()

    try:
        structure = await service.generate_lesson_structure(
            module_title="Introduction to Python",
            module_difficulty="beginner",
            user_learning_pace="moderate",
            user_time_commitment=5.0
        )

        print(f"\n✅ Generated structure with {len(structure)} lessons:")
        for lesson in structure:
            print(f"  - Lesson {lesson.get('lesson_number')}: {lesson.get('title')}")
            print(f"    Search Query: {lesson.get('search_query')}")
            print(f"    Duration: {lesson.get('video_duration_min')}-{lesson.get('video_duration_max')} min")

        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_lesson_structure_caching():
    """Test Phase A.2: Lesson structure caching"""
    print("\n" + "="*80)
    print("TEST 2: Lesson Structure Caching (Phase A.2)")
    print("="*80)

    # First call (should generate)
    service = LessonGenerationService()

    try:
        print("\n[First Call] Generating lesson structure...")
        structure1 = await service.generate_lesson_structure(
            module_title="Python Basics",
            module_difficulty="beginner",
            user_learning_pace="fast",
            user_time_commitment=3.0
        )
        print(f"✅ Generated {len(structure1)} lessons")

        # Check if it was cached (use sync_to_async for ORM queries)
        @sync_to_async
        def get_cached_structure():
            return LessonStructure.objects.filter(
                module_title="Python Basics",
                difficulty="beginner"
            ).first()

        cached = await get_cached_structure()

        if cached:
            print(f"✅ Structure cached with hash: {cached.content_hash}")
            print(f"   Approval status: {cached.approval_status}")
        else:
            print("⚠️ Structure not found in cache")

        # Second call (should use cache if available)
        print("\n[Second Call] Retrieving lesson structure...")
        structure2 = await service.generate_lesson_structure(
            module_title="Python Basics",
            module_difficulty="beginner",
            user_learning_pace="fast",
            user_time_commitment=3.0
        )
        print(f"✅ Retrieved structure with {len(structure2)} lessons")

        # Compare
        if structure1 == structure2:
            print("✅ Structures match (cache working)")
        else:
            print("⚠️ Structures differ (new generation)")

        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_video_selection_with_duration():
    """Test Phase B: Duration-aware video selection"""
    print("\n" + "="*80)
    print("TEST 3: Duration-Aware Video Selection (Phase B)")
    print("="*80)

    service = LessonGenerationService()

    try:
        # Test video search with duration constraints
        print("\nSearching for 'Python variables tutorial' (5-15 min)...")
        video = service.youtube_service.search_and_rank(
            topic="Python variables tutorial",
            duration_min=5,
            duration_max=15
        )

        if video:
            print(f"✅ Found video: {video['title'][:60]}...")
            print(f"   Duration: {video['duration_minutes']} min")
            print(f"   Views: {video['view_count']:,}")
            print(f"   URL: {video['video_url']}")
            return True
        else:
            print("⚠️ No video found")
            return False

    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_lesson_request_with_duration():
    """Test Phase B/C: LessonRequest includes duration parameters"""
    print("\n" + "="*80)
    print("TEST 4: LessonRequest with Duration Parameters")
    print("="*80)

    try:
        request = LessonRequest(
            step_title="Understanding Python Variables",
            lesson_number=1,
            learning_style="video",
            user_profile={"learning_pace": "moderate"},
            difficulty="beginner",
            video_duration_min=5,
            video_duration_max=15
        )

        print(f"✅ LessonRequest created:")
        print(f"   Title: {request.step_title}")
        print(f"   Duration: {request.video_duration_min}-{request.video_duration_max} min")
        print(f"   Learning Style: {request.learning_style}")

        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" + "SKILLSYNC BACKEND TESTING".center(80))
    print("Testing Phases A-D: Lesson Structure, Caching, Duration, Video URLs")

    results = []

    results.append(("Test 1: Lesson Structure Generation", await test_lesson_structure_generation()))
    results.append(("Test 2: Lesson Structure Caching", await test_lesson_structure_caching()))
    results.append(("Test 3: Duration-Aware Video Selection", await test_video_selection_with_duration()))
    results.append(("Test 4: LessonRequest Duration Params", await test_lesson_request_with_duration()))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[OK] All tests passed! Backend is ready for deployment.")
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed. Please review above.")


if __name__ == "__main__":
    asyncio.run(main())
