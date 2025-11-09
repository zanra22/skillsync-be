"""
Lesson Generators Module

Modular generators for each learning style:
- hands_on: Coding exercises and practice (70% practice, 30% theory)
- video: YouTube videos with AI-generated analysis
- reading: Long-form educational content with diagrams
- mixed: Combination of all approaches

Each generator implements the BaseLessonGenerator interface for consistency.

Import examples:
    from helpers.lesson_generation.generators import (
        BaseLessonGenerator,
        HandsOnGenerator,
        VideoGenerator,
        ReadingGenerator,
        MixedGenerator
    )

    # Use any generator with the same interface
    generator = HandsOnGenerator(service=ai_lesson_service)
    lesson = await generator.generate(
        step_title="Python asyncio",
        lesson_number=1,
        user_profile=user_data,
        research_data=research_context,
        ai_generate_func=orchestrator.generate
    )
"""

from .base import BaseLessonGenerator
from .hands_on import HandsOnGenerator
from .video import VideoGenerator
from .reading import ReadingGenerator
from .mixed import MixedGenerator

__all__ = [
    'BaseLessonGenerator',
    'HandsOnGenerator',
    'VideoGenerator',
    'ReadingGenerator',
    'MixedGenerator'
]
