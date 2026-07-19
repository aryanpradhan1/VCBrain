#!/usr/bin/env python3
"""Debug Tavily search results for team member discovery."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.diligence_memo.clients import TavilySearchClient

def debug_search():
    """Test Tavily search for a known LinkedIn profile."""
    print("=" * 60)
    print("Debugging Tavily Search")
    print("=" * 60)

    # Test 1: Search for Aryan (who we know has LinkedIn)
    test_cases = [
        {
            "name": "Aryan Pradhan",
            "role": "COO",
            "company": "Jvala",
            "query": '"Aryan Pradhan" COO Jvala LinkedIn'
        },
        {
            "name": "Aryan Pradhan",
            "role": "",
            "company": "",
            "query": '"Aryan Pradhan" LinkedIn'
        },
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}: {test['query']}")
        print('='*60)

        try:
            client = TavilySearchClient()
            results = client.search(test['query'], max_results=5)

            print(f"✅ Found {len(results)} results:\n")

            for j, item in enumerate(results, 1):
                print(f"Result {j}:")
                print(f"  Title: {item.title}")
                print(f"  URL: {item.url}")
                print(f"  Content: {item.content[:200]}...")
                print()

                # Check for LinkedIn in URL or content
                full_text = f"{item.url} {item.content}"
                if 'linkedin.com/in/' in full_text.lower():
                    print(f"  ✅ Contains LinkedIn profile!")
                if 'github.com/' in full_text.lower():
                    print(f"  ✅ Contains GitHub profile!")
                print()

        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_search()
