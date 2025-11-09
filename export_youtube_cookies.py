#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Export YouTube cookies for use in yt-dlp

This script extracts cookies from your browser and saves them to a file
that can be used by yt-dlp to authenticate as a real user instead of a bot.

Usage:
    python export_youtube_cookies.py

Output:
    Saves cookies to: ~/.skillsync/youtube_cookies.txt
"""

import subprocess
import sys
from pathlib import Path


def export_cookies():
    """Export cookies from Chrome using yt-dlp."""
    print("[*] Exporting YouTube cookies from Chrome...")
    print()

    cache_dir = Path.home() / '.skillsync'
    cache_file = cache_dir / 'youtube_cookies.txt'

    try:
        # Create directory if needed
        cache_dir.mkdir(parents=True, exist_ok=True)
        print(f"[DIR] Cache directory: {cache_dir}")
        print()

        # Try exporting from different browsers
        browsers = [
            ('chrome', 'Google Chrome'),
            ('chromium', 'Chromium'),
            ('firefox', 'Firefox'),
            ('edge', 'Microsoft Edge'),
        ]

        for browser_key, browser_name in browsers:
            print(f"[*] Trying {browser_name}...")

            try:
                cmd = [
                    'yt-dlp',
                    '--cookies-from-browser', browser_key,
                    '--cookies', str(cache_file),
                    '--no-warnings',
                    'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                # Check if cookies file was created
                if cache_file.exists():
                    file_size = cache_file.stat().st_size
                    if file_size > 100:
                        print(f"[OK] SUCCESS! Exported cookies from {browser_name}")
                        print(f"     Saved to: {cache_file}")
                        print(f"     Size: {file_size} bytes")
                        print()
                        print("[OK] Cookies are ready! YouTube video lessons should now work.")
                        return True

            except subprocess.TimeoutExpired:
                print(f"[TIMEOUT] {browser_name} timed out")
                continue
            except Exception as e:
                print(f"[X] Failed: {str(e)[:100]}")
                continue

        print()
        print("[X] Could not export cookies from any browser.")
        print()
        print("Make sure:")
        print("  1. yt-dlp is installed: pip install yt-dlp")
        print("  2. You have Chrome, Firefox, or Edge installed")
        print("  3. You're logged into YouTube in your browser")
        print()
        return False

    except Exception as e:
        print(f"[X] Error: {e}")
        return False


if __name__ == '__main__':
    success = export_cookies()
    sys.exit(0 if success else 1)
