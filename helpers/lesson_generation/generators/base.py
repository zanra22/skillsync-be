"""
Base Generator Class

Provides common interface and utilities for all lesson generators.
Subclasses implement specific learning style generation (hands-on, video, reading, mixed).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BaseLessonGenerator(ABC):
    """
    Abstract base class for lesson generators.

    All generators must implement:
    1. generate() - Main lesson generation
    2. get_name() - Human-readable name
    """

    @abstractmethod
    async def generate(
        self,
        step_title: str,
        lesson_number: int,
        user_profile: Dict[str, Any],
        difficulty: str = 'beginner',
        industry: str = 'Technology',
        research_data: Optional[Dict] = None,
        ai_generate_func = None
    ) -> Dict[str, Any]:
        """
        Generate a lesson of this type.

        Args:
            step_title: Topic/skill to teach
            lesson_number: Sequential lesson number
            user_profile: User's preferences and context
            difficulty: 'beginner', 'intermediate', or 'advanced'
            industry: User's industry
            research_data: Multi-source research context (optional)
            ai_generate_func: Function to call for AI generation (e.g., orchestrator.generate)

        Returns:
            Lesson data dict with fields appropriate to learning style

        Raises:
            Exception: If generation fails
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return human-readable generator name"""
        pass
