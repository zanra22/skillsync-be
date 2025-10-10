"""
GitHub API Integration Service

Fetches code examples and repositories using GitHub's Code Search API.
API Docs: https://docs.github.com/en/rest/search

Features:
- 5,000 requests per hour with authentication
- 10 requests per minute unauthenticated
- Search for code examples
- Filter by language, stars, and recency

Author: SkillSync Team
Created: October 9, 2025
"""

import httpx
from typing import Optional, Dict, List
import logging
from datetime import datetime, timedelta
import asyncio
from django.conf import settings

logger = logging.getLogger(__name__)


class GitHubAPIService:
    """
    GitHub API integration for fetching quality code examples
    
    Rate Limits:
    - With authentication: 5,000 requests/hour
    - Without authentication: 60 requests/hour
    
    API Documentation: https://docs.github.com/en/rest
    """
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub API service
        
        Args:
            token: GitHub personal access token (get from https://github.com/settings/tokens)
                   If not provided, will try to use GITHUB_API_TOKEN from settings
        """
        self.token = token or getattr(settings, 'GITHUB_API_TOKEN', None)
        self.timeout = httpx.Timeout(10.0, connect=5.0)
        self.headers = {
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'User-Agent': 'SkillSync-LearningPlatform/1.0'
        }
        
        if self.token:
            self.headers['Authorization'] = f'Bearer {self.token}'
            logger.info("✓ GitHub API initialized with authentication")
        else:
            logger.warning("⚠️  GitHub API initialized without token (limited to 60 requests/hour)")
    
    async def search_code(
        self,
        query: str,
        language: Optional[str] = None,
        min_stars: int = 100,
        max_results: int = 5,
        recent_only: bool = True
    ) -> List[Dict]:
        """
        Search for code examples on GitHub
        
        Args:
            query: Search query (e.g., "function", "class", topic keywords)
            language: Programming language filter (e.g., "python", "javascript")
            min_stars: Minimum repository stars (default: 100)
            max_results: Maximum results to return (default: 5)
            recent_only: Only search repos updated in last year (default: True)
        
        Returns:
            List of code example dictionaries
        """
        # Try main search first
        results = await self._execute_search(query, language, min_stars, max_results, recent_only)
        
        # Fallback 1: If no results and query is multi-word, try first keyword only
        if not results and ' ' in query:
            first_keyword = query.split()[0]
            logger.debug(f"   No results for '{query}', trying simplified: '{first_keyword}'")
            results = await self._execute_search(first_keyword, language, min_stars, max_results, recent_only)
        
        # Fallback 2: If still no results and min_stars > 0, lower star threshold
        if not results and min_stars > 0:
            logger.debug(f"   No results with {min_stars}+ stars, trying with 10+ stars")
            results = await self._execute_search(query, language, 10, max_results, recent_only)
        
        # Fallback 3: If still no results and language specified, try without language filter
        if not results and language:
            logger.debug(f"   No results for {language}, trying all languages")
            results = await self._execute_search(query, None, min_stars, max_results, recent_only)
        
        return results
    
    async def _execute_search(
        self,
        query: str,
        language: Optional[str] = None,
        min_stars: int = 100,
        max_results: int = 5,
        recent_only: bool = True
    ) -> List[Dict]:
        """
        Execute a single GitHub code search
        
        Returns:
            List of code example dictionaries
        """
        try:
            # Build search query
            search_query = query
            
            if language:
                search_query += f" language:{language}"
            
            if min_stars > 0:
                search_query += f" stars:>={min_stars}"
            
            # REMOVED: Date filter too restrictive, causing 0 results
            # Most quality code examples are older than 2 years
            # GitHub star count is sufficient quality indicator
            
            params = {
                'q': search_query,
                'sort': 'stars',  # Sort by repository stars
                'order': 'desc',
                'per_page': min(max_results, 100)  # Max 100 per page
            }
            
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(
                    f"{self.BASE_URL}/search/code",
                    params=params
                )
                response.raise_for_status()
                data = response.json()
            
            items = data.get('items', [])
            
            # Process and format results
            results = []
            for item in items[:max_results]:
                formatted_item = await self._format_code_result(item)
                if formatted_item:
                    results.append(formatted_item)
            
            logger.info(f"✓ Found {len(results)} GitHub code examples for: {query} ({language})")
            return results
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.error("GitHub API rate limit exceeded")
            elif e.response.status_code == 401:
                logger.error("GitHub API authentication failed - check your token")
            elif e.response.status_code == 422:
                logger.warning(f"GitHub API invalid query (422) for: {query} (language: {language})")
            else:
                logger.error(f"GitHub API error: {e.response.status_code}")
            return []
        except httpx.TimeoutException:
            logger.error(f"Timeout searching GitHub for: {query}")
            return []
        except Exception as e:
            logger.error(f"Error searching GitHub: {str(e)}")
            return []
    
    async def _format_code_result(self, item: Dict) -> Optional[Dict]:
        """
        Format code search result
        
        Args:
            item: Raw search result from GitHub API
        
        Returns:
            Formatted result dictionary
        """
        try:
            repo = item.get('repository', {})
            
            # Fetch file content
            content = await self._fetch_file_content(item.get('url'))
            
            return {
                'name': item.get('name', ''),
                'path': item.get('path', ''),
                'html_url': item.get('html_url', ''),
                'repository': {
                    'name': repo.get('full_name', ''),
                    'description': repo.get('description', ''),
                    'stars': repo.get('stargazers_count', 0),
                    'language': repo.get('language', ''),
                    'url': repo.get('html_url', '')
                },
                'content': content or 'Content not available',
                'score': item.get('score', 0)
            }
            
        except Exception as e:
            logger.error(f"Error formatting code result: {str(e)}")
            return None
    
    async def _fetch_file_content(self, file_url: str) -> Optional[str]:
        """
        Fetch actual file content
        
        Args:
            file_url: API URL for the file
        
        Returns:
            File content (first 500 characters)
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(file_url)
                response.raise_for_status()
                data = response.json()
            
            # Content is base64 encoded
            import base64
            content = base64.b64decode(data.get('content', '')).decode('utf-8')
            
            # Return first 500 characters
            return content[:500] if content else None
            
        except Exception as e:
            logger.error(f"Error fetching file content: {str(e)}")
            return None
    
    async def search_repositories(
        self,
        topic: str,
        language: Optional[str] = None,
        min_stars: int = 1000,
        max_results: int = 5
    ) -> List[Dict]:
        """
        Search for repositories by topic
        
        Args:
            topic: Topic or keyword
            language: Programming language filter
            min_stars: Minimum stars (default: 1000)
            max_results: Maximum results (default: 5)
        
        Returns:
            List of repository dictionaries
        """
        try:
            # Build query
            search_query = f"{topic} stars:>={min_stars}"
            
            if language:
                search_query += f" language:{language}"
            
            params = {
                'q': search_query,
                'sort': 'stars',
                'order': 'desc',
                'per_page': max_results
            }
            
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(
                    f"{self.BASE_URL}/search/repositories",
                    params=params
                )
                response.raise_for_status()
                data = response.json()
            
            items = data.get('items', [])
            
            results = [
                {
                    'name': repo.get('full_name', ''),
                    'description': repo.get('description', ''),
                    'stars': repo.get('stargazers_count', 0),
                    'forks': repo.get('forks_count', 0),
                    'language': repo.get('language', ''),
                    'url': repo.get('html_url', ''),
                    'topics': repo.get('topics', []),
                    'created_at': repo.get('created_at', ''),
                    'updated_at': repo.get('updated_at', '')
                }
                for repo in items
            ]
            
            logger.info(f"✓ Found {len(results)} GitHub repositories for: {topic}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching repositories: {str(e)}")
            return []
    
    async def get_learning_resources(
        self,
        topic: str,
        language: str
    ) -> Dict[str, List[Dict]]:
        """
        Get comprehensive learning resources (code examples + repositories)
        
        Args:
            topic: Topic to search for
            language: Programming language
        
        Returns:
            Dictionary with code_examples and repositories
        """
        # Run searches in parallel
        code_task = self.search_code(
            query=topic,
            language=language,
            min_stars=100,
            max_results=5
        )
        
        repo_task = self.search_repositories(
            topic=topic,
            language=language,
            min_stars=500,
            max_results=3
        )
        
        code_examples, repositories = await asyncio.gather(code_task, repo_task)
        
        return {
            'code_examples': code_examples,
            'repositories': repositories
        }
    
    async def check_rate_limit(self) -> Dict:
        """
        Check GitHub API rate limit status
        
        Returns:
            Dictionary with rate limit information
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(f"{self.BASE_URL}/rate_limit")
                response.raise_for_status()
                data = response.json()
            
            core_limit = data.get('resources', {}).get('core', {})
            search_limit = data.get('resources', {}).get('search', {})
            
            return {
                'core': {
                    'limit': core_limit.get('limit', 0),
                    'remaining': core_limit.get('remaining', 0),
                    'used': core_limit.get('limit', 0) - core_limit.get('remaining', 0),
                    'reset': datetime.fromtimestamp(core_limit.get('reset', 0)).strftime('%Y-%m-%d %H:%M:%S')
                },
                'search': {
                    'limit': search_limit.get('limit', 0),
                    'remaining': search_limit.get('remaining', 0),
                    'used': search_limit.get('limit', 0) - search_limit.get('remaining', 0),
                    'reset': datetime.fromtimestamp(search_limit.get('reset', 0)).strftime('%Y-%m-%d %H:%M:%S')
                }
            }
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            return {'error': str(e)}


# Example usage and testing
if __name__ == "__main__":
    async def test_github():
        # Initialize without token for testing (limited rate)
        service = GitHubAPIService()
        
        print("\n🔍 Testing GitHub API Integration\n")
        
        # Check rate limit
        print("📊 Checking rate limit...")
        rate_limit = await service.check_rate_limit()
        
        if 'error' not in rate_limit:
            print(f"  Core API: {rate_limit['core']['remaining']}/{rate_limit['core']['limit']} remaining")
            print(f"  Search API: {rate_limit['search']['remaining']}/{rate_limit['search']['limit']} remaining")
            print(f"  Resets at: {rate_limit['core']['reset']}\n")
        else:
            print(f"  Error: {rate_limit['error']}\n")
        
        # Search Python code
        print("🐍 Searching Python code examples for 'variables'...")
        code_results = await service.search_code(
            query="variables examples",
            language="python",
            min_stars=100,
            max_results=3
        )
        
        print(f"\n✓ Found {len(code_results)} code examples\n")
        
        for i, result in enumerate(code_results, 1):
            print(f"Code Example {i}:")
            print(f"  File: {result['name']}")
            print(f"  Path: {result['path']}")
            print(f"  Repository: {result['repository']['name']} (⭐ {result['repository']['stars']:,})")
            print(f"  URL: {result['html_url']}")
            print(f"  Content preview: {result['content'][:100]}...")
            print("\n" + "="*80 + "\n")
        
        # Search repositories
        print("📦 Searching Python learning repositories...")
        repos = await service.search_repositories(
            topic="python tutorial",
            language="python",
            min_stars=1000,
            max_results=3
        )
        
        print(f"\n✓ Found {len(repos)} repositories\n")
        
        for i, repo in enumerate(repos, 1):
            print(f"Repository {i}:")
            print(f"  Name: {repo['name']}")
            print(f"  Description: {repo['description']}")
            print(f"  Stars: ⭐ {repo['stars']:,}")
            print(f"  Language: {repo['language']}")
            print(f"  URL: {repo['url']}")
            print("\n" + "="*80 + "\n")
    
    asyncio.run(test_github())
