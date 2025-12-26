"""
YouTube Video Search and Ranking Service

Handles video discovery with smart filtering and quality ranking.
Integrates with YouTubeQualityRanker for 5-factor quality assessment.

Phase D: Simplified for metadata-only (no transcript fetching)

Key features:
- Search with preferred caption filtering
- Fallback to uncaptioned videos if needed
- Duration-aware filtering (beginner: 5-15min, advanced: 40-60min)
- Top-3 quality ranking
- Videos embedded as reference material (URLs only)
"""

import re
import logging
from typing import Optional, Dict, List
from datetime import datetime
import time

from .quality_ranker import YouTubeQualityRanker

logger = logging.getLogger(__name__)


class YouTubeService:
    """
    Main YouTube service for video search and ranking (Phase E: 3-Tier Quality Filtering).

    Responsibilities:
    - Search YouTube API with 3-tier quality filtering
    - Tier 1: Premium (500k+ views, 5k+ likes, 1 year old max)
    - Tier 2: Solid (200k+ views, 2k+ likes, 2 years old max)
    - Tier 3: Acceptable (50k+ views, 500+ likes, 3 years old max)
    - Rank videos using quality ranker

    Phase E Changes:
    - Added 3-tier fallback filtering system
    - Flexible duration ranges (5-30 min)
    - View/like thresholds per tier
    - Recency filtering per tier
    - Removed Dailymotion references
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
        """
        Initialize YouTube service.

        Args:
            api_key: YouTube Data API v3 key (legacy, for backward compatibility)
            groq_api_key: Optional Groq API key (deprecated - no longer used)
            service_account: Optional Google Cloud service account dict with OAuth2 credentials
        """
        self.youtube_api_key = api_key
        self.groq_api_key = groq_api_key  # Kept for backward compatibility but not used
        self.service_account = service_account
        self.quality_ranker = YouTubeQualityRanker()
        self.last_youtube_call = 0
        self._youtube_service = None  # Lazy loaded YouTube API service

    def _get_youtube_service(self):
        """
        Build and cache YouTube API service using best available credentials.

        Priority:
        1. OAuth2 with Google Cloud service account (for server-to-server auth)
        2. Simple API key (legacy fallback)
        """
        if self._youtube_service is not None:
            return self._youtube_service

        try:
            from googleapiclient.discovery import build
            from google.oauth2 import service_account

            # Try OAuth2 with service account first (prevents bot detection)
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

            logger.error("[X] No YouTube credentials available (no service account or API key)")
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
            max_results: Number of top results to consider
            duration_min: Override minimum duration (optional)
            duration_max: Override maximum duration (optional)

        Returns:
            Best video from highest tier available, or None
        """
        timestamp = time.time()
        logger.info(f"[search_and_rank] CALLED at {timestamp} with topic='{topic}', max_results={max_results}")
        print(f"[search_and_rank] CALLED at {timestamp} with topic='{topic}'", flush=True)

        youtube = self._get_youtube_service()
        if not youtube:
            logger.error("YouTube API not available (no credentials configured)")
            return None

        logger.info(f"[search_and_rank] YouTube service initialized at {timestamp}, proceeding with search...")
        print(f"[search_and_rank] YouTube service initialized, proceeding with search...", flush=True)

        try:

            # Search for video
            # Note: Keep query simple to ensure caption filter returns results
            # Adding "tutorial programming" too restrictive and causes zero results with caption filter
            search_query = f"{topic}"
            logger.info(f"🔍 Searching YouTube: {search_query}")

            # Search for videos (Phase D: caption filter removed)
            # We no longer require captions since videos are used as reference material only
            search_response = youtube.search().list(
                q=search_query,
                part='snippet',
                type='video',
                maxResults=10,  # Get more to filter from
                order='relevance',
                videoDuration='medium',  # 4-20 minutes
                videoDefinition='high',
                relevanceLanguage='en'
            ).execute()

            # Check if search returned results
            if not search_response.get('items'):
                logger.warning("⚠️ No YouTube videos found for query")
                print("⚠️ No YouTube videos found at all", flush=True)
                return None

            found_count = len(search_response.get('items', []))
            logger.info(f"[search_and_rank] Search found {found_count} videos")
            print(f"[search_and_rank] Found {found_count} videos", flush=True)

            # Get detailed stats for top N results
            video_ids = [item['id']['videoId'] for item in search_response['items'][:max_results]]
            video_response = youtube.videos().list(
                id=','.join(video_ids),
                part='snippet,contentDetails,statistics'
            ).execute()

            if not video_response.get('items'):
                return None

            # Enrich videos with channel info and duration filtering
            videos_to_rank = []
            for video_details in video_response['items']:
                video_id = video_details['id']
                duration_minutes = self._parse_youtube_duration(
                    video_details['contentDetails']['duration']
                )

                # PHASE B: Filter by duration if specified
                # This enables adaptive video selection based on user's skill level and time commitment
                if duration_min is not None or duration_max is not None:
                    if duration_min and duration_minutes < duration_min:
                        logger.debug(f"   ⏭️  Video too short ({duration_minutes}m < {duration_min}m), skipping")
                        continue
                    if duration_max and duration_minutes > duration_max:
                        logger.debug(f"   ⏭️  Video too long ({duration_minutes}m > {duration_max}m), skipping")
                        continue
                    logger.debug(f"   ✅ Duration matches: {duration_minutes}m ({duration_min}-{duration_max}m)")

                try:
                    # Get channel info for authority scoring
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

                except Exception as e:
                    logger.debug(f"Could not fetch channel data: {e}")
                    channel_data = {
                        'subscriber_count': 0,
                        'is_verified': False,
                    }

                # Build video metadata (Phase D: removed caption filter requirement)
                # Transcripts are no longer required - we use videos as reference material only
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

                logger.info(
                    f"📊 Video {video_id}: {duration_minutes}m duration, "
                    f"views={video_data['view_count']:,}, "
                    f"likes={video_data['like_count']:,}"
                )

                videos_to_rank.append(video_data)

            if not videos_to_rank:
                logger.warning("❌ No videos to rank")
                return None

            # Rank videos by quality (Phase B: no longer requires transcripts)
            logger.info(f"[search_and_rank] About to rank {len(videos_to_rank)} videos")
            print(f"[search_and_rank] About to rank {len(videos_to_rank)} videos with topic '{topic}'", flush=True)
            ranked = self.quality_ranker.rank_videos(videos_to_rank, topic, max_results=1)
            logger.info(f"[search_and_rank] Quality ranking returned {len(ranked) if ranked else 0} videos")
            print(f"[search_and_rank] Quality ranking returned {len(ranked) if ranked else 0} videos", flush=True)

            if not ranked:
                logger.warning("❌ No videos passed quality threshold")
                print("❌ No videos passed quality threshold", flush=True)
                # PHASE B: No fallback to Groq transcription - we don't need transcripts anymore
                # If no videos passed quality, return None and let lesson generation skip YouTube video
                if videos_to_rank:
                    best_video = videos_to_rank[0]
                    logger.info(f"⚠️ No perfect match, returning best available: {best_video['video_id']}")
                    return best_video
                return None

            best_video = ranked[0]
            logger.info(
                f"✅ Selected video: {best_video['title'][:50]}... "
                f"(Score: {best_video.get('quality_score', 0):.2f})"
            )
            print(f"✅ [search_and_rank] SUCCESS: Selected video {best_video['video_id']} with score {best_video.get('quality_score', 0):.2f}", flush=True)

            return best_video

        except Exception as e:
            logger.error(f"❌ YouTube search failed: {type(e).__name__}: {e}", exc_info=True)
            print(f"❌ [search_and_rank] EXCEPTION: {type(e).__name__}: {str(e)[:200]}", flush=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
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

