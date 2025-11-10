#!/usr/bin/env python
"""
Debug script to diagnose why transcript detection is failing.

Tests:
1. YouTube API caption filter (does it return results?)
2. YouTubeTranscriptApi (can it detect transcripts for known videos?)
3. Comparison of videos with/without captions
"""
import os
import sys
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
import django
django.setup()

from helpers.youtube.youtube_service import YouTubeService
from youtube_transcript_api import YouTubeTranscriptApi

print("=" * 80)
print("DEBUG: Transcript Detection Diagnostics")
print("=" * 80)

# Initialize YouTube service
youtube_api_key = os.getenv('YOUTUBE_API_KEY')
groq_api_key = os.getenv('GROQ_API_KEY')

if not youtube_api_key:
    print("[ERROR] YOUTUBE_API_KEY not set")
    sys.exit(1)

print(f"\n[INFO] Initializing YouTubeService...")
youtube_service = YouTubeService(youtube_api_key, groq_api_key)

# Test 1: Search with caption filter
print(f"\n{'='*80}")
print("[TEST 1] YouTube API search WITH caption filter (videoCaption='closedCaption')")
print(f"{'='*80}")

youtube = youtube_service._get_youtube_service()
if not youtube:
    print("[ERROR] Could not get YouTube API service")
    sys.exit(1)

try:
    search_response = youtube.search().list(
        q="Python tutorial",
        part='snippet',
        type='video',
        maxResults=5,
        order='relevance',
        videoDuration='medium',
        videoDefinition='high',
        videoCaption='closedCaption',  # CAPTION FILTER
        relevanceLanguage='en'
    ).execute()

    items = search_response.get('items', [])
    print(f"[RESULT] Found {len(items)} videos WITH caption filter")
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item['id']['videoId']} - {item['snippet']['title'][:60]}")

except Exception as e:
    print(f"[ERROR] Search with caption filter failed: {e}")

# Test 2: Search WITHOUT caption filter
print(f"\n{'='*80}")
print("[TEST 2] YouTube API search WITHOUT caption filter")
print(f"{'='*80}")

try:
    search_response = youtube.search().list(
        q="Python tutorial",
        part='snippet',
        type='video',
        maxResults=5,
        order='relevance',
        videoDuration='medium',
        videoDefinition='high',
        # NO CAPTION FILTER
        relevanceLanguage='en'
    ).execute()

    items = search_response.get('items', [])
    print(f"[RESULT] Found {len(items)} videos WITHOUT caption filter")
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item['id']['videoId']} - {item['snippet']['title'][:60]}")

except Exception as e:
    print(f"[ERROR] Search without caption filter failed: {e}")

# Test 3: Check transcript detection for known videos
print(f"\n{'='*80}")
print("[TEST 3] Transcript detection for specific videos")
print(f"{'='*80}")

# Videos to test (mix of ones likely to have and not have captions)
test_videos = [
    ("Xam4yW3Ts5I", "Namaste Effect - Python"),  # Known to have captions
    ("ftmdDlwMwwQ", "mCoding - async Python"),    # From debug script (no captions)
    ("dQw4w9WgXcQ", "Rick Roll"),                  # Famous video (check if has captions)
]

for video_id, description in test_videos:
    print(f"\n[Video] {video_id} - {description}")

    try:
        transcript = YouTubeTranscriptApi.get_transcript(
            video_id,
            languages=['en', 'en-US', 'en-GB']
        )
        print(f"  ✅ Transcript available: {len(transcript)} entries, {sum(len(e['text']) for e in transcript)} chars")
    except Exception as e:
        error_type = type(e).__name__
        print(f"  ❌ No transcript: {error_type}: {str(e)[:80]}")

print(f"\n{'='*80}")
print("DIAGNOSTICS COMPLETE")
print(f"{'='*80}")
print("\n[ANALYSIS]")
print("If Test 1 finds 0 results but Test 2 finds results:")
print("  → The videoCaption filter is NOT working (API limitation or permissions)")
print("  → Videos are being selected without captions")
print("  → yt-dlp Groq fallback will fail on Azure due to bot detection")
print("\nIf Test 3 shows transcripts exist for videos returned in Test 2:")
print("  → The transcript detection method is not being called properly")
print("  → Something changed in how has_transcript() is invoked")
