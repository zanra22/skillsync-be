"""
Generic OpenRouter AI Provider
Capable of supporting any model hosted on OpenRouter.

Common Models:
- qwen/qwen3-coder:free
- deepseek/deepseek-chat-v3
- google/gemini-pro
"""

import os
import logging
from datetime import datetime
import asyncio
from typing import Optional, Dict, Any

from .provider import AIProvider

logger = logging.getLogger(__name__)

class OpenRouterProvider(AIProvider):
    """Generic OpenRouter provider using OpenAI SDK"""

    def __init__(self, api_key: Optional[str] = None, model: str = None):
        """
        Initialize OpenRouter provider.

        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            model: Model ID (e.g., 'qwen/qwen3-coder:free')
        """
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        self.model = model
        self._client = None
        self._last_call = None
        
        if not self.model:
            logger.warning("No model specified for OpenRouterProvider. Defaulting to 'qwen/qwen3-coder:free' as fallback.")
            self.model = 'qwen/qwen3-coder:free'

    @property
    def name(self) -> str:
        return f"OpenRouter ({self.model})"

    @property
    def is_available(self) -> bool:
        """Check if API key is configured"""
        return bool(self.api_key)

    async def generate(
        self,
        prompt: str,
        json_mode: bool = False,
        max_tokens: int = 4096
    ) -> str:
        """
        Generate content using OpenRouter.
        
        Args:
            prompt: Text prompt
            json_mode: Force JSON response
            max_tokens: Max tokens to generate

        Returns:
            Generated text
        """
        # Simple rate limit protection (can be customized per model if needed)
        if self._last_call:
            elapsed = (datetime.now() - self._last_call).total_seconds()
            if elapsed < 1:  # 1s buffer generic
                await asyncio.sleep(1 - elapsed)

        self._last_call = datetime.now()

        # Lazy client initialization
        if not self._client:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.api_key,
                timeout=60.0,
                max_retries=1
            )

        extra_headers = {
            "HTTP-Referer": "https://skillsync.studio",
            "X-Title": "SkillSync Learning Platform"
        }

        kwargs = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,  # Lower temp for coding/structured tasks
            "max_tokens": max_tokens,
            "extra_headers": extra_headers
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await self._client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"❌ OpenRouter ({self.model}) generation failed: {e}")
            raise e

    async def cleanup(self) -> None:
        """Close HTTP client connection"""
        if self._client:
            try:
                await self._client.close()
                logger.debug(f"🧹 Closed OpenRouter client for {self.model}")
            except Exception as e:
                logger.debug(f"⚠️ Error closing OpenRouter client: {e}")
            finally:
                self._client = None
