"""
AI-Powered Lesson Generation Service

Generates personalized lessons based on learning style:
- hands_on: Coding exercises, projects, practice
- video: YouTube videos + AI-generated study guides
- reading: Long-form text + diagrams
- mixed: Combination of all approaches

Uses:
- DeepSeek V3.1 (primary) for text generation
- Groq Llama 3.3 70B (fallback) for text generation
- Gemini 2.0 Flash (backup) for text generation
- YouTube Data API v3 for video search (FREE)
- YouTube Transcript API for captions (FREE)
- Unsplash API for hero images (FREE)
- Mermaid.js for diagrams (client-side rendering)
"""

from helpers.github_api import GitHubAPIService

import os
import json
import logging
import requests
import hashlib
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Import research engine
from .multi_source_research import multi_source_research_engine

# Import YouTube service module
from .youtube import YouTubeService, VideoAnalyzer

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class LessonRequest:
    """Request data for lesson generation"""
    step_title: str
    lesson_number: int
    learning_style: str  # 'hands_on', 'video', 'reading', 'mixed'
    user_profile: Dict  # User's onboarding data (REQUIRED for personalization)
    difficulty: str = 'beginner'
    industry: str = 'Technology'
    category: Optional[str] = None  # e.g., 'python', 'javascript', 'react'
    programming_language: Optional[str] = None  # e.g., 'python', 'javascript'
    enable_research: bool = True  # Enable multi-source research (default: True)


import re

class LessonGenerationService:
    """
    Main service for generating AI-powered lessons.
    Routes to appropriate generator based on learning style.
    """
    
    def __init__(self):
        # API Keys
        self.last_youtube_call = 0  # Rate limiting for YouTube API
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.youtube_api_key = os.getenv('YOUTUBE_API_KEY')
        self.unsplash_api_key = os.getenv('UNSPLASH_ACCESS_KEY')
        self.groq_api_key = os.getenv('GROQ_API_KEY')  # For Whisper transcription fallback
        self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')  # For DeepSeek V3.1 FREE

        # YouTube service account for OAuth2 authentication (prevents bot detection)
        # Loaded from Django settings (either from Key Vault in production or env var)
        try:
            from django.conf import settings
            self.youtube_service_account = getattr(settings, 'YOUTUBE_SERVICE_ACCOUNT', None)
        except Exception as e:
            logger.warning(f"Could not load YouTube service account from Django settings: {e}")
            self.youtube_service_account = None

        # Multi-source research engine
        self.research_engine = multi_source_research_engine
        logger.info("🔬 Multi-source research engine initialized")

        # YouTube service with quality ranking and transcript fallback
        # Now with OAuth2 service account authentication (prevents bot detection)
        self.youtube_service = YouTubeService(
            self.youtube_api_key,
            self.groq_api_key,
            service_account=self.youtube_service_account
        )
        self.video_analyzer = VideoAnalyzer()
        if self.youtube_service_account:
            logger.info("🎥 YouTube service initialized with OAuth2 service account authentication")
        else:
            logger.info("🎥 YouTube service initialized with API key fallback")

        # API URLs - Use Gemini 2.0 Flash Experimental (stable, free tier)
        # Free tier: 15 RPM, 200 RPD (better RPM than 2.5 Flash which has 10 RPM)
        # Stick with 2.0 for now - higher RPM is critical for our fallback system
        self.gemini_endpoint = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent'
        
        # Model usage tracking
        self._model_usage = {
            'deepseek_v31': 0,
            'groq': 0,
            'gemini': 0
        }
        
        # Rate limiting tracking
        self._last_deepseek_call = None  # DeepSeek: 20 req/min = 3s intervals
        self._last_gemini_call = None    # Gemini 2.0 Flash: 10 req/min = 6s intervals
        # Groq: No rate limiting needed (14,400 req/day is very generous)

        # Async client instances (initialized lazily, closed on cleanup)
        self._deepseek_client = None
        self._groq_client = None
        self._gemini_client = None
        
        # Validate critical APIs
        if not self.gemini_api_key:
            logger.warning("⚠️ GEMINI_API_KEY not found - lesson generation will fail")
        
        if not self.youtube_api_key:
            logger.warning("⚠️ YOUTUBE_API_KEY not found - video lessons will be limited")
        
        if not self.unsplash_api_key:
            logger.warning("⚠️ UNSPLASH_ACCESS_KEY not found - using placeholder images")
        
        if not self.groq_api_key:
            logger.warning("⚠️ GROQ_API_KEY not found - Whisper transcription fallback unavailable")
        
        if not self.openrouter_api_key:
            logger.warning("⚠️ OPENROUTER_API_KEY not found - DeepSeek V3.1 unavailable, will use Groq/Gemini only")
        else:
            logger.info("✅ Hybrid AI System: DeepSeek V3.1 (primary) → Groq (fallback) → Gemini (backup)")
    
    async def cleanup(self):
        """
        Clean up async resources to prevent Windows asyncio warnings.
        
        Call this before event loop closes to properly close HTTP connections.
        Prevents "RuntimeError: Event loop is closed" warnings on Windows.
        """
        if self._deepseek_client:
            try:
                await self._deepseek_client.close()
                logger.debug("🧹 Closed DeepSeek client")
            except Exception as e:
                logger.debug(f"⚠️ Error closing DeepSeek client: {e}")
        
        if self._groq_client:
            try:
                await self._groq_client.close()
                logger.debug("🧹 Closed Groq client")
            except Exception as e:
                logger.debug(f"⚠️ Error closing Groq client: {e}")
        
        if self._gemini_client:
            try:
                # Gemini client may be synchronous or async depending on library; attempt async close, then sync
                try:
                    await self._gemini_client.close()
                except Exception:
                    try:
                        self._gemini_client.close()
                    except Exception:
                        pass
                logger.debug("🧹 Closed Gemini client")
            except Exception as e:
                logger.debug(f"⚠️ Error closing Gemini client: {e}")
    
    # ========================================
    # HYBRID AI GENERATION SYSTEM
    # ========================================
    
    async def _generate_with_ai(self, prompt: str, json_mode: bool = False, max_tokens: int = 8000) -> str:
        """
        Hybrid AI generation with automatic fallback
        
        Priority order:
        1. DeepSeek V3.1 (FREE 1M tokens/month) - Best for coding
        2. Groq Llama 3.3 70B (FREE 14,400/day) - Fastest
        3. Gemini 2.0 Flash (FREE 50/day) - Final backup
        
        Args:
            prompt: Text prompt
            json_mode: Whether to force JSON response
            max_tokens: Maximum tokens to generate
        
        Returns:
            Generated text content
        """
        # Try DeepSeek V3.1 first (FREE tier via OpenRouter)
        if self.openrouter_api_key:
            try:
                logger.debug("🤖 Trying DeepSeek V3.1 (FREE)...")
                content = await self._generate_with_deepseek_v31(prompt, json_mode, max_tokens)
                self._model_usage['deepseek_v31'] += 1
                logger.info("✅ DeepSeek V3.1 success")
                return content
            except Exception as e:
                error_msg = str(e).lower()
                if 'quota' in error_msg or 'limit' in error_msg or '429' in error_msg:
                    logger.warning(f"⚠️ DeepSeek V3.1 quota exceeded, falling back to Groq")
                else:
                    logger.warning(f"⚠️ DeepSeek V3.1 error: {e}, falling back to Groq")
        
        # Fallback to Groq (FREE unlimited)
        if self.groq_api_key:
            try:
                logger.debug("🚀 Trying Groq Llama 3.3 70B...")
                content = await self._generate_with_groq(prompt, json_mode, max_tokens)
                self._model_usage['groq'] += 1
                logger.info("✅ Groq success")
                return content
            except Exception as e:
                logger.warning(f"⚠️ Groq error: {e}, falling back to Gemini")
        
        # Final fallback to Gemini (FREE 50/day)
        logger.debug("🔷 Trying Gemini 2.0 Flash...")
        content = await self._generate_with_gemini(prompt, json_mode, max_tokens)
        self._model_usage['gemini'] += 1
        logger.info("✅ Gemini success")
        return content
    
    async def _generate_with_deepseek_v31(self, prompt: str, json_mode: bool = False, max_tokens: int = 8000) -> str:
        """
        DeepSeek V3.1 via OpenRouter (FREE tier) using OpenAI SDK
        
        Model: deepseek/deepseek-chat:free (IMPORTANT: :free suffix!)
        Free Tier: 1M tokens/month
        Quality: GPT-4o level for coding (84% HumanEval)
        Speed: 60-80 tokens/sec
        Rate Limit: 20 req/min = 3-second intervals
        """
        from openai import AsyncOpenAI
        from datetime import datetime
        import asyncio
        
        # Rate limiting: 20 req/min = 3 seconds per request
        if self._last_deepseek_call:
            elapsed = (datetime.now() - self._last_deepseek_call).total_seconds()
            if elapsed < 3:
                wait_time = 3 - elapsed
                logger.info(f"⏱️ DeepSeek rate limit: waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
        
        self._last_deepseek_call = datetime.now()
        
        # Initialize OpenAI client with OpenRouter base URL (lazy initialization)
        if not self._deepseek_client:
            self._deepseek_client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.openrouter_api_key,
                timeout=60.0,
                max_retries=0  # Fail fast to Groq instead of consuming quota on retries
            )
        
        # Extra headers for OpenRouter leaderboard (optional)
        extra_headers = {
            "HTTP-Referer": "https://skillsync.studio",
            "X-Title": "SkillSync Learning Platform"
        }
        
        # Build completion request
        kwargs = {
            "model": "deepseek/deepseek-chat-v3.1:free",  # CRITICAL: :free suffix for FREE tier!
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": max_tokens,
            "extra_headers": extra_headers
        }
        
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        
        response = await self._deepseek_client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
    
    async def _generate_with_groq(self, prompt: str, json_mode: bool = False, max_tokens: int = 8000) -> str:
        """
        Groq Llama 3.3 70B (FREE tier)
        
        Model: llama-3.3-70b-versatile
        Free Tier: 14,400 requests/day
        Quality: GPT-4 class (84% HumanEval)
        Speed: 900 tokens/sec (fastest)
        """
        from groq import AsyncGroq
        
        # Initialize Groq client (lazy initialization)
        if not self._groq_client:
            self._groq_client = AsyncGroq(api_key=self.groq_api_key)
        
        messages = [{"role": "user", "content": prompt}]
        
        kwargs = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": max_tokens
        }
        
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        
        response = await self._groq_client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
    
    async def _generate_with_gemini(self, prompt: str, json_mode: bool = False, max_tokens: int = 8000) -> str:
        """
        Gemini 2.0 Flash (FREE tier)

        Model: gemini-2.0-flash-exp
        Free Tier: 1,500 requests/day, 10 req/min
        Quality: Good (71.9% HumanEval)
        Speed: 80 tokens/sec
        Rate Limit: 10 req/min = 6-second intervals
        """
        import google.generativeai as genai
        from datetime import datetime
        import asyncio

        # Rate limiting: 10 req/min = 6 seconds per request
        if self._last_gemini_call:
            elapsed = (datetime.now() - self._last_gemini_call).total_seconds()
            if elapsed < 6:
                wait_time = 6 - elapsed
                logger.info(f"⏱️ Gemini rate limit: waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

        self._last_gemini_call = datetime.now()

        # Configure Gemini
        genai.configure(api_key=self.gemini_api_key)

        # Create model
        generation_config = {
            "temperature": 0.7,
            "max_output_tokens": max_tokens,
        }

        if json_mode:
            generation_config["response_mime_type"] = "application/json"

        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            generation_config=generation_config
        )

        # Generate content
        response = await model.generate_content_async(prompt)
        return response.text
    
    def get_model_usage_stats(self) -> Dict[str, int]:
        """Get statistics on which models were used"""
        total = sum(self._model_usage.values())
        if total == 0:
            return self._model_usage
        
        return {
            **self._model_usage,
            'total': total,
            'deepseek_percentage': round(self._model_usage['deepseek_v31'] / total * 100, 1),
            'groq_percentage': round(self._model_usage['groq'] / total * 100, 1),
            'gemini_percentage': round(self._model_usage['gemini'] / total * 100, 1)
        }
    
    # ========================================
    # USER PROFILE UTILITIES
    # ========================================
    
    def _calculate_lesson_duration(self, base_duration: int, user_profile: Optional[Dict] = None) -> int:
        """
        Adjust lesson duration based on user's weekly time commitment.
        
        Args:
            base_duration: Default lesson duration (minutes)
            user_profile: User's onboarding data with time_commitment
        
        Returns:
            Adjusted duration in minutes
        """
        if not user_profile:
            return base_duration
        
        if isinstance(user_profile, dict):
            time_commitment = user_profile.get('time_commitment', '3-5')
        else:
            time_commitment = getattr(user_profile, 'time_commitment', '3-5')
        
        # Duration multipliers based on time commitment
        multipliers = {
            '1-3': 0.7,    # 30% shorter lessons (e.g., 45min → 32min)
            '3-5': 1.0,    # Standard duration (45min)
            '5-10': 1.3,   # 30% longer lessons (45min → 59min)
            '10+': 1.5     # 50% longer lessons (45min → 68min)
        }
        
        multiplier = multipliers.get(time_commitment, 1.0)
        adjusted_duration = int(base_duration * multiplier)
        
        logger.debug(f"⏰ Duration adjustment: {base_duration}min → {adjusted_duration}min (time_commitment: {time_commitment})")
        return adjusted_duration
    
    def _get_time_guidance(self, user_profile: Optional[Dict] = None) -> str:
        """
        Get time guidance string for AI prompts based on user's time commitment.
        
        Args:
            user_profile: User's onboarding data
            
        Returns:
            Time guidance string for AI prompts
        """
        if not user_profile:
            return "moderate study sessions (1-2 hours each)"
        
        if isinstance(user_profile, dict):
            time_commitment = user_profile.get('time_commitment', '3-5')
        else:
            time_commitment = getattr(user_profile, 'time_commitment', '3-5')
        
        time_mapping = {
            '1-3': 'short, focused study sessions (30-60 minutes each)',
            '3-5': 'moderate study sessions (1-2 hours each)',
            '5-10': 'extended study sessions (2-3 hours each)',
            '10+': 'intensive study sessions (3-4 hours each, multiple per week)'
        }
        
        return time_mapping.get(time_commitment, 'moderate study sessions (1-2 hours each)')

    def _format_goals_context(self, user_profile: Optional[Dict] = None) -> str:
        """
        Format user's top goals into a short human-readable string for prompts.
        """
        if not user_profile:
            return ""

        if isinstance(user_profile, dict):
            goals = user_profile.get('goals') or []
        else:
            goals = getattr(user_profile, 'goals', []) or []
        if not goals:
            return ""

        # goals may be objects or dicts with different key names
        parts = []
        for i, g in enumerate(goals[:3], start=1):
            if isinstance(g, dict):
                name = g.get('skillName') or g.get('skill_name') or g.get('skill') or 'skill'
                lvl = g.get('targetSkillLevel') or g.get('target_skill_level') or g.get('level', '')
                pr = g.get('priority', '')
            else:
                # Attribute-style object
                name = getattr(g, 'skillName', None) or getattr(g, 'skill_name', None) or 'skill'
                lvl = getattr(g, 'targetSkillLevel', None) or getattr(g, 'target_skill_level', None) or ''
                pr = getattr(g, 'priority', '')

            snippet = f"{i}) {name}"
            if lvl:
                snippet += f" ({lvl})"
            if pr:
                snippet += f" - priority {pr}"
            parts.append(snippet)

        return "\n".join(parts)
    
    def _adjust_content_complexity(self, content_items: List, user_profile: Optional[Dict] = None) -> List:
        """
        Adjust content complexity/count based on user's available time.
        
        Args:
            content_items: List of exercises, concepts, etc.
            user_profile: User's onboarding data
            
        Returns:
            Adjusted list of content items
        """
        if not user_profile or not content_items:
            return content_items
        
        if isinstance(user_profile, dict):
            time_commitment = user_profile.get('time_commitment', '3-5')
        else:
            time_commitment = getattr(user_profile, 'time_commitment', '3-5')
        
        if time_commitment == '1-3':  # Casual learners
            # Keep first 60% of items (reduce complexity)
            reduced_count = max(2, int(len(content_items) * 0.6))
            return content_items[:reduced_count]
        elif time_commitment == '10+':  # Intensive learners
            # Can handle more content (return all)
            return content_items
        else:
            # Standard amount for moderate learners
            return content_items

    # ========================================
    # USER PROFILE / GOALS HELPERS
    # ========================================

    def _format_goals(self, user_profile: Optional[Dict] = None) -> str:
        """
        Format the user's top goals into a compact, prompt-safe bullet list.

        Accepts goals passed either as list of dicts or attribute objects.
        Returns empty string when no goals present.
        """
        if not user_profile:
            return ""

        if isinstance(user_profile, dict):
            goals = user_profile.get('goals') or []
        else:
            goals = getattr(user_profile, 'goals', []) or []
        if not goals:
            return ""

        lines = []
        for i, g in enumerate(goals[:5], start=1):
            # support dict or attribute-style objects
            if isinstance(g, dict):
                skill = g.get('skill_name') or g.get('skillName') or ''
                level = g.get('target_skill_level') or g.get('targetSkillLevel') or ''
                desc = g.get('description', '') or ''
                pr = g.get('priority', '')
            else:
                skill = getattr(g, 'skill_name', None) or getattr(g, 'skillName', None) or ''
                level = getattr(g, 'target_skill_level', None) or getattr(g, 'targetSkillLevel', None) or ''
                desc = getattr(g, 'description', None) or ''
                pr = getattr(g, 'priority', None) or ''

            # sanitize newlines and excessive length
            desc = str(desc).replace('\n', ' ').strip()
            skill = str(skill).strip()
            level = str(level).strip()

            if skill:
                lines.append(f"{i}. {skill} ({level}) — {desc} [priority {pr}]")
            else:
                lines.append(f"{i}. {desc} [priority {pr}]")

        return "\n".join(lines)

    def _build_profile_context(self, user_profile: Optional[Dict] = None) -> str:
        """
        Build a short profile context string for inclusion in AI prompts.

        Includes: role, current_role, career_stage, transition_timeline, and formatted goals.
        Returns an empty string if no meaningful profile data is present.
        """
        if not user_profile:
            return ""

        if isinstance(user_profile, dict):
            role = user_profile.get('role') or user_profile.get('user_role') or ''
            current_role = user_profile.get('current_role') or user_profile.get('currentRole') or ''
            career_stage = user_profile.get('career_stage') or user_profile.get('careerStage') or ''
            transition = user_profile.get('transition_timeline') or user_profile.get('transitionTimeline') or ''
        else:
            role = getattr(user_profile, 'role', '') or getattr(user_profile, 'user_role', '') or ''
            current_role = getattr(user_profile, 'current_role', '') or getattr(user_profile, 'currentRole', '') or ''
            career_stage = getattr(user_profile, 'career_stage', '') or getattr(user_profile, 'careerStage', '') or ''
            transition = getattr(user_profile, 'transition_timeline', '') or getattr(user_profile, 'transitionTimeline', '') or ''

        parts = []
        if role:
            parts.append(f"Role: {role}")
        if current_role:
            parts.append(f"Current role: {current_role}")
        if career_stage:
            parts.append(f"Career stage: {career_stage}")
        if transition:
            parts.append(f"Transition timeline: {transition}")

        goals_text = self._format_goals(user_profile)
        if goals_text:
            parts.append("LEARNER GOALS:\n" + goals_text)

        if not parts:
            return ""

        # Join with blank line for readability in prompts
        return "\n".join(parts) + "\n"
    
    # ========================================
    # MAIN ENTRY POINT
    # ========================================
    
    async def generate_lesson(self, request: LessonRequest) -> Dict[str, Any]:
        """
        Main entry point for lesson generation.
        
        Flow:
        1. Run multi-source research (if enabled) - NEW!
        2. Route to appropriate generator based on learning style (uses hybrid AI)
        3. Inject research data into AI prompts
        
        NOW USES HYBRID AI SYSTEM:
        - Primary: DeepSeek V3.1 (FREE 1M tokens/month, GPT-4o quality)
        - Fallback: Groq Llama 3.3 70B (FREE 14,400 req/day)
        - Backup: Gemini 2.0 Flash (FREE 50 req/day)
        """
        logger.info(f"🎓 [LessonGen] Generating lesson: {request.step_title} - Lesson {request.lesson_number} ({request.learning_style})")

        try:
            # Step 1: Run multi-source research (if enabled)
            research_data = None
            if request.enable_research:
                logger.info("🔬 [LessonGen] Starting multi-source research...")
                research_data = await self._run_research(request)

                if research_data:
                    research_summary = research_data.get('summary', 'No summary')
                    research_time = research_data.get('research_time_seconds', 0)
                    logger.info(f"✅ [LessonGen] Research complete in {research_time:.1f}s: {research_summary}")
                else:
                    logger.warning("⚠️ [LessonGen] Research failed or returned no data - proceeding with AI-only generation")
            else:
                logger.info("ℹ️ [LessonGen] Multi-source research disabled - using AI-only generation")

            # Step 2: Route to appropriate generator (with research context)
            # Helper function to extract source attribution from research data
            def extract_source_attribution(research_data):
                if not research_data or 'sources' not in research_data:
                    return {}
                sources = research_data['sources']
                attribution = {}
                # Official docs
                doc = sources.get('official_docs')
                if doc and isinstance(doc, dict) and doc.get('url'):
                    attribution['official_docs'] = [doc['url']]
                # Stack Overflow
                so = sources.get('stackoverflow_answers', [])
                attribution['stackoverflow'] = [a['question_url'] for a in so if a.get('question_url')]
                # GitHub
                gh = sources.get('github_examples', [])
                attribution['github'] = [g['repo_url'] for g in gh if g.get('repo_url')]
                # Dev.to
                dev = sources.get('dev_articles', [])
                attribution['devto'] = [d['url'] for d in dev if d.get('url')]
                return attribution

            # Route to appropriate generator, then inject source_attribution
            if request.learning_style == 'hands_on':
                logger.info(f"🎓 [LessonGen] Routing to hands-on lesson generator for: {request.step_title}")
                result = await self._generate_hands_on_lesson(request, research_data)
                result['source_attribution'] = extract_source_attribution(research_data)
                logger.info(f"🎓 [LessonGen] Hands-on lesson generated for: {request.step_title}")
                return result
            elif request.learning_style == 'video':
                logger.info(f"🎓 [LessonGen] Routing to video lesson generator for: {request.step_title}")
                result = await self._generate_video_lesson(request, research_data)
                result['source_attribution'] = extract_source_attribution(research_data)
                logger.info(f"🎓 [LessonGen] Video lesson generated for: {request.step_title}")
                return result
            elif request.learning_style == 'reading':
                logger.info(f"🎓 [LessonGen] Routing to reading lesson generator for: {request.step_title}")
                result = await self._generate_reading_lesson(request, research_data)
                result['source_attribution'] = extract_source_attribution(research_data)
                logger.info(f"🎓 [LessonGen] Reading lesson generated for: {request.step_title}")
                return result
            elif request.learning_style == 'mixed':
                logger.info(f"🎓 [LessonGen] Routing to mixed lesson generator for: {request.step_title}")
                result = await self._generate_mixed_lesson(request, research_data)
                result['source_attribution'] = extract_source_attribution(research_data)
                logger.info(f"🎓 [LessonGen] Mixed lesson generated for: {request.step_title}")
                return result
            else:
                logger.error(f"[LessonGen] Unknown learning style: {request.learning_style}")
                raise ValueError(f"Unknown learning style: {request.learning_style}")
        except Exception as e:
            logger.error(f"❌ [LessonGen] Lesson generation failed: {e}", exc_info=True)
            return await self._generate_fallback_lesson(request)
    
    # ========================================
    # MULTI-SOURCE RESEARCH (NEW!)
    # ========================================
    
    async def _run_research(self, request: LessonRequest) -> Optional[Dict[str, Any]]:
        """
        Run multi-source research BEFORE lesson generation.
        
        Fetches from:
        - Official documentation (Python.org, MDN, React.dev, etc.)
        - Stack Overflow (top-voted answers)
        - GitHub (production code examples)
        - Dev.to (community articles)
        
        Returns research data or None if failed.
        """
        try:
            # Determine category and language from request
            category = request.category or self._infer_category(request.step_title)
            language = request.programming_language or self._infer_language(request.step_title)
            
            logger.debug(f"   Category: {category}, Language: {language}")
            
            # Run async research (now properly await it)
            research_data = await self.research_engine.research_topic(
                topic=request.step_title,
                category=category,
                language=language
            )
            
            return research_data
        
        except Exception as e:
            logger.error(f"❌ Research failed: {e}")
            import traceback
            logger.debug(f"   Traceback: {traceback.format_exc()}")
            return None
    
    def _infer_category(self, topic: str) -> str:
        """
        Infer category from topic title for official documentation lookup.
        
        Args:
            topic: Topic title (e.g., 'Python Variables', 'React Hooks', 'SQL Joins')
        
        Returns:
            Category string for docs lookup, or 'general' if no match
        """
        topic_lower = topic.lower()
        
        # 🎯 CRITICAL: Order matters! Check more specific patterns first
        # Use word boundaries to avoid false positives
        category_keywords = {
            # Databases (check BEFORE 'go' to avoid mongo → go)
            'mongodb': ['mongodb', 'mongo db', ' mongo '],  # Space ensures word boundary
            'sql': ['sql', 'mysql', 'postgresql', 'postgres', 'sqlite', 'database'],
            
            # DevOps/Tools (check BEFORE 'go', 'angular' to avoid false matches)
            'docker': ['docker', 'container'],
            'kubernetes': ['kubernetes', 'k8s'],
            'git': [' git ', 'github', 'gitlab', 'git branching'],  # Space for word boundary
            
            # JavaScript ecosystem (check BEFORE generic 'javascript')
            'nextjs': ['next.js', 'nextjs', 'next js', 'nextrouting'],
            'react': ['react', ' jsx ', 'react native'],  # Space for word boundary
            'vue': ['vue', 'vuejs', 'vue.js', 'nuxt', 'vue component'],
            'angular': ['angular', ' ng ', 'angular service'],  # Space for word boundary
            'typescript': ['typescript', ' ts '],  # Space to avoid matching "cats"
            'javascript': ['javascript', ' js ', 'node', 'nodejs', 'express', 'npm', 'webpack'],
            
            # Python ecosystem
            'python': ['python', ' py ', 'django', 'flask', 'fastapi', 'pandas', 'numpy', 'pytorch'],
            
            # Other popular languages (check 'go' AFTER 'mongo')
            'go': [' go ', 'golang', 'go goroutine'],  # Space to avoid "mongo"
            'rust': ['rust', 'cargo'],
            'java': ['java', 'spring', 'maven', 'gradle'],
            'csharp': ['c#', 'csharp', '.net', 'dotnet', 'asp.net'],
            'php': ['php', 'laravel', 'symfony', 'composer'],
            'ruby': [' ruby ', 'rails', ' gem '],  # Space to avoid "management"
            'swift': ['swift', 'ios', 'swiftui'],
            'kotlin': ['kotlin', 'android'],
            
            # Web technologies
            'html': ['html', 'html5'],
            'css': ['css', 'css3', 'sass', 'scss', 'tailwind'],
        }
        
        # Find first matching category
        for category, keywords in category_keywords.items():
            if any(keyword in topic_lower for keyword in keywords):
                return category
        
        # No match - return 'general' (no default assumption)
        return 'general'
    
    def _infer_language(self, topic: str) -> Optional[str]:
        """
        Infer programming language from topic for GitHub code search.
        
        Args:
            topic: Topic title (e.g., 'Python Variables', 'SQL Joins')
        
        Returns:
            Language string for GitHub search, or None if no language detected
            (None = search all languages, don't restrict)
        """
        topic_lower = topic.lower()
        
        # 🎯 CRITICAL: Order matters! Check specific patterns first
        # Use word boundaries to avoid false positives
        language_keywords = {
            # Databases (check BEFORE 'go' to avoid mongo → go)
            'sql': ['sql', 'mysql', 'postgresql', 'postgres', 'sqlite', 't-sql', 'pl/sql'],
            
            # Shell scripting (check BEFORE generic patterns)
            'powershell': ['powershell', 'ps1', 'pwsh'],
            'shell': [' bash ', 'bash script', ' sh ', ' zsh '],  # Space for word boundary
            
            # Web frameworks/libraries (check BEFORE generic JS/TS)
            'vue': ['vue', 'vuejs', 'vue.js', 'vue component'],
            'javascript': ['react', 'react hook'],  # React uses JSX

            # Core programming languages
            'python': ['python', ' py ', 'django', 'flask', 'fastapi', 'pandas', 'numpy'],
            'typescript': ['typescript', ' ts ', 'angular'],  # Angular uses TypeScript
            'javascript': ['javascript', ' js ', 'node', 'nodejs', 'npm', 'express', 'next.js', 'nextjs'],
            'java': ['java', 'spring', 'maven'],
            'go': [' go ', 'golang', 'go goroutine'],  # Space to avoid "mongo", "algorithm"
            'rust': ['rust', 'cargo'],
            'cpp': ['c++', 'cpp'],
            'c': ['c language', ' c '],  # Space to avoid matching "react", "docker"
            'csharp': ['c#', 'csharp', '.net', 'dotnet'],
            'php': ['php', 'laravel', 'symfony'],
            'ruby': [' ruby ', 'rails'],  # Space to avoid "management"
            'swift': ['swift', 'ios', 'swiftui'],
            'kotlin': ['kotlin', 'android'],
            'scala': ['scala'],
            'r': ['r language', ' r '],  # Space to avoid matching "react"
            'dart': ['dart', 'flutter'],
            'elixir': ['elixir', 'phoenix'],
            'haskell': ['haskell'],
            'lua': ['lua'],
            'perl': ['perl'],
            
            # Web technologies (GitHub treats these as languages)
            'html': ['html', 'html5'],
            'css': ['css', 'css3', 'sass', 'scss', 'less', 'tailwind'],
            
            # Markup/Config
            'yaml': ['yaml', 'yml'],
            'json': ['json'],
            'xml': ['xml'],
            'markdown': ['markdown', ' md '],
        }
        
        # Find first matching language
        for language, keywords in language_keywords.items():
            if any(keyword in topic_lower for keyword in keywords):
                return language
        
        # 🎯 NEW: No default! Return None if no language detected
        # This allows GitHub to search across ALL languages
        # Better than forcing Python for non-programming topics
        return None
    
    # ========================================
    # HANDS-ON LESSONS (70% practice, 30% theory)
    # ========================================
    
    async def _generate_hands_on_lesson(self, request: LessonRequest, research_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Generate hands-on lesson with coding exercises.
        
        Structure:
        - Brief text explanation (200-300 words)
        - 3-4 coding exercises (progressive difficulty)
        - Starter code templates
        - Expected outputs
        - Progressive hints (3 per exercise)
        - Solutions
        
        Now includes research context for accuracy!
        """
        logger.info(f"🛠️ Generating hands-on lesson for: {request.step_title}")
        
        prompt = self._create_hands_on_prompt(request, research_data)

        # Call Gemini API
        response = self._call_gemini_api(prompt)

        if not response:
            return await self._generate_fallback_lesson(request)
        
        # Parse AI response
        lesson_data = self._parse_hands_on_response(response, request)

        # Generate unique lesson description
        lesson_data['summary'] = await self._generate_lesson_description(request, lesson_data.get('introduction', ''))

        # Adjust content complexity based on user's time commitment
        if 'exercises' in lesson_data:
            lesson_data['exercises'] = self._adjust_content_complexity(
                lesson_data['exercises'], 
                request.user_profile
            )
        
        if 'key_concepts' in lesson_data:
            lesson_data['key_concepts'] = self._adjust_content_complexity(
                lesson_data['key_concepts'], 
                request.user_profile
            )
        
        # Add metadata
        lesson_data['lesson_type'] = 'hands_on'
        lesson_data['estimated_duration'] = self._calculate_lesson_duration(45, request.user_profile)  # Time-aware duration
        
        # Add research metadata if available
        if research_data:
            lesson_data['research_metadata'] = {
                'research_time': research_data.get('research_time_seconds', 0),
                'sources_used': research_data.get('summary', ''),
                'source_type': 'multi_source'
            }
        else:
            lesson_data['research_metadata'] = {
                'source_type': 'ai_only'
            }
        
        logger.info(f"✅ Hands-on lesson generated: {len(lesson_data.get('exercises', []))} exercises")
        
        return lesson_data
    
    def _create_hands_on_prompt(self, request: LessonRequest, research_data: Optional[Dict] = None) -> str:
        """Create Gemini prompt for hands-on lesson with research context"""
        
        # Build research context section if available
        research_context = ""
        if research_data:
            research_context = f"""
**📚 VERIFIED RESEARCH CONTEXT (Use this to ensure accuracy!):**

{self.research_engine.format_for_ai_prompt(research_data)}

**CRITICAL: Base your lesson on the research above. Verify all code examples, concepts, and best practices against the official docs and community consensus.**
"""
        
        # Build user profile context
        profile_context = self._build_profile_context(request.user_profile)
        profile_section = ""
        if profile_context:
            profile_section = f"""
**LEARNER PROFILE:**
{profile_context}
**IMPORTANT: Tailor examples and scenarios to align with the learner's role, career stage, and goals above.**
"""
        
        return f"""You are an expert programming instructor creating a **hands-on coding lesson** for: \"{request.step_title} - Lesson {request.lesson_number}\".

**LEARNER CONTEXT:**
- Difficulty Level: {request.difficulty}
- Industry: {request.industry}
- Learning Style: Hands-on (prefers doing over watching)
- Time Commitment: {self._get_time_guidance(request.user_profile)}
{profile_section}{research_context}

**CRITICAL REQUIREMENTS:**
1. **70% Practice, 30% Theory** - Focus on exercises, not lectures
2. **Progressive Difficulty** - Start simple, build complexity
3. **Real-world Relevance** - Use practical examples from {request.industry}
4. **Immediate Feedback** - Clear expected outputs for each exercise
5. **Accuracy First** - Use research context above to verify all information
6. **Time-Appropriate Pacing** - Design for {self._get_time_guidance(request.user_profile)}

**STRICT OUTPUT INSTRUCTIONS (IMPORTANT):**
- Output ONLY a single valid JSON object, with NO markdown, no code block markers, and no extra commentary or explanation.
- DO NOT include any text, explanation, or formatting before or after the JSON.
- DO NOT use markdown code blocks (no ```json or ```).
- The output MUST be valid, parseable JSON. Do not use trailing commas or comments.
- If you are unsure, repair the JSON before outputting.
- All fields in the example below are required unless otherwise specified.

**OUTPUT FORMAT (STRICT JSON, NO MARKDOWN):**
{{
    "title": "Engaging lesson title",
    "summary": "2-3 sentence overview of what learner will master",
    "introduction": {{
        "text": "Brief explanation (200-300 words max)",
        "key_concepts": ["concept1", "concept2", "concept3"]
    }},
    "exercises": [
        {{
            "number": 1,
            "title": "Exercise title (action-oriented)",
            "difficulty": "easy|medium|hard",
            "instructions": "Clear step-by-step instructions",
            "starter_code": "# Starter template with TODO comments",
            "expected_output": "Exact expected result",
            "hints": [
                "Hint 1 (gentle nudge)",
                "Hint 2 (more specific)",
                "Hint 3 (almost the solution)"
            ],
            "solution": "Complete working solution with comments",
            "learning_objective": "What this exercise teaches"
        }}
        // 3-4 exercises total
    ],
    "practice_project": {{
        "title": "Mini-project title",
        "description": "Combine all concepts into one project",
        "requirements": ["requirement1", "requirement2", "requirement3"],
        "starter_template": "// Project starter code",
        "estimated_time": "20-30 minutes"
    }},
    "quiz": [
        {{
            "question": "Test conceptual understanding",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "B",
            "explanation": "Why this is correct"
        }}
        // 3-5 questions
    ]
}}

**EXAMPLE TOPICS BY INDUSTRY:**
- Technology: Build a REST API endpoint, Create a React component
- Finance: Calculate compound interest, Parse financial data
- Healthcare: Process patient records, Validate medical data
- Education: Grade calculator, Student attendance tracker

Generate the complete lesson now for: \"{request.step_title}\".\n"""
        
    def _parse_hands_on_response(self, ai_text: str, request: LessonRequest) -> Dict:
        """Parse Gemini response into structured lesson data"""
        try:
            # Extract JSON from markdown code block
            if '```json' in ai_text:
                start = ai_text.find('```json') + 7
                end = ai_text.find('```', start)
                json_str = ai_text[start:end].strip()
            elif '```' in ai_text:
                start = ai_text.find('```') + 3
                end = ai_text.find('```', start)
                json_str = ai_text[start:end].strip()
            else:
                json_str = ai_text.strip()
            
            lesson_data = json.loads(json_str)
            
            # Validate structure
            required_keys = ['title', 'introduction', 'exercises']
            if not all(key in lesson_data for key in required_keys):
                raise ValueError(f"Missing required keys. Found: {lesson_data.keys()}")
            
            # Add 'type' field if missing
            if 'type' not in lesson_data:
                lesson_data['type'] = 'hands_on'
            
            return lesson_data
        
        except Exception as e:
            logger.error(f"❌ Failed to parse hands-on lesson: {e}")
            logger.debug(f"Raw AI response: {ai_text[:500]}...")
            
            # Return minimal structure
            return {
                'type': 'hands_on',  # REQUIRED: type field for test script
                'title': f'{request.step_title} - Lesson {request.lesson_number}',
                'summary': 'Hands-on practice lesson',
                'introduction': {
                    'text': f'Practice exercises for {request.step_title}',
                    'key_concepts': []
                },
                'exercises': [],
                'error': str(e)
            }
    
    # ========================================
    # VIDEO LESSONS (YouTube + AI analysis)
    # ========================================
    
    async def _generate_video_lesson(self, request: LessonRequest, research_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Generate video-based lesson with YouTube content + AI analysis.
        
        Flow:
        1. Search YouTube for best tutorial video
        2. Fetch video transcript/captions
        3. Gemini analyzes transcript (with research context!)
        4. Generate study guide, timestamps, quiz
        
        Result: Video player + AI-curated notes (verified with research)
        """
        logger.info(f"🎥 Generating video lesson for: {request.step_title}")
        
        # Step 1: Search YouTube with quality ranking
        video_data = self.youtube_service.search_and_rank(request.step_title)

        if not video_data:
            logger.warning(f"⚠️ No YouTube video found for: {request.step_title}")
            return await self._generate_fallback_lesson(request)
        
        # Step 2: Fetch transcript (with YouTube captions + Groq fallback)
        transcript = self.youtube_service.get_transcript(video_data['video_id'])
        
        if not transcript:
            logger.warning(f"⚠️ No transcript available (tried YouTube + Groq): {video_data['video_id']}")
            # Still return video, but without AI analysis
            lesson_data = {
                'type': 'video',  # ✅ FIX: Added 'type' field for test compatibility
                'lesson_type': 'video',
                'title': video_data['title'],
                'video': video_data,
                'summary': video_data['description'][:300],
                'note': 'Transcript not available - watch video for full content',
                'estimated_duration': video_data.get('duration_minutes', 15)
            }
            
            # Add research metadata even if no transcript
            if research_data:
                lesson_data['research_metadata'] = {
                    'research_time': research_data.get('research_time_seconds', 0),
                    'sources_used': research_data.get('summary', ''),
                    'source_type': 'multi_source'
                }

            # Generate unique lesson description
            lesson_data['summary'] = await self._generate_lesson_description(request, lesson_data['summary'])

            return lesson_data
        
        # Step 3: Gemini analyzes transcript (WITH RESEARCH CONTEXT!)
        # Pass the AI call function to the analyzer
        analysis = self.video_analyzer.analyze_transcript(
            transcript=transcript,
            topic=request.step_title,
            user_profile=request.user_profile,
            research_context=research_data,
            ai_call_func=self._call_gemini_api
        )
        
        # Step 4: Combine video + analysis
        lesson_data = {
            'type': 'video',  # ✅ FIX: Added 'type' field for test compatibility
            'lesson_type': 'video',
            'title': video_data['title'],
            'summary': analysis.get('summary', video_data['description'][:300]),
            'video': video_data,
            'key_concepts': analysis.get('key_concepts', []),
            'timestamps': analysis.get('timestamps', []),
            'study_guide': analysis.get('study_guide', ''),
            'quiz': analysis.get('quiz', []),
            'estimated_duration': video_data.get('duration_minutes', 15)
        }

        # Generate unique lesson description
        lesson_data['summary'] = await self._generate_lesson_description(request, lesson_data['summary'])

        # Adjust content complexity based on user's time commitment
        if 'quiz' in lesson_data and lesson_data['quiz']:
            lesson_data['quiz'] = self._adjust_content_complexity(
                lesson_data['quiz'], 
                request.user_profile
            )
        
        if 'key_concepts' in lesson_data and lesson_data['key_concepts']:
            lesson_data['key_concepts'] = self._adjust_content_complexity(
                lesson_data['key_concepts'], 
                request.user_profile
            )
        
        # Add research metadata
        if research_data:
            lesson_data['research_metadata'] = {
                'research_time': research_data.get('research_time_seconds', 0),
                'sources_used': research_data.get('summary', ''),
                'source_type': 'multi_source'
            }
        else:
            lesson_data['research_metadata'] = {
                'source_type': 'ai_only'
            }
        
        logger.info(f"✅ Video lesson generated: {video_data['title'][:50]}... ({lesson_data['estimated_duration']} min)")
        
        return lesson_data
    
    # YouTube service methods have been moved to helpers.youtube module
    # Classes involved:
    # - YouTubeService: Video search with quality ranking
    # - TranscriptService: YouTube transcript + Groq fallback
    # - GroqTranscription: Groq Whisper API wrapper
    # - VideoAnalyzer: Transcript analysis and study guide generation
    #
    # These methods are now called via: self.youtube_service and self.video_analyzer
    
    # ========================================
    # READING LESSONS (Long-form text + diagrams)
    # ========================================
    
    async def _generate_reading_lesson(self, request: LessonRequest, research_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Generate reading-focused lesson with long-form text content.
        
        Structure:
        - In-depth text (2,000-3,000 words)
        - Mermaid.js diagrams (syntax only, rendered client-side)
        - Hero image (Unsplash API)
        - Comprehension quiz
        
        Now includes research context for accuracy!
        """
        logger.info(f"📚 Generating reading lesson for: {request.step_title}")
        
        prompt = self._create_reading_prompt(request, research_data)
        # Call Gemini API
        response = self._call_gemini_api(prompt)
        if not response:
            return await self._generate_fallback_lesson(request)
        # Parse response
        lesson_data = self._parse_reading_response(response, request)

        # Generate unique lesson description
        lesson_data['summary'] = await self._generate_lesson_description(request, lesson_data.get('summary', ''))

        # --- Fetch and inject real GitHub star counts for code examples ---
        if lesson_data.get('code_examples'):
            github_service = GitHubAPIService()
            for example in lesson_data['code_examples']:
                repo_url = None
                # Try to extract repo URL from code example if present
                if 'repository' in example and example['repository'].get('url'):
                    repo_url = example['repository']['url']
                elif 'source_url' in example:
                    repo_url = example['source_url']
                elif 'url' in example:
                    repo_url = example['url']
                # If we have a repo URL, fetch real star count
                if repo_url:
                    # Extract owner/repo from URL
                    import re
                    m = re.search(r'github.com/([^/]+/[^/]+)', repo_url)
                    if m:
                        repo_full_name = m.group(1)
                        try:
                            # Fetch repo info from GitHub API
                            repo_info = await github_service.search_repositories(repo_full_name, max_results=1)
                            if repo_info and isinstance(repo_info, list):
                                stars = repo_info[0].get('stars', None)
                                if stars is not None:
                                    example['real_github_stars'] = stars
                        except Exception as e:
                            logger.warning(f"Could not fetch GitHub stars for {repo_full_name}: {e}")

        # Generate diagrams separately (better success rate)
        if lesson_data.get('content'):
            content_summary = lesson_data['content'][:500]  # First 500 chars for context
            diagrams = self._generate_diagrams(request.step_title, content_summary)
            lesson_data['diagrams'] = diagrams
        else:
            lesson_data['diagrams'] = []

        # Add hero image
        lesson_data['hero_image'] = self._get_unsplash_image(request.step_title)

        # Add metadata
        lesson_data['lesson_type'] = 'reading'
        lesson_data['estimated_duration'] = self._calculate_lesson_duration(30, request.user_profile)  # Time-aware duration

        # Add research metadata
        if research_data:
            lesson_data['research_metadata'] = {
                'research_time': research_data.get('research_time_seconds', 0),
                'sources_used': research_data.get('summary', ''),
                'source_type': 'multi_source'
            }
        else:
            lesson_data['research_metadata'] = {
                'source_type': 'ai_only'
            }

        logger.info(f"✅ Reading lesson generated: {len(lesson_data.get('content', ''))} characters")

        return lesson_data
    
    def _create_reading_prompt(self, request: LessonRequest, research_data: Optional[Dict] = None) -> str:
        """Create Gemini prompt for reading lesson - optimized for reliable JSON output with research context"""
        
        # Build research context section if available
        research_context = ""
        if research_data:
            research_context = f"""

**📚 VERIFIED RESEARCH CONTEXT (Use this as the foundation for your lesson!):**

{self.research_engine.format_for_ai_prompt(research_data)}

**CRITICAL: Base ALL content on the research above. Verify code examples against official docs. Cite community best practices.**
"""
        
        # Build user profile context
        profile_context = self._build_profile_context(request.user_profile)
        profile_section = ""
        if profile_context:
            profile_section = f"""

**LEARNER PROFILE:**
{profile_context}
**IMPORTANT: Tailor examples, scenarios, and case studies to align with the learner's role, career stage, and goals above.**
"""
        
        return f"""You are an expert technical writer creating a comprehensive reading lesson.

Topic: "{request.step_title} - Lesson {request.lesson_number}"
Difficulty: {request.difficulty}
Industry: {request.industry}
Time Commitment: {self._get_time_guidance(request.user_profile)}
{profile_section}{research_context}
CRITICAL: Output ONLY valid JSON. No markdown, no explanations, JUST the JSON object.
Design content appropriate for {self._get_time_guidance(request.user_profile)}.

{{
  "title": "Clear, descriptive title",
  "summary": "Brief 2-3 sentence overview",
  "content": "Main lesson content (800-1200 words). Use \\n for line breaks. Include: introduction, key concepts, real-world examples, best practices, common pitfalls.",
  "diagrams": [
    {{
      "title": "Diagram title",
      "mermaid_code": "graph TD\\nA[Start]-->B[End]",
      "description": "What this diagram shows"
    }}
  ],
  "code_examples": [
    {{
      "title": "Example title",
      "language": "python",
      "code": "# Clear, working example",
      "explanation": "What this code does"
    }}
  ],
  "key_takeaways": ["Point 1", "Point 2", "Point 3", "Point 4", "Point 5"],
  "quiz": [
    {{
      "question": "Test question",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "B",
      "explanation": "Why this is correct"
    }}
  ]
}}

RULES:
- Use \\n for line breaks in content (NOT actual newlines)
- Keep content under 1500 words
- Escape all quotes inside strings
- Include 1-2 mermaid diagrams
- Include 2-3 code examples
- Include 8-10 quiz questions
- Verify all information against research context above

Generate the complete JSON now:
- Flowcharts: `graph TD`
- Sequence diagrams: `sequenceDiagram`
- Class diagrams: `classDiagram`
- Entity relationships: `erDiagram`

Generate the complete lesson now for: "{request.step_title}"."""
    
    def _parse_reading_response(self, ai_text: str, request: LessonRequest) -> Dict:
        """Parse Gemini response for reading lesson with JSON repair"""
        try:
            # Extract JSON from markdown code blocks if present
            if '```json' in ai_text:
                start = ai_text.find('```json') + 7
                end = ai_text.find('```', start)
                json_str = ai_text[start:end].strip()
            elif '```' in ai_text:
                start = ai_text.find('```') + 3
                end = ai_text.find('```', start)
                json_str = ai_text[start:end].strip()
            else:
                json_str = ai_text.strip()
            
            logger.debug(f"📝 Extracted JSON length: {len(json_str)} characters")
            
            # 🔧 TRY 1: Parse as-is
            try:
                lesson_data = json.loads(json_str)
                logger.info("✅ JSON parsed successfully on first attempt")
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ JSON parse error: {e}. Attempting repair...")
                
                # 🔧 TRY 2: Auto-repair common issues
                json_str_repaired = self._repair_json(json_str, str(e))
                lesson_data = json.loads(json_str_repaired)
                logger.info("✅ JSON repaired and parsed successfully!")
            
            # Validate required fields
            if 'content' not in lesson_data or not lesson_data['content']:
                logger.error("❌ Parsed JSON missing 'content' field")
                raise ValueError("Missing content field")
            
            # Add 'type' field if missing
            if 'type' not in lesson_data:
                lesson_data['type'] = 'reading'
            
            # Log success metrics
            content_length = len(lesson_data.get('content', ''))
            diagrams_count = len(lesson_data.get('diagrams', []))
            quiz_count = len(lesson_data.get('quiz', []))
            
            logger.info(f"✅ Reading lesson parsed successfully:")
            logger.info(f"   - Content: {content_length} characters")
            logger.info(f"   - Diagrams: {diagrams_count}")
            logger.info(f"   - Quiz: {quiz_count} questions")
            
            return lesson_data
        
        except Exception as e:
            logger.error(f"❌ Failed to parse reading lesson: {e}")
            logger.debug(f"   Raw response (first 500 chars): {ai_text[:500]}")
            return {
                'type': 'reading',  # REQUIRED: type field
                'title': f'{request.step_title} - Lesson {request.lesson_number}',
                'summary': 'Reading lesson generation failed. Please regenerate.',
                'content': '',
                'diagrams': [],
                'quiz': [],
                'error': str(e)
            }
    
    async def _generate_diagrams(self, topic: str, content_summary: str = "") -> List[Dict]:
        """
        Generate Mermaid.js diagrams using hybrid AI system.
        Higher success rate than embedding in main prompt.
        
        NOW USES HYBRID AI SYSTEM:
        - Primary: DeepSeek V3.1 (GPT-4o quality)
        - Fallback: Groq Llama 3.3 70B
        - Backup: Gemini 2.0 Flash
        
        Args:
            topic: Lesson topic
            content_summary: Optional context from lesson content
        
        Returns:
            List of diagram objects with mermaid_code
        """
        logger.info(f"📊 Generating diagrams for: {topic}")
        
        prompt = f"""Generate 2-3 Mermaid.js diagrams for this programming topic.

Topic: {topic}
{f"Context: {content_summary[:500]}" if content_summary else ""}

Output ONLY a JSON array of diagrams. No markdown, no explanations.

[
  {{
    "title": "Clear diagram title",
    "type": "flowchart",
    "mermaid_code": "graph TD\\n    A[Start] --> B[Process]\\n    B --> C[Decision]\\n    C -->|Yes| D[End]\\n    C -->|No| B",
    "description": "Brief description of what this shows"
  }},
  {{
    "title": "Another diagram",
    "type": "sequence",
    "mermaid_code": "sequenceDiagram\\n    User->>App: Request\\n    App->>DB: Query\\n    DB-->>App: Data\\n    App-->>User: Response",
    "description": "Shows the interaction flow"
  }}
]

RULES:
- Use proper Mermaid.js syntax (test at mermaid.live)
- Escape special characters properly
- Use \\n for line breaks (NOT actual newlines)
- Types: flowchart, sequence, class, er, state
- Include 2-3 diagrams that explain key concepts
- Keep diagrams simple and readable

Generate the JSON array now:"""
        
        try:
            # NOW USES HYBRID AI SYSTEM
            response = await self._generate_with_ai(prompt, json_mode=True, max_tokens=3000)
            
            if not response:
                logger.warning("⚠️ Gemini returned no response for diagrams")
                return []
            
            # Extract JSON
            json_str = response.strip()
            if '```json' in response:
                start = response.find('```json') + 7
                end = response.find('```', start)
                json_str = response[start:end].strip()
            elif '```' in response:
                start = response.find('```') + 3
                end = response.find('```', start)
                json_str = response[start:end].strip()
            
            # Parse
            diagrams = json.loads(json_str)
            
            # Handle different response formats
            if not isinstance(diagrams, list):
                # If it's a dict with a 'diagrams' key, extract that
                if isinstance(diagrams, dict) and 'diagrams' in diagrams:
                    diagrams = diagrams['diagrams']
                # If it's a single diagram dict, wrap in list
                elif isinstance(diagrams, dict) and ('type' in diagrams or 'code' in diagrams):
                    diagrams = [diagrams]
                # If it's a string (Mermaid code), create a diagram object
                elif isinstance(diagrams, str):
                    diagrams = [{'type': 'mermaid', 'code': diagrams}]
                else:
                    logger.warning(f"⚠️ Diagrams response format not recognized: {type(diagrams)}")
                    return []
            
            logger.info(f"✅ Generated {len(diagrams)} diagrams")
            return diagrams
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse diagrams JSON: {e}")
            logger.debug(f"   Response (first 300 chars): {response[:300] if response else 'None'}")
            return []
        except Exception as e:
            logger.error(f"❌ Diagram generation failed: {e}")
            return []
    
    async def _generate_lesson_description(self, request: LessonRequest, lesson_content: str = "") -> str:
        """
        Generate a unique, AI-powered description for each lesson.

        Makes each lesson description specific to the lesson number and content,
        explaining what students will learn in this particular lesson.
        """
        prompt = '''Generate a unique, engaging description for lesson {lesson_number} on "{step_title}".

This is part of a learning module. Make the description specific to this lesson and explain what students will learn.

{lesson_content}

Description should be 2-3 sentences, highlighting the key learning objectives for this specific lesson.

Output only the description text, no quotes or extra formatting.'''.format(
            lesson_number=request.lesson_number,
            step_title=request.step_title,
            lesson_content=f"Lesson content preview: {lesson_content[:300]}" if lesson_content else ""
        )

        try:
            description = await self._generate_with_ai(prompt, max_tokens=200)
            return description.strip() if description else f"Lesson {request.lesson_number} on {request.step_title}"
        except Exception as e:
            logger.warning(f"⚠️ Failed to generate unique description: {e}")
            return f"Lesson {request.lesson_number} on {request.step_title}"
    
    def _get_unsplash_image(self, topic: str) -> Optional[Dict]:
        """
        Get hero image from Unsplash API.
        Returns image URL and attribution.
        """
        if not self.unsplash_api_key:
            logger.warning("⚠️ Unsplash API key not configured - using placeholder")
            return {
                'url': f'https://via.placeholder.com/1200x600?text={topic}',
                'attribution': None
            }
        
        try:
            response = requests.get(
                "https://api.unsplash.com/search/photos",
                params={
                    "query": f"{topic} programming technology",
                    "per_page": 1,
                    "orientation": "landscape"
                },
                headers={"Authorization": f"Client-ID {self.unsplash_api_key}"},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['results']:
                    photo = data['results'][0]
                    return {
                        'url': photo['urls']['regular'],
                        'attribution': {
                            'author': photo['user']['name'],
                            'author_url': photo['user']['links']['html'],
                            'unsplash_url': photo['links']['html']
                        }
                    }
            
            # Fallback to placeholder
            return {
                'url': f'https://via.placeholder.com/1200x600?text={topic}',
                'attribution': None
            }
        
        except Exception as e:
            logger.warning(f"⚠️ Unsplash API error: {e}")
            return {
                'url': f'https://via.placeholder.com/1200x600?text={topic}',
                'attribution': None
            }
    
    # ========================================
    # MIXED LESSONS (Combine all approaches)
    # ========================================
    
    async def _generate_mixed_lesson(self, request: LessonRequest, research_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Generate mixed lesson combining all learning styles.
        
        Distribution:
        - 30% Text content (reading)
        - 30% Video tutorial (with analysis)
        - 20% Hands-on exercises
        - 10% Diagrams (Mermaid.js)
        - 10% Quiz/tests
        
        NOW USES HYBRID AI SYSTEM:
        - Primary: DeepSeek V3.1 (GPT-4o quality)
        - Fallback: Groq Llama 3.3 70B
        - Backup: Gemini 2.0 Flash
        """
        logger.info(f"🎨 Generating mixed lesson for: {request.step_title}")
        
        # Generate components from each style
        # (lighter versions to balance total content)
        
        # 1. Text introduction (shorter than reading-only) - NOW USES HYBRID AI
        text_prompt = self._create_mixed_text_prompt(request)
        text_response = await self._generate_with_ai(text_prompt, json_mode=False, max_tokens=4000)
        text_content = self._parse_mixed_text(text_response) if text_response else {}
        
        # 2. Video component (with optional transcript analysis)
        video_data = self.youtube_service.search_and_rank(request.step_title)

        # 2b. Try to get transcript for video analysis (YouTube or Groq fallback)
        video_analysis = {}
        if video_data:
            transcript = self.youtube_service.get_transcript(video_data['video_id'])
            
            # If we got transcript, do light analysis for mixed lesson
            if transcript:
                logger.info("📝 Analyzing video transcript for mixed lesson...")
                # Lightweight analysis (just key points, not full video lesson analysis)
                analysis_prompt = f"""Analyze this video transcript for "{request.step_title}":

{transcript[:3000]}  # First 3000 chars only for mixed lessons

Provide SHORT analysis (this is part of a mixed lesson):
- summary (2-3 sentences max)
- key_concepts (3-5 points)
- 2 important timestamps

Output as JSON with keys: summary, key_concepts[], timestamps[]"""
                
                # NOW USES HYBRID AI
                analysis_response = await self._generate_with_ai(analysis_prompt, json_mode=True, max_tokens=2000)
                if analysis_response:
                    try:
                        import json
                        video_analysis = json.loads(analysis_response.strip('`').replace('json\n', '').strip())
                    except:
                        logger.warning("⚠️ Could not parse video analysis, skipping")
        
        # 3. Hands-on exercises (fewer than hands-on-only) - NOW USES HYBRID AI
        exercises_prompt = self._create_mixed_exercises_prompt(request)
        exercises_response = await self._generate_with_ai(exercises_prompt, json_mode=False, max_tokens=3000)
        exercises = self._parse_mixed_exercises(exercises_response) if exercises_response else []
        
        # 4. Generate diagrams separately (better success rate) - NOW USES HYBRID AI
        diagrams = await self._generate_diagrams(request.step_title, text_content.get('introduction', '')[:500])
        
        # 5. Combine everything
        lesson_data = {
            'type': 'mixed',  # REQUIRED: type field
            'lesson_type': 'mixed',
            'title': f"{request.step_title} - Lesson {request.lesson_number}",
            'summary': text_content.get('summary', f'Comprehensive lesson on {request.step_title}'),
            
            # Text component (30%)
            'text_content': text_content.get('introduction', ''),
            'text_introduction': text_content.get('introduction', ''),
            'key_concepts': text_content.get('key_concepts', []),
            
            # Video component (30%) - now includes Groq transcription fallback
            'video': video_data,
            'video_summary': video_analysis.get('summary', ''),  # From transcript analysis
            'video_key_concepts': video_analysis.get('key_concepts', []),  # From transcript
            'video_timestamps': video_analysis.get('timestamps', []),  # From transcript
            
            # Hands-on component (20%)
            'exercises': exercises[:2],  # Just 2 exercises
            
            # Diagrams (10%) - from separate generation
            'diagrams': diagrams,
            
            # Quiz (10%)
            'quiz': text_content.get('quiz', []),
            
            'estimated_duration': self._calculate_lesson_duration(60, request.user_profile)  # Time-aware duration (mixed approach)
        }

        # Generate unique lesson description
        lesson_data['summary'] = await self._generate_lesson_description(request, lesson_data['summary'])

        # Adjust content complexity based on user's time commitment
        if 'exercises' in lesson_data:
            lesson_data['exercises'] = self._adjust_content_complexity(
                lesson_data['exercises'], 
                request.user_profile
            )
        
        if 'quiz' in lesson_data:
            lesson_data['quiz'] = self._adjust_content_complexity(
                lesson_data['quiz'], 
                request.user_profile
            )

        # Add research metadata
        if research_data:
            lesson_data['research_metadata'] = {
                'research_time': research_data.get('research_time_seconds', 0),
                'sources_used': research_data.get('summary', ''),
                'source_type': 'multi_source'
            }
        else:
            lesson_data['research_metadata'] = {
                'source_type': 'ai_only'
            }

        logger.info(f"✅ Mixed lesson generated successfully")

        return lesson_data

    # ========================================
    # HELPER METHODS
    # ========================================

    def _call_gemini_api(self, prompt: str) -> Optional[str]:
        """
        Synchronous wrapper for calling Gemini API.
        Used by methods that haven't been converted to async yet.
        """
        import asyncio
        try:
            # Run async method in sync context
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, create a new task
                future = asyncio.ensure_future(self._generate_with_ai(prompt, json_mode=False))
                return future.result() if hasattr(future, 'result') else None
            else:
                # Otherwise run normally
                return loop.run_until_complete(self._generate_with_ai(prompt, json_mode=False))
        except Exception as e:
            logger.error(f"❌ Gemini API call failed: {e}")
            return None

    async def _generate_fallback_lesson(self, request: LessonRequest) -> Dict[str, Any]:
        """
        Generate a basic fallback lesson when AI generation fails.
        Returns minimal structure to prevent complete failure.
        """
        logger.warning(f"⚠️ Generating fallback lesson for: {request.step_title}")

        return {
            'type': request.learning_style,
            'lesson_type': request.learning_style,
            'title': f"{request.step_title} - Lesson {request.lesson_number}",
            'summary': f"This is a placeholder lesson for {request.step_title}. The AI generation encountered an error. Please try regenerating this lesson.",
            'content': f"# {request.step_title}\n\nThis lesson content is currently unavailable due to a generation error. Please try again later.",
            'estimated_duration': 30,
            'error': 'AI generation failed, fallback lesson provided'
        }

    def _repair_json(self, json_str: str, error_msg: str) -> str:
        """
        Attempt to repair common JSON errors.

        Args:
            json_str: Malformed JSON string
            error_msg: Error message from json.loads()

        Returns:
            Repaired JSON string (best effort)
        """
        import re

        # Remove any trailing commas before closing braces/brackets
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)

        # Remove comments (// and /* */)
        json_str = re.sub(r'//.*?$', '', json_str, flags=re.MULTILINE)
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)

        # Ensure the JSON starts with { or [
        json_str = json_str.strip()
        if not json_str.startswith(('{', '[')):
            # Try to find the first { or [
            match = re.search(r'[{\[]', json_str)
            if match:
                json_str = json_str[match.start():]

        # Ensure the JSON ends with } or ]
        if not json_str.endswith(('}', ']')):
            # Try to find the last } or ]
            matches = list(re.finditer(r'[}\]]', json_str))
            if matches:
                json_str = json_str[:matches[-1].end()]

        return json_str

    def _create_mixed_text_prompt(self, request: LessonRequest) -> str:
        """Create prompt for text component of mixed lesson"""
        return f"""Create a concise text introduction for: "{request.step_title}"

REQUIREMENTS:
- 400-600 words (shorter than full reading lesson)
- Clear explanation of core concepts
- 3-5 key takeaways
- 3-5 quiz questions

Output as JSON:
{{
    "summary": "2-3 sentence overview",
    "introduction": "Main text content (400-600 words)",
    "key_concepts": ["concept1", "concept2", "concept3"],
    "quiz": [
        {{
            "question": "Test question",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "B",
            "explanation": "Why this is correct"
        }}
    ]
}}

Generate for: {request.step_title}"""

    def _parse_mixed_text(self, response: str) -> Dict:
        """Parse text component response"""
        try:
            if '```json' in response:
                start = response.find('```json') + 7
                end = response.find('```', start)
                json_str = response[start:end].strip()
            else:
                json_str = response.strip()

            return json.loads(json_str)
        except Exception as e:
            logger.error(f"❌ Failed to parse mixed text: {e}")
            return {
                'summary': '',
                'introduction': '',
                'key_concepts': [],
                'quiz': []
            }

    def _create_mixed_exercises_prompt(self, request: LessonRequest) -> str:
        """Create prompt for exercises component of mixed lesson"""
        return f"""Create 2 practice exercises for: "{request.step_title}"

REQUIREMENTS:
- Focus on hands-on practice
- Include starter code and solution
- Progressive difficulty

Output as JSON array:
[
    {{
        "title": "Exercise title",
        "instructions": "What to build",
        "starter_code": "// Code template",
        "solution": "// Complete solution",
        "hints": ["Hint 1", "Hint 2"]
    }}
]

Generate for: {request.step_title}"""

    def _parse_mixed_exercises(self, response: str) -> List[Dict]:
        """Parse exercises response"""
        try:
            if '```json' in response:
                start = response.find('```json') + 7
                end = response.find('```', start)
                json_str = response[start:end].strip()
            else:
                json_str = response.strip()

            exercises = json.loads(json_str)
            return exercises if isinstance(exercises, list) else []
        except Exception as e:
            logger.error(f"❌ Failed to parse mixed exercises: {e}")
            return []

    async def generate_lessons_for_module(self, module, user_profile: Optional[Dict] = None) -> int:
        """
        Generate all lessons for a module (3-5 lessons by default).
        Called directly from Django mutation when Azure Function provides request key.

        Args:
            module: Module object with id, title, difficulty, etc.
            user_profile: User's onboarding profile (optional)

        Returns:
            Number of lessons created
        """
        from asgiref.sync import sync_to_async
        from lessons.models import LessonContent

        logger.info(f"🚀 [Module] Generating lessons for module: {module.title}")

        try:
            # Determine number of lessons based on module difficulty
            lesson_counts = {
                'beginner': 5,
                'intermediate': 5,
                'advanced': 4
            }
            num_lessons = lesson_counts.get(module.difficulty, 5)
            logger.info(f"📚 Generating {num_lessons} lessons for {module.difficulty} module")

            lessons_created = 0

            # Generate lessons (3-5 depending on complexity)
            for lesson_num in range(1, num_lessons + 1):
                try:
                    # Determine learning style (rotate through styles)
                    styles = ['hands_on', 'video', 'reading', 'mixed']
                    learning_style = styles[(lesson_num - 1) % len(styles)]

                    # Create lesson request
                    lesson_request = LessonRequest(
                        step_title=module.title,
                        lesson_number=lesson_num,
                        learning_style=learning_style,
                        user_profile=user_profile or {},
                        difficulty=module.difficulty,
                        category=getattr(module, 'category', None),
                        enable_research=True
                    )

                    # Generate lesson
                    logger.info(f"  📝 Generating lesson {lesson_num}/{num_lessons} ({learning_style})")
                    lesson_data = await self.generate_lesson(lesson_request)

                    # Save to database
                    lesson_content = await sync_to_async(LessonContent.objects.create)(
                        module=module,
                        lesson_number=lesson_num,
                        content=lesson_data.get('content', {}),
                        learning_style=learning_style,
                        difficulty=module.difficulty,
                        source_type='ai_only',
                        source_attribution=lesson_data.get('source_attribution', {})
                    )
                    logger.info(f"  ✅ Lesson {lesson_num} created: {lesson_content.id}")
                    lessons_created += 1

                except Exception as lesson_error:
                    logger.warning(f"  ⚠️ Failed to generate lesson {lesson_num}: {lesson_error}")
                    # Continue with next lesson even if one fails
                    continue

            logger.info(f"✅ Successfully created {lessons_created}/{num_lessons} lessons")
            return lessons_created

        except Exception as e:
            logger.error(f"❌ Failed to generate lessons for module: {e}", exc_info=True)
            raise
