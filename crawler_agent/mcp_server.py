from __future__ import annotations

import asyncio
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field, HttpUrl

from mcp import types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler

from .safety import require_public_http_url
from .adaptive_strategy import should_continue_crawling


server = Server("crawl4ai-mcp")


class ScrapeArgs(BaseModel):
    url: HttpUrl
    crawler: Dict[str, Any] = Field(default_factory=dict, description="Crawl4AI crawler config overrides")
    browser: Dict[str, Any] = Field(default_factory=dict, description="Crawl4AI browser config overrides")
    script: Optional[str] = Field(default=None, description="Optional C4A-Script")
    timeout_sec: Optional[int] = Field(default=45, ge=1, le=600)


class ScrapeResult(BaseModel):
    url: HttpUrl
    markdown: str
    links: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CrawlArgs(BaseModel):
    seed_url: HttpUrl
    max_depth: int = Field(default=1, ge=1, le=4)
    max_pages: int = Field(default=5, ge=1, le=100)
    same_domain_only: bool = True
    include_patterns: List[str] = Field(default_factory=list)
    exclude_patterns: List[str] = Field(default_factory=list)
    adaptive: bool = Field(default=False, description="Enable adaptive crawling to stop when sufficient info is gathered")
    crawler: Dict[str, Any] = Field(default_factory=dict)
    browser: Dict[str, Any] = Field(default_factory=dict)
    script: Optional[str] = None
    timeout_sec: Optional[int] = Field(default=60, ge=1, le=900)


class CrawlPage(BaseModel):
    url: HttpUrl
    markdown: str
    links: List[str] = Field(default_factory=list)


class CrawlResult(BaseModel):
    start_url: HttpUrl
    pages: List[CrawlPage]
    total_pages: int


@server.list_tools()
async def list_tools() -> List[types.Tool]:
    return [
        types.Tool(
            name="scrape",
            description=(
                "Fetch a single URL with Crawl4AI and return markdown + links. "
                "Use for a specific page."
            ),
            inputSchema=ScrapeArgs.model_json_schema(),
        ),
        types.Tool(
            name="crawl",
            description=(
                "Breadth-first crawl up to max_depth starting from seed_url, returning markdown per page. "
                "Respects same_domain_only and allows include/exclude regex patterns."
            ),
            inputSchema=CrawlArgs.model_json_schema(),
        ),
    ]


async def _run_scrape(args: ScrapeArgs) -> ScrapeResult:
    require_public_http_url(str(args.url))
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url=str(args.url),
            script=args.script,
            # If you need to map dicts to config objects later, do so here.
            # crawler_config=CrawlerRunConfig(**args.crawler) if args.crawler else None,
            # browser_config=BrowserConfig(**args.browser) if args.browser else None,
        )
    links = []
    raw_links = getattr(result, "links", []) or []
    for link in raw_links:
        if isinstance(link, str):
            links.append(link)
        else:
            href = link.get("href") or link.get("url")
            if isinstance(href, str):
                links.append(href)
    return ScrapeResult(url=str(args.url), markdown=result.markdown or "", links=links, metadata={})


def _compile_patterns(patterns: List[str]) -> List[re.Pattern[str]]:
    compiled: List[re.Pattern[str]] = []
    for p in patterns:
        try:
            compiled.append(re.compile(p))
        except re.error:
            # Ignore invalid patterns
            continue
    return compiled


def _url_allowed(url: str, seed_host: str, same_domain_only: bool, include: List[re.Pattern[str]], exclude: List[re.Pattern[str]]) -> bool:
    try:
        require_public_http_url(url)
    except ValueError:
        return False

    parsed = urlparse(url)
    if same_domain_only and parsed.hostname and parsed.hostname != seed_host:
        return False
    text = url
    if include and not any(p.search(text) for p in include):
        return False
    if any(p.search(text) for p in exclude):
        return False
    return True


async def _run_crawl(args: CrawlArgs) -> CrawlResult:
    require_public_http_url(str(args.seed_url))
    seed_host = urlparse(str(args.seed_url)).hostname or ""
    include = _compile_patterns(args.include_patterns)
    exclude = _compile_patterns(args.exclude_patterns)

    visited: Set[str] = set()
    frontier: List[tuple[str, int]] = [(str(args.seed_url), 0)]
    pages: List[CrawlPage] = []

    async with AsyncWebCrawler() as crawler:
        while frontier and len(pages) < args.max_pages:
            url, depth = frontier.pop(0)
            if url in visited:
                continue
            visited.add(url)

            # Scrape current URL
            result = await crawler.arun(url=url, script=args.script)
            page_links: List[str] = []
            raw_links = getattr(result, "links", []) or []
            for link in raw_links:
                if isinstance(link, str):
                    candidate = link
                else:
                    candidate = link.get("href") or link.get("url")
                if isinstance(candidate, str):
                    page_links.append(candidate)

            pages.append(CrawlPage(url=url, markdown=result.markdown or "", links=page_links))
            
            # Adaptive crawling: check if we should continue
            if args.adaptive:
                page_contents = [page.markdown for page in pages]
                if not should_continue_crawling(page_contents, args.max_pages):
                    break
            
            if depth + 1 <= args.max_depth:
                for href in page_links:
                    if len(pages) >= args.max_pages:
                        break
                    if _url_allowed(href, seed_host, args.same_domain_only, include, exclude):
                        if href not in visited and all(href != u for u, _ in frontier):
                            frontier.append((href, depth + 1))

    return CrawlResult(start_url=str(args.seed_url), pages=pages, total_pages=len(pages))


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> Any:
    if name == "scrape":
        parsed = ScrapeArgs.model_validate(arguments)
        result = await _run_scrape(parsed)
        return json.loads(result.model_dump_json())
    elif name == "crawl":
        parsed = CrawlArgs.model_validate(arguments)
        result = await _run_crawl(parsed)
        return json.loads(result.model_dump_json())
    else:
        raise ValueError(f"Unknown tool: {name}")


async def _run_stdio_server() -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="crawl4ai-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(notification_options=NotificationOptions(), experimental_capabilities={}),
            ),
        )


def main() -> None:
    # Currently only stdio mode is supported for simplicity
    asyncio.run(_run_stdio_server())


if __name__ == "__main__":
    main()
