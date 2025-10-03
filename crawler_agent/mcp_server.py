from __future__ import annotations

import asyncio
import json
import re
import time
import os
import sys
import logging
import io
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field, HttpUrl

from mcp import types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

from urllib.parse import urlparse, urljoin

from crawl4ai import AsyncWebCrawler

from .safety import require_public_http_url
from .adaptive_strategy import should_continue_crawling
from .persistence import (
    Manifest,
    PageRecord,
    append_jsonl,
    append_links_csv,
    ensure_run_dir,
    generate_run_id,
    persist_page_markdown,
    update_totals,
    write_manifest,
    append_log_jsonl,
)
from .sitemap_utils import discover_sitemaps, parse_sitemap_xml, filter_urls, fetch_text

# Configure stderr logging (stdout is reserved for MCP stdio messages)
_LOG_LEVEL = os.getenv("CRAWL4AI_MCP_LOG", "INFO").upper()
logger = logging.getLogger("crawl4ai_mcp")
if not logger.handlers:
    _h = logging.StreamHandler(sys.stderr)
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    logger.addHandler(_h)
logger.setLevel(_LOG_LEVEL)
logger.propagate = False


# Supresor de output de Crawl4AI para evitar warnings en MCP stdio
class SuppressCrawl4AIOutput:
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = io.StringIO()
        return self
    
    def __exit__(self, *args):
        sys.stdout = self._stdout


server = Server("crawl4ai-mcp")


class ScrapeArgs(BaseModel):
    url: HttpUrl
    crawler: Dict[str, Any] = Field(default_factory=dict, description="Crawl4AI crawler config overrides")
    browser: Dict[str, Any] = Field(default_factory=dict, description="Crawl4AI browser config overrides")
    script: Optional[str] = Field(default=None, description="Optional C4A-Script")
    timeout_sec: Optional[int] = Field(default=45, ge=1, le=600)
    output_dir: Optional[str] = Field(default=None, description="If provided, persist to disk and return metadata only")


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
    output_dir: Optional[str] = Field(default=None, description="If provided, persist to disk and return metadata only")


class CrawlPage(BaseModel):
    url: HttpUrl
    markdown: str
    links: List[str] = Field(default_factory=list)


class CrawlResult(BaseModel):
    start_url: HttpUrl
    pages: List[CrawlPage]
    total_pages: int


class CrawlSiteArgs(BaseModel):
    entry_url: HttpUrl
    output_dir: str
    max_depth: int = Field(ge=1, le=6, default=2)
    max_pages: int = Field(ge=1, le=5000, default=200)
    same_domain_only: bool = True
    include_patterns: List[str] = Field(default_factory=list)
    exclude_patterns: List[str] = Field(default_factory=list)
    formats: List[str] = Field(default_factory=lambda: ["md", "jsonl"])  # md,jsonl,links_csv
    adaptive: bool = False
    respect_robots: str = Field(default="enforce")  # enforce|warn|ignore (placeholder)
    politeness_delay_ms: int = 500
    max_concurrency: int = 2
    timeout_sec: int = 600


class CrawlSitemapArgs(BaseModel):
    sitemap_url: HttpUrl
    output_dir: str
    max_entries: int = 1000
    include_patterns: List[str] = Field(default_factory=list)
    exclude_patterns: List[str] = Field(default_factory=list)
    formats: List[str] = Field(default_factory=lambda: ["md", "jsonl"])  # md,jsonl,links_csv
    politeness_delay_ms: int = 500
    max_concurrency: int = 2
    timeout_sec: int = 900


class ScrapePersistResult(BaseModel):
    run_id: str
    output_dir: str
    manifest_path: str
    file_path: str
    bytes_written: int
    started_at: str
    finished_at: str


class CrawlPersistResult(BaseModel):
    run_id: str
    output_dir: str
    manifest_path: str
    pages_ok: int
    pages_failed: int
    bytes_written: int
    started_at: str
    finished_at: str | None


@server.list_tools()
async def list_tools() -> List[types.Tool]:
    logger.debug("list_tools called")
    return [
        types.Tool(
            name="scrape",
            description=(
                "Fetch a single URL with Crawl4AI. Returns markdown + links by default. "
                "If output_dir provided, persists to disk and returns metadata only (avoids context bloat)."
            ),
            inputSchema=ScrapeArgs.model_json_schema(),
        ),
        types.Tool(
            name="crawl",
            description=(
                "Breadth-first crawl up to max_depth starting from seed_url. Returns markdown per page by default. "
                "If output_dir provided, persists to disk and returns metadata only (avoids context bloat). "
                "Respects same_domain_only and allows include/exclude regex patterns."
            ),
            inputSchema=CrawlArgs.model_json_schema(),
        ),
        types.Tool(
            name="crawl_site",
            description=(
                "Site crawler that persists results to disk. Returns manifest path and output directory. "
                "Does not return page content to avoid context bloat."
            ),
            inputSchema=CrawlSiteArgs.model_json_schema(),
        ),
        types.Tool(
            name="crawl_sitemap",
            description=(
                "Crawl URLs discovered from sitemap.xml/robots.txt. Persists results to disk and returns manifest path."
            ),
            inputSchema=CrawlSitemapArgs.model_json_schema(),
        ),
    ]


async def _run_scrape(args: ScrapeArgs) -> ScrapeResult:
    require_public_http_url(str(args.url))
    async with AsyncWebCrawler() as crawler:
        with SuppressCrawl4AIOutput():
            result = await crawler.arun(
                url=str(args.url),
                script=args.script,
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


async def _persist_scrape(args: ScrapeArgs) -> ScrapePersistResult:
    require_public_http_url(str(args.url))
    run_id = generate_run_id("scrape")
    logger.info("persist_scrape start run_id=%s url=%s", run_id, str(args.url))
    
    run_dir = ensure_run_dir(args.output_dir, run_id)
    started_at = datetime.now(timezone.utc)
    
    # Create manifest
    manifest = Manifest(
        run_id=run_id,
        entry=str(args.url),
        mode="scrape",
        started_at=started_at.isoformat(),
        config=args.model_dump(),
    )
    write_manifest(run_dir, manifest)
    
    # Scrape the content
    async with AsyncWebCrawler() as crawler:
        with SuppressCrawl4AIOutput():
            result = await crawler.arun(
                url=str(args.url),
                script=args.script,
            )
    
    # Process links
    links = []
    raw_links = getattr(result, "links", []) or []
    for link in raw_links:
        if isinstance(link, str):
            links.append(link)
        else:
            href = link.get("href") or link.get("url")
            if isinstance(href, str):
                links.append(href)
    
    # Persist to disk
    markdown = result.markdown or ""
    file_path, content_bytes = persist_page_markdown(run_dir, str(args.url), markdown)
    page_record = PageRecord(
        url=str(args.url),
        status="ok",
        error=None,
        duration_ms=0,  # We don't track this for single scrape
        path=file_path,
        content_bytes=content_bytes
    )
    
    # Update manifest
    manifest.pages = [page_record]
    manifest.finished_at = datetime.now(timezone.utc).isoformat()
    manifest.totals = {"pages_ok": 1, "pages_failed": 0, "bytes_written": page_record.content_bytes}
    write_manifest(run_dir, manifest)
    
    # Log and save links if any
    if links:
        append_links_csv(run_dir, str(args.url), links)
    
    logger.info("persist_scrape done run_id=%s file=%s bytes=%d", run_id, Path(file_path).name, page_record.content_bytes)
    
    return ScrapePersistResult(
        run_id=run_id,
        output_dir=str(run_dir),
        manifest_path=str(run_dir / "manifest.json"),
        file_path=str(file_path),
        bytes_written=page_record.content_bytes,
        started_at=started_at.isoformat(),
        finished_at=manifest.finished_at
    )


def _compile_patterns(patterns: List[str]) -> List[re.Pattern[str]]:
    compiled: List[re.Pattern[str]] = []
    for p in patterns:
        try:
            compiled.append(re.compile(p))
        except re.error:
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


def _extract_links_from_result(base_url: str, result: Any) -> List[str]:
    links: List[str] = []
    raw_links = getattr(result, "links", []) or []
    for link in raw_links:
        if isinstance(link, str):
            candidate = link
        else:
            candidate = link.get("href") or link.get("url")
        if isinstance(candidate, str):
            links.append(candidate)
    # Also extract absolute URLs from markdown content
    md = getattr(result, "markdown", "") or ""
    if md:
        for match in re.findall(r"https?://[^\s)\]]+", md):
            links.append(match)
    # Normalize and de-duplicate
    dedup: List[str] = []
    seen: Set[str] = set()
    for u in links:
        # Resolve relative links if any
        abs_u = urljoin(base_url, u)
        if abs_u not in seen:
            seen.add(abs_u)
            dedup.append(abs_u)
    return dedup


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

            with SuppressCrawl4AIOutput():
                result = await crawler.arun(url=url, script=args.script)
            page_links: List[str] = _extract_links_from_result(url, result)

            pages.append(CrawlPage(url=url, markdown=result.markdown or "", links=page_links))

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


async def _persist_crawl(args: CrawlArgs) -> CrawlPersistResult:
    require_public_http_url(str(args.seed_url))
    run_id = generate_run_id("crawl")
    logger.info("persist_crawl start run_id=%s seed=%s depth=%d pages=%d", run_id, str(args.seed_url), args.max_depth, args.max_pages)
    
    run_dir = ensure_run_dir(args.output_dir, run_id)
    started_at = datetime.now(timezone.utc)
    
    # Create manifest
    manifest = Manifest(
        run_id=run_id,
        entry=str(args.seed_url),
        mode="crawl",
        started_at=started_at.isoformat(),
        config=args.model_dump(),
    )
    write_manifest(run_dir, manifest)
    
    # Crawl logic (same as _run_crawl but with persistence)
    seed_host = urlparse(str(args.seed_url)).hostname or ""
    include = _compile_patterns(args.include_patterns)
    exclude = _compile_patterns(args.exclude_patterns)
    
    visited: Set[str] = set()
    frontier: List[tuple[str, int]] = [(str(args.seed_url), 0)]
    pages_ok = 0
    pages_failed = 0
    total_bytes = 0
    
    async with AsyncWebCrawler() as crawler:
        while frontier and len(visited) < args.max_pages:
            url, depth = frontier.pop(0)
            if url in visited or depth > args.max_depth:
                continue
            visited.add(url)
            
            try:
                logger.debug("crawling url=%s depth=%d", url, depth)
                with SuppressCrawl4AIOutput():
                    result = await crawler.arun(url=url, script=args.script)
                markdown = result.markdown or ""
                
                # Persist page
                file_path, content_bytes = persist_page_markdown(run_dir, url, markdown)
                page_record = PageRecord(
                    url=url,
                    status="ok",
                    error=None,
                    duration_ms=0,  # We don't track timing in this simplified version
                    path=file_path,
                    content_bytes=content_bytes
                )
                total_bytes += page_record.content_bytes
                
                # Save to manifest
                append_jsonl(run_dir, page_record.model_dump())
                pages_ok += 1
                
                # Extract and save links
                links = _extract_links_from_result(url, result)
                if links:
                    append_links_csv(run_dir, url, links)
                
                logger.info("crawled url=%s depth=%d bytes=%d", url, depth, page_record.content_bytes)
                
                # Add new URLs to frontier if not at max depth
                if depth < args.max_depth:
                    for href in links:
                        if args.adaptive and should_continue_crawling(len(visited), args.max_pages):
                            break
                        if _url_allowed(href, seed_host, args.same_domain_only, include, exclude):
                            if href not in visited and all(href != u for u, _ in frontier):
                                frontier.append((href, depth + 1))
                                
            except Exception as e:
                logger.warning("failed to crawl url=%s: %s", url, str(e))
                page_record = PageRecord(
                    url=url,
                    status="failed",
                    error=str(e),
                    duration_ms=0,
                    path=None,
                    content_bytes=None
                )
                append_jsonl(run_dir, page_record.model_dump())
                pages_failed += 1
    
    # Update manifest with final results
    manifest.finished_at = datetime.now(timezone.utc).isoformat()
    manifest.totals = {"pages_ok": pages_ok, "pages_failed": pages_failed, "bytes_written": total_bytes}
    write_manifest(run_dir, manifest)
    
    logger.info("persist_crawl done run_id=%s pages_ok=%d pages_failed=%d bytes=%d", run_id, pages_ok, pages_failed, total_bytes)
    
    return CrawlPersistResult(
        run_id=run_id,
        output_dir=str(run_dir),
        manifest_path=str(run_dir / "manifest.json"),
        pages_ok=pages_ok,
        pages_failed=pages_failed,
        bytes_written=total_bytes,
        started_at=started_at.isoformat(),
        finished_at=manifest.finished_at
    )


async def _persist_crawl_site(args: CrawlSiteArgs) -> CrawlPersistResult:
    require_public_http_url(str(args.entry_url))
    run_id = generate_run_id("site")
    logger.info("crawl_site start run_id=%s entry=%s depth=%d pages=%d", run_id, str(args.entry_url), args.max_depth, args.max_pages)
    run_dir = ensure_run_dir(args.output_dir, run_id)

    manifest = Manifest(
        run_id=run_id,
        entry=str(args.entry_url),
        mode="site",
        started_at=datetime.now(timezone.utc).isoformat(),
        config=args.model_dump(),
    )
    write_manifest(run_dir, manifest)

    include = _compile_patterns(args.include_patterns)
    exclude = _compile_patterns(args.exclude_patterns)
    seed_host = urlparse(str(args.entry_url)).hostname or ""

    visited: Set[str] = set()
    frontier: List[tuple[str, int]] = [(str(args.entry_url), 0)]

    async with AsyncWebCrawler() as crawler:
        while frontier and manifest.totals.get("pages_ok", 0) < args.max_pages:
            url, depth = frontier.pop(0)
            if url in visited:
                continue
            visited.add(url)

            t0 = time.perf_counter()
            try:
                append_log_jsonl(run_dir, {"event": "fetch_start", "url": url, "depth": depth, "ts": time.time()})
                with SuppressCrawl4AIOutput():
                    result = await crawler.arun(url=url)
                links: List[str] = _extract_links_from_result(url, result)

                path, nbytes = persist_page_markdown(run_dir, url, result.markdown or "")
                append_jsonl(run_dir, {"url": url, "markdown_path": path, "bytes": nbytes})
                if "links_csv" in args.formats and links:
                    append_links_csv(run_dir, url, links)

                rec = PageRecord(
                    url=url,
                    status="ok",
                    path=path,
                    content_bytes=nbytes,
                    duration_ms=int((time.perf_counter() - t0) * 1000),
                )
                manifest.pages.append(rec)
                update_totals(manifest, rec)
                append_log_jsonl(run_dir, {"event": "fetch_ok", "url": url, "bytes": nbytes, "links": len(links), "ts": time.time()})

                if depth + 1 <= args.max_depth:
                    for href in links:
                        if manifest.totals.get("pages_ok", 0) >= args.max_pages:
                            break
                        if _url_allowed(href, seed_host, args.same_domain_only, include, exclude):
                            if href not in visited and all(href != u for u, _ in frontier):
                                frontier.append((href, depth + 1))

            except Exception as e:
                rec = PageRecord(
                    url=url,
                    status="error",
                    path=None,
                    content_bytes=None,
                    error=str(e),
                    duration_ms=int((time.perf_counter() - t0) * 1000),
                )
                manifest.pages.append(rec)
                update_totals(manifest, rec)
                append_log_jsonl(run_dir, {"event": "fetch_error", "url": url, "error": str(e), "ts": time.time()})

            write_manifest(run_dir, manifest)
            await asyncio.sleep(args.politeness_delay_ms / 1000.0)

    manifest.finished_at = datetime.now(timezone.utc).isoformat()
    manifest_path = write_manifest(run_dir, manifest)

    logger.info(
        "crawl_site done run_id=%s ok=%d failed=%d bytes=%d dir=%s",
        run_id,
        manifest.totals.get("pages_ok", 0),
        manifest.totals.get("pages_failed", 0),
        manifest.totals.get("bytes_written", 0),
        str(run_dir),
    )

    return CrawlPersistResult(
        run_id=run_id,
        output_dir=str(run_dir),
        manifest_path=manifest_path,
        pages_ok=manifest.totals.get("pages_ok", 0),
        pages_failed=manifest.totals.get("pages_failed", 0),
        bytes_written=manifest.totals.get("bytes_written", 0),
        started_at=manifest.started_at,
        finished_at=manifest.finished_at,
    )


async def _persist_crawl_sitemap(args: CrawlSitemapArgs) -> CrawlPersistResult:
    run_id = generate_run_id("sitemap")
    logger.info("crawl_sitemap start run_id=%s sitemap=%s max_entries=%d", run_id, str(args.sitemap_url), args.max_entries)
    run_dir = ensure_run_dir(args.output_dir, run_id)

    manifest = Manifest(
        run_id=run_id,
        entry=str(args.sitemap_url),
        mode="sitemap",
        started_at=datetime.now(timezone.utc).isoformat(),
        config=args.model_dump(),
    )
    write_manifest(run_dir, manifest)

    # Fetch and parse sitemap(s)
    sitemap_text = await fetch_text(str(args.sitemap_url))
    seeds: List[str] = []
    if sitemap_text:
        seeds = parse_sitemap_xml(sitemap_text)
    seeds = seeds[: args.max_entries]
    seeds = filter_urls(seeds, args.include_patterns, args.exclude_patterns)

    async with AsyncWebCrawler() as crawler:
        for url in seeds:
            if manifest.totals.get("pages_ok", 0) >= args.max_entries:
                break
            t0 = time.perf_counter()
            try:
                append_log_jsonl(run_dir, {"event": "fetch_start", "url": url, "ts": time.time()})
                with SuppressCrawl4AIOutput():
                    result = await crawler.arun(url=url)
                links: List[str] = _extract_links_from_result(url, result)

                path, nbytes = persist_page_markdown(run_dir, url, result.markdown or "")
                append_jsonl(run_dir, {"url": url, "markdown_path": path, "bytes": nbytes})
                if "links_csv" in args.formats and links:
                    append_links_csv(run_dir, url, links)

                rec = PageRecord(
                    url=url,
                    status="ok",
                    path=path,
                    content_bytes=nbytes,
                    duration_ms=int((time.perf_counter() - t0) * 1000),
                )
                manifest.pages.append(rec)
                update_totals(manifest, rec)
                append_log_jsonl(run_dir, {"event": "fetch_ok", "url": url, "bytes": nbytes, "links": len(links), "ts": time.time()})

            except Exception as e:
                rec = PageRecord(
                    url=url,
                    status="error",
                    path=None,
                    content_bytes=None,
                    error=str(e),
                    duration_ms=int((time.perf_counter() - t0) * 1000),
                )
                manifest.pages.append(rec)
                update_totals(manifest, rec)
                append_log_jsonl(run_dir, {"event": "fetch_error", "url": url, "error": str(e), "ts": time.time()})

            write_manifest(run_dir, manifest)
            await asyncio.sleep(args.politeness_delay_ms / 1000.0)

    manifest.finished_at = datetime.now(timezone.utc).isoformat()
    manifest_path = write_manifest(run_dir, manifest)

    logger.info(
        "crawl_sitemap done run_id=%s ok=%d failed=%d bytes=%d dir=%s",
        run_id,
        manifest.totals.get("pages_ok", 0),
        manifest.totals.get("pages_failed", 0),
        manifest.totals.get("bytes_written", 0),
        str(run_dir),
    )

    return CrawlPersistResult(
        run_id=run_id,
        output_dir=str(run_dir),
        manifest_path=manifest_path,
        pages_ok=manifest.totals.get("pages_ok", 0),
        pages_failed=manifest.totals.get("pages_failed", 0),
        bytes_written=manifest.totals.get("bytes_written", 0),
        started_at=manifest.started_at,
        finished_at=manifest.finished_at,
    )


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> Any:
    logger.info("call_tool name=%s", name)
    if name == "scrape":
        parsed = ScrapeArgs.model_validate(arguments)
        if parsed.output_dir:
            result = await _persist_scrape(parsed)
            logger.info("scrape persist done url=%s bytes=%d", str(parsed.url), result.bytes_written)
        else:
            result = await _run_scrape(parsed)
            logger.info("scrape done url=%s chars=%d links=%d", str(parsed.url), len(result.markdown or ""), len(result.links))
        return json.loads(result.model_dump_json())
    elif name == "crawl":
        parsed = CrawlArgs.model_validate(arguments)
        if parsed.output_dir:
            result = await _persist_crawl(parsed)
            logger.info("crawl persist done start=%s pages_ok=%d", str(parsed.seed_url), result.pages_ok)
        else:
            result = await _run_crawl(parsed)
            logger.info("crawl done start=%s pages=%d", str(parsed.seed_url), result.total_pages)
        return json.loads(result.model_dump_json())
    elif name == "crawl_site":
        parsed = CrawlSiteArgs.model_validate(arguments)
        result = await _persist_crawl_site(parsed)
        return json.loads(result.model_dump_json())
    elif name == "crawl_sitemap":
        parsed = CrawlSitemapArgs.model_validate(arguments)
        result = await _persist_crawl_sitemap(parsed)
        return json.loads(result.model_dump_json())
    else:
        logger.error("unknown tool name=%s", name)
        raise ValueError(f"Unknown tool: {name}")


async def _run_stdio_server() -> None:
    logger.info("server starting (stdio)")
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
    logger.info("server stopped")


def main() -> None:
    asyncio.run(_run_stdio_server())


if __name__ == "__main__":
    main()
