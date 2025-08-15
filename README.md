# Crawler Agent

A Model Context Protocol (MCP) server that exposes [Crawl4AI](https://docs.crawl4ai.com/) functionality as tools for AI agents, similar to Firecrawl's scrape and crawl capabilities.

## Features

- **🔧 MCP Tools**: Exposes `scrape` and `crawl` tools via stdio MCP server
- **🌐 Web Scraping**: Single-page scraping with markdown extraction
- **🕷️ Web Crawling**: Multi-page breadth-first crawling with depth control
- **🧠 Adaptive Crawling**: Smart crawling that stops when sufficient content is gathered
- **🛡️ Safety**: Blocks internal networks, localhost, and private IPs
- **📱 Agent Ready**: Works with OpenAI Agents SDK, Cursor, and Claude Code
- **⚡ Fast**: Powered by Playwright and Crawl4AI's optimized extraction

## Quick Start

### 1. Installation

```bash
# Clone and setup
git clone <repo-url>
cd crawler_agent
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Install Playwright browsers
python -m playwright install chromium
```

### 2. Test the MCP Server

```bash
# Test basic functionality
python -m crawler_agent.smoke_client

# Test adaptive crawling
python test_adaptive.py
```

### 3. Use with OpenAI Agents SDK

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="your-key-here"

# Run the example agent
python -m crawler_agent.agents_example
```

## Tools Reference

The MCP server exposes 4 production-ready tools with content hiding features:

### `scrape`

Fetch a single URL and return markdown content.

**Arguments:**
- `url` (required): The URL to scrape
- `output_dir` (optional): If provided, persists content to disk and returns metadata only
- `crawler`: Optional Crawl4AI crawler config overrides  
- `browser`: Optional Crawl4AI browser config overrides
- `script`: Optional C4A-Script for page interaction
- `timeout_sec`: Request timeout (default: 45s, max: 600s)

**Returns (without output_dir):**
```json
{
  "url": "https://example.com",
  "markdown": "# Page Title\n\nContent...",
  "links": ["https://example.com/page1", "..."],
  "metadata": {}
}
```

**Returns (with output_dir):**
```json
{
  "run_id": "scrape_20250815_122811_4fb188",
  "file_path": "/path/to/output/pages/example.com_index.md",
  "manifest_path": "/path/to/output/manifest.json",
  "bytes_written": 230
}
```

### `crawl`

Multi-page breadth-first crawling with filtering and adaptive stopping.

**Arguments:**
- `seed_url` (required): Starting URL for the crawl
- `max_depth`: Maximum link depth to follow (default: 1, max: 4)
- `max_pages`: Maximum pages to crawl (default: 5, max: 100)
- `same_domain_only`: Stay within the same domain (default: true)
- `include_patterns`: Regex patterns URLs must match
- `exclude_patterns`: Regex patterns to exclude URLs
- `adaptive`: Enable adaptive crawling (default: false)
- `output_dir` (optional): If provided, persists content to disk and returns metadata only
- `crawler`, `browser`, `script`, `timeout_sec`: Same as scrape

**Returns (without output_dir):**
```json
{
  "start_url": "https://example.com",
  "pages": [
    {
      "url": "https://example.com/page1",
      "markdown": "Content...",
      "links": ["..."]
    }
  ],
  "total_pages": 3
}
```

**Returns (with output_dir):**
```json
{
  "run_id": "crawl_20250815_122828_464944",
  "pages_ok": 3,
  "pages_failed": 0,
  "manifest_path": "/path/to/output/manifest.json",
  "bytes_written": 690
}
```

### `crawl_site`

Comprehensive site crawling with persistence (always requires output_dir).

**Arguments:**
- `entry_url` (required): Starting URL for site crawl
- `output_dir` (required): Directory to persist results
- `max_depth`: Maximum crawl depth (default: 2, max: 6)
- `max_pages`: Maximum pages to crawl (default: 200, max: 5000)
- Additional config options for filtering and performance

**Returns:**
```json
{
  "run_id": "site_20250815_122851_0e2455",
  "output_dir": "/path/to/output",
  "manifest_path": "/path/to/output/manifest.json",
  "pages_ok": 15,
  "pages_failed": 2,
  "bytes_written": 45672
}
```

### `crawl_sitemap`

Sitemap-based crawling with persistence (always requires output_dir).

**Arguments:**
- `sitemap_url` (required): URL to sitemap.xml
- `output_dir` (required): Directory to persist results  
- `max_entries`: Maximum sitemap entries to process (default: 1000)
- Additional config options for filtering and performance

**Returns:**
```json
{
  "run_id": "sitemap_20250815_123006_667d71",
  "output_dir": "/path/to/output",
  "manifest_path": "/path/to/output/manifest.json", 
  "pages_ok": 25,
  "pages_failed": 0,
  "bytes_written": 123456
}
```

## Usage Examples

### Standalone MCP Server

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

params = StdioServerParameters(
    command="python",
    args=["-m", "crawler_agent.mcp_server"]
)

async with stdio_client(params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        
        # Scrape a single page
        result = await session.call_tool("scrape", {
            "url": "https://example.com"
        })
        
        # Crawl with adaptive stopping
        result = await session.call_tool("crawl", {
            "seed_url": "https://docs.example.com",
            "max_pages": 10,
            "adaptive": True
        })
```

### OpenAI Agents SDK Integration

```python
from agents import Agent, Runner
from agents.mcp.server import MCPServerStdio

async with MCPServerStdio(
    params={
        "command": "python", 
        "args": ["-m", "crawler_agent.mcp_server"]
    },
    cache_tools_list=True
) as server:
    
    agent = Agent(
        name="Research Assistant",
        instructions="Use scrape and crawl tools to research topics.",
        mcp_servers=[server],
        mcp_config={"convert_schemas_to_strict": True}
    )
    
    result = await Runner.run(
        agent, 
        "Research the latest AI safety papers"
    )
```

### Cursor/Claude Code Integration

This project supports both **Cursor** and **Claude Code** with synchronized configuration:

#### Cursor Setup
- Uses `.cursorrules` for AI assistant behavior and project guidance
- Automatic MCP tool detection and integration
- Project-specific rules and workflow guidance

#### Claude Code Setup  
- Uses `CLAUDE.md` for comprehensive project context and memory bank
- Native MCP integration via `mcp__crawl4ai-mcp__*` tool calls
- Global config: `~/.claude/claude_desktop_config.json` or project config: `.mcp.json`

#### Dual Environment Features
- **Synchronized Documentation**: Changes to documentation are maintained across both environments
- **Shared MCP Configuration**: Both use the same MCP server and tool schemas
- **Consistent Workflows**: Virtual environment protocols, testing commands, and development standards are identical
- **Cross-Compatible**: Projects work seamlessly whether using Cursor or Claude Code

## Configuration

### Environment Variables

- `TARGET_URL`: Default URL for smoke testing (default: https://modelcontextprotocol.io/docs)
- `RESEARCH_TASK`: Custom research task for agents example
- `OPENAI_API_KEY`: Required for OpenAI Agents SDK

### Safety Settings

The server blocks these URL patterns by default:
- `localhost`, `127.0.0.1`, `::1`
- Private IP ranges (RFC 1918)
- `file://` schemes
- `.local`, `.internal`, `.lan` domains

## Advanced Features

### Adaptive Crawling

When `adaptive: true` is set, the crawler uses a simple content-based stopping strategy:

- Stops when total content exceeds 5,000 characters
- Prevents over-crawling for information gathering tasks
- More sophisticated LLM-based strategies can be added

### Custom Filtering

Use regex patterns to control which URLs are crawled:

```python
await session.call_tool("crawl", {
    "seed_url": "https://docs.example.com",
    "include_patterns": [r"/docs/", r"/api/"],
    "exclude_patterns": [r"/old/", r"\.pdf$"]
})
```

### Browser Configuration

Pass custom browser/crawler settings:

```python
await session.call_tool("scrape", {
    "url": "https://example.com",
    "browser": {"headless": True, "viewport": {"width": 1280, "height": 720}},
    "crawler": {"verbose": True}
})
```

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   AI Agent      │───▶│   MCP Server     │───▶│   Crawl4AI      │
│ (Cursor/Agents) │    │ (stdio/stdio)    │    │ (Playwright)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  Safety Guards   │
                       │ (URL validation) │
                       └──────────────────┘
```

## Development

### Project Structure

```
crawler_agent/
├── __init__.py
├── mcp_server.py         # Main MCP server
├── safety.py            # URL safety validation
├── adaptive_strategy.py  # Adaptive crawling logic
├── smoke_client.py       # Basic testing client
└── agents_example.py     # OpenAI Agents SDK example
```

### Testing

```bash
# Test MCP server
python -m crawler_agent.smoke_client

# Test adaptive crawling
python test_adaptive.py

# Test with agents (requires OPENAI_API_KEY)
python -m crawler_agent.agents_example
```

### Contributing

1. **Environment Setup**: Always activate `.venv` before development work
2. **Documentation**: Follow the Documentation Memory Rule - synchronize changes across CLAUDE.md, .cursorrules, and README.md
3. **Code Style**: Follow `.cursorrules` for Cursor or `CLAUDE.md` for Claude Code
4. **Testing**: Use `python -m crawler_agent.smoke_client` for validation
5. **Safety**: Ensure security guards are maintained for all new features
6. **Dual Compatibility**: Verify changes work in both Cursor and Claude Code environments

## References

- [Crawl4AI Documentation](https://docs.crawl4ai.com/)
- [Model Context Protocol](https://modelcontextprotocol.io/introduction)
- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/mcp/)
- [MCP Tools Reference](https://openai.github.io/openai-agents-python/tools/)

## License

MIT License - see LICENSE file for details.
