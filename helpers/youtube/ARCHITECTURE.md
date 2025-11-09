# YouTube Service Module Architecture

**Date:** November 8, 2025
**Status:** ✅ Complete and Integrated

## Overview

The YouTube Service Module provides a modular, testable, and maintainable solution for YouTube video search, quality ranking, transcript extraction, and analysis.

## Module Structure

```
helpers/youtube/
├── __init__.py                 # Module exports
├── quality_ranker.py           # 5-factor quality scoring
├── youtube_service.py          # Main video search service
├── transcript_service.py       # Transcript fetching with fallbacks
├── groq_transcription.py       # Groq Whisper API wrapper
├── video_analyzer.py           # Transcript analysis and study materials
└── ARCHITECTURE.md             # This file
```

## Components

### 1. YouTubeQualityRanker (`quality_ranker.py`)

**Responsibility:** Rank videos by quality using 5-factor scoring

**Weight Distribution:**
- View Count: 30% (logarithmic scale: 10K-1M+)
- Like Engagement: 25% (engagement rate proxy)
- Channel Authority: 20% (subscribers + verified status)
- Transcript Quality: 15% (topic relevance + clarity + structure)
- Recency: 10% (optimal 6 months - 3 years)

**Key Methods:**
- `rank_videos()` - Rank list of videos and return top N
- `_calculate_quality_score()` - Compute weighted quality score
- `filter_by_quality_threshold()` - Filter by minimum score
- `get_quality_summary()` - Human-readable quality summary

**Usage:**
```python
from helpers.youtube import YouTubeQualityRanker

ranker = YouTubeQualityRanker()
ranked = ranker.rank_videos(videos, topic="Python Functions", max_results=3)
```

### 2. YouTubeService (`youtube_service.py`)

**Responsibility:** Search YouTube API and select best video using quality ranking

**Features:**
- Search with caption preference
- Fallback to uncaptioned videos
- Enrich with channel authority data
- Integrate quality ranking
- Return metadata with quality scores

**Key Methods:**
- `search_and_rank()` - Search YouTube and rank results
- `get_transcript()` - Get transcript (delegates to TranscriptService)
- `_parse_youtube_duration()` - Parse ISO 8601 durations

**Usage:**
```python
from helpers.youtube import YouTubeService

service = YouTubeService(youtube_api_key, groq_api_key)
video = service.search_and_rank("Python asyncio")
transcript = service.get_transcript(video['video_id'])
```

### 3. TranscriptService (`transcript_service.py`)

**Responsibility:** Fetch transcripts with intelligent fallback

**Fallback Chain:**
1. YouTube native captions (fastest, preferred)
2. Groq Whisper transcription (slower, reliable)
3. Return None (graceful failure)

**Key Methods:**
- `has_transcript()` - Check if video has accessible captions
- `get_transcript()` - Fetch transcript with fallback
- Rate limiting to prevent 429 errors

**Usage:**
```python
from helpers.youtube import TranscriptService

service = TranscriptService(youtube_api_key, groq_api_key)
transcript = service.get_transcript("dQw4w9WgXcQ")
```

### 4. GroqTranscription (`groq_transcription.py`)

**Responsibility:** Groq Whisper API wrapper for video audio transcription

**Process:**
1. Download YouTube audio with yt-dlp
2. Transcribe with Groq Whisper
3. Cleanup temporary files

**Key Methods:**
- `transcribe()` - Main transcription method
- `_download_audio()` - Download video audio to MP3
- `_cleanup_audio()` - Safe file cleanup

**Requirements:**
- yt-dlp: `pip install yt-dlp`
- FFmpeg: https://www.gyan.dev/ffmpeg/builds/
- Groq API Key: `GROQ_API_KEY` environment variable

**Usage:**
```python
from helpers.youtube import GroqTranscription

transcriber = GroqTranscription(groq_api_key)
transcript = transcriber.transcribe("dQw4w9WgXcQ")
```

### 5. VideoAnalyzer (`video_analyzer.py`)

**Responsibility:** Analyze video transcripts and generate study materials

**Outputs:**
- Summary (3-4 sentences)
- Key concepts (list)
- Timestamps (time-code annotations)
- Study guide (structured notes)
- Quiz (comprehension questions)

**Key Methods:**
- `analyze_transcript()` - Main analysis method
- `_build_analysis_prompt()` - Create AI prompt
- `_format_research_context()` - Format research data for prompt
- `_parse_analysis_response()` - Parse JSON response

**Usage:**
```python
from helpers.youtube import VideoAnalyzer

analyzer = VideoAnalyzer()
analysis = analyzer.analyze_transcript(
    transcript=transcript,
    topic="Python Functions",
    user_profile=user_profile,
    research_context=research_data,
    ai_call_func=gemini_api_call
)

print(analysis['summary'])
print(analysis['key_concepts'])
print(analysis['timestamps'])
print(analysis['study_guide'])
print(analysis['quiz'])
```

## Integration with ai_lesson_service.py

### Before (Old Implementation)
```python
# Many individual methods in LessonGenerationService:
def _search_youtube_video(self, topic: str)
def _has_transcript(self, video_id: str)
def _get_youtube_transcript(self, video_id: str)
def _transcribe_with_groq(self, video_id: str)
def _parse_youtube_duration(self, duration_str: str)
def _analyze_video_transcript(self, transcript: str, request, research_data)
```

### After (Modular Implementation)
```python
# In __init__:
self.youtube_service = YouTubeService(youtube_api_key, groq_api_key)
self.video_analyzer = VideoAnalyzer()

# In _generate_video_lesson():
video_data = self.youtube_service.search_and_rank(request.step_title)
transcript = self.youtube_service.get_transcript(video_data['video_id'])
analysis = self.video_analyzer.analyze_transcript(
    transcript=transcript,
    topic=request.step_title,
    user_profile=request.user_profile,
    research_context=research_data,
    ai_call_func=self._call_gemini_api
)
```

## Benefits of Modularization

### 1. **Separation of Concerns**
- Each class has a single responsibility
- YouTube service doesn't know about Gemini
- Groq transcription can be used independently
- Quality ranker is reusable for other video sources

### 2. **Testability**
- Easy to mock individual components
- Can test quality ranking independently
- Can test transcript fetching without lesson generation
- Can test analysis without YouTube search

### 3. **Reusability**
- YouTubeQualityRanker can rank videos from any source
- TranscriptService can be extended for other platforms
- VideoAnalyzer can analyze any transcript
- GroqTranscription can transcribe any audio

### 4. **Maintainability**
- Bug fixes in one component don't affect others
- Each file ~400-500 lines (vs. 2340+ line monolith)
- Clear imports and dependencies
- Easy to find related code

### 5. **Scalability**
- Can add new video platforms easily
- Can add new quality factors without refactoring
- Can extend analyzer with new output types
- Can swap AI providers without touching video logic

## Performance Characteristics

### Time Budget
- YouTube Search: 2-3 seconds
- Quality Ranking: <1 second
- Transcript Fetch (native): 1-2 seconds
- Groq Transcription: 3-5 seconds per 10-min video
- Video Analysis: 5-10 seconds
- **Total: 11-20 seconds** (well under 25s target)

### API Quota Usage
- YouTube Data API: ~2 requests per lesson
- Groq API: Only on fallback (~5% of lessons)
- No rate limiting concerns

## Future Enhancement Opportunities

### 1. **Add YouTube Quality Persistence**
```python
# Cache quality scores for frequently searched topics
class YouTubeQualityCache:
    def get_or_rank(self, topic: str, videos: List[Dict]) -> List[Dict]
```

### 2. **Support Additional Video Platforms**
```python
# Create PlatformService base class
class VideoService:
    def search_and_rank(self, topic: str) -> Optional[Dict]
    def get_transcript(self, video_id: str) -> Optional[str]

# Implement for Udemy, Skillshare, etc.
class UdemyService(VideoService):
    ...

class VimeoService(VideoService):
    ...
```

### 3. **Enhanced Transcript Analysis**
```python
# Add semantic analysis
class SemanticAnalyzer:
    def extract_learning_objectives(self, transcript: str) -> List[str]
    def identify_prerequisites(self, transcript: str) -> List[str]
    def suggest_follow_up_topics(self, transcript: str) -> List[str]
```

### 4. **A/B Testing for Quality Scores**
```python
# Track which weight combinations produce best lessons
class QualityScoreOptimizer:
    def log_lesson_feedback(self, video_id: str, score: int, breakdown: Dict)
    def optimize_weights(self) -> Dict[str, float]
```

## Configuration

### Environment Variables
```bash
# Required
YOUTUBE_API_KEY=...
GEMINI_API_KEY=...

# Optional (for Groq transcription fallback)
GROQ_API_KEY=...

# Optional (for age-restricted videos)
YOUTUBE_COOKIES_FILE=/path/to/cookies.txt
```

### Quality Thresholds (in quality_ranker.py)
```python
MIN_VIEW_COUNT = 10000              # Videos need 10K+ views
MIN_LIKE_RATIO = 0.90               # 90%+ engagement
MIN_CHANNEL_SUBSCRIBERS = 50000     # 50K+ subscriber channels preferred
OPTIMAL_AGE_MIN_MONTHS = 6          # Videos 6 months - 3 years old
OPTIMAL_AGE_MAX_MONTHS = 36
```

## Testing

### Unit Tests (Example)
```python
def test_quality_ranker():
    ranker = YouTubeQualityRanker()

    # Create mock videos
    videos = [
        {
            'video_id': 'test1',
            'title': 'Python Basics',
            'view_count': 100000,
            'like_count': 5000,
            'subscriber_count': 500000,
            'published_at': '2024-01-01T00:00:00Z'
        }
    ]

    # Rank videos
    ranked = ranker.rank_videos(videos, "Python Functions")

    # Assert top video has quality score
    assert ranked[0]['quality_score'] > 0
    assert ranked[0]['quality_breakdown'] is not None
```

### Integration Tests (Example)
```python
def test_youtube_service_integration():
    service = YouTubeService(os.getenv('YOUTUBE_API_KEY'))

    # Search for video
    video = service.search_and_rank("Python asyncio")

    # Assert we got a video
    assert video is not None
    assert 'video_id' in video
    assert 'quality_score' in video

    # Assert transcript can be fetched
    if video['has_transcript']:
        transcript = service.get_transcript(video['video_id'])
        assert len(transcript) > 0
```

## Debugging

### Enable Detailed Logging
```python
import logging

logger = logging.getLogger('helpers.youtube')
logger.setLevel(logging.DEBUG)
```

### Common Issues

**Issue:** "yt-dlp not installed"
**Solution:** `pip install yt-dlp`

**Issue:** "FFmpeg not found"
**Solution:** Install FFmpeg from https://www.gyan.dev/ffmpeg/builds/

**Issue:** "403 Forbidden - video may be age/geo restricted"
**Solution:** Set `YOUTUBE_COOKIES_FILE` environment variable

**Issue:** "YouTube API quota exceeded"
**Solution:** Check API quotas in Google Cloud Console, consider spreading requests over time

## Conclusion

The YouTube Service Module provides a clean, testable, and maintainable solution for YouTube integration in lesson generation. The modular design allows for easy testing, reuse, and future extensions while keeping the main lesson generation service focused on its core responsibility.
