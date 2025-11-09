"""
Google Gemini 2.0 Flash AI Provider

Model: gemini-2.0-flash-exp
Free Tier: 1,500 requests/day, 10 req/min
Quality: Good (71.9% HumanEval)
Speed: 80 tokens/sec
Rate Limit: 10 req/min = 6-second intervals
"""

import os
import logging
from datetime import datetime
import asyncio
from typing import Optional

from .provider import AIProvider

logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    """Google Gemini 2.0 Flash with rate limiting"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini provider.

        Args:
            api_key: Google API key (defaults to GEMINI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self._last_call = None

    @property
    def name(self) -> str:
        return "Gemini 2.0 Flash"

    @property
    def is_available(self) -> bool:
        """Check if API key is configured"""
        return bool(self.api_key)

    async def generate(
        self,
        prompt: str,
        json_mode: bool = False,
        max_tokens: int = 8000
    ) -> str:
        """
        Generate content using Gemini 2.0 Flash.

        Implements rate limiting: 10 req/min = 6-second intervals

        Args:
            prompt: Text prompt
            json_mode: Force JSON response (Gemini supports this)
            max_tokens: Max tokens to generate

        Returns:
            Generated text

        Raises:
            Exception: If API call fails
        """
        # Rate limiting: 10 req/min = 6 seconds per request
        if self._last_call:
            elapsed = (datetime.now() - self._last_call).total_seconds()
            if elapsed < 6:
                wait_time = 6 - elapsed
                logger.info(f"⏱️ Gemini rate limit: waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

        self._last_call = datetime.now()

        # Configure Gemini (can be called multiple times, just updates config)
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)

        # Create generation config
        generation_config = {
            "temperature": 0.7,
            "max_output_tokens": max_tokens,
        }

        if json_mode:
            generation_config["response_mime_type"] = "application/json"

        # Create model with config
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            generation_config=generation_config
        )

        # Generate content
        response = await model.generate_content_async(prompt)
        return response.text

    async def cleanup(self) -> None:
        """
        Gemini doesn't maintain persistent client connections.
        No cleanup needed.
        """
        pass
