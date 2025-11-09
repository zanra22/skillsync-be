"""
YouTube Service Module

Provides comprehensive YouTube video search, quality ranking, and transcript extraction
for lesson generation. Integrates multi-factor quality ranking with transcript availability.

Features:
- Smart video filtering (top-3 with quality criteria)
- 5-factor quality ranking (views, engagement, channel, transcript, recency)
- Transcript extraction (YouTube captions + Groq Whisper fallback)
- Detailed video metadata and quality metrics

Classes:
- YouTubeService: Main service for video search and ranking
- TranscriptService: YouTube transcript fetching and fallback
- GroqTranscription: Groq Whisper API wrapper for video transcription
- VideoAnalyzer: Video transcript analysis with AI
"""

from .youtube_service import YouTubeService
from .transcript_service import TranscriptService
from .quality_ranker import YouTubeQualityRanker
from .groq_transcription import GroqTranscription
from .video_analyzer import VideoAnalyzer

__all__ = [
    'YouTubeService',
    'TranscriptService',
    'YouTubeQualityRanker',
    'GroqTranscription',
    'VideoAnalyzer',
]
