"""
Lesson Structure Calculator

Determines how to structure lessons based on:
- Topic complexity
- Learning style
- User skill level
- User role

Research-backed: Uses cognitive science, spaced learning principles.
Science-driven: 15-30 min optimal per session (non-negotiable).
"""

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def calculate_lesson_structure(
    topic_complexity: str,
    learning_style: str,
    current_skill_level: str,
    user_role: Optional[str] = None
) -> Dict[str, any]:
    """
    Determine lesson structure based on complexity, learning style, and user context.

    This determines HOW MANY PARTS a lesson should be split into and WHAT DEPTH.
    This is INDEPENDENT of time_commitment (pacing is separate).

    Args:
        topic_complexity: 'simple' | 'medium' | 'complex'
        learning_style: 'hands_on' | 'video' | 'reading' | 'mixed'
        current_skill_level: 'beginner' | 'intermediate' | 'expert'
        user_role: 'student' | 'professional' | 'career_shifter' (optional)

    Returns:
        {
            'num_parts': int,                    # 1-5 parts
            'optimal_duration_per_part': int,   # 15-30 minutes
            'content_depth': str,                # 'foundational' | 'comprehensive' | 'advanced'
            'weeks_to_complete_all': float,      # Estimated weeks (depends on time_commitment)
            'rationale': str                     # Human-readable explanation
        }

    Examples:
        >>> calculate_lesson_structure('medium', 'hands_on', 'beginner')
        {
            'num_parts': 3,
            'optimal_duration_per_part': 30,
            'content_depth': 'foundational',
            'rationale': 'Medium topic for beginner requires 3 parts × 30min foundational lessons'
        }

        >>> calculate_lesson_structure('complex', 'hands_on', 'expert', 'professional')
        {
            'num_parts': 2,
            'optimal_duration_per_part': 30,
            'content_depth': 'advanced',
            'rationale': 'Complex topic for expert requires 2 parts × 30min advanced lessons'
        }
    """

    # Step 1: Get optimal duration based on learning style (research-backed)
    optimal_durations = {
        'video': 15,      # Attention span limit
        'reading': 25,    # Reading cognitive load
        'hands_on': 30,   # Coding cognitive load
        'mixed': 20       # Balanced
    }

    optimal_duration = optimal_durations.get(learning_style, 20)

    # Step 2: Determine number of parts from complexity + skill level matrix
    complexity_matrix = {
        ('simple', 'beginner'): 1,
        ('simple', 'intermediate'): 1,
        ('simple', 'expert'): 1,

        ('medium', 'beginner'): 3,
        ('medium', 'intermediate'): 2,
        ('medium', 'expert'): 1,

        ('complex', 'beginner'): 5,
        ('complex', 'intermediate'): 3,
        ('complex', 'expert'): 2,
    }

    num_parts = complexity_matrix.get((topic_complexity, current_skill_level), 2)

    # Step 3: Adjust based on user role (affects learning pace and context needs)
    if user_role == 'career_shifter':
        # Career shifters need more context-building
        num_parts = min(num_parts + 1, 5)
        logger.debug(f"Career shifter adjustment: +1 part for context building")
    elif user_role == 'professional':
        # Professionals get same parts but we'll adjust depth (handled below)
        pass
    # 'student': default behavior

    # Step 4: Determine content depth based on skill level and role
    content_depth_matrix = {
        'beginner': 'foundational',        # Core concepts only
        'intermediate': 'comprehensive',    # Core + practical + pitfalls
        'expert': 'advanced'                # Edge cases + optimization + patterns
    }

    content_depth = content_depth_matrix.get(current_skill_level, 'comprehensive')

    # For professionals, optionally increase depth (they learn faster)
    # But keep foundational learners at foundational
    if user_role == 'professional' and content_depth != 'foundational':
        content_depth = 'advanced'
        logger.debug("Professional depth adjustment: increased to advanced")

    # Step 5: Build response
    return {
        'num_parts': num_parts,
        'optimal_duration_per_part': optimal_duration,
        'content_depth': content_depth,
        'learning_style': learning_style,
        'topic_complexity': topic_complexity,
        'skill_level': current_skill_level,
        'user_role': user_role or 'unknown',
        'rationale': (
            f"{topic_complexity.capitalize()} topic for {current_skill_level} requires "
            f"{num_parts} parts × {optimal_duration}min {content_depth} lessons"
        )
    }


def calculate_schedule(
    num_parts: int,
    sessions_per_week: int,
    spaced_learning: bool = True
) -> Dict[str, any]:
    """
    Calculate schedule for when to do each lesson part.

    Based on spaced learning research:
    - Day 1: Initial learning
    - Day 2: First review (prevents 70% forgetting)
    - Day 7: Reinforce long-term memory
    - Day 30: Lock into long-term retention

    Args:
        num_parts: Number of lesson parts
        sessions_per_week: How many sessions user can do per week
        spaced_learning: Whether to include spaced review schedule

    Returns:
        {
            'sessions_per_week': int,
            'weeks_to_complete_all_parts': float,
            'recommended_schedule': [
                {
                    'part_number': 1,
                    'suggested_week': 1,
                    'spaced_reviews': ['Day 2', 'Day 7', 'Day 30']
                },
                ...
            ],
            'ui_message': str
        }
    """

    weeks_to_complete = num_parts / sessions_per_week

    recommended_schedule = []
    for part_num in range(1, num_parts + 1):
        suggested_week = (part_num - 1) // sessions_per_week + 1

        part_schedule = {
            'part_number': part_num,
            'suggested_week': suggested_week,
            'week_of_total': suggested_week
        }

        if spaced_learning:
            part_schedule['spaced_reviews'] = [
                'Day 2 (prevent forgetting)',
                'Day 7 (reinforce memory)',
                'Day 30 (long-term retention)'
            ]

        recommended_schedule.append(part_schedule)

    # UI message for learner
    if weeks_to_complete < 1:
        ui_message = f"Complete this topic in {int(weeks_to_complete * 7)} days with {sessions_per_week} sessions/week"
    else:
        ui_message = f"Complete this topic in {weeks_to_complete:.1f} weeks at {sessions_per_week} session(s)/week"

    return {
        'sessions_per_week': sessions_per_week,
        'weeks_to_complete_all_parts': weeks_to_complete,
        'recommended_schedule': recommended_schedule,
        'ui_message': ui_message,
        'spaced_learning_enabled': spaced_learning
    }


def get_ai_prompt_context(
    part_number: int,
    total_parts: int,
    content_depth: str,
    topic: str,
    optimal_duration: int
) -> str:
    """
    Generate context string for AI to understand part structure.

    Helps AI avoid:
    - Repetition across parts
    - Assuming prior knowledge in later parts
    - Wrong depth level

    Args:
        part_number: Which part is this? (1, 2, 3, etc)
        total_parts: Total parts for this lesson
        content_depth: 'foundational' | 'comprehensive' | 'advanced'
        topic: Lesson topic
        optimal_duration: Minutes per part

    Returns:
        Context string for AI prompt

    Example:
        >>> context = get_ai_prompt_context(1, 3, 'foundational', 'Python Data Types', 30)
        >>> print(context)
        "Generate Part 1 of 3 (foundational depth). Focus on core concepts only.
        Duration: 30 minutes. Do not include collections (lists/dicts) - those are Part 3."
    """

    depth_instructions = {
        'foundational': (
            "Focus on CORE CONCEPTS ONLY. Avoid advanced features, edge cases, or optimization. "
            "Use simple examples. Assume no prior knowledge."
        ),
        'comprehensive': (
            "Cover core concepts + practical applications + common pitfalls. "
            "Include real-world examples. Assume basic familiarity with prerequisites."
        ),
        'advanced': (
            "Focus on advanced patterns, edge cases, and optimization. "
            "Assume strong foundational knowledge. Include performance considerations."
        )
    }

    part_instructions = {
        1: f"This is Part 1 of {total_parts}. Set up foundational concepts that Parts 2-{total_parts} will build on.",
        2: f"This is Part 2 of {total_parts}. Build on Part 1. Introduce new concepts. Prepare for Part {total_parts if total_parts == 2 else 3}.",
    }

    # Default for parts 3+
    if part_number not in part_instructions:
        part_instructions[part_number] = f"This is Part {part_number} of {total_parts}. Build on previous parts. Deepen understanding."

    return f"""**LESSON PART STRUCTURE:**
Part: {part_number}/{total_parts}
Topic: {topic}
Duration: {optimal_duration} minutes
Content Depth: {content_depth}

**DEPTH REQUIREMENTS:**
{depth_instructions.get(content_depth, depth_instructions['comprehensive'])}

**PART-SPECIFIC INSTRUCTIONS:**
{part_instructions.get(part_number, part_instructions[2])}

**CRITICAL:**
- Avoid content already covered in earlier parts
- Don't assume knowledge from later parts
- Each part must be self-contained but work together as a series
- Assume user will wait {7 if part_number > 1 else 1} days between parts (they may forget - provide brief review)
"""


def calculate_sessions_per_week(time_commitment: str) -> int:
    """
    Convert time commitment to estimated sessions per week.

    Args:
        time_commitment: '1-3' | '3-5' | '5-10' | '10+'

    Returns:
        Estimated sessions per week (1-4)
    """
    mapping = {
        '1-3': 1,
        '3-5': 2,
        '5-10': 3,
        '10+': 4
    }
    return mapping.get(time_commitment, 2)
