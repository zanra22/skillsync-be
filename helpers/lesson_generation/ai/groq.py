"""
Groq Llama 3.3 70B AI Provider

Model: llama-3.3-70b-versatile
Free Tier: 14,400 requests/day (essentially unlimited)
Quality: GPT-4 class (84% HumanEval)
Speed: 900 tokens/sec (fastest available)
Rate Limit: None (14,400/day is very generous)
"""

import os
import logging
from typing import Optional

from .provider import AIProvider

logger = logging.getLogger(__name__)


class GroqProvider(AIProvider):
    """Groq Llama 3.3 70B with async support"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Groq provider.

        Args:
            api_key: Groq API key (defaults to GROQ_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        self._client = None

    @property
    def name(self) -> str:
        return "Groq Llama 3.3 70B"

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
        Generate content using Groq Llama 3.3 70B.

        No rate limiting needed - 14,400 requests/day is very generous.

        Args:
            prompt: Text prompt
            json_mode: Force JSON response
            max_tokens: Max tokens to generate

        Returns:
            Generated text

        Raises:
            Exception: If API call fails
        """
        # Lazy client initialization
        if not self._client:
            from groq import AsyncGroq

            self._client = AsyncGroq(api_key=self.api_key)

        messages = [{"role": "user", "content": prompt}]

        kwargs = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": max_tokens
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
                logger.debug("🧹 Closed Groq client")
            except Exception as e:
                logger.debug(f"⚠️ Error closing Groq client: {e}")
            finally:
                self._client = None
