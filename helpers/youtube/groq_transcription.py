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
import json
from typing import Optional, Dict

from .cookies_manager import YouTubeCookiesManager

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


def _generate_oauth2_cookies(service_account_dict: dict) -> Optional[str]:
    """
    Generate YouTube-compatible cookies from Google service account OAuth2 credentials.

    This allows yt-dlp to authenticate with YouTube using OAuth2 instead of user cookies,
    bypassing bot detection and age-restriction errors.

    Args:
        service_account_dict: Google service account JSON dict with credentials

    Returns:
        Path to cookies file or None if generation failed
    """
    if not service_account_dict:
        logger.info("[OAuth2] No service account dict provided, skipping OAuth2 cookies generation")
        return None

    try:
        print("[OAuth2] Generating YouTube cookies from service account...", flush=True)
        logger.info("[OAuth2] Generating YouTube cookies from service account...")

        from google.oauth2 import service_account
        from google.auth.transport.requests import Request

        # Create credentials from service account
        print("[OAuth2] Creating service account credentials...", flush=True)
        credentials = service_account.Credentials.from_service_account_info(
            service_account_dict,
            scopes=['https://www.googleapis.com/auth/youtube.readonly']
        )

        print("[OAuth2] Service account credentials created", flush=True)

        # Refresh credentials to get access token
        print("[OAuth2] Refreshing credentials to get OAuth2 token...", flush=True)
        credentials.refresh(Request())
        access_token = credentials.token

        print(f"[OAuth2] Access token obtained ({len(access_token)} chars), creating cookies file...", flush=True)

        # Create cookies file in Netscape format (compatible with yt-dlp)
        # This mimics browser cookies but uses OAuth2 token
        tmp = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8')
        cookies_file = tmp.name

        # Netscape cookie format header
        tmp.write("# Netscape HTTP Cookie File\n")
        tmp.write("# This is a generated file!  Do not edit.\n")
        tmp.write("\n")

        # Add authentication cookie with OAuth2 token
        # YouTube recognizes SAPISID cookie for OAuth2 authenticated requests
        tmp.write(".youtube.com\tTRUE\t/\tTRUE\t0\tSAPISID\t{}\n".format(access_token))

        # Alternative: Add as Authorization header via environment
        # (but Netscape format is more reliable with yt-dlp)

        tmp.close()

        msg = f"[OK] OAuth2 cookies generated successfully: {cookies_file}"
        print(msg, flush=True)
        logger.info(msg)
        return cookies_file

    except Exception as e:
        error_msg = f"[ERROR] Failed to generate OAuth2 cookies: {type(e).__name__}: {str(e)}"
        print(error_msg, flush=True)
        logger.error(error_msg)
        import traceback
        traceback.print_exc()
        return None


class GroqTranscription:
    """
    Groq Whisper transcription service for video audio.

    Handles:
    1. Video audio extraction (via yt-dlp)
    2. Whisper transcription (via Groq API)
    3. Error handling and retry logic
    4. Cleanup of temporary files
    """

    def __init__(self, groq_api_key: Optional[str] = None, service_account: Optional[dict] = None):
        """
        Initialize Groq transcription service.

        Args:
            groq_api_key: Groq API key for Whisper access
            service_account: Google service account dict for YouTube OAuth2 authentication
        """
        print(f"[GroqTranscription.__init__] CALLED", flush=True)
        print(f"[GroqTranscription.__init__] service_account type: {type(service_account)}", flush=True)
        print(f"[GroqTranscription.__init__] service_account is None: {service_account is None}", flush=True)

        self.groq_api_key = groq_api_key
        self.service_account = service_account
        self.oauth2_cookies_file = None
        self._oauth2_cookies_generated = False

        print(f"[GroqTranscription.__init__] Initialization complete - OAuth2 cookies will be generated lazily on first use", flush=True)

    def _ensure_oauth2_cookies(self) -> None:
        """
        Lazily generate OAuth2 cookies from service account on first use.
        This defers the network call until actually needed, preventing initialization hangs.

        CRITICAL FIX 1.1: Validates file exists, is readable, and has correct permissions.
        """
        if self._oauth2_cookies_generated or not self.service_account:
            return

        try:
            print(f"[GroqTranscription._ensure_oauth2_cookies] Generating OAuth2 cookies on first use...", flush=True)
            self.oauth2_cookies_file = _generate_oauth2_cookies(self.service_account)

            # CRITICAL FIX 1.1: Validate OAuth2 cookies file
            if self.oauth2_cookies_file:
                # Check file exists
                if not os.path.exists(self.oauth2_cookies_file):
                    print(f"[ERROR] OAuth2 cookies file NOT created: {self.oauth2_cookies_file}", flush=True)
                    logger.error(f"OAuth2 cookies file not created at: {self.oauth2_cookies_file}")
                    self.oauth2_cookies_file = None
                else:
                    # Make file readable by subprocess (subprocess might run as different user)
                    try:
                        os.chmod(self.oauth2_cookies_file, 0o644)
                        file_size = os.path.getsize(self.oauth2_cookies_file)
                        print(f"[OK] OAuth2 cookies file ready: {file_size} bytes at {self.oauth2_cookies_file}", flush=True)
                        logger.info(f"✅ OAuth2 cookies file validated: {file_size} bytes, permissions 0o644")
                    except Exception as perm_err:
                        print(f"[WARNING] Failed to set file permissions: {perm_err}", flush=True)
                        logger.warning(f"Failed to set OAuth2 cookies file permissions: {perm_err}")
                        # Continue anyway - might still work with current permissions
            else:
                print(f"[ERROR] OAuth2 cookies generation returned None", flush=True)
                logger.error("OAuth2 cookies generation failed - returned None")

            self._oauth2_cookies_generated = True
        except Exception as e:
            print(f"[ERROR] Exception in _ensure_oauth2_cookies: {type(e).__name__}: {str(e)[:100]}", flush=True)
            logger.error(f"Exception in _ensure_oauth2_cookies: {type(e).__name__}: {str(e)[:200]}")
            self.oauth2_cookies_file = None
            self._oauth2_cookies_generated = True  # Mark as attempted (don't retry infinitely)

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
            # Lazily generate OAuth2 cookies on first actual use
            self._ensure_oauth2_cookies()

            # CRITICAL FIX 1.5: Refresh OAuth2 token before download to ensure it's valid
            # OAuth2 tokens expire after ~1 hour, so we refresh before each use
            if self.service_account and self.oauth2_cookies_file:
                try:
                    print(f"[GroqTranscription._download_audio] Refreshing OAuth2 token before download...", flush=True)
                    from google.oauth2 import service_account
                    from google.auth.transport.requests import Request

                    credentials = service_account.Credentials.from_service_account_info(
                        self.service_account,
                        scopes=['https://www.googleapis.com/auth/youtube.readonly']
                    )

                    # Check if token needs refresh
                    if not credentials.valid:
                        print(f"[GroqTranscription._download_audio] Token invalid, refreshing...", flush=True)
                        credentials.refresh(Request())
                        print(f"[GroqTranscription._download_audio] Token refreshed successfully", flush=True)
                        logger.info("✅ OAuth2 token refreshed before download")

                        # Regenerate cookies file with fresh token
                        self.oauth2_cookies_file = _generate_oauth2_cookies(self.service_account)
                        if self.oauth2_cookies_file:
                            os.chmod(self.oauth2_cookies_file, 0o644)
                            print(f"[GroqTranscription._download_audio] New OAuth2 cookies file ready", flush=True)
                    else:
                        print(f"[GroqTranscription._download_audio] Token still valid, proceeding...", flush=True)

                except Exception as refresh_err:
                    print(f"[WARNING] Failed to refresh OAuth2 token: {type(refresh_err).__name__}: {str(refresh_err)[:100]}", flush=True)
                    logger.warning(f"Failed to refresh OAuth2 token: {refresh_err}")
                    # Continue anyway - might still work with existing token

            video_url = f'https://www.youtube.com/watch?v={video_id}'

            # Create temporary file
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            audio_file = tmp.name
            tmp.close()

            # Get cookies file - priority: OAuth2 → Browser cookies → None
            cookies_file = None

            # Priority 1: Use OAuth2 cookies generated from service account
            if self.oauth2_cookies_file:
                cookies_file = self.oauth2_cookies_file
                print(f"[yt-dlp] Using OAuth2 cookies file: {cookies_file}", flush=True)
                logger.debug(f"🔐 Using OAuth2 service account cookies for YouTube authentication")
                logger.debug(f"🔐 Cookies file path: {cookies_file}")
            else:
                # Priority 2: Fall back to browser cookies (auto-export if needed)
                print(f"[yt-dlp] No OAuth2 cookies, trying browser cookies...", flush=True)
                cookies_file = YouTubeCookiesManager.get_cookies_file()
                if cookies_file:
                    print(f"[yt-dlp] Using browser cookies: {cookies_file}", flush=True)
                    logger.debug(f"📝 Using browser cookies for YouTube authentication: {cookies_file[:50]}...")

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
                    error_msg = str(api_err)[:200]
                    # Check if it's a bot detection error
                    if 'bot' in error_msg.lower() or 'sign in' in error_msg.lower():
                        logger.warning(f"🤖 Bot detection error - YouTube cookies needed. Set YOUTUBE_COOKIES_FILE environment variable")
                    logger.debug(f"yt-dlp Python API failed: {error_msg}, falling back to subprocess")

            # Fallback to subprocess mode
            print(f"[yt-dlp] Using subprocess mode...", flush=True)
            logger.debug("Using yt-dlp subprocess mode...")

            # Build yt-dlp command
            # CRITICAL FIX 1.2: Add User-Agent to prevent bot detection
            # CRITICAL FIX 1.3: Remove -U (update flag) and --quiet for error visibility
            cmd = [
                'yt-dlp',
                '-v',  # FIXED: Changed from '-vU' → '-v' (remove update check)
                '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',  # CRITICAL FIX 1.2
                '-x',  # Extract audio only
                '--audio-format', 'mp3',
                '--audio-quality', '5',  # Lower quality = faster download
                '--socket-timeout', '30',  # CRITICAL FIX 1.4: Add socket timeout
                '-o', audio_file,
                '--no-playlist',
                # REMOVED: '--quiet' - CRITICAL FIX 1.3: Need to see errors for debugging
                video_url
            ]

            if cookies_file:
                print(f"[yt-dlp] Adding cookies to command: --cookies {cookies_file}", flush=True)
                cmd.insert(-1, '--cookies')
                cmd.insert(-1, cookies_file)
            else:
                print(f"[yt-dlp] No cookies file - downloading without authentication", flush=True)

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

                    # If bot detection error, don't retry - need cookies
                    if 'bot' in stderr.lower() or 'sign in' in stderr.lower():
                        logger.warning("🤖 Bot detection error - YouTube requires authentication")
                        if not cookies_file:
                            logger.info("🔐 Configure YOUTUBE_COOKIES_FILE environment variable to handle bot detection")
                            logger.info("   See: https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp")
                        # Don't retry if bot blocked
                        break

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
