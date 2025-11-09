"""
DeepSeek V3.1 AI Provider

Model: deepseek/deepseek-chat-v3.1:free (FREE tier via OpenRouter)
Free Tier: 1M tokens/month
Quality: GPT-4o level for coding (84% HumanEval)
Speed: 60-80 tokens/sec
Rate Limit: 20 req/min = 3-second intervals
"""

import os
import logging
from datetime import datetime
import asyncio
from typing import Optional

from .provider import AIProvider

logger = logging.getLogger(__name__)


class DeepSeekProvider(AIProvider):
    """DeepSeek V3.1 via OpenRouter with OpenAI SDK"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize DeepSeek provider.

        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        self._client = None
        self._last_call = None

    @property
    def name(self) -> str:
        return "DeepSeek V3.1"

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
        Generate content using DeepSeek V3.1.

        Implements rate limiting: 20 req/min = 3-second intervals

        Args:
            prompt: Text prompt
            json_mode: Force JSON response
            max_tokens: Max tokens to generate

        Returns:
            Generated text

        Raises:
            Exception: If API call fails
        """
        # Rate limiting: 20 req/min = 3 seconds per request
        if self._last_call:
            elapsed = (datetime.now() - self._last_call).total_seconds()
            if elapsed < 3:
                wait_time = 3 - elapsed
                logger.info(f"⏱️ DeepSeek rate limit: waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

        self._last_call = datetime.now()

        # Lazy client initialization
        if not self._client:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.api_key,
                timeout=60.0,
                max_retries=0  # Fail fast to Groq instead of consuming quota on retries
            )

        # Extra headers for OpenRouter leaderboard (optional)
        extra_headers = {
            "HTTP-Referer": "https://skillsync.studio",
            "X-Title": "SkillSync Learning Platform"
        }

        # Build completion request
        kwargs = {
            "model": "deepseek/deepseek-chat-v3.1:free",  # CRITICAL: :free suffix for FREE tier!
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": max_tokens,
            "extra_headers": extra_headers
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    async def cleanup(self) -> None:
        """Close HTTP client connection"""
        if self._client:
            try:
                await self._client.close()
                logger.debug("🧹 Closed DeepSeek client")
            except Exception as e:
                logger.debug(f"⚠️ Error closing DeepSeek client: {e}")
            finally:
                self._client = None
