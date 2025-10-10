"""
AI-Powered Topic Classification Service

Dynamic, robust topic classification using:
1. AI semantic understanding (primary)
2. Keyword matching (fallback)
3. Context-aware detection
4. Self-learning capability

This replaces static keyword dictionaries with intelligent classification.
"""

import os
import json
import logging
import asyncio
from typing import Dict, Optional, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class AITopicClassifier:
    """
    Intelligent topic classifier using AI for dynamic, context-aware detection.
    
    Features:
    - Semantic understanding (not just keywords)
    - Handles new frameworks/languages automatically
    - Context-aware (understands "React Hooks" vs "React Native")
    - Self-improving (learns from corrections)
    """
    
    def __init__(self):
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self._classification_cache = {}  # Cache AI responses
        self._last_api_call = None  # Track last API call for rate limiting
        self._min_interval = 6.0  # Minimum 6 seconds between API calls (10 req/min = 6s interval)
        
        # Fallback keywords (used only if AI fails)
        self._fallback_keywords = self._load_fallback_keywords()
    
    async def classify_topic(self, topic: str) -> Dict[str, Optional[str]]:
        """
        Classify topic using AI semantic understanding.
        
        Args:
            topic: Topic title (e.g., "Svelte Stores", "Rust Lifetimes", "Kubernetes CRDs")
        
        Returns:
            {
                'category': 'react' | 'python' | 'docker' | 'general',
                'language': 'jsx' | 'python' | None,
                'confidence': 0.95,  # AI confidence score
                'reasoning': 'Angular is a TypeScript framework',
                'related_topics': ['typescript', 'frontend', 'spa']
            }
        """
        # Check cache first (performance optimization)
        if topic in self._classification_cache:
            logger.debug(f"📦 Cache hit for: {topic}")
            return self._classification_cache[topic]
        
        try:
            # Rate limiting: Ensure 6 seconds between API calls (10 req/min max)
            if self._last_api_call is not None:
                from datetime import datetime
                elapsed = (datetime.now() - self._last_api_call).total_seconds()
                if elapsed < self._min_interval:
                    wait_time = self._min_interval - elapsed
                    logger.debug(f"⏱️  Rate limiting: waiting {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
            
            # PRIMARY: AI-powered classification
            self._last_api_call = datetime.now()  # Update timestamp
            classification = await self._ai_classify(topic)
            
            # Cache the result
            self._classification_cache[topic] = classification
            
            return classification
        
        except Exception as e:
            logger.warning(f"⚠️  AI classification failed for '{topic}': {e}")
            
            # FALLBACK: Keyword-based detection
            return self._fallback_classify(topic)
    
    async def _ai_classify(self, topic: str) -> Dict[str, Optional[str]]:
        """
        Use Gemini AI to intelligently classify the topic.
        
        This understands:
        - Semantic context ("React Hooks" → React, not generic JavaScript)
        - New technologies (Svelte, Solid.js, Bun, Deno)
        - Proper categorization (Angular → TypeScript, not JavaScript)
        """
        import google.generativeai as genai
        
        genai.configure(api_key=self.gemini_api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        prompt = f"""
You are a technical topic classifier for a learning platform.

TASK: Classify the following topic into category and programming language.

TOPIC: "{topic}"

RULES:
1. Category = The main framework/technology/domain (react, python, docker, sql, general, etc.)
2. Language = Programming language used (python, javascript, typescript, jsx, go, rust, etc.)
   - Return None if it's a non-programming topic (e.g., "Project Management")
3. Consider the CONTEXT:
   - "React Hooks" → category: react, language: jsx
   - "Angular Services" → category: angular, language: typescript (Angular uses TypeScript)
   - "Vue Components" → category: vue, language: vue
   - "Next.js Routing" → category: nextjs, language: javascript
   - "MongoDB Aggregation" → category: mongodb, language: None (database, not a language)
   - "Docker Containers" → category: docker, language: None (DevOps tool)
   - "Algorithm Design" → category: general, language: None (theory)

4. For NEW technologies you don't recognize:
   - Research it briefly
   - Categorize based on its domain
   - Example: "Svelte Stores" → category: svelte, language: javascript
   - Example: "Bun Runtime" → category: javascript, language: javascript

5. Confidence score (0-1):
   - 1.0 = Absolutely certain (e.g., "Python Variables")
   - 0.8 = Very confident (e.g., "React Hooks")
   - 0.5 = Uncertain (e.g., ambiguous topic)

RESPOND IN JSON ONLY:
{{
    "category": "string or null",
    "language": "string or null",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation (1 sentence)",
    "related_topics": ["related", "topics", "list"]
}}

Example for "Angular Services":
{{
    "category": "angular",
    "language": "typescript",
    "confidence": 0.95,
    "reasoning": "Angular is a TypeScript-based framework; services are core Angular concepts",
    "related_topics": ["typescript", "dependency-injection", "frontend"]
}}
"""
        
        response = await model.generate_content_async(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,  # Low temperature for consistent classification
                response_mime_type="application/json"
            )
        )
        
        # Parse AI response
        result = json.loads(response.text)
        
        logger.info(f"🤖 AI classified '{topic}' → {result['category']}/{result['language']} (confidence: {result['confidence']:.2f})")
        logger.debug(f"   Reasoning: {result['reasoning']}")
        
        return result
    
    def _fallback_classify(self, topic: str) -> Dict[str, Optional[str]]:
        """
        Fallback to keyword-based classification if AI fails.
        
        This is the OLD approach (static keywords) but kept as safety net.
        """
        topic_lower = topic.lower()
        
        # Detect category
        category = 'general'
        for cat, keywords in self._fallback_keywords['categories'].items():
            if any(kw in topic_lower for kw in keywords):
                category = cat
                break
        
        # Detect language
        language = None
        for lang, keywords in self._fallback_keywords['languages'].items():
            if any(kw in topic_lower for kw in keywords):
                language = lang
                break
        
        logger.info(f"🔙 Fallback classified '{topic}' → {category}/{language}")
        
        return {
            'category': category,
            'language': language,
            'confidence': 0.6,  # Lower confidence for keyword matching
            'reasoning': 'Fallback keyword matching (AI unavailable)',
            'related_topics': []
        }
    
    def _load_fallback_keywords(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Load fallback keywords (our current keyword dictionaries).
        Used only when AI classification fails.
        """
        return {
            'categories': {
                # Databases
                'mongodb': ['mongodb', 'mongo db', ' mongo '],
                'sql': ['sql', 'mysql', 'postgresql', 'postgres', 'sqlite'],
                
                # DevOps
                'docker': ['docker', 'container'],
                'kubernetes': ['kubernetes', 'k8s'],
                'git': [' git ', 'github', 'gitlab'],
                
                # JavaScript ecosystem
                'nextjs': ['next.js', 'nextjs'],
                'react': ['react', ' jsx '],
                'vue': ['vue', 'vuejs'],
                'angular': ['angular', ' ng '],
                'typescript': ['typescript', ' ts '],
                'javascript': ['javascript', ' js ', 'node', 'npm'],
                
                # Python
                'python': ['python', 'django', 'flask', 'fastapi'],
                
                # Other languages
                'go': [' go ', 'golang'],
                'rust': ['rust', 'cargo'],
                'java': ['java', 'spring'],
                'php': ['php', 'laravel'],
                'ruby': ['ruby', 'rails'],
                'swift': ['swift', 'swiftui'],
                'kotlin': ['kotlin'],
                
                # Web
                'html': ['html', 'html5'],
                'css': ['css', 'css3', 'flexbox', 'grid', 'tailwind'],
            },
            'languages': {
                'python': ['python', 'django', 'flask'],
                'javascript': ['javascript', 'node', 'npm'],
                'typescript': ['typescript', 'angular'],
                'jsx': ['react', ' jsx '],
                'vue': ['vue', 'vuejs'],
                'go': [' go ', 'golang'],
                'rust': ['rust'],
                'java': ['java'],
                'php': ['php'],
                'ruby': ['ruby'],
                'swift': ['swift'],
                'kotlin': ['kotlin'],
                'cpp': ['c++', 'cpp'],
                'csharp': ['c#', 'csharp', '.net'],
                'sql': ['sql', 'mysql', 'postgresql'],
                'html': ['html'],
                'css': ['css'],
                'shell': [' bash ', ' sh ', ' zsh '],
                'powershell': ['powershell', 'pwsh'],
            }
        }
    
    async def validate_classification(
        self,
        topic: str,
        expected_category: Optional[str],
        expected_language: Optional[str]
    ) -> bool:
        """
        Validate AI classification against expected results.
        Used for testing and self-improvement.
        
        Args:
            topic: Topic to classify
            expected_category: Expected category
            expected_language: Expected language
        
        Returns:
            True if classification matches expectations
        """
        result = await self.classify_topic(topic)
        
        matches = (
            result['category'] == expected_category and
            result['language'] == expected_language
        )
        
        if not matches:
            logger.warning(
                f"⚠️  Classification mismatch for '{topic}':\n"
                f"   Expected: {expected_category}/{expected_language}\n"
                f"   Got: {result['category']}/{result['language']}\n"
                f"   Reasoning: {result['reasoning']}"
            )
        
        return matches
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get classification cache statistics."""
        return {
            'cached_topics': len(self._classification_cache),
            'fallback_categories': len(self._fallback_keywords['categories']),
            'fallback_languages': len(self._fallback_keywords['languages'])
        }


# Singleton instance
_classifier = None

def get_topic_classifier() -> AITopicClassifier:
    """Get or create the global topic classifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = AITopicClassifier()
    return _classifier
