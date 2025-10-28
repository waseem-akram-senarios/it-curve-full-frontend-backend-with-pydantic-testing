#!/usr/bin/env python3
"""
Test script to verify web search functionality
"""
import asyncio
import sys
import os

# Add the IT_Curves_Bot directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'IT_Curves_Bot'))

async def test_search():
    """Test the search_web_manual function"""
    print("🧪 Testing Web Search Functionality...")
    print("=" * 60)
    
    try:
        from side_functions import search_web_manual
        
        # Test search queries
        test_queries = [
            "Find the address of Starbucks near 100 Main Street, Rockville, Maryland",
            "Find coffee shops near Washington DC"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Query: {query}")
            print("-" * 60)
            
            try:
                result = await search_web_manual(query)
                print(f"✅ Result: {result[:200]}...")
                
                if "timed out" in result.lower() or "unavailable" in result.lower() or "failed" in result.lower():
                    print(f"⚠️ Search returned error message")
                else:
                    print(f"✅ Search completed successfully!")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
            
            print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"❌ Failed to import or test: {e}")

if __name__ == "__main__":
    asyncio.run(test_search())
