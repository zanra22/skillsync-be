"""
Mixed Lesson Generator

Generates balanced, multi-modal lessons combining:
- Educational text explanation (40%)
- Practical exercises (40%)
- Visual diagrams and examples (20%)

Learning style: Best for learners who benefit from diverse input modalities
Estimated time: 50-75 minutes
"""

import logging
from typing import Any, Dict, Optional

from .base import BaseLessonGenerator

logger = logging.getLogger(__name__)


class MixedGenerator(BaseLessonGenerator):
    """
    Generates mixed-mode lessons combining text, practice, and visuals.

    Wraps the existing _generate_mixed_lesson() logic from ai_lesson_service
    while providing a clean, modular interface.
    """

    def __init__(self, service):
        """
        Initialize with reference to parent service.

        Args:
            service: LessonGenerationService instance with _generate_mixed_lesson() method
        """
        self.service = service

    def get_name(self) -> str:
        return "Mixed Lesson Generator"

    async def generate(
        self,
        step_title: str,
        lesson_number: int,
        user_profile: Dict[str, Any],
        difficulty: str = 'beginner',
        industry: str = 'Technology',
        research_data: Optional[Dict] = None,
        ai_generate_func = None,
        category: Optional[str] = None,
        programming_language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate mixed lesson.

        Args:
            step_title: Skill/topic to teach
            lesson_number: Sequential number
            user_profile: User context for personalization
            difficulty: beginner|intermediate|advanced
            industry: User's industry
            research_data: Multi-source research enrichment
            ai_generate_func: AI generation function (optional, uses service default)
            category: Technology category (e.g., 'python')
            programming_language: Programming language (e.g., 'python')

        Returns:
            Lesson dict with:
            {
                'type': 'mixed',
                'title': str,
                'summary': str,
                'content': {
                    'text': str (40% - explanatory content),
                    'exercises': [
                        {
                            'number': int,
                            'title': str,
                            'instructions': str,
                            'starter_code': str (optional),
                            'solution': str,
                            'learning_objective': str
                        }
                    ] (40% - practical practice),
                    'diagrams': [
                        {
                            'title': str,
                            'mermaid_syntax': str,
                            'description': str
                        }
                    ] (20% - visual learning)
                },
                'key_concepts': [str],
                'quiz': [{...}],
                'lesson_type': 'mixed',
                'estimated_duration': int (minutes),
                'research_metadata': {...}
            }
        """
        logger.info(f"🎯 Generating mixed lesson: {step_title}")

        # Create request object matching service expectations
        from helpers.ai_lesson_service import LessonRequest

        request = LessonRequest(
            step_title=step_title,
            lesson_number=lesson_number,
            learning_style='mixed',
            user_profile=user_profile,
            difficulty=difficulty,
            industry=industry,
            category=category,
            programming_language=programming_language,
            enable_research=bool(research_data)
        )

        # Delegate to service's existing implementation
        lesson = await self.service._generate_mixed_lesson(request, research_data)

        logger.info(f"✅ Mixed lesson generated: {lesson.get('title', 'Untitled')}")
        return lesson
