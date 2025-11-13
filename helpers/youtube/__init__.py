"""
YouTube Service Module (Phase D: Simplified)

Provides YouTube video search with quality ranking for lesson generation.
Phase D changes: Removed transcript extraction (videos used as reference only).

Features:
- Smart video filtering with duration-aware selection
- 5-factor quality ranking (views, engagement, channel authority, duration, recency)
- Metadata extraction (title, description, channel, view count, duration)
- Detailed video metadata for embedding in lessons

Classes:
- YouTubeService: Main service for video search and ranking
- YouTubeQualityRanker: 5-factor quality assessment
- VideoAnalyzer: Video content analysis (kept for potential future use)

Deprecated (removed Phase D):
- TranscriptService: No longer needed (videos used as reference material)
- GroqTranscription: Removed to eliminate bot detection issues from yt-dlp
"""

from .youtube_service import YouTubeService
from .quality_ranker import YouTubeQualityRanker
from .video_analyzer import VideoAnalyzer

__all__ = [
    'YouTubeService',
    'YouTubeQualityRanker',
    'VideoAnalyzer',
]
