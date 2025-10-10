"""
Stack Overflow API Integration Service

Fetches top-voted answers from Stack Overflow using the Stack Exchange API (FREE).
API Docs: https://api.stackexchange.com/docs

Features:
- 10,000 requests per day (no API key required)
- 300 requests per day (with API key - higher quota)
- Fetches accepted answers with high votes
- Filters by tags and quality

Author: SkillSync Team
Created: October 9, 2025
"""

import httpx
from typing import Optional, Dict, List
import logging
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class StackOverflowAPIService:
    """
    Stack Exchange API integration for fetching quality Q&A content
    
    Rate Limits:
    - Without API key: 10,000 requests/day per IP
    - With API key: 10,000 requests/day per IP + 300 per key
    
    API Documentation: https://api.stackexchange.com/docs
    """
    
    BASE_URL = "https://api.stackexchange.com/2.3"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Stack Overflow API service
        
        Args:
            api_key: Optional API key for higher quota (register at https://stackapps.com/)
        """
        self.api_key = api_key
        self.timeout = httpx.Timeout(10.0, connect=5.0)
        self.headers = {
            'User-Agent': 'SkillSync-LearningPlatform/1.0',
            'Accept': 'application/json'
        }
    
    async def search_questions(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        max_results: int = 5,
        min_votes: int = 5
    ) -> List[Dict]:
        """
        Search Stack Overflow questions with advanced filtering
        
        Args:
            query: Search query
            tags: Optional list of tags to filter by (e.g., ['python', 'variables'])
            max_results: Maximum number of results (default: 5)
            min_votes: Minimum vote count (default: 5)
        
        Returns:
            List of question dictionaries with answers
        
        Note:
            Stack Exchange API has strict IP-based throttling:
            - Max 30 requests/second per IP
            - Ban period: 30 seconds to several minutes
            - If banned, gracefully returns empty list to allow other sources
        """
        try:
            # Build search parameters for /questions endpoint
            # This endpoint is more reliable than /search or /search/advanced
            params = {
                'order': 'desc',
                'sort': 'votes',
                'site': 'stackoverflow',
                'pagesize': max_results * 2,  # Get more to filter for accepted answers
                'filter': '!9_bDDxJY5',  # Predefined filter that includes body
            }
            
            # Add search query using 'intitle' for better results
            if query:
                params['intitle'] = query
            
            if tags:
                params['tagged'] = ';'.join(tags)
            
            if self.api_key:
                params['key'] = self.api_key
            
            # Search for questions using /questions endpoint (most reliable)
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(
                    f"{self.BASE_URL}/questions",  # Changed to /questions endpoint
                    params=params
                )
                response.raise_for_status()
                data = response.json()
            
            questions = data.get('items', [])
            
            # Filter by minimum votes AND accepted answer
            filtered_questions = [
                q for q in questions
                if q.get('score', 0) >= min_votes 
                and q.get('accepted_answer_id') is not None  # Only questions with accepted answers
            ]
            
            # Fetch answers for each question
            results = []
            for question in filtered_questions[:max_results]:
                question_with_answers = await self._fetch_question_with_answers(
                    question['question_id']
                )
                if question_with_answers:
                    results.append(question_with_answers)
            
            logger.info(f"✓ Found {len(results)} Stack Overflow Q&As for: {query}")
            return results
            
        except httpx.TimeoutException:
            logger.error(f"Timeout searching Stack Overflow for: {query}")
            return []
        except httpx.HTTPError as e:
            error_msg = str(e)
            
            # Check for throttle violation (400 or 429)
            if "400" in error_msg or "429" in error_msg:
                logger.warning(f"⚠️ Stack Overflow API throttled (IP ban) - skipping for now")
                logger.info("💡 Stack Exchange throttle info:")
                logger.info("   - Max 30 requests/second per IP")
                logger.info("   - Ban period: 30 sec to few minutes")
                logger.info("   - System will use other research sources")
            else:
                logger.error(f"HTTP error searching Stack Overflow: {error_msg}")
            return []
        except Exception as e:
            logger.error(f"Error searching Stack Overflow: {str(e)}")
            return []
    
    async def _fetch_question_with_answers(self, question_id: int) -> Optional[Dict]:
        """
        Fetch a question with its top-voted answers
        
        Args:
            question_id: Stack Overflow question ID
        
        Returns:
            Dictionary with question and answers
        """
        try:
            params = {
                'order': 'desc',
                'sort': 'votes',  # Sort answers by votes
                'site': 'stackoverflow',
                'filter': 'withbody',  # Include answer body
            }
            
            if self.api_key:
                params['key'] = self.api_key
            
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                # Fetch question details
                question_response = await client.get(
                    f"{self.BASE_URL}/questions/{question_id}",
                    params=params
                )
                question_response.raise_for_status()
                question_data = question_response.json()
                
                if not question_data.get('items'):
                    return None
                
                question = question_data['items'][0]
                
                # Fetch answers
                answers_response = await client.get(
                    f"{self.BASE_URL}/questions/{question_id}/answers",
                    params=params
                )
                answers_response.raise_for_status()
                answers_data = answers_response.json()
                
                answers = answers_data.get('items', [])
                
                # Get top 3 answers or accepted answer
                top_answers = []
                accepted_answer = None
                
                for answer in answers:
                    if answer.get('is_accepted'):
                        accepted_answer = self._format_answer(answer)
                    elif len(top_answers) < 3:
                        top_answers.append(self._format_answer(answer))
                
                # Prioritize accepted answer
                if accepted_answer:
                    top_answers.insert(0, accepted_answer)
                
                return {
                    'question_id': question_id,
                    'title': question.get('title', ''),
                    'body': self._clean_html(question.get('body', '')),
                    'score': question.get('score', 0),
                    'view_count': question.get('view_count', 0),
                    'tags': question.get('tags', []),
                    'link': question.get('link', ''),
                    'creation_date': self._format_date(question.get('creation_date')),
                    'answers': top_answers[:3],  # Top 3 answers max
                    'has_accepted_answer': question.get('accepted_answer_id') is not None
                }
                
        except Exception as e:
            logger.error(f"Error fetching question {question_id}: {str(e)}")
            return None
    
    def _format_answer(self, answer: Dict) -> Dict:
        """
        Format answer data
        
        Args:
            answer: Raw answer data from API
        
        Returns:
            Formatted answer dictionary
        """
        return {
            'answer_id': answer.get('answer_id'),
            'body': self._clean_html(answer.get('body', '')),
            'score': answer.get('score', 0),
            'is_accepted': answer.get('is_accepted', False),
            'creation_date': self._format_date(answer.get('creation_date')),
            'author': answer.get('owner', {}).get('display_name', 'Anonymous'),
            'author_reputation': answer.get('owner', {}).get('reputation', 0)
        }
    
    def _clean_html(self, html_text: str) -> str:
        """
        Clean HTML tags from Stack Overflow content
        
        Args:
            html_text: HTML text
        
        Returns:
            Cleaned text (first 1000 characters)
        """
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_text, 'html.parser')
            
            # Extract code blocks
            code_blocks = soup.find_all('code')
            code_texts = [code.get_text() for code in code_blocks]
            
            # Get text without HTML
            text = soup.get_text(separator=' ', strip=True)
            
            # Limit length
            return text[:1000] if text else ''
            
        except Exception as e:
            logger.error(f"Error cleaning HTML: {str(e)}")
            return html_text[:1000]
    
    def _format_date(self, timestamp: Optional[int]) -> Optional[str]:
        """
        Format Unix timestamp to readable date
        
        Args:
            timestamp: Unix timestamp
        
        Returns:
            Formatted date string
        """
        if not timestamp:
            return None
        
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime('%Y-%m-%d')
        except Exception:
            return None
    
    async def get_top_answers_by_tag(
        self,
        tag: str,
        query: Optional[str] = None,
        max_results: int = 5
    ) -> List[Dict]:
        """
        Get top answers filtered by tag
        
        Args:
            tag: Tag to filter by (e.g., 'python', 'javascript')
            query: Optional search query
            max_results: Maximum results
        
        Returns:
            List of answers
        """
        return await self.search_questions(
            query=query or tag,
            tags=[tag],
            max_results=max_results
        )
    
    async def check_rate_limit(self) -> Dict:
        """
        Check current API rate limit status
        
        Returns:
            Dictionary with quota information
        """
        try:
            params = {'site': 'stackoverflow'}
            if self.api_key:
                params['key'] = self.api_key
            
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(
                    f"{self.BASE_URL}/info",
                    params=params
                )
                response.raise_for_status()
                data = response.json()
            
            quota_remaining = data.get('quota_remaining', 0)
            quota_max = data.get('quota_max', 10000)
            
            return {
                'quota_remaining': quota_remaining,
                'quota_max': quota_max,
                'quota_used': quota_max - quota_remaining,
                'percentage_used': ((quota_max - quota_remaining) / quota_max) * 100
            }
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            return {
                'quota_remaining': 'unknown',
                'quota_max': 'unknown',
                'error': str(e)
            }


# Example usage and testing
if __name__ == "__main__":
    async def test_stackoverflow():
        service = StackOverflowAPIService()
        
        print("\n🔍 Testing Stack Overflow API Integration\n")
        
        # Check rate limit
        print("📊 Checking rate limit...")
        rate_limit = await service.check_rate_limit()
        print(f"  Quota: {rate_limit['quota_remaining']}/{rate_limit['quota_max']} remaining")
        print(f"  Used: {rate_limit.get('percentage_used', 0):.1f}%\n")
        
        # Search Python questions
        print("🐍 Searching Python questions about 'variables'...")
        results = await service.search_questions(
            query="variables",
            tags=['python'],
            max_results=3
        )
        
        print(f"\n✓ Found {len(results)} questions\n")
        
        for i, result in enumerate(results, 1):
            print(f"Question {i}:")
            print(f"  Title: {result['title']}")
            print(f"  Score: {result['score']} votes")
            print(f"  Views: {result['view_count']:,}")
            print(f"  Tags: {', '.join(result['tags'])}")
            print(f"  Answers: {len(result['answers'])}")
            print(f"  Link: {result['link']}")
            
            if result['answers']:
                top_answer = result['answers'][0]
                print(f"\n  Top Answer:")
                print(f"    Score: {top_answer['score']} votes")
                print(f"    Accepted: {'✓' if top_answer['is_accepted'] else '✗'}")
                print(f"    Author: {top_answer['author']} (rep: {top_answer['author_reputation']:,})")
                print(f"    Preview: {top_answer['body'][:200]}...")
            
            print("\n" + "="*80 + "\n")
    
    asyncio.run(test_stackoverflow())
