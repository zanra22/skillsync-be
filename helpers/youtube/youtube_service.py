"""
YouTube Video Search and Ranking Service

Handles video discovery with smart filtering and quality ranking.
Integrates with YouTubeQualityRanker for 5-factor quality assessment.

Key features:
- Search with preferred caption filtering
- Fallback to uncaptioned videos if needed
- Top-3 quality ranking
- Groq transcription fallback
"""

import re
import logging
from typing import Optional, Dict, List
from datetime import datetime
import time

from .quality_ranker import YouTubeQualityRanker
from .transcript_service import TranscriptService

logger = logging.getLogger(__name__)


class YouTubeService:
    """
    Main YouTube service for video search and ranking.

    Responsibilities:
    - Search YouTube API
    - Filter by quality criteria
    - Rank videos using quality ranker
    - Integrate with transcript service for fallback
    """

    def __init__(self, api_key: str, groq_api_key: Optional[str] = None, service_account: Optional[Dict] = None):
        """
        Initialize YouTube service.

        Args:
            api_key: YouTube Data API v3 key (legacy, for backward compatibility)
            groq_api_key: Optional Groq API key for transcription fallback
            service_account: Optional Google Cloud service account dict with OAuth2 credentials
        """
        self.youtube_api_key = api_key
        self.groq_api_key = groq_api_key
        self.service_account = service_account
        self.quality_ranker = YouTubeQualityRanker()
        self.transcript_service = TranscriptService(api_key, groq_api_key, service_account=service_account)
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

    def search_and_rank(self, topic: str, max_results: int = 3) -> Optional[Dict]:
        """
        Search YouTube for best tutorial video with smart filtering.

        Priority filter (top 3 results):
        1. Has transcript (YouTube captions)
        2. Like ratio > 0.85 (quality content)
        3. View count > 10,000 (established content)

        Fallback: Try Groq transcription on top result (once)
        Skip: If Groq fails, skip YouTube (don't block generation)

        Args:
            topic: Topic to search for
            max_results: Number of top results to consider

        Returns:
            Video metadata with quality indicators or None
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

            # First try: Get videos WITH captions
            search_response = youtube.search().list(
                q=search_query,
                part='snippet',
                type='video',
                maxResults=10,  # Get more to filter from
                order='relevance',
                videoDuration='medium',  # 4-20 minutes
                videoDefinition='high',
                videoCaption='closedCaption',  # Prefer captioned videos
                relevanceLanguage='en'
            ).execute()

            # Track if caption filter search returned results
            caption_filter_worked = bool(search_response.get('items'))
            logger.info(f"[search_and_rank] Caption filter worked: {caption_filter_worked}, found {len(search_response.get('items', []))} videos")
            print(f"[search_and_rank] Caption filter worked: {caption_filter_worked}", flush=True)

            # Fallback: If no captioned videos, get any relevant videos
            if not search_response.get('items'):
                logger.warning("⚠️ No videos with captions found, trying without caption filter...")
                print("⚠️ No videos with captions found, trying without caption filter...", flush=True)
                search_response = youtube.search().list(
                    q=search_query,
                    part='snippet',
                    type='video',
                    maxResults=10,
                    order='relevance',
                    videoDuration='medium',
                    videoDefinition='high',
                    relevanceLanguage='en'
                ).execute()

                if not search_response.get('items'):
                    logger.warning("⚠️ No YouTube videos found")
                    print("⚠️ No YouTube videos found at all", flush=True)
                    return None

                logger.info(f"[search_and_rank] Fallback search found {len(search_response.get('items', []))} videos")
                print(f"[search_and_rank] Fallback search found {len(search_response.get('items', []))} videos", flush=True)

            # Get detailed stats for top N results
            video_ids = [item['id']['videoId'] for item in search_response['items'][:max_results]]
            video_response = youtube.videos().list(
                id=','.join(video_ids),
                part='snippet,contentDetails,statistics'
            ).execute()

            if not video_response.get('items'):
                return None

            # Enrich videos with channel and transcript info
            videos_to_rank = []
            for video_details in video_response['items']:
                video_id = video_details['id']

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

                # Determine transcript availability
                # OPTIMIZATION: If caption filter worked, trust YouTube's API - no need to call transcript API
                # Calling has_transcript() on every video causes rate limiting (429 errors)
                if caption_filter_worked:
                    # Videos from caption filter search are guaranteed to have captions
                    has_transcript = True
                    logger.debug(f"   ✅ Video from caption-filtered search (has transcripts)")
                else:
                    # Fallback search: skip transcript checking to avoid rate limiting
                    # These videos may not have transcripts anyway
                    has_transcript = False
                    logger.debug(f"   ⚠️ Video from fallback search (no transcript verification)")

                # Build video metadata
                video_data = {
                    'video_id': video_id,
                    'title': video_details['snippet']['title'],
                    'description': video_details['snippet']['description'],
                    'channel': video_details['snippet']['channelTitle'],
                    'thumbnail_url': video_details['snippet']['thumbnails']['high']['url'],
                    'video_url': f'https://www.youtube.com/watch?v={video_id}',
                    'embed_url': f'https://www.youtube.com/embed/{video_id}',
                    'duration_minutes': self._parse_youtube_duration(
                        video_details['contentDetails']['duration']
                    ),
                    'view_count': int(video_details['statistics'].get('viewCount', 0)),
                    'like_count': int(video_details['statistics'].get('likeCount', 0)),
                    'published_at': video_details['snippet']['publishedAt'],
                    'has_transcript': has_transcript,
                    **channel_data,
                }

                logger.info(
                    f"📊 Video {video_id}: views={video_data['view_count']:,}, "
                    f"likes={video_data['like_count']:,}, "
                    f"transcript={'✅' if has_transcript else '❌'}"
                )

                videos_to_rank.append(video_data)

            if not videos_to_rank:
                logger.warning("❌ No videos to rank")
                return None

            # Rank videos by quality
            logger.info(f"[search_and_rank] About to rank {len(videos_to_rank)} videos")
            print(f"[search_and_rank] About to rank {len(videos_to_rank)} videos with topic '{topic}'", flush=True)
            ranked = self.quality_ranker.rank_videos(videos_to_rank, topic, max_results=1)
            logger.info(f"[search_and_rank] Quality ranking returned {len(ranked) if ranked else 0} videos")
            print(f"[search_and_rank] Quality ranking returned {len(ranked) if ranked else 0} videos", flush=True)

            if not ranked:
                logger.warning("❌ No videos passed quality threshold")
                print("❌ No videos passed quality threshold, trying Groq fallback", flush=True)
                # Fallback: Try Groq on best available
                if videos_to_rank:
                    best_video = videos_to_rank[0]
                    logger.warning(f"⚠️ No perfect match, trying Groq transcription on: {best_video['video_id']}")
                    print(f"⚠️ No perfect match, trying Groq transcription on: {best_video['video_id']}", flush=True)

                    if self.groq_api_key and self.transcript_service.groq_transcription:
                        print(f"[search_and_rank] Calling groq_transcription.transcribe() for {best_video['video_id']}", flush=True)
                        transcript = self.transcript_service.groq_transcription.transcribe(
                            best_video['video_id']
                        )
                        if transcript:
                            logger.info("✅ Groq transcription successful")
                            print("✅ Groq transcription successful", flush=True)
                            return best_video
                        else:
                            logger.warning("❌ Groq transcription failed")
                            print("❌ Groq transcription failed", flush=True)
                            return None
                    else:
                        print("[search_and_rank] Groq not available (no API key or groq_transcription)", flush=True)
                        return None
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

    def get_transcript(self, video_id: str) -> Optional[str]:
        """
        Get transcript for a video (with fallback).

        Args:
            video_id: YouTube video ID

        Returns:
            Transcript text or None
        """
        return self.transcript_service.get_transcript(video_id)
