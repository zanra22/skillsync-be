"""
YouTube Cookies Manager

Automatically exports and manages YouTube cookies from browser for yt-dlp authentication.
This handles YouTube bot detection by using real browser cookies.

Features:
- Auto-exports cookies from Chrome/Firefox on first use
- Caches exported cookies locally
- Falls back gracefully if export fails
- No manual setup needed for users
"""

import os
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class YouTubeCookiesManager:
    """
    Manages YouTube authentication cookies for yt-dlp.

    Strategies:
    1. Use YOUTUBE_COOKIES_FILE env var if set (user-provided)
    2. Use cached cookies from ~/.skillsync/youtube_cookies.txt
    3. Auto-export from Chrome/Firefox if available
    4. Return None if all strategies fail (graceful degradation)
    """

    CACHE_DIR = Path.home() / '.skillsync'
    CACHE_FILE = CACHE_DIR / 'youtube_cookies.txt'

    @staticmethod
    def get_cookies_file() -> Optional[str]:
        """
        Get path to YouTube cookies file.

        Priority:
        1. YOUTUBE_COOKIES_FILE env var (user-provided)
        2. Cached local cookies
        3. Auto-export from browser
        4. None (will skip authentication)

        Returns:
            Path to cookies file or None if unavailable
        """
        # Strategy 1: Check environment variable
        env_cookies = os.getenv('YOUTUBE_COOKIES_FILE') or os.getenv('YT_COOKIES_FILE')
        if env_cookies and Path(env_cookies).exists():
            logger.debug(f"✅ Using cookies from environment: {env_cookies}")
            return env_cookies

        # Strategy 2: Check cached cookies
        if YouTubeCookiesManager.CACHE_FILE.exists():
            logger.debug(f"✅ Using cached cookies: {YouTubeCookiesManager.CACHE_FILE}")
            return str(YouTubeCookiesManager.CACHE_FILE)

        # Strategy 3: Auto-export from browser
        logger.info("🔍 Attempting to auto-export YouTube cookies from browser...")
        cookies_path = YouTubeCookiesManager._auto_export_cookies()
        if cookies_path:
            logger.info(f"✅ Successfully exported cookies to: {cookies_path}")
            return cookies_path

        # Strategy 4: Give up gracefully
        logger.warning(
            "⚠️ Could not obtain YouTube cookies. "
            "Set YOUTUBE_COOKIES_FILE env var or export manually with:\n"
            "   yt-dlp --cookies-from-browser chrome --cookies /path/to/cookies.txt"
        )
        return None

    @staticmethod
    def _auto_export_cookies() -> Optional[str]:
        """
        Automatically export cookies from Chrome/Firefox.

        Uses yt-dlp's built-in --cookies-from-browser feature.

        Returns:
            Path to exported cookies file or None if failed
        """
        try:
            # Try Chrome first (most common)
            browsers = ['chrome', 'firefox', 'edge']

            for browser in browsers:
                try:
                    logger.debug(f"Trying to export cookies from {browser}...")

                    # Create cache directory if needed
                    YouTubeCookiesManager.CACHE_DIR.mkdir(parents=True, exist_ok=True)

                    # Export cookies using yt-dlp
                    cmd = [
                        'yt-dlp',
                        '--cookies-from-browser', browser,
                        '--cookies', str(YouTubeCookiesManager.CACHE_FILE),
                        '--no-warnings',
                        'https://www.youtube.com/watch?v=dQw4w9WgXcQ'  # Dummy video
                    ]

                    logger.debug(f"Running: {' '.join(cmd)}")

                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )

                    # Check if cookies file was created
                    if YouTubeCookiesManager.CACHE_FILE.exists():
                        file_size = YouTubeCookiesManager.CACHE_FILE.stat().st_size
                        if file_size > 100:  # Valid cookies file is at least 100 bytes
                            logger.info(
                                f"✅ Exported cookies from {browser} "
                                f"({file_size} bytes) to {YouTubeCookiesManager.CACHE_FILE}"
                            )
                            return str(YouTubeCookiesManager.CACHE_FILE)

                except subprocess.TimeoutExpired:
                    logger.debug(f"⏱️ Cookie export from {browser} timed out")
                    continue
                except Exception as e:
                    logger.debug(f"⚠️ Failed to export from {browser}: {str(e)[:100]}")
                    continue

            return None

        except Exception as e:
            logger.warning(f"⚠️ Cookie auto-export failed: {str(e)[:100]}")
            return None

    @staticmethod
    def validate_cookies_file(cookies_path: str) -> bool:
        """
        Validate that cookies file exists and has valid format.

        Args:
            cookies_path: Path to cookies file

        Returns:
            True if valid, False otherwise
        """
        try:
            path = Path(cookies_path)

            # Check file exists
            if not path.exists():
                logger.warning(f"❌ Cookies file not found: {cookies_path}")
                return False

            # Check file is readable
            if not os.access(cookies_path, os.R_OK):
                logger.warning(f"❌ Cookies file not readable: {cookies_path}")
                return False

            # Check file has valid header
            with open(cookies_path, 'r') as f:
                first_line = f.readline().strip()

            if not first_line.startswith('#'):
                logger.warning(
                    f"⚠️ Cookies file has invalid format: {cookies_path}\n"
                    f"   First line should start with '# HTTP Cookie File' or '# Netscape HTTP Cookie File'"
                )
                return False

            logger.debug(f"✅ Cookies file valid: {cookies_path}")
            return True

        except Exception as e:
            logger.warning(f"❌ Error validating cookies file: {str(e)[:100]}")
            return False

    @staticmethod
    def clear_cache():
        """Clear cached cookies file."""
        try:
            if YouTubeCookiesManager.CACHE_FILE.exists():
                YouTubeCookiesManager.CACHE_FILE.unlink()
                logger.info(f"✅ Cleared cached cookies: {YouTubeCookiesManager.CACHE_FILE}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to clear cookie cache: {str(e)[:100]}")
