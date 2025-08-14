#!/usr/bin/env python3
"""
Test script for adaptive crawling functionality.
"""

import asyncio
import json
from crawler_agent.mcp_server import _run_crawl, CrawlArgs


async def test_adaptive_crawling():
    """Test adaptive crawling against the MCP docs site."""
    
    print("🧪 Testing adaptive crawling...")
    
    # Test without adaptive crawling
    print("\n1. Regular crawl (max 3 pages):")
    args_regular = CrawlArgs(
        seed_url="https://modelcontextprotocol.io/docs",
        max_pages=3,
        max_depth=2,
        adaptive=False
    )
    
    result_regular = await _run_crawl(args_regular)
    print(f"   Pages crawled: {result_regular.total_pages}")
    total_chars_regular = sum(len(page.markdown) for page in result_regular.pages)
    print(f"   Total content: {total_chars_regular:,} characters")
    
    # Test with adaptive crawling
    print("\n2. Adaptive crawl (max 3 pages, stops early if enough content):")
    args_adaptive = CrawlArgs(
        seed_url="https://modelcontextprotocol.io/docs",
        max_pages=3,
        max_depth=2,
        adaptive=True
    )
    
    result_adaptive = await _run_crawl(args_adaptive)
    print(f"   Pages crawled: {result_adaptive.total_pages}")
    total_chars_adaptive = sum(len(page.markdown) for page in result_adaptive.pages)
    print(f"   Total content: {total_chars_adaptive:,} characters")
    
    if result_adaptive.total_pages < result_regular.total_pages:
        print("   ✅ Adaptive crawling stopped early!")
    else:
        print("   ℹ️  Adaptive crawling didn't stop early (content threshold not reached)")
    
    print("\n3. Sample URLs crawled:")
    for i, page in enumerate(result_adaptive.pages):
        print(f"   {i+1}. {page.url}")


if __name__ == "__main__":
    asyncio.run(test_adaptive_crawling())
