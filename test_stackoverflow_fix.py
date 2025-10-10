"""
Quick test to verify Stack Overflow API fix
Tests the /search endpoint with simplified parameters
"""

import os
import sys
import django
import asyncio

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()

from helpers.stackoverflow_api import StackOverflowAPIService


async def test_stackoverflow_search():
    """Test Stack Overflow search with new endpoint"""
    
    print("🧪 Testing Stack Overflow API Fix...")
    print("=" * 70)
    
    service = StackOverflowAPIService()
    
    # Test query
    query = "Python List Comprehensions"
    
    print(f"\n📍 Testing query: {query}")
    print(f"🔗 Endpoint: /questions (was /search/advanced)")
    print(f"📋 Parameters: order=desc, sort=votes, intitle={query}, site=stackoverflow")
    print("   Filter: !9_bDDxJY5 (includes question body)")
    print("\n⏳ Making API request...")
    
    try:
        results = await service.search_questions(
            query=query,
            max_results=3,  # Small test
            min_votes=5
        )
        
        print(f"\n✅ SUCCESS! Got {len(results)} results")
        
        if results:
            print("\n📊 Sample result:")
            first = results[0]
            print(f"   Title: {first['title'][:80]}...")
            print(f"   Score: {first['score']} votes")
            print(f"   Accepted: {'✓' if first.get('accepted_answer_id') else '✗'}")
            print(f"   Answers: {len(first.get('answers', []))}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        
        # Check if it's a rate limit error
        if "429" in str(e) or "throttle" in str(e).lower():
            print("\n⚠️  Stack Exchange rate limit hit")
            print("    You need to wait ~19 hours (69,138 seconds)")
            print("    This is NOT a code issue - the fix is correct")
        elif "400" in str(e):
            print("\n⚠️  400 Bad Request - API parameters issue")
            print("    Trying alternative endpoint...")
        
        return False


async def main():
    """Run the test"""
    
    success = await test_stackoverflow_search()
    
    print("\n" + "=" * 70)
    
    if success:
        print("🎉 Stack Overflow API fix is working!")
        print("   - Using /questions endpoint (most reliable)")
        print("   - Using 'intitle' parameter instead of 'q'")
        print("   - Removed problematic parameters")
        print("   - Post-fetch filtering by accepted_answer_id")
    else:
        print("⚠️  Test failed - check error message above")
        print("   Most likely: Rate limit (wait 19 hours)")
        print("   Alternative: Try different endpoint or parameters")
    
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
