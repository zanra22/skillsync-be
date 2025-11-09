"""
Reading Lesson Generator

Generates long-form educational content with:
- In-depth text explanations
- Mermaid.js diagrams and visualizations
- Code examples with explanations
- Step-by-step walkthroughs
- Summary and key takeaways
- Knowledge check quiz

Learning style: Best for detailed, self-paced learners
Estimated time: 60-90 minutes
"""

import logging
from typing import Any, Dict, Optional

from .base import BaseLessonGenerator

logger = logging.getLogger(__name__)


class ReadingGenerator(BaseLessonGenerator):
    """
    Generates reading-based lessons with detailed content.

    Wraps the existing _generate_reading_lesson() logic from ai_lesson_service
    while providing a clean, modular interface.
    """

    def __init__(self, service):
        """
        Initialize with reference to parent service.

        Args:
            service: LessonGenerationService instance with _generate_reading_lesson() method
        """
        self.service = service

    def get_name(self) -> str:
        return "Reading Lesson Generator"

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
        Generate reading lesson.

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
                'type': 'reading',
                'title': str,
                'summary': str,
                'content': {
                    'sections': [
                        {
                            'title': str,
                            'text': str (long-form markdown),
                            'code_examples': [
                                {
                                    'language': str,
                                    'code': str,
                                    'explanation': str
                                }
                            ]
                        }
                    ],
                    'diagrams': [
                        {
                            'title': str,
                            'mermaid_syntax': str,
                            'description': str
                        }
                    ]
                },
                'key_takeaways': [str],
                'quiz': [{...}],
                'lesson_type': 'reading',
                'estimated_duration': int (minutes),
                'research_metadata': {...}
            }
        """
        logger.info(f"📖 Generating reading lesson: {step_title}")

        # Create request object matching service expectations
        from helpers.ai_lesson_service import LessonRequest

        request = LessonRequest(
            step_title=step_title,
            lesson_number=lesson_number,
            learning_style='reading',
            user_profile=user_profile,
            difficulty=difficulty,
            industry=industry,
            category=category,
            programming_language=programming_language,
            enable_research=bool(research_data)
        )

        # Delegate to service's existing implementation
        lesson = await self.service._generate_reading_lesson(request, research_data)

        logger.info(f"✅ Reading lesson generated: {lesson.get('title', 'Untitled')}")
        return lesson
