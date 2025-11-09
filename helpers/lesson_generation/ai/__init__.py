"""
AI Providers Module

Abstracts different AI models (DeepSeek, Groq, Gemini) behind a common interface.
Provides automatic fallback through HybridAIOrchestrator.

Import examples:
    from helpers.lesson_generation.ai import (
        AIProvider,
        HybridAIOrchestrator,
        DeepSeekProvider,
        GroqProvider,
        GeminiProvider
    )

    # Create providers
    providers = [
        DeepSeekProvider(),
        GroqProvider(),
        GeminiProvider()
    ]

    # Create orchestrator with automatic fallback
    orchestrator = HybridAIOrchestrator(providers)

    # Generate with automatic fallback
    content = await orchestrator.generate(
        prompt="Explain asyncio in Python",
        json_mode=False,
        max_tokens=8000
    )

    # Get usage stats
    stats = orchestrator.get_usage_stats()
    print(stats)  # {'DeepSeek': 5, 'Groq': 2, 'Gemini': 0, 'total': 7, ...}

    # Cleanup
    await orchestrator.cleanup()
"""

from .provider import AIProvider, HybridAIOrchestrator
from .deepseek import DeepSeekProvider
from .groq import GroqProvider
from .gemini import GeminiProvider

__all__ = [
    'AIProvider',
    'HybridAIOrchestrator',
    'DeepSeekProvider',
    'GroqProvider',
    'GeminiProvider'
]
