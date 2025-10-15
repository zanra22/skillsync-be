"""
Test script for LessonGenerationService
Tests all 4 learning styles: hands_on, video, reading, mixed
"""
import os
import sys
import django
import json
from pathlib import Path

# Setup Django
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()

from helpers.ai_lesson_service import LessonGenerationService, LessonRequest
from dataclasses import dataclass


@dataclass
class TestUserProfile:
    """Mock user profile for testing"""
    role: str = 'learner'
    industry: str = 'Technology'
    career_stage: str = 'entry_level'
    learning_style: str = 'hands_on'
    time_commitment: str = '3-5'


def print_separator(title):
    """Print a nice separator"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_hands_on_lesson():
    """Test hands-on lesson generation"""
    print_separator("TEST 1: HANDS-ON LESSON GENERATION")
    
    service = LessonGenerationService()
    profile = TestUserProfile(learning_style='hands_on')
    
    print("📝 Generating hands-on lesson: Python Variables...")
    print(f"   Learning Style: {profile.learning_style}")
    print(f"   Industry: {profile.industry}")
    print(f"   Career Stage: {profile.career_stage}\n")
    
    try:
        request = LessonRequest(
            step_title="Python Variables",
            lesson_number=1,
            learning_style="hands_on",
            user_profile=profile,
            difficulty='beginner',
            industry=profile.industry
        )
        lesson = service.generate_lesson(request)
        
        print("✅ Lesson generated successfully!")
        print(f"   Type: {lesson['type']}")
        print(f"   Title: {lesson.get('title', 'N/A')}")
        print(f"   Estimated Duration: {lesson.get('estimated_duration', 'N/A')} minutes")
        print(f"   Has Code Editor: {lesson.get('has_code_editor', False)}")
        print(f"   Number of Exercises: {len(lesson.get('exercises', []))}")
        
        # Show first exercise
        if lesson.get('exercises'):
            print(f"\n📚 First Exercise:")
            ex = lesson['exercises'][0]
            print(f"   Title: {ex.get('title', 'N/A')}")
            print(f"   Difficulty: {ex.get('difficulty', 'N/A')}")
            print(f"   Has Hints: {len(ex.get('hints', []))} hints")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_video_lesson():
    """Test video lesson generation"""
    print_separator("TEST 2: VIDEO LESSON GENERATION")
    
    service = LessonGenerationService()
    profile = TestUserProfile(learning_style='video')
    
    print("🎥 Generating video lesson: JavaScript Functions...")
    print(f"   Learning Style: {profile.learning_style}")
    print(f"   Will search YouTube for best tutorial\n")
    
    try:
        request = LessonRequest(
            step_title="JavaScript Functions",
            lesson_number=1,
            learning_style="video",
            user_profile=profile,
            difficulty='beginner',
            industry=profile.industry
        )
        lesson = service.generate_lesson(request)
        
        print("✅ Lesson generated successfully!")
        print(f"   Type: {lesson['type']}")
        print(f"   Has Video: {lesson.get('has_video', False)}")
        print(f"   Video ID: {lesson.get('video_id', 'N/A')}")
        print(f"   Video URL: {lesson.get('video_url', 'N/A')}")
        print(f"   Summary Length: {len(lesson.get('summary', ''))} characters")
        print(f"   Key Concepts: {len(lesson.get('key_concepts', []))} points")
        print(f"   Timestamps: {len(lesson.get('timestamps', []))} markers")
        print(f"   Quiz Questions: {len(lesson.get('quiz', []))} questions")
        
        # Show first timestamp
        if lesson.get('timestamps'):
            print(f"\n⏱️  First Timestamp:")
            ts = lesson['timestamps'][0]
            print(f"   {ts.get('time', 'N/A')} - {ts.get('description', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_reading_lesson():
    """Test reading lesson generation"""
    print_separator("TEST 3: READING LESSON GENERATION")
    
    service = LessonGenerationService()
    profile = TestUserProfile(learning_style='reading')
    
    print("📚 Generating reading lesson: React Hooks...")
    print(f"   Learning Style: {profile.learning_style}")
    print(f"   Will generate long-form content + diagrams\n")
    
    try:
        request = LessonRequest(
            step_title="React Hooks",
            lesson_number=1,
            learning_style="reading",
            user_profile=profile,
            difficulty='beginner',
            industry=profile.industry
        )
        lesson = service.generate_lesson(request)
        
        print("✅ Lesson generated successfully!")
        print(f"   Type: {lesson['type']}")
        print(f"   Content Length: {len(lesson.get('content', ''))} characters")
        print(f"   Diagrams: {len(lesson.get('diagrams', []))} diagrams")
        print(f"   Hero Image: {lesson.get('hero_image', 'N/A')}")
        print(f"   Quiz Questions: {len(lesson.get('quiz', []))} questions")
        
        # Show first diagram
        if lesson.get('diagrams'):
            print(f"\n📊 First Diagram:")
            diag = lesson['diagrams'][0]
            print(f"   Title: {diag.get('title', 'N/A')}")
            print(f"   Mermaid Code: {len(diag.get('mermaid_code', ''))} characters")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mixed_lesson():
    """Test mixed lesson generation"""
    print_separator("TEST 4: MIXED LESSON GENERATION")
    
    service = LessonGenerationService()
    profile = TestUserProfile(learning_style='mixed')
    
    print("🎨 Generating mixed lesson: SQL Basics...")
    print(f"   Learning Style: {profile.learning_style}")
    print(f"   Will combine text + video + exercises + diagrams\n")
    
    try:
        request = LessonRequest(
            step_title="SQL Basics",
            lesson_number=1,
            learning_style="mixed",
            user_profile=profile,
            difficulty='beginner',
            industry=profile.industry
        )
        lesson = service.generate_lesson(request)
        
        print("✅ Lesson generated successfully!")
        print(f"   Type: {lesson['type']}")
        print(f"   Text Content: {len(lesson.get('text_content', ''))} characters")
        print(f"   Has Video: {lesson.get('video', 'N/A') != 'N/A'}")
        print(f"   Exercises: {len(lesson.get('exercises', []))} exercises")
        print(f"   Diagrams: {len(lesson.get('diagrams', []))} diagrams")
        print(f"   Quiz Questions: {len(lesson.get('quiz', []))} questions")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "🚀" * 40)
    print("  LESSON GENERATION SERVICE - COMPREHENSIVE TEST")
    print("🚀" * 40)
    
    # Check API keys
    print("\n📋 Checking API Keys...")
    gemini_key = os.getenv('GEMINI_API_KEY')
    youtube_key = os.getenv('YOUTUBE_API_KEY')
    unsplash_key = os.getenv('UNSPLASH_ACCESS_KEY')
    groq_key = os.getenv('GROQ_API_KEY')
    
    print(f"   ✅ Gemini API: {'Configured' if gemini_key else '❌ MISSING'}")
    print(f"   {'✅' if youtube_key else '⚠️ '} YouTube API: {'Configured' if youtube_key else 'Not configured (optional)'}")
    print(f"   {'✅' if unsplash_key else '⚠️ '} Unsplash API: {'Configured' if unsplash_key else 'Not configured (optional)'}")
    print(f"   {'✅' if groq_key else '⚠️ '} Groq API: {'Configured' if groq_key else 'Not configured (Whisper fallback unavailable)'}")
    
    if not gemini_key:
        print("\n❌ ERROR: GEMINI_API_KEY not found in .env file!")
        print("   Please add it to continue.")
        return
    
    # Run tests
    results = {
        'hands_on': test_hands_on_lesson(),
        'video': test_video_lesson(),
        'reading': test_reading_lesson(),
        'mixed': test_mixed_lesson(),
    }
    
    # Summary
    print_separator("TEST SUMMARY")
    
    total = len(results)
    passed = sum(results.values())
    failed = total - passed
    
    print(f"Total Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"\nSuccess Rate: {(passed/total)*100:.1f}%")
    
    for style, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {style.replace('_', ' ').title()} Lesson")
    
    print("\n" + "=" * 80 + "\n")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED! Lesson generation service is working perfectly.")
    else:
        print("⚠️  Some tests failed. Check the errors above for details.")


if __name__ == '__main__':
    main()
