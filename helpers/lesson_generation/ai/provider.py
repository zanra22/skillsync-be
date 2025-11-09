"""
Abstract AI Provider Interface

Defines the contract for all AI model implementations.
Supports DeepSeek V3.1, Groq, and Gemini with automatic fallback.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """
    Abstract base class for AI text generation providers.

    All implementations must handle:
    1. Rate limiting specific to their tier
    2. Lazy client initialization
    3. Resource cleanup
    4. JSON mode (if supported)
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        json_mode: bool = False,
        max_tokens: int = 8000
    ) -> str:
        """
        Generate content using the AI model.

        Args:
            prompt: Text prompt to send to model
            json_mode: Force JSON response format
            max_tokens: Maximum tokens in response

        Returns:
            Generated text content

        Raises:
            Exception: If generation fails (caller will fallback)
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources (HTTP clients, connections, etc.)"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'DeepSeek V3.1')"""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether provider has necessary API credentials"""
        pass


class HybridAIOrchestrator:
    """
    Manages fallback chain across multiple AI providers.

    Priority:
    1. DeepSeek V3.1 (best quality, limited quota)
    2. Groq Llama 3.3 70B (fast, generous quota)
    3. Gemini 2.0 Flash (reliable backup)
    """

    def __init__(self, providers: list[AIProvider]):
        """
        Initialize with list of providers in priority order.

        Args:
            providers: List of AIProvider instances (in fallback priority)
        """
        self.providers = providers
        self._model_usage = {provider.name: 0 for provider in providers}

    async def generate(
        self,
        prompt: str,
        json_mode: bool = False,
        max_tokens: int = 8000
    ) -> str:
        """
        Generate with automatic fallback to next available provider.

        Tries each provider in order until one succeeds.
        Logs all failures for debugging.

        Args:
            prompt: Text prompt
            json_mode: Force JSON response
            max_tokens: Max tokens to generate

        Returns:
            Generated text from first successful provider

        Raises:
            Exception: If all providers fail
        """
        last_error = None

        for provider in self.providers:
            if not provider.is_available:
                logger.debug(f"⏭️ Skipping {provider.name} (not configured)")
                continue

            try:
                logger.debug(f"🤖 Trying {provider.name}...")
                content = await provider.generate(prompt, json_mode, max_tokens)
                self._model_usage[provider.name] += 1
                logger.info(f"✅ {provider.name} success")
                return content

            except Exception as e:
                error_msg = str(e).lower()
                last_error = e

                # Quota exhaustion is expected, don't spam logs
                if any(x in error_msg for x in ['quota', 'limit', '429', 'exceeded']):
                    logger.warning(f"⚠️ {provider.name} quota exceeded, trying next provider")
                else:
                    logger.warning(f"⚠️ {provider.name} error: {e}, trying next provider")

        # All providers exhausted
        raise Exception(
            f"All AI providers failed. Last error: {last_error}. "
            f"Available providers: {[p.name for p in self.providers if p.is_available]}"
        )

    async def cleanup(self) -> None:
        """Clean up all provider resources"""
        for provider in self.providers:
            try:
                await provider.cleanup()
            except Exception as e:
                logger.debug(f"⚠️ Error cleaning up {provider.name}: {e}")

    def get_usage_stats(self) -> Dict[str, any]:
        """Get statistics on which models were used"""
        total = sum(self._model_usage.values())
        if total == 0:
            return self._model_usage.copy()

        stats = self._model_usage.copy()
        stats['total'] = total

        # Add percentages
        for provider_name in stats:
            if provider_name != 'total':
                percentage = round(stats[provider_name] / total * 100, 1)
                stats[f'{provider_name}_percentage'] = percentage

        return stats
