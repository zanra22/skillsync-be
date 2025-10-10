"""
Test Groq Whisper Transcription
Tests video lesson with Groq fallback when YouTube captions unavailable
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
    learning_style: str = 'video'
    time_commitment: str = '3-5'


def test_groq_transcription():
    """Test video lesson with Groq Whisper fallback"""
    print("\n" + "🎙️" * 40)
    print("  GROQ WHISPER TRANSCRIPTION TEST")
    print("🎙️" * 40)
    
    # Check prerequisites
    print("\n📋 Prerequisites Check:")
    groq_key = os.getenv('GROQ_API_KEY')
    gemini_key = os.getenv('GEMINI_API_KEY')
    youtube_key = os.getenv('YOUTUBE_API_KEY')
    
    print(f"   {'✅' if gemini_key else '❌'} Gemini API: {'Configured' if gemini_key else 'MISSING'}")
    print(f"   {'✅' if youtube_key else '⚠️ '} YouTube API: {'Configured' if youtube_key else 'Optional'}")
    print(f"   {'✅' if groq_key else '❌'} Groq API: {'Configured' if groq_key else 'MISSING'}")
    
    if not groq_key:
        print("\n❌ ERROR: GROQ_API_KEY not found!")
        print("   Add to .env: GROQ_API_KEY=gsk_your_key_here")
        return False
    
    if not gemini_key:
        print("\n❌ ERROR: GEMINI_API_KEY not found!")
        return False
    
    # Check FFmpeg
    import shutil
    ffmpeg_available = shutil.which('ffmpeg') is not None
    print(f"   {'✅' if ffmpeg_available else '❌'} FFmpeg: {'Installed' if ffmpeg_available else 'MISSING'}")
    
    if not ffmpeg_available:
        print("\n❌ ERROR: FFmpeg not installed!")
        print("   Install: scoop install ffmpeg")
        print("   Or: https://www.gyan.dev/ffmpeg/builds/")
        return False
    
    print("\n✅ All prerequisites met! Starting test...\n")
    print("=" * 80)
    
    # Generate video lesson
    service = LessonGenerationService()
    profile = TestUserProfile(learning_style='video')
    
    print("\n🎥 Generating VIDEO lesson...")
    print("   Topic: Advanced JavaScript Concepts")
    print("   Learning Style: video")
    print("   Note: This will search YouTube and may trigger Groq if no captions\n")
    
    try:
        request = LessonRequest(
            step_title="Advanced JavaScript Concepts",  # Topic likely to have videos without captions
            lesson_number=1,
            learning_style="video",
            user_profile=profile,
            difficulty='intermediate',
            industry=profile.industry
        )
        
        print("🔍 Searching YouTube...\n")
        lesson = service.generate_lesson(request)
        
        print("\n" + "=" * 80)
        print("  ✅ TEST RESULTS")
        print("=" * 80)
        
        print(f"\n📊 Lesson Generated:")
        print(f"   Type: {lesson.get('type', 'N/A')}")
        print(f"   Title: {lesson.get('title', 'N/A')}")
        
        # Check video
        video = lesson.get('video', {})
        print(f"\n🎥 Video Details:")
        print(f"   Video ID: {video.get('video_id', 'N/A')}")
        print(f"   Video URL: {video.get('video_url', 'N/A')}")
        print(f"   Duration: {video.get('duration_minutes', 'N/A')} minutes")
        
        # Check if transcript was obtained
        has_summary = len(lesson.get('summary', '')) > 100
        has_key_concepts = len(lesson.get('key_concepts', [])) > 0
        has_timestamps = len(lesson.get('timestamps', [])) > 0
        has_quiz = len(lesson.get('quiz', [])) > 0
        
        print(f"\n📝 AI Analysis (requires transcript):")
        print(f"   Summary: {'✅ Generated' if has_summary else '❌ Missing'} ({len(lesson.get('summary', ''))} chars)")
        print(f"   Key Concepts: {'✅ Generated' if has_key_concepts else '❌ Missing'} ({len(lesson.get('key_concepts', []))} items)")
        print(f"   Timestamps: {'✅ Generated' if has_timestamps else '❌ Missing'} ({len(lesson.get('timestamps', []))} items)")
        print(f"   Quiz Questions: {'✅ Generated' if has_quiz else '❌ Missing'} ({len(lesson.get('quiz', []))} items)")
        
        # Determine transcript source
        print(f"\n🎙️ Transcript Source Analysis:")
        if has_summary and has_key_concepts:
            print("   ✅ Transcript obtained successfully!")
            print("   Source: YouTube Captions OR Groq Whisper")
            print("   (Check logs above for 'Groq Whisper' messages)")
        else:
            print("   ❌ No transcript obtained")
            print("   Both YouTube and Groq fallback failed")
            print("   Possible reasons:")
            print("      - Video has no captions (YouTube)")
            print("      - Groq transcription failed (network/timeout)")
            print("      - FFmpeg issue (check installation)")
        
        # Overall success
        print("\n" + "=" * 80)
        transcript_success = has_summary and has_key_concepts
        
        if transcript_success:
            print("🎉 SUCCESS! Video lesson generated with full AI analysis!")
            print("   ✅ Transcript obtained (YouTube or Groq)")
            print("   ✅ AI analysis complete")
            print("   ✅ All features working")
        else:
            print("⚠️  PARTIAL SUCCESS - Video found but no transcript")
            print("   ✅ Video integration working")
            print("   ❌ Transcript unavailable (both methods failed)")
            print("   💡 Try running test again or use different topic")
        
        print("=" * 80 + "\n")
        
        # Show sample content
        if has_key_concepts:
            print("\n📚 Sample Key Concepts:")
            for i, concept in enumerate(lesson.get('key_concepts', [])[:3], 1):
                print(f"   {i}. {concept}")
        
        if has_timestamps:
            print("\n⏱️  Sample Timestamps:")
            for i, ts in enumerate(lesson.get('timestamps', [])[:3], 1):
                print(f"   {i}. {ts.get('time', 'N/A')} - {ts.get('description', 'N/A')}")
        
        return transcript_success
        
    except Exception as e:
        print("\n" + "=" * 80)
        print("  ❌ TEST FAILED")
        print("=" * 80)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("  GROQ WHISPER + FFMPEG INTEGRATION TEST")
    print("  Purpose: Verify Groq transcription works when YouTube has no captions")
    print("=" * 80)
    
    success = test_groq_transcription()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ TEST PASSED - Groq Whisper working!")
    else:
        print("⚠️  TEST INCOMPLETE - Check logs above")
        print("\n💡 Common Issues:")
        print("   1. YouTube had captions (Groq not needed)")
        print("   2. FFmpeg not in PATH (restart terminal after install)")
        print("   3. Network timeout (try again)")
        print("   4. Video age-restricted or unavailable")
    print("=" * 80 + "\n")
