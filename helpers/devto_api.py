"""
Dev.to API Integration Service

Fetches community articles from Dev.to (Forem platform).
API Docs: https://developers.forem.com/api

Features:
- FREE and unlimited API access
- No authentication required for public data
- Search by tags
- Filter by reactions, views, comments

Author: SkillSync Team
Created: October 9, 2025
"""

import httpx
from typing import Optional, Dict, List
import logging
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class DevToAPIService:
    """
    Dev.to API integration for fetching quality community articles
    
    Rate Limits: None (FREE unlimited access)
    API Documentation: https://developers.forem.com/api
    """
    
    BASE_URL = "https://dev.to/api"
    
    def __init__(self):
        """Initialize Dev.to API service"""
        self.timeout = httpx.Timeout(10.0, connect=5.0)
        self.headers = {
            'User-Agent': 'SkillSync-LearningPlatform/1.0',
            'Accept': 'application/json'
        }
    
    async def search_articles(
        self,
        query: Optional[str] = None,
        tag: Optional[str] = None,
        min_reactions: int = 20,
        max_results: int = 5,
        top_period: int = 7
    ) -> List[Dict]:
        """
        Search Dev.to articles
        
        Args:
            query: Search query (optional if tag is provided)
            tag: Tag to filter by (e.g., 'python', 'javascript', 'react')
            min_reactions: Minimum number of positive reactions (default: 20)
            max_results: Maximum results to return (default: 5)
            top_period: Number of days to look back for top articles (default: 7)
        
        Returns:
            List of article dictionaries
        """
        try:
            params = {
                'per_page': 30,  # Fetch more, filter later
                'top': top_period  # Top articles in last N days
            }
            
            if tag:
                params['tag'] = tag
            
            if query:
                params['q'] = query
            
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(
                    f"{self.BASE_URL}/articles",
                    params=params
                )
                response.raise_for_status()
                articles = response.json()
            
            # Filter by minimum reactions
            filtered_articles = [
                article for article in articles
                if article.get('positive_reactions_count', 0) >= min_reactions
            ]
            
            # Sort by reactions (highest first)
            sorted_articles = sorted(
                filtered_articles,
                key=lambda x: x.get('positive_reactions_count', 0),
                reverse=True
            )
            
            # Format results
            results = []
            for article in sorted_articles[:max_results]:
                formatted_article = await self._format_article(article)
                if formatted_article:
                    results.append(formatted_article)
            
            logger.info(f"✓ Found {len(results)} Dev.to articles for: {tag or query}")
            return results
            
        except httpx.TimeoutException:
            logger.error(f"Timeout searching Dev.to for: {tag or query}")
            return []
        except httpx.HTTPError as e:
            logger.error(f"HTTP error searching Dev.to: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error searching Dev.to: {str(e)}")
            return []
    
    async def _format_article(self, article: Dict) -> Optional[Dict]:
        """
        Format article data
        
        Args:
            article: Raw article data from API
        
        Returns:
            Formatted article dictionary
        """
        try:
            # Fetch full article content if needed
            article_id = article.get('id')
            full_article = await self._fetch_article_by_id(article_id) if article_id else article
            
            return {
                'id': article.get('id'),
                'title': article.get('title', ''),
                'description': article.get('description', ''),
                'url': article.get('url', ''),
                'cover_image': article.get('cover_image'),
                'published_at': article.get('published_at', ''),
                'reactions_count': article.get('positive_reactions_count', 0),
                'comments_count': article.get('comments_count', 0),
                'reading_time_minutes': article.get('reading_time_minutes', 0),
                'tags': article.get('tag_list', []),
                'author': {
                    'name': article.get('user', {}).get('name', 'Unknown'),
                    'username': article.get('user', {}).get('username', ''),
                    'profile_url': article.get('user', {}).get('website_url', '')
                },
                'body_markdown': full_article.get('body_markdown', '')[:1000] if full_article else ''
            }
            
        except Exception as e:
            logger.error(f"Error formatting article: {str(e)}")
            return None
    
    async def _fetch_article_by_id(self, article_id: int) -> Optional[Dict]:
        """
        Fetch full article details by ID
        
        Args:
            article_id: Article ID
        
        Returns:
            Full article data
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(f"{self.BASE_URL}/articles/{article_id}")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error fetching article {article_id}: {str(e)}")
            return None
    
    async def get_top_articles_by_tag(
        self,
        tag: str,
        max_results: int = 5,
        top_period: int = 7
    ) -> List[Dict]:
        """
        Get top articles for a specific tag
        
        Args:
            tag: Tag to search (e.g., 'python', 'javascript')
            max_results: Maximum results (default: 5)
            top_period: Number of days (default: 7)
        
        Returns:
            List of top articles
        """
        return await self.search_articles(
            tag=tag,
            min_reactions=20,
            max_results=max_results,
            top_period=top_period
        )
    
    async def get_trending_articles(
        self,
        tags: List[str],
        max_results_per_tag: int = 3
    ) -> Dict[str, List[Dict]]:
        """
        Get trending articles for multiple tags
        
        Args:
            tags: List of tags to search
            max_results_per_tag: Max results per tag (default: 3)
        
        Returns:
            Dictionary mapping tag to articles
        """
        tasks = [
            self.get_top_articles_by_tag(tag, max_results=max_results_per_tag)
            for tag in tags
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            tag: result if not isinstance(result, Exception) else []
            for tag, result in zip(tags, results)
        }
    
    async def search_beginner_friendly_articles(
        self,
        tag: str,
        max_results: int = 5
    ) -> List[Dict]:
        """
        Search for beginner-friendly articles
        
        Args:
            tag: Tag to search
            max_results: Maximum results
        
        Returns:
            List of beginner-friendly articles
        """
        # Search with beginner-related keywords
        articles = await self.search_articles(
            query=f"{tag} tutorial beginner",
            tag=tag,
            min_reactions=10,  # Lower threshold for beginners
            max_results=max_results * 2  # Fetch more for filtering
        )
        
        # Filter for beginner content (check title/description)
        beginner_keywords = ['beginner', 'introduction', 'getting started', 'tutorial', 'basics', 'guide']
        
        beginner_articles = []
        for article in articles:
            title_lower = article['title'].lower()
            desc_lower = article['description'].lower()
            
            if any(keyword in title_lower or keyword in desc_lower for keyword in beginner_keywords):
                beginner_articles.append(article)
            
            if len(beginner_articles) >= max_results:
                break
        
        return beginner_articles
    
    async def get_article_statistics(self, tag: str) -> Dict:
        """
        Get statistics about articles for a tag
        
        Args:
            tag: Tag to analyze
        
        Returns:
            Statistics dictionary
        """
        try:
            articles = await self.search_articles(
                tag=tag,
                min_reactions=0,
                max_results=50,
                top_period=30
            )
            
            if not articles:
                return {'error': 'No articles found'}
            
            total_reactions = sum(a['reactions_count'] for a in articles)
            total_comments = sum(a['comments_count'] for a in articles)
            avg_reading_time = sum(a['reading_time_minutes'] for a in articles) / len(articles)
            
            return {
                'total_articles': len(articles),
                'total_reactions': total_reactions,
                'avg_reactions': total_reactions / len(articles),
                'total_comments': total_comments,
                'avg_comments': total_comments / len(articles),
                'avg_reading_time_minutes': round(avg_reading_time, 1),
                'top_article': max(articles, key=lambda x: x['reactions_count'])['title']
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return {'error': str(e)}


# Example usage and testing
if __name__ == "__main__":
    async def test_devto():
        service = DevToAPIService()
        
        print("\n🔍 Testing Dev.to API Integration\n")
        
        # Search Python articles
        print("🐍 Searching Python articles...")
        articles = await service.search_articles(
            tag='python',
            min_reactions=50,
            max_results=5,
            top_period=7
        )
        
        print(f"\n✓ Found {len(articles)} articles\n")
        
        for i, article in enumerate(articles, 1):
            print(f"Article {i}:")
            print(f"  Title: {article['title']}")
            print(f"  Reactions: 💖 {article['reactions_count']}")
            print(f"  Comments: 💬 {article['comments_count']}")
            print(f"  Reading time: ⏱️  {article['reading_time_minutes']} min")
            print(f"  Tags: {', '.join(article['tags'])}")
            print(f"  Author: {article['author']['name']} (@{article['author']['username']})")
            print(f"  URL: {article['url']}")
            print(f"  Description: {article['description'][:150]}...")
            print("\n" + "="*80 + "\n")
        
        # Get beginner articles
        print("👶 Searching beginner-friendly JavaScript articles...")
        beginner_articles = await service.search_beginner_friendly_articles(
            tag='javascript',
            max_results=3
        )
        
        print(f"\n✓ Found {len(beginner_articles)} beginner articles\n")
        
        for i, article in enumerate(beginner_articles, 1):
            print(f"Beginner Article {i}:")
            print(f"  {article['title']}")
            print(f"  💖 {article['reactions_count']} reactions")
            print(f"  🔗 {article['url']}\n")
        
        # Get statistics
        print("📊 Getting Python article statistics...")
        stats = await service.get_article_statistics('python')
        
        if 'error' not in stats:
            print(f"\nPython Tag Statistics:")
            print(f"  Total articles: {stats['total_articles']}")
            print(f"  Total reactions: {stats['total_reactions']:,}")
            print(f"  Avg reactions: {stats['avg_reactions']:.1f}")
            print(f"  Avg reading time: {stats['avg_reading_time_minutes']} min")
            print(f"  Top article: {stats['top_article']}")
        else:
            print(f"  Error: {stats['error']}")
    
    asyncio.run(test_devto())
