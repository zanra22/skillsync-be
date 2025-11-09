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

    def __init__(self, api_key: str, groq_api_key: Optional[str] = None):
        """
        Initialize YouTube service.

        Args:
            api_key: YouTube Data API v3 key
            groq_api_key: Optional Groq API key for transcription fallback
        """
        self.youtube_api_key = api_key
        self.groq_api_key = groq_api_key
        self.quality_ranker = YouTubeQualityRanker()
        self.transcript_service = TranscriptService(api_key, groq_api_key)
        self.last_youtube_call = 0

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
        if not self.youtube_api_key:
            logger.error("❌ YouTube API key not configured")
            return None

        try:
            from googleapiclient.discovery import build
            youtube = build('youtube', 'v3', developerKey=self.youtube_api_key)

            # Search for video
            search_query = f"{topic} tutorial programming"
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

            # Fallback: If no captioned videos, get any relevant videos
            if not search_response.get('items'):
                logger.warning("⚠️ No videos with captions found, trying without caption filter...")
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
                    return None

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

                # Check if transcript available
                has_transcript = self.transcript_service.has_transcript(video_id)

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
            ranked = self.quality_ranker.rank_videos(videos_to_rank, topic, max_results=1)

            if not ranked:
                logger.warning("❌ No videos passed quality threshold")
                # Fallback: Try Groq on best available
                if videos_to_rank:
                    best_video = videos_to_rank[0]
                    logger.warning(f"⚠️ No perfect match, trying Groq transcription on: {best_video['video_id']}")

                    if self.groq_api_key and self.transcript_service.groq_transcription:
                        transcript = self.transcript_service.groq_transcription.transcribe(
                            best_video['video_id']
                        )
                        if transcript:
                            logger.info("✅ Groq transcription successful")
                            return best_video
                        else:
                            logger.warning("❌ Groq transcription failed")
                            return None
                    else:
                        return None
                return None

            best_video = ranked[0]
            logger.info(
                f"✅ Selected video: {best_video['title'][:50]}... "
                f"(Score: {best_video.get('quality_score', 0):.2f})"
            )

            return best_video

        except Exception as e:
            logger.error(f"❌ YouTube search failed: {e}")
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
