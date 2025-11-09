"""
Groq Whisper Transcription Service

Transcribes YouTube video audio using Groq Whisper API (FREE fallback).
Only used when YouTube captions are unavailable (~5% of videos).

NOTE: Requires FFmpeg and yt-dlp to be installed on the system.
Installation:
- FFmpeg: https://www.gyan.dev/ffmpeg/builds/
- yt-dlp: pip install yt-dlp

Groq Free Tier: 14,400 minutes/day (240 hours) - more than enough!
Speed: 3-5 seconds per 10-minute video
"""

import os
import re
import logging
import tempfile
import subprocess
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy import of yt-dlp to avoid import errors if not installed
_yt_dlp = None

def _get_yt_dlp():
    """Lazy load yt-dlp module on first use."""
    global _yt_dlp
    if _yt_dlp is None:
        try:
            import yt_dlp
            _yt_dlp = yt_dlp
        except ImportError:
            logger.warning("⚠️ yt-dlp not installed - Groq fallback will use subprocess mode")
            _yt_dlp = False
    return _yt_dlp


class GroqTranscription:
    """
    Groq Whisper transcription service for video audio.

    Handles:
    1. Video audio extraction (via yt-dlp)
    2. Whisper transcription (via Groq API)
    3. Error handling and retry logic
    4. Cleanup of temporary files
    """

    def __init__(self, groq_api_key: Optional[str] = None):
        """
        Initialize Groq transcription service.

        Args:
            groq_api_key: Groq API key for Whisper access
        """
        self.groq_api_key = groq_api_key

    def transcribe(self, video_id: str) -> Optional[str]:
        """
        Transcribe YouTube video using Groq Whisper API.

        Process:
        1. Extract video ID from various formats
        2. Download audio with yt-dlp
        3. Transcribe with Groq Whisper
        4. Cleanup temporary files

        Args:
            video_id: YouTube video ID or full URL

        Returns:
            Transcript text or None if failed
        """
        if not self.groq_api_key:
            logger.info("ℹ️  Groq transcription skipped - GROQ_API_KEY not configured")
            return None

        try:
            from groq import Groq

            logger.info(f"🎙️ Transcribing video with Groq Whisper: {video_id}")

            # Extract video ID if full URL was passed
            if 'youtube.com' in video_id or 'youtu.be' in video_id:
                m = re.search(r'(?:v=|youtu\.be/)([A-Za-z0-9_-]{6,20})', video_id)
                if m:
                    extracted = m.group(1)
                    logger.debug(f"🔎 Extracted video id from url: {extracted}")
                    video_id = extracted

            # Validate video ID format
            if not re.match(r'^[A-Za-z0-9_-]{4,20}$', str(video_id)):
                logger.warning(f"⚠️ Invalid or missing YouTube video id: {video_id}")
                return None

            # Step 1: Download audio
            audio_file = self._download_audio(video_id)
            if not audio_file:
                return None

            try:
                # Step 2: Transcribe with Groq
                client = Groq(api_key=self.groq_api_key)
                with open(audio_file, 'rb') as f:
                    transcription = client.audio.transcriptions.create(
                        file=f,
                        model="whisper-large-v3",  # Best accuracy
                        response_format="text",
                        language="en"
                    )

                logger.info(f"✅ Groq transcription complete: {len(transcription)} characters")
                return transcription

            except Exception as e:
                logger.error(f"❌ Groq transcription API error: {str(e)[:200]}")
                return None

            finally:
                # Cleanup temporary file
                self._cleanup_audio(audio_file)

        except Exception as e:
            logger.error(f"❌ Groq transcription failed: {str(e)[:200]}")
            return None

    def _download_audio(self, video_id: str) -> Optional[str]:
        """
        Download audio from YouTube video using yt-dlp.

        Args:
            video_id: YouTube video ID

        Returns:
            Path to temporary audio file or None if failed
        """
        try:
            video_url = f'https://www.youtube.com/watch?v={video_id}'

            # Create temporary file
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            audio_file = tmp.name
            tmp.close()

            # Get optional cookies file for age-restricted videos
            cookies_file = os.getenv('YOUTUBE_COOKIES_FILE') or os.getenv('YT_COOKIES_FILE')

            # Try using yt-dlp Python API first
            yt_dlp = _get_yt_dlp()
            if yt_dlp and yt_dlp != False:
                try:
                    logger.debug(f"Downloading audio using yt-dlp Python API...")

                    # Remove .mp3 extension for yt-dlp output template
                    output_template = audio_file.replace('.mp3', '')

                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '128',
                        }],
                        'outtmpl': output_template,
                        'quiet': True,
                        'no_warnings': True,
                        'socket_timeout': 30,
                    }

                    if cookies_file:
                        ydl_opts['cookiefile'] = cookies_file

                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([video_url])

                    logger.debug(f"yt-dlp Python API completed successfully")
                    return audio_file

                except Exception as api_err:
                    logger.debug(f"yt-dlp Python API failed: {str(api_err)[:200]}, falling back to subprocess")

            # Fallback to subprocess mode
            logger.debug("Using yt-dlp subprocess mode...")

            # Build yt-dlp command
            cmd = [
                'yt-dlp',
                '-vU',
                '-x',  # Extract audio only
                '--audio-format', 'mp3',
                '--audio-quality', '5',  # Lower quality = faster download
                '-o', audio_file,
                '--no-playlist',
                '--quiet',
                video_url
            ]

            if cookies_file:
                cmd.insert(-1, '--cookies')
                cmd.insert(-1, cookies_file)

            # Try downloading with retries and backoff
            max_attempts = 3
            attempt = 0
            last_err = None

            while attempt < max_attempts:
                attempt += 1
                try:
                    logger.debug(f"Downloading audio (attempt {attempt}/{max_attempts})...")

                    subprocess.run(
                        cmd,
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=120
                    )

                    logger.debug(f"yt-dlp subprocess completed successfully")
                    return audio_file

                except subprocess.CalledProcessError as cpe:
                    last_err = cpe
                    stderr = (cpe.stderr or '')[:2000]
                    logger.warning(f"⚠️ yt-dlp failed (exit {cpe.returncode}) on attempt {attempt}: {stderr}")

                    # If 403 (forbidden), likely age/geo restricted
                    if '403' in stderr or 'forbidden' in stderr.lower():
                        logger.warning("🚫 Video appears to be age/geo restricted or blocked")
                        if not cookies_file:
                            logger.info("🔐 Configure YOUTUBE_COOKIES_FILE to handle age-restricted videos")
                        # Don't retry if restricted
                        break

                    # Exponential backoff before retry
                    if attempt < max_attempts:
                        wait_time = 1 * attempt
                        logger.info(f"⏳ Retrying in {wait_time}s...")
                        time.sleep(wait_time)

                except subprocess.TimeoutExpired as te:
                    last_err = te
                    logger.warning(f"⚠️ yt-dlp timeout on attempt {attempt}")
                    if attempt < max_attempts:
                        time.sleep(1 * attempt)

                except FileNotFoundError:
                    logger.error("⚠️ yt-dlp not installed - cannot download audio")
                    logger.info("💡 Install: pip install yt-dlp (FFmpeg still required)")
                    self._cleanup_audio(audio_file)
                    return None

            # If we get here, all attempts failed
            logger.error(f"❌ Failed to download audio after {max_attempts} attempts: {last_err}")
            self._cleanup_audio(audio_file)
            return None

        except Exception as e:
            logger.error(f"❌ Audio download failed: {str(e)[:200]}")
            return None

    def _cleanup_audio(self, audio_file: str) -> None:
        """
        Safely delete temporary audio file.

        Args:
            audio_file: Path to audio file to delete
        """
        try:
            if audio_file and os.path.exists(audio_file):
                os.remove(audio_file)
                logger.debug(f"✅ Cleaned up temp file: {audio_file}")
        except Exception as e:
            logger.debug(f"⚠️ Failed to remove temp audio file: {str(e)[:100]}")
