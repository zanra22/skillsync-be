"""
Video Source Fallback Service

Implements 2-tier fallback strategy for tutorial video discovery:
- Tier 1: YouTube (preferred, best transcripts, 10K/day quota)
- Tier 2: DailyMotion (fallback, 5K/day quota)

Automatically falls back to DailyMotion if:
1. YouTube search returns no results
2. YouTube videos don't meet quality threshold
3. YouTube videos are unavailable for transcription

Author: SkillSync Team
Created: November 12, 2025
"""

import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class VideoSourceFallbackService:
    """
    Orchestrates video source fallback with tracking.

    Returns:
    - Selected video metadata
    - Source used (youtube or dailymotion)
    - Fallback reason (if applicable)
    """

    def __init__(self, youtube_service, dailymotion_service):
        """
        Initialize fallback service.

        Args:
            youtube_service: YouTubeService instance
            dailymotion_service: DailyMotionAPIService instance
        """
        self.youtube_service = youtube_service
        self.dailymotion_service = dailymotion_service
        self.last_fallback_topic = None
        self.fallback_count = 0

    async def search_with_fallback(
        self,
        topic: str,
        max_results: int = 3
    ) -> Tuple[Optional[Dict], str, Optional[str]]:
        """
        Search for tutorial video with 2-tier fallback.

        Tier 1: YouTube (primary)
        Tier 2: DailyMotion (fallback)

        Args:
            topic: Topic to search for
            max_results: Number of results to consider

        Returns:
            Tuple of:
            - selected_video: Video metadata or None
            - source_used: 'youtube', 'dailymotion', or 'none'
            - fallback_reason: Reason for fallback (or None if YouTube succeeded)
        """
        logger.info(f"🎬 Video search with fallback: {topic}")
        print(f"[VideoSourceFallback] Starting search for: {topic}", flush=True)

        # Tier 1: Try YouTube
        try:
            logger.info(f"   📺 Tier 1: Trying YouTube...")
            print(f"   📺 Tier 1: Searching YouTube...", flush=True)

            youtube_video = self.youtube_service.search_and_rank(
                topic=topic,
                max_results=max_results
            )

            if youtube_video:
                logger.info(f"✅ YouTube success: {youtube_video['title'][:50]}")
                print(f"   ✅ YouTube: Found {youtube_video['video_id']}", flush=True)
                return youtube_video, 'youtube', None

            logger.warning(f"   ⚠️ No YouTube videos met quality threshold for: {topic}")
            print(f"   ⚠️ YouTube: No results or quality threshold not met, trying fallback...", flush=True)

        except Exception as e:
            logger.warning(f"   ⚠️ YouTube search error: {type(e).__name__}: {str(e)[:100]}")
            print(f"   ⚠️ YouTube error: {type(e).__name__}, trying fallback...", flush=True)

        # Tier 2: Fallback to DailyMotion
        try:
            logger.info(f"   🎥 Tier 2: Trying DailyMotion fallback...")
            print(f"   🎥 Tier 2: Searching DailyMotion...", flush=True)

            dailymotion_videos = await self.dailymotion_service.search_tutorial_videos(
                topic=topic,
                max_results=max_results
            )

            if dailymotion_videos:
                selected = dailymotion_videos[0]
                logger.warning(
                    f"⚠️ Using DailyMotion fallback for {topic}: "
                    f"{selected['title'][:50]}"
                )
                print(f"   ✅ DailyMotion: Found fallback video {selected['video_id']}", flush=True)

                # Track fallback usage
                self.last_fallback_topic = topic
                self.fallback_count += 1

                return selected, 'dailymotion', 'youtube_not_available'

            logger.error(f"   ❌ DailyMotion also failed for: {topic}")
            print(f"   ❌ DailyMotion: No results found", flush=True)
            return None, 'none', 'all_sources_failed'

        except Exception as e:
            logger.error(f"   ❌ DailyMotion fallback error: {type(e).__name__}: {str(e)}")
            print(f"   ❌ DailyMotion error: {type(e).__name__}", flush=True)
            return None, 'none', f'fallback_error: {type(e).__name__}'

    async def search_specific_source(
        self,
        topic: str,
        source: str,
        max_results: int = 3
    ) -> Optional[Dict]:
        """
        Search specific video source without fallback.

        Useful for testing or when specific source is required.

        Args:
            topic: Topic to search
            source: 'youtube' or 'dailymotion'
            max_results: Number of results to consider

        Returns:
            Selected video metadata or None
        """
        logger.debug(f"Searching {source} specifically for: {topic}")

        if source.lower() == 'youtube':
            return self.youtube_service.search_and_rank(
                topic=topic,
                max_results=max_results
            )
        elif source.lower() == 'dailymotion':
            videos = await self.dailymotion_service.search_tutorial_videos(
                topic=topic,
                max_results=max_results
            )
            return videos[0] if videos else None
        else:
            logger.error(f"Unknown video source: {source}")
            return None

    def get_statistics(self) -> Dict:
        """
        Get fallback usage statistics.

        Returns:
            Statistics dict with usage info
        """
        return {
            'fallback_count': self.fallback_count,
            'last_fallback_topic': self.last_fallback_topic,
            'service_health': {
                'youtube': 'available',
                'dailymotion': 'available'
            }
        }
