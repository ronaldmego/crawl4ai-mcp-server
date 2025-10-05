# Project Structure

## Root Directory Layout
```
├── crawler_agent/           # Main Python package
├── crawls/                  # Output directory for crawl results
├── venv/                    # Virtual environment (local development)
├── .kiro/                   # Kiro IDE configuration and steering
├── .git/                    # Git repository
├── requirements.txt         # Python dependencies
├── docker-compose.yml       # Docker services configuration
├── Dockerfile              # Multi-stage container build
├── .mcp.json               # MCP server configuration
└── README.md               # Project documentation
```

## Core Package (`crawler_agent/`)
```
crawler_agent/
├── __init__.py             # Package initialization
├── mcp_server.py           # Main MCP server implementation (518 lines)
├── safety.py               # URL validation and security guards
├── adaptive_strategy.py    # Adaptive crawling logic
├── persistence.py          # File I/O and data persistence
├── sitemap_utils.py        # Sitemap parsing utilities
├── smoke_client.py         # Basic testing client
├── agents_example.py       # OpenAI Agents SDK integration example
└── __pycache__/           # Python bytecode cache
```

## Configuration Files

### MCP Configuration (`.mcp.json`)
- Project-scoped MCP server configuration
- Docker-based server setup with volume mounts
- Environment variable configuration

### Docker Configuration
- `Dockerfile`: Multi-stage build with Playwright browsers
- `docker-compose.yml`: Services for production, development, and testing
- `docker-run.sh`: Helper script for Docker operations

### Development Configuration
- `.cursorrules`: Cursor IDE project rules and conventions
- `.gitignore`: Standard Python gitignore with project-specific additions
- `CLAUDE.md`: Claude Code environment documentation (if present)

## Output Structure (`crawls/`)
When tools use `output_dir` parameter, results are persisted with this structure:
```
crawls/
└── {run_id}/
    ├── manifest.json       # Run metadata and results summary
    ├── pages/             # Individual page content (markdown)
    ├── data.jsonl         # Structured page records
    ├── links.csv          # Extracted links (optional)
    └── log.jsonl          # Crawl operation logs
```

## Architecture Patterns

### MCP Server Pattern
- Single server instance in `mcp_server.py`
- Tool registration via decorators (`@server.list_tools()`, `@server.call_tool()`)
- Pydantic models for input validation and JSON schema generation
- Async/await throughout for non-blocking operations

### Safety-First Design
- All URLs validated through `safety.py` before processing
- Blocks localhost, private IPs, and internal domains
- Configurable include/exclude patterns for URL filtering

### Content Management
- Dual mode: return content directly OR persist to disk
- Disk persistence avoids context bloat in AI conversations
- Structured output with manifests for programmatic access

### Error Handling
- Graceful degradation for failed URLs
- Structured logging to stderr (stdout reserved for MCP)
- Detailed error records in persistence mode

## Naming Conventions
- **Files**: snake_case (e.g., `mcp_server.py`, `adaptive_strategy.py`)
- **Classes**: PascalCase (e.g., `ScrapeArgs`, `CrawlResult`)
- **Functions**: snake_case (e.g., `require_public_http_url`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `PUBLIC_SCHEMES`)
- **Run IDs**: `{mode}_{timestamp}_{random}` (e.g., `scrape_20250815_122811_4fb188`)

## Import Organization
- Standard library imports first
- Third-party imports second
- Local imports last
- Relative imports for package modules (e.g., `from .safety import`)