"""
YouTube Video Search and Ranking Service - Phase E: 3-Tier Quality Filtering

Tier 1 (Premium): 500k+ views, 5k+ likes, <1 year old, 8-20 min
Tier 2 (Solid): 200k+ views, 2k+ likes, <2 years old, 5-25 min
Tier 3 (Acceptable): 50k+ views, 500+ likes, <3 years old, 5-30 min
"""

import re
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import time

from .quality_ranker import YouTubeQualityRanker

logger = logging.getLogger(__name__)


class YouTubeService:
    """
    Main YouTube service for video search and ranking (Phase E: 3-Tier Quality Filtering).
    """

    # Tier 1: Premium Content (Try First)
    TIER1_MIN_VIEWS = 500000
    TIER1_MIN_LIKES = 5000
    TIER1_MAX_AGE_YEARS = 1
    TIER1_DURATION_MIN = 8
    TIER1_DURATION_MAX = 20

    # Tier 2: Solid Content (Fallback)
    TIER2_MIN_VIEWS = 200000
    TIER2_MIN_LIKES = 2000
    TIER2_MAX_AGE_YEARS = 2
    TIER2_DURATION_MIN = 5
    TIER2_DURATION_MAX = 25

    # Tier 3: Acceptable Content (Last Resort)
    TIER3_MIN_VIEWS = 50000
    TIER3_MIN_LIKES = 500
    TIER3_MAX_AGE_YEARS = 3
    TIER3_DURATION_MIN = 5
    TIER3_DURATION_MAX = 30

    def __init__(self, api_key: str, groq_api_key: Optional[str] = None, service_account: Optional[Dict] = None):
        self.youtube_api_key = api_key
        self.groq_api_key = groq_api_key  # Kept for backward compatibility but not used
        self.service_account = service_account
        self.quality_ranker = YouTubeQualityRanker()
        self.last_youtube_call = 0
        self._youtube_service = None

    def _get_youtube_service(self):
        """Build and cache YouTube API service."""
        if self._youtube_service is not None:
            return self._youtube_service

        try:
            from googleapiclient.discovery import build
            from google.oauth2 import service_account

            # Try OAuth2 with service account first
            if self.service_account:
                try:
                    credentials = service_account.Credentials.from_service_account_info(
                        self.service_account,
                        scopes=['https://www.googleapis.com/auth/youtube.readonly']
                    )
                    self._youtube_service = build('youtube', 'v3', credentials=credentials)
                    logger.info("[OK] YouTube API using OAuth2 service account authentication")
                    return self._youtube_service
                except Exception as e:
                    logger.warning(f"[WARN] Failed to use service account auth: {e}, falling back to API key")

            # Fallback to simple API key
            if self.youtube_api_key:
                self._youtube_service = build('youtube', 'v3', developerKey=self.youtube_api_key)
                logger.info("[OK] YouTube API using simple API key (developerKey)")
                return self._youtube_service

            logger.error("[X] No YouTube credentials available")
            return None

        except Exception as e:
            logger.error(f"[X] Failed to build YouTube API service: {e}")
            return None

    def search_and_rank(
        self,
        topic: str,
        max_results: int = 3,
        include_caption_status: bool = True,
        duration_min: Optional[int] = None,
        duration_max: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Search YouTube for best tutorial video with 3-tier quality filtering.

        Tier System (tries in order, returns first match):
        - Tier 1 (Premium): 500k+ views, 5k+ likes, <1 year, 8-20 min
        - Tier 2 (Solid): 200k+ views, 2k+ likes, <2 years, 5-25 min
        - Tier 3 (Acceptable): 50k+ views, 500+ likes, <3 years, 5-30 min

        Args:
            topic: Topic to search for
            max_results: Number of top results to consider (not used in tier system)
            duration_min: Override minimum duration (optional)
            duration_max: Override maximum duration (optional)

        Returns:
            Best video from highest tier available, or None
        """
        timestamp = time.time()
        logger.info(f"[search_and_rank] CALLED at {timestamp} with topic='{topic}'")

        youtube = self._get_youtube_service()
        if not youtube:
            logger.error("YouTube API not available (no credentials configured)")
            return None

        logger.info(f"[search_and_rank] YouTube service initialized, proceeding with 3-tier search...")

        try:
            # Search for videos
            search_query = f"{topic}"
            logger.info(f"🔍 Searching YouTube: {search_query}")

            search_response = youtube.search().list(
                q=search_query,
                part='snippet',
                type='video',
                maxResults=25,  # Get more results for tier filtering
                order='relevance',
                videoDuration='medium',  # 4-20 minutes
                videoDefinition='high',
                relevanceLanguage='en'
            ).execute()

            if not search_response.get('items'):
                logger.warning("⚠️ No YouTube videos found for query")
                return None

            logger.info(f"[search_and_rank] Search found {len(search_response['items'])} videos")

            # Get detailed stats for ALL results (for tier filtering)
            video_ids = [item['id']['videoId'] for item in search_response['items']]
            video_response = youtube.videos().list(
                id=','.join(video_ids),
                part='snippet,contentDetails,statistics'
            ).execute()

            if not video_response.get('items'):
                return None

            # Build all video metadata
            all_videos = []
            for video_details in video_response['items']:
                video_data = self._build_video_metadata(video_details, youtube)
                if video_data:
                    all_videos.append(video_data)

            if not all_videos:
                logger.warning("❌ No valid videos found")
                return None

            logger.info(f"📊 Built metadata for {len(all_videos)} videos")

            # Try Tier 1 (Premium)
            tier1_videos = self._filter_by_tier(all_videos, tier=1, duration_min=duration_min, duration_max=duration_max)
            if tier1_videos:
                logger.info(f"✅ Found {len(tier1_videos)} Tier 1 (Premium) videos")
                best = self._rank_and_select(tier1_videos, topic)
                if best:
                    logger.info(f"🏆 Selected Tier 1 video: {best['title'][:50]}...")
                    return best

            # Try Tier 2 (Solid)
            tier2_videos = self._filter_by_tier(all_videos, tier=2, duration_min=duration_min, duration_max=duration_max)
            if tier2_videos:
                logger.info(f"✅ Found {len(tier2_videos)} Tier 2 (Solid) videos")
                best = self._rank_and_select(tier2_videos, topic)
                if best:
                    logger.info(f"🥈 Selected Tier 2 video: {best['title'][:50]}...")
                    return best

            # Try Tier 3 (Acceptable)
            tier3_videos = self._filter_by_tier(all_videos, tier=3, duration_min=duration_min, duration_max=duration_max)
            if tier3_videos:
                logger.info(f"✅ Found {len(tier3_videos)} Tier 3 (Acceptable) videos")
                best = self._rank_and_select(tier3_videos, topic)
                if best:
                    logger.info(f"🥉 Selected Tier 3 video: {best['title'][:50]}...")
                    return best

            # No videos passed any tier
            logger.warning("❌ No videos passed tier filters")
            return None

        except Exception as e:
            logger.error(f"❌ YouTube search failed: {type(e).__name__}: {e}", exc_info=True)
            return None

    def _build_video_metadata(self, video_details: Dict, youtube) -> Optional[Dict]:
        """Build video metadata dict from YouTube API response."""
        try:
            video_id = video_details['id']
            duration_minutes = self._parse_youtube_duration(
                video_details['contentDetails']['duration']
            )

            # Get channel info for authority scoring
            try:
                channel_response = youtube.channels().list(
                    part='statistics,snippet',
                    forUsername=video_details['snippet']['channelTitle']
                ).execute()

                channel_data = {}
                if channel_response.get('items'):
                    channel_stats = channel_response['items'][0]['statistics']
                    channel_snippet = channel_response['items'][0]['snippet']
                    channel_data = {
                        'subscriber_count': int(channel_stats.get('subscriberCount', 0)),
                        'is_verified': 'Verified' in channel_snippet.get('description', ''),
                    }
                else:
                    channel_data = {'subscriber_count': 0, 'is_verified': False}

            except Exception:
                channel_data = {'subscriber_count': 0, 'is_verified': False}

            # Build video metadata
            video_data = {
                'video_id': video_id,
                'title': video_details['snippet']['title'],
                'description': video_details['snippet']['description'],
                'channel': video_details['snippet']['channelTitle'],
                'thumbnail_url': video_details['snippet']['thumbnails']['high']['url'],
                'video_url': f'https://www.youtube.com/watch?v={video_id}',
                'embed_url': f'https://www.youtube.com/embed/{video_id}',
                'duration_minutes': duration_minutes,
                'view_count': int(video_details['statistics'].get('viewCount', 0)),
                'like_count': int(video_details['statistics'].get('likeCount', 0)),
                'published_at': video_details['snippet']['publishedAt'],
                **channel_data,
            }

            return video_data

        except Exception as e:
            logger.debug(f"Failed to build video metadata: {e}")
            return None

    def _filter_by_tier(
        self,
        videos: List[Dict],
        tier: int,
        duration_min: Optional[int] = None,
        duration_max: Optional[int] = None
    ) -> List[Dict]:
        """
        Filter videos by tier requirements.

        Args:
            videos: List of video metadata dicts
            tier: Tier number (1, 2, or 3)
            duration_min: Override minimum duration
            duration_max: Override maximum duration

        Returns:
            List of videos that pass tier requirements
        """
        # Get tier thresholds
        if tier == 1:
            min_views = self.TIER1_MIN_VIEWS
            min_likes = self.TIER1_MIN_LIKES
            max_age_years = self.TIER1_MAX_AGE_YEARS
            dur_min = duration_min or self.TIER1_DURATION_MIN
            dur_max = duration_max or self.TIER1_DURATION_MAX
        elif tier == 2:
            min_views = self.TIER2_MIN_VIEWS
            min_likes = self.TIER2_MIN_LIKES
            max_age_years = self.TIER2_MAX_AGE_YEARS
            dur_min = duration_min or self.TIER2_DURATION_MIN
            dur_max = duration_max or self.TIER2_DURATION_MAX
        elif tier == 3:
            min_views = self.TIER3_MIN_VIEWS
            min_likes = self.TIER3_MIN_LIKES
            max_age_years = self.TIER3_MAX_AGE_YEARS
            dur_min = duration_min or self.TIER3_DURATION_MIN
            dur_max = duration_max or self.TIER3_DURATION_MAX
        else:
            return []

        filtered = []
        for video in videos:
            # Check views
            if video['view_count'] < min_views:
                continue

            # Check likes
            if video['like_count'] < min_likes:
                continue

            # Check like ratio (maintain ~1% minimum)
            like_ratio = video['like_count'] / max(video['view_count'], 1)
            if like_ratio < 0.005:  # 0.5% minimum (allowing some flexibility)
                continue

            # Check age
            try:
                pub_date = datetime.fromisoformat(video['published_at'].replace('Z', '+00:00'))
                age_years = (datetime.now(pub_date.tzinfo) - pub_date).days / 365.25
                if age_years > max_age_years:
                    continue
            except Exception:
                # If can't parse date, skip age check
                pass

            # Check duration
            duration = video['duration_minutes']
            if duration < dur_min or duration > dur_max:
                continue

            # Passed all checks
            filtered.append(video)

        return filtered

    def _rank_and_select(self, videos: List[Dict], topic: str) -> Optional[Dict]:
        """
        Rank videos and select the best one.

        Args:
            videos: List of video metadata dicts
            topic: Search topic for relevance scoring

        Returns:
            Best video or None
        """
        if not videos:
            return None

        # Use quality ranker to score videos
        ranked = self.quality_ranker.rank_videos(videos, topic, max_results=1)

        if ranked:
            best = ranked[0]
            logger.info(
                f"   Video: {best['title'][:50]}... "
                f"Score: {best.get('quality_score', 0):.2f}, "
                f"Views: {best['view_count']:,}, "
                f"Likes: {best['like_count']:,}"
            )
            return best

        # If no videos passed ranking, return best available
        if videos:
            return videos[0]

        return None

    def _parse_youtube_duration(self, duration_str: str) -> int:
        """
        Parse ISO 8601 duration (PT15M33S) to minutes.

        Args:
            duration_str: ISO 8601 duration string

        Returns:
            Duration in minutes
        """
        minutes = 0
        hours_match = re.search(r'(\d+)H', duration_str)
        minutes_match = re.search(r'(\d+)M', duration_str)

        if hours_match:
            minutes += int(hours_match.group(1)) * 60
        if minutes_match:
            minutes += int(minutes_match.group(1))

        return minutes or 10  # Default to 10 if parsing fails
