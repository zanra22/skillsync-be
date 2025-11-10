"""
YouTube Transcript Service

Handles transcript fetching from YouTube with fallback to Groq Whisper.

Features:
- YouTube caption fetching (youtube-transcript-api)
- Transcript availability checking
- Groq Whisper fallback for videos without captions
- Rate limiting to prevent API throttling
"""

import logging
from typing import Optional
import time

from .groq_transcription import GroqTranscription

logger = logging.getLogger(__name__)


class TranscriptService:
    """
    Manages YouTube transcript fetching with fallback strategies.

    Priority:
    1. YouTube native captions (fast, free)
    2. Groq Whisper transcription (slower, but reliable)
    """

    def __init__(self, youtube_api_key: str, groq_api_key: Optional[str] = None, service_account: Optional[dict] = None):
        """
        Initialize transcript service.

        Args:
            youtube_api_key: YouTube API key (for context)
            groq_api_key: Optional Groq API key for fallback transcription
            service_account: Optional Google service account dict for YouTube OAuth2 authentication
        """
        print(f"[TranscriptService.__init__] CALLED", flush=True)
        print(f"[TranscriptService.__init__] groq_api_key: {bool(groq_api_key)}", flush=True)
        print(f"[TranscriptService.__init__] service_account: {bool(service_account)}", flush=True)

        self.youtube_api_key = youtube_api_key
        self.groq_api_key = groq_api_key
        self.service_account = service_account

        if groq_api_key:
            print(f"[TranscriptService.__init__] Creating GroqTranscription with service_account", flush=True)
            self.groq_transcription = GroqTranscription(groq_api_key, service_account=service_account)
        else:
            print(f"[TranscriptService.__init__] Skipping GroqTranscription - groq_api_key is None", flush=True)
            self.groq_transcription = None

        self.last_youtube_call = 0

    def has_transcript(self, video_id: str) -> bool:
        """
        Quick check if video has accessible transcript.

        Actually tries to fetch first few entries to verify it works.
        Returns True if transcript available, False otherwise.

        RATE LIMITING: Adds delay between checks to prevent 429 errors
        from YouTube's transcript API.

        Args:
            video_id: YouTube video ID

        Returns:
            True if transcript is available, False otherwise
        """
        # RATE LIMITING: Prevent 429 errors from rapid transcript checks
        # Each call to YouTubeTranscriptApi.get_transcript() hits YouTube's caption endpoint
        # Without rate limiting, checking 10 videos = 10 rapid requests = 429 error
        current_time = time.time()
        time_since_last_call = current_time - self.last_youtube_call

        # 1 second minimum between calls to transcript API
        if time_since_last_call < 1:
            wait_time = 1 - time_since_last_call
            logger.debug(f"⏳ Rate limiting has_transcript(): waiting {wait_time:.2f}s...")
            time.sleep(wait_time)

        self.last_youtube_call = time.time()

        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            # Actually try to fetch transcript (not just list)
            # This catches XML parsing errors before we commit to the video
            transcript = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=['en', 'en-US', 'en-GB']  # English variants
            )

            # Verify we got some data
            return len(transcript) > 0

        except Exception as e:
            # If any error (XML parse, not found, 429 rate limit, etc), assume no transcript
            logger.debug(f"   No accessible transcript for {video_id}: {str(e)[:50]}")
            return False

    def get_transcript(self, video_id: str, skip_groq_fallback: bool = False) -> Optional[str]:
        """
        Fetch YouTube video transcript/captions.

        Uses youtube-transcript-api first (FREE, no API key needed).
        Falls back to Groq Whisper if captions unavailable (unless skip_groq_fallback=True).

        With rate limiting. Only 1 Groq attempt to avoid spam.

        Args:
            video_id: YouTube video ID
            skip_groq_fallback: If True, don't use Groq transcription (for caption-filtered videos)

        Returns:
            Transcript text or None if all methods fail
        """
        # RATE LIMITING: Prevent 429 errors from rapid requests
        current_time = time.time()
        time_since_last_call = current_time - self.last_youtube_call

        if time_since_last_call < 5:
            wait_time = 5 - time_since_last_call
            logger.info(f"⏳ YouTube rate limiting: waiting {wait_time:.1f}s before next request...")
            time.sleep(wait_time)

        self.last_youtube_call = time.time()

        # DB hygiene: close any old/stale DB connections before long network I/O
        try:
            from django.db import close_old_connections
            close_old_connections()
        except Exception:
            # Best-effort: if Django isn't available in this execution context, continue
            logger.debug("⚠️ close_old_connections() unavailable or failed - continuing")

        # Try YouTube native captions first
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            logger.info(f"📝 [get_transcript] Fetching transcript for video: {video_id}")
            print(f"[get_transcript] Attempting youtube-transcript-api for {video_id}", flush=True)

            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)

            # Combine all transcript entries
            full_transcript = " ".join([entry['text'] for entry in transcript_list])

            logger.info(f"✅ [get_transcript] Transcript fetched: {len(full_transcript)} characters")
            print(f"[get_transcript] SUCCESS: Got {len(full_transcript)} chars from YouTube", flush=True)

            return full_transcript

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)[:200]}"
            logger.warning(f"⚠️ [get_transcript] YouTube transcript unavailable: {error_msg}")
            print(f"[get_transcript] YouTube API failed: {error_msg}", flush=True)

            # Fallback to Groq Whisper (unless explicitly skipped)
            if not skip_groq_fallback and self.groq_transcription:
                logger.warning(f"🎙️ [get_transcript] Trying Groq Whisper fallback for: {video_id}")
                print(f"[get_transcript] Attempting Groq fallback...", flush=True)
                try:
                    groq_transcript = self.groq_transcription.transcribe(video_id)
                    if groq_transcript:
                        logger.info(f"✅ [get_transcript] Groq transcription successful: {len(groq_transcript)} characters")
                        print(f"[get_transcript] Groq SUCCESS: {len(groq_transcript)} chars", flush=True)
                        return groq_transcript
                except Exception as groq_e:
                    logger.error(f"❌ [get_transcript] Groq transcription also failed: {str(groq_e)[:100]}")
                    print(f"[get_transcript] Groq FAILED: {type(groq_e).__name__}", flush=True)
            elif skip_groq_fallback:
                logger.info(f"ℹ️ [get_transcript] Skipping Groq fallback (caption_filter_matched=True)")
                print(f"[get_transcript] Skipping Groq - relying on caption filter match", flush=True)

            return None
