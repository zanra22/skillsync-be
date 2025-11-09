"""
Video Transcript Analysis Service

Analyzes YouTube video transcripts and generates study materials using AI.

Features:
- Transcript analysis with Gemini
- Study guide generation
- Quiz creation
- Timestamp extraction
- Research context integration
"""

import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class VideoAnalyzer:
    """
    Analyzes video transcripts and generates educational materials.

    Responsibilities:
    - Parse and structure transcript content
    - Generate study guides
    - Create review quizzes
    - Extract key concepts
    """

    def __init__(self, gemini_client=None):
        """
        Initialize video analyzer.

        Args:
            gemini_client: Optional Gemini API client
        """
        self.gemini_client = gemini_client

    def analyze_transcript(
        self,
        transcript: str,
        topic: str,
        user_profile: Optional[Dict] = None,
        research_context: Optional[Dict] = None,
        ai_call_func=None
    ) -> Dict[str, Any]:
        """
        Analyze video transcript and generate study materials.

        Args:
            transcript: Video transcript text
            topic: Topic/lesson title
            user_profile: Optional user learning profile
            research_context: Optional multi-source research context
            ai_call_func: Function to call for AI generation

        Returns:
            Dict with summary, key_concepts, timestamps, study_guide, quiz
        """
        if not transcript:
            logger.warning("⚠️ No transcript provided for analysis")
            return {}

        if not ai_call_func:
            logger.error("❌ No AI call function provided")
            return {}

        try:
            # Build research context section if available
            research_section = ""
            if research_context:
                research_section = self._format_research_context(research_context)

            # Build user profile context if available
            profile_section = ""
            if user_profile:
                profile_section = self._build_profile_context(user_profile)

            # Build analysis prompt
            prompt = self._build_analysis_prompt(
                transcript,
                topic,
                profile_section,
                research_section
            )

            # Call AI for analysis
            logger.info(f"🤖 Analyzing transcript for: {topic}")
            response = ai_call_func(prompt)

            if not response:
                logger.error("❌ AI analysis returned empty response")
                return {}

            # Parse JSON response
            analysis = self._parse_analysis_response(response)

            if analysis:
                logger.info(f"✅ Transcript analysis complete")
                return analysis
            else:
                logger.error("❌ Failed to parse analysis response")
                return {}

        except Exception as e:
            logger.error(f"❌ Transcript analysis failed: {str(e)[:200]}")
            return {}

    def _build_analysis_prompt(
        self,
        transcript: str,
        topic: str,
        profile_section: str,
        research_section: str
    ) -> str:
        """
        Build AI prompt for transcript analysis.

        Args:
            transcript: Video transcript
            topic: Lesson topic
            profile_section: User profile context
            research_section: Multi-source research context

        Returns:
            Complete prompt for AI analysis
        """
        prompt = f"""You are analyzing a YouTube tutorial video transcript about: "{topic}".

**LEARNER CONTEXT:**
{profile_section if profile_section else "General learner audience"}

**VIDEO TRANSCRIPT:**
{transcript[:8000]}
{f"... (truncated, total length: {len(transcript)} chars)" if len(transcript) > 8000 else ""}

{research_section if research_section else ""}

**YOUR TASK:**
Generate structured study materials from this video. {
    "Use the research context to verify accuracy and add missing information." if research_section else ""
}

**OUTPUT FORMAT (STRICT JSON):**
```json
{{
  "summary": "3-4 sentence summary of what the video teaches",
  "key_concepts": [
    "Main concept 1",
    "Main concept 2",
    "Main concept 3"
  ],
  "timestamps": [
    {{
      "time": "2:34",
      "description": "Explains function parameters"
    }},
    {{
      "time": "5:12",
      "description": "Demonstrates practical example"
    }}
  ],
  "study_guide": "Detailed notes covering:\\n- Topic 1: Explanation\\n- Topic 2: Explanation\\n- Key takeaways",
  "quiz": [
    {{
      "question": "Based on the video, what is...",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "B",
      "explanation": "The video explains at 3:45..."
    }}
  ]
}}
```

Generate the analysis now."""
        return prompt

    def _format_research_context(self, research_context: Dict) -> str:
        """
        Format multi-source research context for prompt.

        Args:
            research_context: Research data from multi_source_research

        Returns:
            Formatted research context string
        """
        if not research_context:
            return ""

        try:
            sections = []

            # Documentation
            if research_context.get('documentation'):
                doc_links = research_context['documentation'][:2]
                doc_str = "\n".join([f"- {d['title']}: {d['url']}" for d in doc_links])
                sections.append(f"**Official Documentation:**\n{doc_str}")

            # Stack Overflow
            if research_context.get('stackoverflow'):
                so_items = research_context['stackoverflow'][:3]
                so_str = "\n".join([f"- {s['title']}: {s['url']}" for s in so_items])
                sections.append(f"**Stack Overflow Solutions:**\n{so_str}")

            # GitHub
            if research_context.get('github'):
                gh_items = research_context['github'][:2]
                gh_str = "\n".join([f"- {g['title']}: {g['url']}" for g in gh_items])
                sections.append(f"**GitHub Examples:**\n{gh_str}")

            # Dev.to
            if research_context.get('devto'):
                devto_items = research_context['devto'][:1]
                devto_str = "\n".join([f"- {d['title']}: {d['url']}" for d in devto_items])
                sections.append(f"**Community Articles:**\n{devto_str}")

            if sections:
                return (
                    "\n\n**📚 VERIFIED RESEARCH CONTEXT (Cross-reference video content with this!):**\n\n"
                    + "\n\n".join(sections) +
                    "\n\n**CRITICAL: Verify video content against research above. Flag any discrepancies. Add missing best practices.**"
                )
            return ""

        except Exception as e:
            logger.warning(f"⚠️ Could not format research context: {str(e)[:100]}")
            return ""

    def _build_profile_context(self, user_profile: Dict) -> str:
        """
        Build user profile context for prompt.

        Args:
            user_profile: User learning profile

        Returns:
            Profile context string
        """
        try:
            parts = []

            if user_profile.get('skill_level'):
                parts.append(f"- Skill Level: {user_profile['skill_level']}")

            if user_profile.get('learning_style'):
                parts.append(f"- Preferred Learning Style: {user_profile['learning_style']}")

            if user_profile.get('time_commitment'):
                parts.append(f"- Time Commitment: {user_profile['time_commitment']}")

            if user_profile.get('career_stage'):
                parts.append(f"- Career Stage: {user_profile['career_stage']}")

            if parts:
                return "**LEARNER PROFILE:**\n" + "\n".join(parts) + "\n"
            return ""

        except Exception as e:
            logger.warning(f"⚠️ Could not build profile context: {str(e)[:100]}")
            return ""

    def _parse_analysis_response(self, response: str) -> Optional[Dict]:
        """
        Parse AI response into analysis structure.

        Args:
            response: AI response text

        Returns:
            Parsed analysis dict or None
        """
        try:
            # Find JSON block
            if '```json' in response:
                start = response.find('```json') + 7
                end = response.find('```', start)
                json_str = response[start:end].strip()
            elif '```' in response:
                start = response.find('```') + 3
                end = response.find('```', start)
                json_str = response[start:end].strip()
            else:
                json_str = response.strip()

            # Parse JSON
            analysis = json.loads(json_str)

            # Validate structure
            if not isinstance(analysis, dict):
                logger.error("❌ Analysis is not a dict")
                return None

            # Ensure required fields
            required_fields = ['summary', 'key_concepts', 'timestamps', 'study_guide', 'quiz']
            for field in required_fields:
                if field not in analysis:
                    logger.warning(f"⚠️ Missing field in analysis: {field}")
                    analysis[field] = [] if field in ['key_concepts', 'timestamps', 'quiz'] else ""

            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse JSON from response: {str(e)[:100]}")
            logger.debug(f"Response text: {response[:500]}...")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to parse analysis response: {str(e)[:200]}")
            return None
