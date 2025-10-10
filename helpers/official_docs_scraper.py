"""
Official Documentation Scraper Service

Fetches content from official documentation sources for various programming languages,
frameworks, and tools. Uses web scraping with BeautifulSoup to extract relevant content.

Author: SkillSync Team
Created: October 9, 2025
"""

import httpx
from bs4 import BeautifulSoup
from typing import Optional, Dict, List
import asyncio
from urllib.parse import urljoin, quote
import logging

logger = logging.getLogger(__name__)


class OfficialDocsScraperService:
    """
    Scrapes official documentation from various sources
    
    Supported sources:
    - Python: docs.python.org
    - JavaScript: developer.mozilla.org (MDN)
    - React: react.dev
    - Django: docs.djangoproject.com
    - Next.js: nextjs.org/docs
    - Node.js: nodejs.org/docs
    - TypeScript: typescriptlang.org/docs
    - Vue.js: vuejs.org/guide
    - And more...
    """
    
    # Mapping of categories/languages to their official documentation URLs
    DOC_SOURCES = {
        'python': {
            'base_url': 'https://docs.python.org/3/',
            'search_url': 'https://docs.python.org/3/search.html?q={query}',
            'description': 'Official Python Documentation'
        },
        'javascript': {
            'base_url': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript',
            'search_url': 'https://developer.mozilla.org/en-US/search?q={query}',
            'description': 'MDN Web Docs - JavaScript'
        },
        'react': {
            'base_url': 'https://react.dev',
            'search_url': 'https://react.dev/search?q={query}',
            'description': 'Official React Documentation'
        },
        'django': {
            'base_url': 'https://docs.djangoproject.com/en/stable/',
            'search_url': 'https://docs.djangoproject.com/en/stable/search/?q={query}',
            'description': 'Official Django Documentation'
        },
        'nextjs': {
            'base_url': 'https://nextjs.org/docs',
            'search_url': 'https://nextjs.org/docs?search={query}',
            'description': 'Official Next.js Documentation'
        },
        'nodejs': {
            'base_url': 'https://nodejs.org/docs/latest/api/',
            'search_url': 'https://nodejs.org/api/',
            'description': 'Official Node.js Documentation'
        },
        'typescript': {
            'base_url': 'https://www.typescriptlang.org/docs/',
            'search_url': 'https://www.typescriptlang.org/docs/handbook/',
            'description': 'Official TypeScript Documentation'
        },
        'vue': {
            'base_url': 'https://vuejs.org/guide/',
            'search_url': 'https://vuejs.org/guide/introduction.html',
            'description': 'Official Vue.js Documentation'
        },
        'angular': {
            'base_url': 'https://angular.dev/docs',
            'search_url': 'https://angular.dev/search?query={query}',
            'description': 'Official Angular Documentation'
        },
        'flask': {
            'base_url': 'https://flask.palletsprojects.com/',
            'search_url': 'https://flask.palletsprojects.com/en/latest/search/?q={query}',
            'description': 'Official Flask Documentation'
        },
        'fastapi': {
            'base_url': 'https://fastapi.tiangolo.com/',
            'search_url': 'https://fastapi.tiangolo.com/',
            'description': 'Official FastAPI Documentation'
        },
        'express': {
            'base_url': 'https://expressjs.com/',
            'search_url': 'https://expressjs.com/en/api.html',
            'description': 'Official Express.js Documentation'
        },
        'docker': {
            'base_url': 'https://docs.docker.com/',
            'search_url': 'https://docs.docker.com/search/?q={query}',
            'description': 'Official Docker Documentation'
        },
    }
    
    def __init__(self):
        self.timeout = httpx.Timeout(10.0, connect=5.0)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    
    async def fetch_official_docs(self, topic: str, category: str) -> Optional[Dict]:
        """
        Fetch official documentation for a given topic
        
        Args:
            topic: The topic to search for (e.g., "variables", "functions")
            category: The category/language (e.g., "python", "javascript")
        
        Returns:
            Dictionary with documentation content or None if not found
        """
        category_lower = category.lower()
        
        if category_lower not in self.DOC_SOURCES:
            logger.warning(f"No official docs source configured for category: {category}")
            return None
        
        doc_source = self.DOC_SOURCES[category_lower]
        
        try:
            # Try to fetch the base documentation page
            result = await self._fetch_and_parse(
                doc_source['base_url'],
                topic,
                doc_source['description']
            )
            
            if result:
                logger.info(f"✓ Fetched official docs for {category}: {topic}")
                return result
            
            logger.warning(f"No official docs found for {category}: {topic}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching official docs for {category}: {str(e)}")
            return None
    
    async def _fetch_and_parse(self, url: str, topic: str, source_name: str) -> Optional[Dict]:
        """
        Fetch and parse HTML content from a documentation page
        
        Args:
            url: The URL to fetch
            topic: The topic being searched
            source_name: Name of the documentation source
        
        Returns:
            Parsed content dictionary or None
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'lxml')
                
                # Extract relevant content
                content = self._extract_content(soup, topic)
                
                if content:
                    return {
                        'source': source_name,
                        'url': url,
                        'title': content.get('title', topic),
                        'content': content.get('text', ''),
                        'code_examples': content.get('code_examples', []),
                        'sections': content.get('sections', [])
                    }
                
                return None
                
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching {url}")
            return None
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching {url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error parsing {url}: {str(e)}")
            return None
    
    def _extract_content(self, soup: BeautifulSoup, topic: str) -> Optional[Dict]:
        """
        Extract relevant content from parsed HTML
        
        Args:
            soup: BeautifulSoup parsed HTML
            topic: The topic being searched
        
        Returns:
            Dictionary with extracted content
        """
        try:
            # Try to find the main content area
            # Different docs sites use different structures
            main_content = (
                soup.find('main') or
                soup.find('article') or
                soup.find('div', class_='document') or
                soup.find('div', class_='content') or
                soup.find('div', id='content') or
                soup.body
            )
            
            if not main_content:
                return None
            
            # Extract title
            title = None
            title_tag = (
                main_content.find('h1') or
                soup.find('title')
            )
            if title_tag:
                title = title_tag.get_text(strip=True)
            
            # Extract text content (first 2000 characters)
            paragraphs = main_content.find_all(['p', 'div'], limit=10)
            text_content = ' '.join([p.get_text(strip=True) for p in paragraphs])[:2000]
            
            # Extract code examples
            code_examples = []
            code_blocks = main_content.find_all(['code', 'pre'], limit=5)
            for code_block in code_blocks:
                code_text = code_block.get_text(strip=True)
                if code_text and len(code_text) > 10:  # Skip very short snippets
                    code_examples.append(code_text[:500])  # Limit length
            
            # Extract section headings
            sections = []
            headings = main_content.find_all(['h2', 'h3'], limit=10)
            for heading in headings:
                section_text = heading.get_text(strip=True)
                if section_text:
                    sections.append(section_text)
            
            return {
                'title': title or topic,
                'text': text_content,
                'code_examples': code_examples,
                'sections': sections
            }
            
        except Exception as e:
            logger.error(f"Error extracting content: {str(e)}")
            return None
    
    async def fetch_multiple_categories(self, topic: str, categories: List[str]) -> Dict[str, Optional[Dict]]:
        """
        Fetch official docs from multiple categories in parallel
        
        Args:
            topic: The topic to search for
            categories: List of categories to search
        
        Returns:
            Dictionary mapping category to documentation content
        """
        tasks = [
            self.fetch_official_docs(topic, category)
            for category in categories
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            category: result if not isinstance(result, Exception) else None
            for category, result in zip(categories, results)
        }
    
    def get_supported_categories(self) -> List[str]:
        """
        Get list of supported documentation categories
        
        Returns:
            List of category names
        """
        return list(self.DOC_SOURCES.keys())
    
    def get_doc_source_info(self, category: str) -> Optional[Dict]:
        """
        Get information about a documentation source
        
        Args:
            category: The category to get info for
        
        Returns:
            Dictionary with source info or None
        """
        return self.DOC_SOURCES.get(category.lower())


# Example usage and testing
if __name__ == "__main__":
    async def test_scraper():
        scraper = OfficialDocsScraperService()
        
        print("\n🔍 Testing Official Documentation Scraper\n")
        print(f"Supported categories: {', '.join(scraper.get_supported_categories())}\n")
        
        # Test Python documentation
        print("📚 Fetching Python documentation for 'variables'...")
        result = await scraper.fetch_official_docs("variables", "python")
        if result:
            print(f"✓ Found: {result['title']}")
            print(f"  URL: {result['url']}")
            print(f"  Content length: {len(result['content'])} chars")
            print(f"  Code examples: {len(result['code_examples'])}")
        else:
            print("✗ Not found")
        
        print("\n" + "="*80 + "\n")
        
        # Test JavaScript documentation
        print("📚 Fetching JavaScript documentation for 'functions'...")
        result = await scraper.fetch_official_docs("functions", "javascript")
        if result:
            print(f"✓ Found: {result['title']}")
            print(f"  URL: {result['url']}")
            print(f"  Content length: {len(result['content'])} chars")
            print(f"  Code examples: {len(result['code_examples'])}")
        else:
            print("✗ Not found")
    
    asyncio.run(test_scraper())
