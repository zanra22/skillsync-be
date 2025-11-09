"""
Lesson Generation Module

Modular, service-based lesson generation architecture with:
- AI provider abstraction (DeepSeek, Groq, Gemini)
- Specialized generators for each learning style
- Reusable utility functions
- Clean separation of concerns

Structure:
    ai/              - AI provider implementations (DeepSeek, Groq, Gemini)
    generators/      - Lesson generators by learning style
    utilities/       - Helper functions (prompts, parsing, formatting)

Usage:
    from helpers.lesson_generation.ai import HybridAIOrchestrator, DeepSeekProvider, GroqProvider, GeminiProvider
    from helpers.lesson_generation.generators import HandsOnGenerator, VideoGenerator, ReadingGenerator, MixedGenerator
    from helpers.lesson_generation.utilities import PromptBuilder, ResponseParser
"""

__all__ = [
    # AI providers
    'AIProvider',
    'HybridAIOrchestrator',
    'DeepSeekProvider',
    'GroqProvider',
    'GeminiProvider',
]
