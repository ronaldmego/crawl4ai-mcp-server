from __future__ import annotations

import asyncio
import os
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

TARGET_URL = os.environ.get("TARGET_URL", "https://modelcontextprotocol.io/docs")


async def run() -> None:
    params = StdioServerParameters(
        command="python",
        args=["-m", "crawler_agent.mcp_server"],
        env=os.environ.copy(),
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f"Available tools: {tool_names}")
            assert "scrape" in tool_names, "scrape tool not found"

            result = await session.call_tool("scrape", {"url": TARGET_URL})
            # result.content typically contains JSON or text blocks; for simplicity, print it raw
            print("scrape result:", result)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
