"""
Utilities Module

Helper functions for lesson generation including:
- Lesson structure calculation (research-backed)
- User profile formatting
- Scheduling and spaced learning
- Prompt building

Import examples:
    from helpers.lesson_generation.utilities import (
        calculate_lesson_structure,
        calculate_schedule,
        get_ai_prompt_context,
        calculate_sessions_per_week
    )

    # Calculate structure
    structure = calculate_lesson_structure(
        topic_complexity='medium',
        learning_style='hands_on',
        current_skill_level='beginner'
    )
    # Returns: {num_parts: 3, duration: 30, depth: 'foundational', ...}

    # Calculate schedule
    schedule = calculate_schedule(
        num_parts=structure['num_parts'],
        sessions_per_week=2,
        spaced_learning=True
    )
    # Returns: {weeks_to_complete: 1.5, recommended_schedule: [...], ...}

    # Get AI context
    context = get_ai_prompt_context(
        part_number=1,
        total_parts=3,
        content_depth='foundational',
        topic='Python Data Types',
        optimal_duration=30
    )
    # Use in AI prompt to guide generation
"""

from .lesson_structure import (
    calculate_lesson_structure,
    calculate_schedule,
    get_ai_prompt_context,
    calculate_sessions_per_week
)

__all__ = [
    'calculate_lesson_structure',
    'calculate_schedule',
    'get_ai_prompt_context',
    'calculate_sessions_per_week'
]
