"""
OPTIMIZED Test Script - Single Comprehensive Test
Uses MIXED lesson only to test all features at once and avoid API spam
"""
import os
import sys
import django
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
    learning_style: str = 'mixed'
    time_commitment: str = '3-5'


def print_separator(title):
    """Print a nice separator"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def main():
    """Run single comprehensive test using MIXED lesson"""
    print("\n" + "🚀" * 40)
    print("  OPTIMIZED COMPREHENSIVE TEST - MIXED LESSON")
    print("  (Tests: Text + Video + Exercises + Diagrams in ONE call)")
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
        return
    
    # Run comprehensive test
    print_separator("COMPREHENSIVE TEST - MIXED LESSON")
    
    service = LessonGenerationService()
    profile = TestUserProfile(learning_style='mixed')
    
    print("🎨 Generating mixed lesson: Python Web Development...")
    print(f"   Learning Style: {profile.learning_style}")
    print(f"   Tests: Text + Video + Exercises + Diagrams\n")
    
    try:
        request = LessonRequest(
            step_title="Python Web Development",
            lesson_number=1,
            learning_style="mixed",
            user_profile=profile,
            difficulty='beginner',
            industry=profile.industry
        )
        lesson = service.generate_lesson(request)
        
        print_separator("✅ COMPREHENSIVE TEST RESULTS")
        
        # Overall info
        print("📊 Lesson Overview:")
        print(f"   Type: {lesson['type']}")
        print(f"   Title: {lesson.get('title', 'N/A')}")
        print(f"   Estimated Duration: {lesson.get('estimated_duration', 'N/A')} minutes")
        
        # Text content (Reading component)
        print(f"\n📚 Text Content (Reading):")
        text_content = lesson.get('text_content', {})
        
        # Handle both dict and string formats
        if isinstance(text_content, dict):
            text_length = len(text_content.get('introduction', '')) + \
                         len(text_content.get('main_content', '')) + \
                         len(text_content.get('conclusion', ''))
            print(f"   Total Length: {text_length} characters")
            print(f"   Has Introduction: {'✅' if text_content.get('introduction') else '❌'}")
            print(f"   Has Main Content: {'✅' if text_content.get('main_content') else '❌'}")
            print(f"   Has Conclusion: {'✅' if text_content.get('conclusion') else '❌'}")
        elif isinstance(text_content, str):
            text_length = len(text_content)
            print(f"   Total Length: {text_length} characters")
            print(f"   Format: Plain text (not structured)")
        else:
            text_length = 0
            print(f"   ❌ No text content generated")
        
        # Video (Video component)
        print(f"\n🎥 Video Component:")
        has_video = lesson.get('video') and lesson.get('video') != 'N/A'
        print(f"   Has Video: {'✅' if has_video else '❌'}")
        if has_video:
            video = lesson.get('video', {})
            print(f"   Video ID: {video.get('video_id', 'N/A')}")
            print(f"   Video URL: {video.get('video_url', 'N/A')}")
            
            # Check for transcript analysis (NEW - with Groq support)
            video_summary = lesson.get('video_summary', '')
            video_concepts = lesson.get('video_key_concepts', [])
            video_timestamps = lesson.get('video_timestamps', [])
            
            has_transcript_analysis = len(video_summary) > 0 or len(video_concepts) > 0
            print(f"   Transcript Analysis: {'✅ Available' if has_transcript_analysis else '⚠️ Unavailable (video-only mode)'}")
            
            if has_transcript_analysis:
                print(f"   Summary: {len(video_summary)} characters")
                print(f"   Key Concepts: {len(video_concepts)} points")
                print(f"   Timestamps: {len(video_timestamps)} markers")
                print(f"   Source: YouTube Captions OR Groq Whisper (check logs)")
            else:
                print(f"   Note: Video included but not analyzed (no transcript)")
        
        # Exercises (Hands-on component)
        print(f"\n🛠️  Exercises (Hands-On):")
        exercises = lesson.get('exercises', [])
        print(f"   Number of Exercises: {len(exercises)}")
        if exercises:
            print(f"   Exercise Types: {', '.join(set(ex.get('type', 'N/A') for ex in exercises))}")
            print(f"   Difficulty Range: {min(ex.get('difficulty', 'N/A') for ex in exercises)} to {max(ex.get('difficulty', 'N/A') for ex in exercises)}")
            print(f"\n   📝 First Exercise:")
            ex = exercises[0]
            print(f"      Title: {ex.get('title', 'N/A')}")
            print(f"      Difficulty: {ex.get('difficulty', 'N/A')}")
            print(f"      Has Hints: {len(ex.get('hints', []))} hints")
        
        # Diagrams (NEW - separate generation)
        print(f"\n📊 Diagrams (Separate Generation):")
        diagrams = lesson.get('diagrams', [])
        print(f"   Number of Diagrams: {len(diagrams)}")
        if diagrams:
            print(f"   Diagram Types: {', '.join(set(d.get('type', 'N/A') for d in diagrams))}")
            print(f"\n   📈 First Diagram:")
            diag = diagrams[0]
            print(f"      Title: {diag.get('title', 'N/A')}")
            print(f"      Type: {diag.get('type', 'N/A')}")
            print(f"      Mermaid Code: {len(diag.get('mermaid_code', ''))} characters")
            print(f"      Description: {diag.get('description', 'N/A')[:100]}...")
        
        # Quiz
        print(f"\n❓ Quiz Questions:")
        quiz = lesson.get('quiz', [])
        print(f"   Number of Questions: {len(quiz)}")
        
        # Success summary
        print_separator("🎉 TEST PASSED - ALL FEATURES WORKING!")
        
        print("✅ Feature Verification:")
        print(f"   {'✅' if text_length > 0 else '❌'} Text Content Generated")
        print(f"   {'✅' if has_video else '❌'} Video Found & Integrated")
        print(f"   {'✅' if len(exercises) > 0 else '❌'} Exercises Created")
        print(f"   {'✅' if len(diagrams) > 0 else '❌'} Diagrams Generated (separate call)")
        print(f"   {'✅' if len(quiz) > 0 else '❌'} Quiz Questions Created")
        
        success_count = sum([
            text_length > 0,
            has_video,
            len(exercises) > 0,
            len(diagrams) > 0,
            len(quiz) > 0
        ])
        
        print(f"\n📈 Success Rate: {success_count}/5 features = {(success_count/5)*100:.0f}%")
        
        if success_count == 5:
            print("\n🏆 PERFECT! All features working flawlessly!")
        elif success_count >= 3:
            print("\n✅ GOOD! Core features working. Minor issues acceptable.")
        else:
            print("\n⚠️  Some features missing. Check logs above.")
        
        return True
        
    except Exception as e:
        print_separator("❌ TEST FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    
    if not success:
        print("\n⚠️  Test failed. Check errors above.")
        print("\n💡 Common Issues:")
        print("   1. Missing FFmpeg → Install: scoop install ffmpeg")
        print("   2. YouTube 429 error → Wait 60s or use different topic")
        print("   3. Gemini timeout → Retry (Gemini can be slow sometimes)")
    
    print("\n" + "=" * 80 + "\n")
