"""
Hands-On Lesson Generator

Generates practical, exercise-focused lessons with:
- 70% practice, 30% theory
- Progressive difficulty exercises
- Code templates and solutions
- Real-world project
- Knowledge check quiz

Learning style: Best for learners who prefer doing over watching
Estimated time: 45 minutes
"""

import logging
from typing import Any, Dict, Optional

from .base import BaseLessonGenerator

logger = logging.getLogger(__name__)


class HandsOnGenerator(BaseLessonGenerator):
    """
    Generates hands-on coding lessons with exercises.

    Wraps the existing _generate_hands_on_lesson() logic from ai_lesson_service
    while providing a clean, modular interface.
    """

    def __init__(self, service):
        """
        Initialize with reference to parent service.

        Args:
            service: LessonGenerationService instance with _generate_hands_on_lesson() method
        """
        self.service = service

    def get_name(self) -> str:
        return "Hands-On Lesson Generator"

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
        Generate hands-on lesson.

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
                'type': 'hands_on',
                'title': str,
                'summary': str,
                'introduction': {'text': str, 'key_concepts': [str]},
                'exercises': [
                    {
                        'number': int,
                        'title': str,
                        'difficulty': str,
                        'instructions': str,
                        'starter_code': str,
                        'expected_output': str,
                        'hints': [str],
                        'solution': str,
                        'learning_objective': str
                    }
                ],
                'practice_project': {...},
                'quiz': [{...}],
                'lesson_type': 'hands_on',
                'estimated_duration': int (minutes),
                'research_metadata': {...}
            }
        """
        logger.info(f"🛠️ Generating hands-on lesson: {step_title}")

        # Create request object matching service expectations
        from helpers.ai_lesson_service import LessonRequest

        request = LessonRequest(
            step_title=step_title,
            lesson_number=lesson_number,
            learning_style='hands_on',
            user_profile=user_profile,
            difficulty=difficulty,
            industry=industry,
            category=category,
            programming_language=programming_language,
            enable_research=bool(research_data)
        )

        # Delegate to service's existing implementation
        lesson = await self.service._generate_hands_on_lesson(request, research_data)

        logger.info(f"✅ Hands-on lesson generated: {lesson.get('title', 'Untitled')}")
        return lesson
