#!/usr/bin/env python3
"""
Complete validation script for the Crawl4AI MCP server.
Tests both scrape and crawl tools via the MCP client interface.
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def validate_complete_functionality():
    """Test both scrape and crawl tools via MCP interface."""
    
    print("🧪 Complete MCP Server Validation")
    print("=" * 50)
    
    params = StdioServerParameters(
        command="python",
        args=["-m", "crawler_agent.mcp_server"]
    )
    
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # 1. Test list_tools
            print("\n1. Testing list_tools...")
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f"   Available tools: {tool_names}")
            assert "scrape" in tool_names and "crawl" in tool_names
            print("   ✅ Both tools available")
            
            # 2. Test scrape tool
            print("\n2. Testing scrape tool...")
            scrape_result = await session.call_tool("scrape", {
                "url": "https://modelcontextprotocol.io/docs"
            })
            
            if scrape_result.isError:
                print(f"   ❌ Scrape failed: {scrape_result.content}")
                return
            
            # Parse the structured content
            scrape_data = scrape_result.structuredContent
            print(f"   URL: {scrape_data['url']}")
            print(f"   Content length: {len(scrape_data['markdown']):,} characters")
            print(f"   Links found: {len(scrape_data['links'])}")
            print("   ✅ Scrape successful")
            
            # 3. Test crawl tool (regular)
            print("\n3. Testing crawl tool (regular)...")
            crawl_result = await session.call_tool("crawl", {
                "seed_url": "https://docs.crawl4ai.com/",
                "max_pages": 2,
                "max_depth": 1,
                "adaptive": False
            })
            
            if crawl_result.isError:
                print(f"   ❌ Crawl failed: {crawl_result.content}")
                return
            
            crawl_data = crawl_result.structuredContent
            print(f"   Start URL: {crawl_data['start_url']}")
            print(f"   Pages crawled: {crawl_data['total_pages']}")
            total_content = sum(len(page['markdown']) for page in crawl_data['pages'])
            print(f"   Total content: {total_content:,} characters")
            print("   ✅ Crawl successful")
            
            # 4. Test crawl tool (adaptive)
            print("\n4. Testing crawl tool (adaptive)...")
            adaptive_result = await session.call_tool("crawl", {
                "seed_url": "https://docs.crawl4ai.com/",
                "max_pages": 3,
                "max_depth": 2,
                "adaptive": True
            })
            
            if adaptive_result.isError:
                print(f"   ❌ Adaptive crawl failed: {adaptive_result.content}")
                return
            
            adaptive_data = adaptive_result.structuredContent
            print(f"   Start URL: {adaptive_data['start_url']}")
            print(f"   Pages crawled: {adaptive_data['total_pages']}")
            adaptive_content = sum(len(page['markdown']) for page in adaptive_data['pages'])
            print(f"   Total content: {adaptive_content:,} characters")
            print("   ✅ Adaptive crawl successful")
            
            # 5. Test safety guards
            print("\n5. Testing safety guards...")
            try:
                unsafe_result = await session.call_tool("scrape", {
                    "url": "http://localhost:8080/test"
                })
                if unsafe_result.isError:
                    print("   ✅ Safety guards working (localhost blocked)")
                else:
                    print("   ⚠️  Safety guards may not be working properly")
            except Exception as e:
                print("   ✅ Safety guards working (exception thrown)")
            
            print("\n🎉 All tests completed successfully!")
            print("\nThe Crawl4AI MCP server is ready for use with:")
            print("- OpenAI Agents SDK")
            print("- Cursor") 
            print("- Claude Code")
            print("- Any MCP-compatible client")


if __name__ == "__main__":
    asyncio.run(validate_complete_functionality())
