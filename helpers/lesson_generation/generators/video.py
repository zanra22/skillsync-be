"""
Video Lesson Generator

Generates video-based lessons with:
- YouTube video search with quality ranking
- Transcript extraction (YouTube captions or Groq fallback)
- AI-generated study guide from transcript
- Key concepts extraction
- Timestamped sections
- Knowledge check quiz

Learning style: Best for visual and auditory learners
Estimated time: 30-45 minutes (varies with video length)
"""

import logging
from typing import Any, Dict, Optional

from .base import BaseLessonGenerator

logger = logging.getLogger(__name__)


class VideoGenerator(BaseLessonGenerator):
    """
    Generates video-based lessons with study materials.

    Wraps the existing _generate_video_lesson() logic from ai_lesson_service
    while providing a clean, modular interface.
    """

    def __init__(self, service):
        """
        Initialize with reference to parent service.

        Args:
            service: LessonGenerationService instance with _generate_video_lesson() method
        """
        self.service = service

    def get_name(self) -> str:
        return "Video Lesson Generator"

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
        Generate video lesson.

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
                'type': 'video',
                'title': str,
                'summary': str,
                'video': {
                    'video_id': str,
                    'title': str,
                    'channel': str,
                    'duration': int (seconds),
                    'quality_score': float (0-100),
                    'transcript': str (optional)
                },
                'study_guide': {
                    'summary': str,
                    'key_concepts': [str],
                    'timestamps': [
                        {
                            'time': 'MM:SS',
                            'topic': str,
                            'notes': str
                        }
                    ]
                },
                'quiz': [{...}],
                'lesson_type': 'video',
                'estimated_duration': int (minutes),
                'research_metadata': {...}
            }
        """
        logger.info(f"🎥 Generating video lesson: {step_title}")

        # Create request object matching service expectations
        from helpers.ai_lesson_service import LessonRequest

        request = LessonRequest(
            step_title=step_title,
            lesson_number=lesson_number,
            learning_style='video',
            user_profile=user_profile,
            difficulty=difficulty,
            industry=industry,
            category=category,
            programming_language=programming_language,
            enable_research=bool(research_data)
        )

        # Delegate to service's existing implementation
        lesson = await self.service._generate_video_lesson(request, research_data)

        logger.info(f"✅ Video lesson generated: {lesson.get('title', 'Untitled')}")
        return lesson
