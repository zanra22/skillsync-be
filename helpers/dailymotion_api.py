"""
DailyMotion API Integration Service

Fallback video source for YouTube with 5,000 requests/day quota.

Features:
- FREE API (no authentication required for public search)
- 5,000 requests/day quota (sufficient for fallback use)
- Quality video filtering
- Tutorial-focused search

Author: SkillSync Team
Created: November 12, 2025
"""

import httpx
from typing import Optional, Dict, List
import logging
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class DailyMotionAPIService:
    """
    DailyMotion API integration for video fallback when YouTube unavailable.

    Rate Limits: 5,000 requests/day (excellent for fallback use)
    API Documentation: https://developer.dailymotion.com/
    """

    BASE_URL = "https://api.dailymotion.com"

    def __init__(self):
        """Initialize DailyMotion API service"""
        self.timeout = httpx.Timeout(10.0, connect=5.0)
        self.headers = {
            'User-Agent': 'SkillSync-LearningPlatform/1.0',
            'Accept': 'application/json'
        }

    async def search_videos(
        self,
        query: str,
        max_results: int = 5,
        sort: str = 'relevance',
        min_views: int = 1000
    ) -> List[Dict]:
        """
        Search DailyMotion for tutorial videos.

        Args:
            query: Search query (e.g., 'Python tutorial', 'JavaScript basics')
            max_results: Maximum results to return (default: 5)
            sort: Sort order - 'relevance', 'trending', 'recent' (default: 'relevance')
            min_views: Minimum view count filter (default: 1000)

        Returns:
            List of video metadata dicts
        """
        try:
            logger.info(f"🔍 DailyMotion Search: {query}")

            params = {
                'search': query,
                'limit': 20,  # Fetch more, filter later
                'sort': sort,
                'fields': 'id,title,description,duration,views_total,ratings_total,allow_embed,thumbnail_120_url,thumbnail_240_url,audience'
            }

            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(
                    f"{self.BASE_URL}/videos",
                    params=params
                )
                response.raise_for_status()
                data = response.json()

            videos = data.get('list', [])

            # Filter videos
            filtered_videos = [
                video for video in videos
                if self._is_valid_video(video, min_views)
            ]

            # Format results
            results = []
            for video in filtered_videos[:max_results]:
                formatted = self._format_video(video)
                if formatted:
                    results.append(formatted)

            logger.info(f"✅ DailyMotion: Found {len(results)} videos for: {query}")
            print(f"   ✅ [DailyMotion] Found {len(results)} videos", flush=True)
            return results

        except httpx.TimeoutException:
            logger.warning(f"⏱️ DailyMotion search timeout for: {query}")
            print(f"   ⏱️ [DailyMotion] Search timeout", flush=True)
            return []
        except httpx.HTTPError as e:
            logger.warning(f"⚠️ DailyMotion HTTP error: {e}")
            print(f"   ⚠️ [DailyMotion] HTTP error: {type(e).__name__}", flush=True)
            return []
        except Exception as e:
            logger.error(f"❌ DailyMotion search error: {str(e)}")
            print(f"   ❌ [DailyMotion] Error: {type(e).__name__}: {str(e)[:100]}", flush=True)
            return []

    async def search_tutorial_videos(
        self,
        topic: str,
        max_results: int = 5
    ) -> List[Dict]:
        """
        Search specifically for tutorial videos on DailyMotion.

        Args:
            topic: Topic to search for
            max_results: Maximum results

        Returns:
            List of tutorial videos
        """
        # Add tutorial keywords for better filtering
        query = f"{topic} tutorial"
        return await self.search_videos(
            query=query,
            max_results=max_results,
            sort='relevance',
            min_views=1000
        )

    def _is_valid_video(self, video: Dict, min_views: int = 1000) -> bool:
        """
        Validate if video meets quality criteria.

        Criteria:
        - Has views
        - Views > min_views threshold
        - Video is embeddable (allow_embed = True)
        - Has reasonable duration (not too short, not too long)
        """
        try:
            views = video.get('views_total', 0)
            if views < min_views:
                return False

            # Check if video is embeddable
            if not video.get('allow_embed', False):
                return False

            # Check duration (4-60 minutes = 240-3600 seconds)
            duration = video.get('duration', 0)
            if duration < 240 or duration > 3600:
                return False

            return True
        except Exception as e:
            logger.debug(f"Error validating video: {e}")
            return False

    def _format_video(self, video: Dict) -> Optional[Dict]:
        """
        Format DailyMotion video data for standardized output.

        Args:
            video: Raw video data from API

        Returns:
            Formatted video dict
        """
        try:
            video_id = video.get('id')
            title = video.get('title', '')
            description = video.get('description', '')
            duration = video.get('duration', 0)
            views = video.get('views_total', 0)
            ratings = video.get('ratings_total', 0)

            return {
                'video_id': video_id,
                'title': title,
                'description': description,
                'source': 'dailymotion',
                'video_url': f'https://www.dailymotion.com/video/{video_id}',
                'embed_url': f'https://www.dailymotion.com/embed/video/{video_id}',
                'thumbnail_url': video.get('thumbnail_240_url'),
                'duration_minutes': duration // 60,
                'view_count': views,
                'rating_count': ratings,
                'audience': video.get('audience', 'general'),
                'has_transcript': False,  # DailyMotion doesn't provide transcripts via API
                'caption_filter_matched': False,
            }
        except Exception as e:
            logger.error(f"Error formatting video: {str(e)}")
            return None

    async def get_video_details(self, video_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific video.

        Args:
            video_id: DailyMotion video ID

        Returns:
            Detailed video data
        """
        try:
            params = {
                'fields': 'id,title,description,duration,views_total,ratings_total,created_time,allow_embed,owner.id,owner.username'
            }

            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(
                    f"{self.BASE_URL}/video/{video_id}",
                    params=params
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error fetching video details: {str(e)}")
            return None


# Example usage
if __name__ == "__main__":
    import asyncio

    async def test_dailymotion():
        service = DailyMotionAPIService()

        print("\n🔍 Testing DailyMotion API Integration\n")

        # Search for Python tutorial videos
        print("🐍 Searching Python tutorial videos...")
        videos = await service.search_tutorial_videos(
            topic="Python",
            max_results=5
        )

        print(f"\n✓ Found {len(videos)} videos\n")

        for i, video in enumerate(videos, 1):
            print(f"Video {i}:")
            print(f"  Title: {video['title']}")
            print(f"  Views: 👁️ {video['view_count']:,}")
            print(f"  Duration: ⏱️ {video['duration_minutes']} min")
            print(f"  Rating Count: ⭐ {video['rating_count']}")
            print(f"  URL: {video['video_url']}")
            print()

    asyncio.run(test_dailymotion())
