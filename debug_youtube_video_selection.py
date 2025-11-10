#!/usr/bin/env python
"""
Debug script to test YouTube video selection with different topics.
Shows which topics return videos with transcripts available.
"""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
import django
django.setup()

from helpers.youtube.youtube_service import YouTubeService

print("=" * 80)
print("DEBUG: YouTube Video Selection - Multiple Topics")
print("=" * 80)

# Initialize YouTube service
youtube_api_key = os.getenv('YOUTUBE_API_KEY')
groq_api_key = os.getenv('GROQ_API_KEY')

if not youtube_api_key:
    print("[ERROR] YOUTUBE_API_KEY not set")
    sys.exit(1)

print(f"\n[INFO] Initializing YouTubeService...")
youtube_service = YouTubeService(youtube_api_key, groq_api_key)

# Test multiple topics
test_topics = [
    "Python async programming",
    "JavaScript promises tutorial",
    "Web development basics",
    "Machine learning introduction",
    "React tutorial for beginners",
]

found_with_transcript = False

for idx, topic in enumerate(test_topics, 1):
    print(f"\n{'='*80}")
    print(f"[TEST {idx}] Searching for videos: '{topic}'")
    print(f"{'='*80}")

    try:
        video = youtube_service.search_and_rank(topic)

        if video:
            print(f"\n[OK] Video found!")
            print(f"  Title: {video.get('title', 'Unknown')[:70]}")
            print(f"  Video ID: {video.get('video_id')}")
            print(f"  URL: {video.get('video_url')}")
            print(f"  Transcript Available: {video.get('has_transcript', False)}")
            print(f"  Quality Score: {video.get('quality_score', 'N/A')}")
            print(f"  View Count: {video.get('view_count', 0):,}")
            print(f"  Like Count: {video.get('like_count', 0):,}")
            print(f"  Channel: {video.get('channel', 'Unknown')}")

            if video.get('has_transcript'):
                print(f"\n✅ VIDEO WITH TRANSCRIPT FOUND!")
                found_with_transcript = True

                # Try to get transcript
                print(f"\n[INFO] Attempting to get transcript...")
                video_id = video.get('video_id')
                if youtube_service.transcript_service:
                    transcript = youtube_service.transcript_service.get_transcript(video_id)
                    if transcript:
                        print(f"[OK] Transcript obtained!")
                        print(f"  Length: {len(transcript)} characters")
                        print(f"  First 300 chars:\n  {transcript[:300]}...")
                    else:
                        print(f"[WARN] Could not fetch transcript")

                # Stop after finding first video with transcript
                break
            else:
                print(f"\n⚠️ VIDEO WITHOUT TRANSCRIPT - will need Groq fallback")

        else:
            print(f"[WARN] No video found for this topic")

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*80}")
print("DEBUG COMPLETE")
print(f"{'='*80}")
if found_with_transcript:
    print("\n✅ Found at least one video WITH transcripts available")
    print("   Lesson generation should work well for topics with caption-enabled videos")
else:
    print("\n⚠️  No videos with native transcripts found in test")
    print("   Lesson generation will rely on Groq Whisper fallback (requires yt-dlp)")
