"""
AI-Powered Lesson Generation Service

Generates personalized lessons based on learning style:
- hands_on: Coding exercises, projects, practice
- video: YouTube videos + AI-generated study guides
- reading: Long-form text + diagrams
- mixed: Combination of all approaches

Uses:
        # Gemini API successful response analysis
        lesson_data = {
            'type': 'video',  # REQUIRED: type field
            'lesson_type': 'video',
            'title': video_data['title'],
            'summary': analysis.get('summary', video_data['description'][:300]),
            'video': video_data,
            'key_concepts': analysis.get('key_concepts', []),
            'timestamps': analysis.get('timestamps', []),
            'study_guide': analysis.get('study_guide', ''),
            'quiz': analysis.get('quiz', []),
            'estimated_duration': video_data.get('duration_minutes', 15)
        } for text generation
- YouTube Data API v3 for video search (FREE)
- YouTube Transcript API for captions (FREE)
- Unsplash API for hero images (FREE)
- Mermaid.js for diagrams (client-side rendering)
"""

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

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class LessonRequest:
    """Request data for lesson generation"""
    step_title: str
    lesson_number: int
    learning_style: str  # 'hands_on', 'video', 'reading', 'mixed'
    user_profile: Optional[Dict] = None  # User's onboarding data
    difficulty: str = 'beginner'
    industry: str = 'Technology'
    category: Optional[str] = None  # e.g., 'python', 'javascript', 'react'
    programming_language: Optional[str] = None  # e.g., 'python', 'javascript'
    enable_research: bool = True  # Enable multi-source research (default: True)


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
        
        # Multi-source research engine
        self.research_engine = multi_source_research_engine
        logger.info("🔬 Multi-source research engine initialized")
        
        # API URLs - Use Gemini 2.5 Flash (latest free tier model)
        # Free tier includes: Gemini 2.5 Pro, 2.5 Flash, 2.5 Flash-Lite
        self.gemini_api_url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent'
        
        # Model usage tracking
        self._model_usage = {
            'deepseek_v31': 0,
            'groq': 0,
            'gemini': 0
        }
        
        # Rate limiting tracking
        self._last_deepseek_call = None  # DeepSeek: 20 req/min = 3s intervals
        self._last_gemini_call = None    # Gemini: 10 req/min = 6s intervals
        # Groq: No rate limiting needed (14,400 req/day = unlimited for our use)
        
        # Async client instances (initialized lazily, closed on cleanup)
        self._deepseek_client = None
        self._groq_client = None
        
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
        
        genai.configure(api_key=self.gemini_api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        generation_config = {
            "temperature": 0.7,
            "max_output_tokens": max_tokens,
        }
        
        if json_mode:
            generation_config["response_mime_type"] = "application/json"
        
        response = await model.generate_content_async(
            prompt,
            generation_config=generation_config
        )
        
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
        logger.info(f"🎓 Generating lesson: {request.step_title} - Lesson {request.lesson_number} ({request.learning_style})")
        
        try:
            # Step 1: Run multi-source research BEFORE generation
            research_data = None
            if request.enable_research:
                logger.info(f"🔬 Starting multi-source research for: {request.step_title}")
                research_data = await self._run_research(request)
                
                if research_data:
                    research_summary = research_data.get('summary', 'No summary')
                    research_time = research_data.get('research_time_seconds', 0)
                    logger.info(f"✅ Research complete in {research_time:.1f}s: {research_summary}")
                else:
                    logger.warning("⚠️ Research failed or returned no data - proceeding with AI-only generation")
            else:
                logger.info("ℹ️ Multi-source research disabled - using AI-only generation")
            
            # Step 2: Route to appropriate generator (with research context)
            if request.learning_style == 'hands_on':
                return await self._generate_hands_on_lesson(request, research_data)
            
            elif request.learning_style == 'video':
                return await self._generate_video_lesson(request, research_data)
            
            elif request.learning_style == 'reading':
                return await self._generate_reading_lesson(request, research_data)
            
            elif request.learning_style == 'mixed':
                return await self._generate_mixed_lesson(request, research_data)
            
            else:
                raise ValueError(f"Unknown learning style: {request.learning_style}")
        
        except Exception as e:
            logger.error(f"❌ Lesson generation failed: {e}")
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
            'jsx': ['react', ' jsx ', 'react native', 'react hook'],  # React uses JSX
            
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
            return self._generate_fallback_lesson(request)
        
        # Parse AI response
        lesson_data = self._parse_hands_on_response(response, request)
        
        # Add metadata
        lesson_data['lesson_type'] = 'hands_on'
        lesson_data['estimated_duration'] = 45  # 45 minutes (mostly exercises)
        
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
        
        return f"""You are an expert programming instructor creating a **hands-on coding lesson** for: "{request.step_title} - Lesson {request.lesson_number}".

**LEARNER CONTEXT:**
- Difficulty Level: {request.difficulty}
- Industry: {request.industry}
- Learning Style: Hands-on (prefers doing over watching)
{research_context}
**CRITICAL REQUIREMENTS:**
1. **70% Practice, 30% Theory** - Focus on exercises, not lectures
2. **Progressive Difficulty** - Start simple, build complexity
3. **Real-world Relevance** - Use practical examples from {request.industry}
4. **Immediate Feedback** - Clear expected outputs for each exercise
5. **Accuracy First** - Use research context above to verify all information

**OUTPUT FORMAT (STRICT JSON):**
```json
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
    }},
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
```

**EXAMPLE TOPICS BY INDUSTRY:**
- Technology: Build a REST API endpoint, Create a React component
- Finance: Calculate compound interest, Parse financial data
- Healthcare: Process patient records, Validate medical data
- Education: Grade calculator, Student attendance tracker

Generate the complete lesson now for: "{request.step_title}"."""
        
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
        
        # Step 1: Search YouTube
        video_data = self._search_youtube_video(request.step_title)
        
        if not video_data:
            logger.warning(f"⚠️ No YouTube video found for: {request.step_title}")
            return self._generate_fallback_lesson(request)
        
        # Step 2: Fetch transcript (try YouTube captions first)
        transcript = self._get_youtube_transcript(video_data['video_id'])
        
        # Step 2b: Fallback to Groq Whisper if YouTube captions unavailable
        if not transcript and self.groq_api_key:
            logger.info("⏩ YouTube captions unavailable - using Groq Whisper fallback...")
            transcript = self._transcribe_with_groq(video_data['video_id'])
        
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
            
            return lesson_data
        
        # Step 3: Gemini analyzes transcript (WITH RESEARCH CONTEXT!)
        analysis = self._analyze_video_transcript(transcript, request, research_data)
        
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
    
    def _search_youtube_video(self, topic: str) -> Optional[Dict]:
        """
        Search YouTube for best tutorial video WITH CAPTIONS.
        Prioritizes videos with closed captions available.
        Returns video metadata.
        """
        if not self.youtube_api_key:
            logger.error("❌ YouTube API key not configured")
            return None
        
        try:
            from googleapiclient.discovery import build
            
            youtube = build('youtube', 'v3', developerKey=self.youtube_api_key)
            
            # Search for video
            search_query = f"{topic} tutorial programming"
            logger.info(f"🔍 Searching YouTube: {search_query}")
            
            search_response = youtube.search().list(
                q=search_query,
                part='snippet',
                type='video',
                maxResults=10,  # Get more results to find one with captions
                order='relevance',
                videoDuration='medium',  # 4-20 minutes
                videoDefinition='high',
                videoCaption='closedCaption',  # 🔥 ONLY videos with captions!
                relevanceLanguage='en'
            ).execute()
            
            if not search_response.get('items'):
                logger.warning("⚠️ No videos with captions found, trying without caption filter...")
                # Fallback: Try without caption requirement
                search_response = youtube.search().list(
                    q=search_query,
                    part='snippet',
                    type='video',
                    maxResults=5,
                    order='relevance',
                    videoDuration='medium',
                    videoDefinition='high',
                    relevanceLanguage='en'
                ).execute()
                
                if not search_response.get('items'):
                    return None
            
            # Try each video until we find one with accessible transcript
            for video in search_response['items']:
                video_id = video['id']['videoId']
                
                # Quick check if transcript is available
                if self._has_transcript(video_id):
                    logger.info(f"✅ Found video with transcript: {video_id}")
                    break
            else:
                # No video with transcript found, use first result
                logger.warning("⚠️ No accessible transcripts, using first video")
                video_id = search_response['items'][0]['id']['videoId']
            
            # Get video details (duration, view count, etc.)
            video_response = youtube.videos().list(
                id=video_id,
                part='snippet,contentDetails,statistics'
            ).execute()
            
            if not video_response.get('items'):
                return None
            
            video_details = video_response['items'][0]
            
            # Parse duration (PT15M33S → 15.55 minutes)
            duration_str = video_details['contentDetails']['duration']
            duration_minutes = self._parse_youtube_duration(duration_str)
            
            return {
                'video_id': video_id,
                'title': video_details['snippet']['title'],
                'description': video_details['snippet']['description'],
                'channel': video_details['snippet']['channelTitle'],
                'thumbnail_url': video_details['snippet']['thumbnails']['high']['url'],
                'video_url': f'https://www.youtube.com/watch?v={video_id}',
                'embed_url': f'https://www.youtube.com/embed/{video_id}',
                'duration_minutes': duration_minutes,
                'view_count': int(video_details['statistics'].get('viewCount', 0)),
                'like_count': int(video_details['statistics'].get('likeCount', 0)),
            }
        
        except Exception as e:
            logger.error(f"❌ YouTube search failed: {e}")
            return None
    
    def _parse_youtube_duration(self, duration_str: str) -> int:
        """Parse ISO 8601 duration (PT15M33S) to minutes"""
        import re
        
        # PT15M33S → 15 minutes
        minutes = 0
        hours_match = re.search(r'(\d+)H', duration_str)
        minutes_match = re.search(r'(\d+)M', duration_str)
        
        if hours_match:
            minutes += int(hours_match.group(1)) * 60
        if minutes_match:
            minutes += int(minutes_match.group(1))
        
        return minutes or 10  # Default to 10 if parsing fails
    
    def _has_transcript(self, video_id: str) -> bool:
        """
        Quick check if video has accessible transcript.
        Actually tries to fetch first 3 entries to verify it works.
        Returns True if transcript available, False otherwise.
        """
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            
            # BETTER: Actually try to fetch transcript (not just list)
            # This catches XML parsing errors before we commit to the video
            transcript = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=['en', 'en-US', 'en-GB']  # English variants
            )
            
            # Verify we got some data
            return len(transcript) > 0
        
        except Exception as e:
            # If any error (XML parse, not found, etc), assume no transcript
            logger.debug(f"   No accessible transcript for {video_id}: {str(e)[:50]}")
            return False
    
    def _get_youtube_transcript(self, video_id: str) -> Optional[str]:
        """
        Fetch YouTube video transcript/captions.
        Uses youtube-transcript-api (FREE, no API key needed)
        
        With rate limiting. Only 1 attempt to avoid spam.
        If unavailable, Groq Whisper will be used as fallback.
        """
        # RATE LIMITING: Prevent 429 errors from rapid requests
        import time
        current_time = time.time()
        time_since_last_call = current_time - self.last_youtube_call
        
        if time_since_last_call < 5:
            wait_time = 5 - time_since_last_call
            logger.info(f"⏳ YouTube rate limiting: waiting {wait_time:.1f}s before next request...")
            time.sleep(wait_time)
        
        self.last_youtube_call = time.time()
        
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            
            logger.info(f"📝 Fetching transcript for video: {video_id}")
            
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            
            # Combine all transcript entries
            full_transcript = " ".join([entry['text'] for entry in transcript_list])
            
            logger.info(f"✅ Transcript fetched: {len(full_transcript)} characters")
            
            return full_transcript
        
        except Exception as e:
            logger.warning(f"⚠️ YouTube transcript unavailable: {str(e)[:100]}")
            return None
    
    def _transcribe_with_groq(self, video_id: str) -> Optional[str]:
        """
        Transcribe YouTube video using Groq Whisper API (FREE fallback).
        Only used when YouTube captions are unavailable (~5% of videos).
        
        NOTE: Requires FFmpeg to be installed on the system.
        Installation: https://www.gyan.dev/ffmpeg/builds/ or `scoop install ffmpeg`
        
        Groq Free Tier: 14,400 minutes/day (240 hours) - more than enough!
        Speed: 3-5 seconds per 10-minute video
        
        Returns: Transcript text or None if failed
        """
        if not self.groq_api_key:
            logger.info("ℹ️  Groq transcription skipped - GROQ_API_KEY not configured (optional)")
            return None
        
        try:
            from groq import Groq
            import tempfile
            import subprocess
            import shutil
            
            # Check if FFmpeg is installed
            if not shutil.which('ffmpeg'):
                logger.warning("⚠️ FFmpeg not found - Groq transcription unavailable")
                logger.info("💡 Install FFmpeg: https://www.gyan.dev/ffmpeg/builds/ or 'scoop install ffmpeg'")
                logger.info("💡 Groq is OPTIONAL - 95% of videos work without it")
                return None
            
            logger.info(f"🎙️ Transcribing video with Groq Whisper: {video_id}")
            
            # 1. Download audio using yt-dlp (requires FFmpeg for audio extraction)
            video_url = f'https://www.youtube.com/watch?v={video_id}'
            audio_file = tempfile.mktemp(suffix='.mp3')
            
            # Use yt-dlp to extract audio (fast, no full video download)
            cmd = [
                'yt-dlp',
                '-x',  # Extract audio only
                '--audio-format', 'mp3',
                '--audio-quality', '5',  # Lower quality = faster download
                '-o', audio_file,
                '--no-playlist',
                '--quiet',
                video_url
            ]
            
            subprocess.run(cmd, check=True, timeout=60)  # 60s timeout
            
            # 2. Transcribe with Groq Whisper
            client = Groq(api_key=self.groq_api_key)
            
            with open(audio_file, 'rb') as f:
                transcription = client.audio.transcriptions.create(
                    file=f,
                    model="whisper-large-v3",  # Best accuracy
                    response_format="text",
                    language="en"
                )
            
            # 3. Cleanup
            import os
            os.remove(audio_file)
            
            logger.info(f"✅ Groq transcription complete: {len(transcription)} characters")
            return transcription
        
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Groq transcription timeout for video: {video_id}")
            return None
        except FileNotFoundError:
            logger.warning("⚠️ yt-dlp not installed - Groq transcription unavailable")
            logger.info("💡 Install: pip install yt-dlp (but FFmpeg still required)")
            return None
        except Exception as e:
            logger.error(f"❌ Groq transcription failed: {str(e)[:200]}")
            return None
    
    def _analyze_video_transcript(self, transcript: str, request: LessonRequest, research_data: Optional[Dict] = None) -> Dict:
        """
        Use Gemini to analyze video transcript and generate study materials.
        Now includes research context for verification!
        """
        # Build research context section if available
        research_context = ""
        if research_data:
            research_context = f"""

**📚 VERIFIED RESEARCH CONTEXT (Cross-reference video content with this!):**

{self.research_engine.format_for_ai_prompt(research_data)}

**CRITICAL: Verify video content against research above. Flag any discrepancies. Add missing best practices.**
"""
        
        prompt = f"""You are analyzing a YouTube tutorial video transcript about: "{request.step_title}".

**VIDEO TRANSCRIPT:**
{transcript[:8000]}  
{f"... (truncated, total length: {len(transcript)} chars)" if len(transcript) > 8000 else ""}
{research_context}
**YOUR TASK:**
Generate structured study materials from this video. Use the research context to verify accuracy and add any missing information.

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
    // 5-10 key moments
  ],
  "study_guide": "Detailed notes covering:\n- Topic 1: Explanation\n- Topic 2: Explanation\n...",
  "quiz": [
    {{
      "question": "Based on the video, what is...",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "B",
      "explanation": "The video explains at 3:45..."
    }}
    // 5-7 questions
  ]
}}
```

Generate the analysis now."""
        
        response = self._call_gemini_api(prompt)
        
        if not response:
            return {}
        
        try:
            # Parse JSON response
            if '```json' in response:
                start = response.find('```json') + 7
                end = response.find('```', start)
                json_str = response[start:end].strip()
            else:
                json_str = response.strip()
            
            analysis = json.loads(json_str)
            return analysis
        
        except Exception as e:
            logger.error(f"❌ Failed to parse video analysis: {e}")
            return {}
    
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
            return self._generate_fallback_lesson(request)
        
        # Parse response
        lesson_data = self._parse_reading_response(response, request)
        
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
        lesson_data['estimated_duration'] = 30  # 30 minutes reading
        
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
        
        if not response:
            return self._generate_fallback_lesson(request)
        
        # Parse response
        lesson_data = self._parse_reading_response(response, request)
        
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
        lesson_data['estimated_duration'] = 30  # 30 minutes reading
        
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
        
        return f"""You are an expert technical writer creating a comprehensive reading lesson.

Topic: "{request.step_title} - Lesson {request.lesson_number}"
Difficulty: {request.difficulty}
Industry: {request.industry}
{research_context}
CRITICAL: Output ONLY valid JSON. No markdown, no explanations, JUST the JSON object.

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
        video_data = self._search_youtube_video(request.step_title)
        
        # 2b. Try to get transcript for video analysis (YouTube or Groq fallback)
        video_analysis = {}
        if video_data:
            transcript = self._get_youtube_transcript(video_data['video_id'])
            
            # Fallback to Groq Whisper if YouTube captions unavailable
            if not transcript and self.groq_api_key:
                logger.info("⏩ YouTube captions unavailable - using Groq Whisper fallback...")
                transcript = self._transcribe_with_groq(video_data['video_id'])
            
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
            
            'estimated_duration': 60  # 1 hour (mixed approach takes longer)
        }
        
        # Log video analysis status
        if video_analysis:
            logger.info(f"✅ Mixed lesson with video analysis: {len(video_analysis.get('key_concepts', []))} concepts from transcript")
        else:
            logger.info(f"✅ Mixed lesson generated with {len(lesson_data['exercises'])} exercises (video without transcript)")
        
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
        
        return lesson_data
    
    def _create_mixed_text_prompt(self, request: LessonRequest) -> str:
        """Create prompt for text portion of mixed lesson"""
        return f"""Create a concise introduction for: "{request.step_title}" (500-800 words max).

Include:
- Summary (2-3 sentences)
- Key concepts (5-7 points)
- One Mermaid.js diagram
- 5 quiz questions

Output as JSON with keys: summary, introduction, key_concepts, diagrams[], quiz[]"""
    
    def _create_mixed_exercises_prompt(self, request: LessonRequest) -> str:
        """Create prompt for exercises portion of mixed lesson"""
        return f"""Create 2 coding exercises for: "{request.step_title}".

Each exercise needs:
- Title, instructions, starter_code, expected_output, hints[], solution

Output as JSON array of exercises."""
    
    def _parse_mixed_text(self, ai_text: str) -> Dict:
        """Parse text component of mixed lesson"""
        try:
            if '```json' in ai_text:
                start = ai_text.find('```json') + 7
                end = ai_text.find('```', start)
                json_str = ai_text[start:end].strip()
            else:
                json_str = ai_text.strip()
            
            return json.loads(json_str)
        except:
            return {}
    
    def _parse_mixed_exercises(self, ai_text: str) -> List[Dict]:
        """Parse exercises component of mixed lesson"""
        try:
            if '```json' in ai_text:
                start = ai_text.find('```json') + 7
                end = ai_text.find('```', start)
                json_str = ai_text[start:end].strip()
            else:
                json_str = ai_text.strip()
            
            exercises = json.loads(json_str)
            return exercises if isinstance(exercises, list) else []
        except:
            return []
    
    # ========================================
    # GEMINI API INTEGRATION
    # ========================================
    
    def _call_gemini_api(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """
        Call Gemini API with prompt WITH RETRY LOGIC.
        Returns generated text or None on error.
        
        Implements exponential backoff for network timeouts:
        - Attempt 1: 30s timeout
        - Attempt 2: 45s timeout (after 2s wait)
        - Attempt 3: 60s timeout (after 4s wait)
        """
        if not self.gemini_api_key:
            logger.error("❌ Gemini API key not configured")
            return None
        
        base_timeout = 30
        retry_delays = [2, 4]  # Seconds to wait between retries
        
        for attempt in range(max_retries):
            try:
                timeout = base_timeout + (attempt * 15)  # 30s, 45s, 60s
                
                headers = {'Content-Type': 'application/json'}
                
                payload = {
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }],
                    "generationConfig": {
                        "temperature": 0.3,  # Lower for more consistent output
                        "topK": 20,
                        "topP": 0.8,
                        "maxOutputTokens": 8192,  # Max output length
                        "candidateCount": 1,
                    }
                }
                
                logger.debug(f"📤 Calling Gemini API (attempt {attempt + 1}/{max_retries}, timeout={timeout}s, prompt={len(prompt)} chars)")
                
                response = requests.post(
                    f"{self.gemini_api_url}?key={self.gemini_api_key}",
                    headers=headers,
                    json=payload,
                    timeout=timeout  # Dynamic timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    generated_text = result['candidates'][0]['content']['parts'][0]['text']
                    
                    logger.debug(f"✅ Gemini API success (response length: {len(generated_text)} chars)")
                    
                    return generated_text
                else:
                    logger.error(f"❌ Gemini API error {response.status_code}: {response.text}")
                    # Don't retry on 400-level errors (bad request, auth, etc.)
                    if 400 <= response.status_code < 500:
                        return None
                    # Retry on 500-level errors (server issues)
                    raise Exception(f"Server error: {response.status_code}")
            
            except requests.exceptions.Timeout as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delays[attempt]
                    logger.warning(f"⏱️ Timeout on attempt {attempt + 1}, retrying in {wait_time}s...")
                    import time
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ Gemini API timeout after {max_retries} attempts: {e}")
                    return None
            
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delays[attempt]
                    logger.warning(f"⚠️ Network error on attempt {attempt + 1}, retrying in {wait_time}s...")
                    import time
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ Gemini API call failed after {max_retries} attempts: {e}")
                    return None
            
            except Exception as e:
                logger.error(f"❌ Gemini API unexpected error: {e}")
                return None
        
        return None  # All retries exhausted
    
    # ========================================
    # JSON REPAIR UTILITIES
    # ========================================
    
    def _repair_json(self, json_str: str, error_msg: str) -> str:
        """
        Attempt to auto-repair common JSON errors from AI models.
        
        Common issues:
        1. Unterminated strings (missing closing quote)
        2. Trailing commas
        3. Unescaped quotes in strings
        4. Missing closing brackets
        """
        import re
        
        logger.debug(f"🔧 Attempting JSON repair for error: {error_msg}")
        
        repaired = json_str
        
        # Fix 1: Unterminated string at end (most common)
        if "Unterminated string" in error_msg or "line 1, column 0" in error_msg:
            # Add closing quote to last string if missing
            if repaired.rstrip().endswith(',') or repaired.rstrip().endswith('{'):
                repaired = repaired.rstrip() + '"'
            elif not repaired.rstrip().endswith('"') and not repaired.rstrip().endswith('}'):
                repaired = repaired.rstrip() + '"'
        
        # Fix 2: Trailing commas before closing brackets
        repaired = re.sub(r',\s*}', '}', repaired)
        repaired = re.sub(r',\s*]', ']', repaired)
        
        # Fix 3: Missing closing brackets (try to balance)
        open_braces = repaired.count('{')
        close_braces = repaired.count('}')
        if open_braces > close_braces:
            repaired += '}' * (open_braces - close_braces)
        
        open_brackets = repaired.count('[')
        close_brackets = repaired.count(']')
        if open_brackets > close_brackets:
            repaired += ']' * (open_brackets - close_brackets)
        
        # Fix 4: Unescaped newlines in strings (replace with \n)
        # This is tricky - only do inside quoted strings
        # repaired = re.sub(r'(?<=")([^"]*)\n([^"]*?)(?=")', r'\1\\n\2', repaired)
        
        logger.debug(f"🔧 Repair applied: {len(json_str)} → {len(repaired)} chars")
        
        return repaired
    
    # ========================================
    # FALLBACK CONTENT
    # ========================================
    
    async def _generate_fallback_lesson(self, request: LessonRequest) -> Dict[str, Any]:
        """
        Generate basic fallback lesson when AI fails.
        Minimal structure to prevent complete failure.
        """
        logger.warning(f"⚠️ Using fallback lesson for: {request.step_title}")
        
        return {
            'type': request.learning_style,  # REQUIRED: Match expected field name
            'lesson_type': request.learning_style,
            'title': f"{request.step_title} - Lesson {request.lesson_number}",
            'summary': f"This lesson covers {request.step_title}. Due to technical limitations, detailed content is not available.",
            'content': f"# {request.step_title}\n\nThis is a placeholder lesson. Please try regenerating or contact support.",
            'estimated_duration': 20,
            'is_fallback': True,
            'error_note': 'AI generation unavailable - using fallback content'
        }


# Global instance
lesson_generation_service = LessonGenerationService()
