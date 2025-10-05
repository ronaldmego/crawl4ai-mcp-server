# Product Overview

## Crawl4AI MCP Server

A lightweight Model Context Protocol (MCP) server that exposes Crawl4AI web scraping and crawling capabilities as tools for AI agents. This is a self-hosted, free alternative to Firecrawl's API.

### Core Purpose
- Integrate web scraping into AI workflows via MCP protocol
- Support OpenAI Agents SDK, Cursor, Claude Code, and other MCP-compatible tools
- Provide safe, controlled web crawling with security guards

### Key Features
- **4 MCP Tools**: `scrape`, `crawl`, `crawl_site`, `crawl_sitemap`
- **Content Management**: Optional disk persistence to avoid context bloat
- **Adaptive Crawling**: Smart stopping when sufficient content is gathered
- **Safety First**: Blocks internal networks, localhost, and private IPs
- **Docker Ready**: Containerized deployment for consistent environments

### Target Users
- AI developers building agents that need web data
- Teams wanting self-hosted web scraping capabilities
- Projects requiring MCP-compatible web crawling tools