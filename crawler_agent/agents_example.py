#!/usr/bin/env python3
"""
Example: Using Crawl4AI MCP server with OpenAI Agents SDK

This demonstrates how to wire the MCP server into an Agent and use it
for web scraping tasks.
"""

import asyncio
import os
from typing import Any

try:
    from agents import Agent, Runner
    from agents.mcp.server import MCPServerStdio
except ImportError:
    print("Error: openai-agents not installed. Install with: pip install openai-agents")
    exit(1)


async def main() -> None:
    """Run an agent that uses the Crawl4AI MCP server."""
    
    # Configure the MCP server to run our crawl4ai server
    async with MCPServerStdio(
        params={
            "command": "python",
            "args": ["-m", "crawler_agent.mcp_server"],
        },
        cache_tools_list=True,  # Cache tools for better performance
    ) as crawl4ai_server:
        
        # Create an agent with the MCP server
        agent = Agent(
            name="Web Research Assistant",
            instructions=(
                "You are a helpful research assistant that can scrape and crawl websites. "
                "Use the scrape tool for single pages and crawl for multi-page exploration. "
                "Always summarize the key information from the content you gather."
            ),
            mcp_servers=[crawl4ai_server],
            mcp_config={
                "convert_schemas_to_strict": True,  # Enable strict schema validation
            },
        )
        
        # Test with a research task
        task = os.environ.get(
            "RESEARCH_TASK", 
            "Research the Model Context Protocol documentation and summarize the key concepts"
        )
        
        print(f"🔍 Research task: {task}")
        print("🤖 Starting research...")
        
        result = await Runner.run(
            starting_agent=agent,
            input=task,
            max_turns=5,  # Allow multiple tool calls
        )
        
        print("\n📋 Research Results:")
        print("=" * 50)
        print(result.final_output)


if __name__ == "__main__":
    # Set OpenAI API key from environment
    if not os.environ.get("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not set. The agent may not work properly.")
    
    asyncio.run(main())
