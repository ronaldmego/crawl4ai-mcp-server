# Project Working Agreements for Claude Code

You are a senior software engineer collaborating on `crawler_agent`. Your primary goal is to expose Crawl4AI via an MCP server that integrates cleanly with OpenAI Agents SDK and works well in Cursor/Cloud Code.

## Mission and scope
- Build a robust stdio MCP server wrapping Crawl4AI (`AsyncWebCrawler`) with a minimal tool surface: `crawl_url`, `deep_crawl`, `adaptive_crawl`.
- Provide strict JSON schemas for inputs/outputs; add observability and guardrails.
- Wire into OpenAI Agents SDK using `MCPServerStdio`; cache tool lists when appropriate.

## Workflow
1. Confirm scope and propose a short plan before edits.
2. Make minimal, reversible changes with small diffs.
3. Write/expand tests when feasible; keep coverage meaningful.
4. Run minimal validation (build/test/lint/smoke) and capture outputs.
5. Summarize changes and propose next steps.

## References (authoritative)
- Crawl4AI docs: `https://docs.crawl4ai.com/`
- OpenAI Agents SDK (MCP): `https://openai.github.io/openai-agents-python/mcp/`
- Tools reference: `https://openai.github.io/openai-agents-python/tools/`
- Agent reference (mcp_servers, mcp_config): `https://openai.github.io/openai-agents-python/ref/agent/`
- MCP introduction: `https://modelcontextprotocol.io/introduction`

## Local documentation usage
- Only read targeted excerpts from large files. For `docs/modelcontextprotocol-python-sdk-CLAUDE-MD.txt`, search specific symbols/sections; do not ingest the entire file.
- Prefer parallel, read-only scans (grep + read specific lines) when gathering context.

## Design constraints and NFRs
- Transport: start with stdio MCP; consider SSE/Streamable HTTP later.
- Contracts: strict Pydantic schemas; version tool contracts; deterministic outputs.
- Observability: structured logs; tracing spans for `list_tools`/`call_tool`; basic metrics.
- Safety: domain allow/deny lists; robots.txt compliance; depth/TTL/timeouts; proxy/auth constraints; no internal networks.
- Performance: reuse browser contexts; cache where appropriate; avoid unnecessary deep crawls.

## Coding standards
- Python 3.11+; explicit type hints for public APIs.
- Avoid deep nesting; use guard clauses; no bare `except`.
- Clear docstrings on public functions/classes; meaningful names; small, cohesive functions.
- Do not reformat unrelated code; preserve existing indentation and style.

## MCP tool surface (current implementation)
- `scrape(url, output_dir?) -> { markdown, links, metadata } | { run_id, file_path, manifest_path, ... }`
- `crawl(seed_url, max_depth?, max_pages?, output_dir?, ...) -> { pages[], total_pages } | { run_id, pages_ok, manifest_path, ... }`
- `crawl_site(entry_url, output_dir, ...) -> { run_id, manifest_path, pages_ok, ... }` (always persists)
- `crawl_sitemap(sitemap_url, output_dir, ...) -> { run_id, manifest_path, pages_ok, ... }` (always persists)

### Content Hiding Feature
- **Without `output_dir`**: Tools return full content (backward compatible)
- **With `output_dir`**: Tools persist to disk and return metadata only (avoids context bloat)
- Inputs include `url`/`seed_url`, optional `crawler_config`, `browser_config`, `script`, `timeout_sec`, `output_dir`.

## Validation
- Add a smoke test that:
  - Starts the stdio MCP server.
  - Asserts `list_tools` contains the three tools.
  - Calls `crawl_url` against a simple public URL and verifies non-empty markdown.
- Capture and surface errors with actionable messages.

## Security & privacy
- Block `file://`, `localhost`, RFC1918 addresses; respect robots.txt modes.
- Redact secrets; never log credentials/PII.
- Enforce domain policies and rate limits; require explicit approval to relax these.

## Changes that require explicit approval
- Adding new tools or changing tool contracts.
- Introducing new dependencies or transports (SSE/Streamable HTTP).
- Modifying caching, security policies, or network egress rules.

## How to cite
- When referencing external material, include Markdown links.

## Rollback guidance
- Keep server transport default as stdio; toggles/flags for remote transports.
- Version tool schemas; support previous version for one minor release when changing.

## Development Environment Rules & Memory Bank

### Virtual Environment Protocol (CRITICAL)
- **ALWAYS activate `.venv` before ANY operation**: `source .venv/bin/activate`
- **Required for**: package installation, running servers, testing, development commands
- **Location**: `/Users/sadiuysal/Documents/GitHub/crawler_agent/.venv`
- **Never run Python commands without venv activation** - this causes ModuleNotFoundError

### MCP Server Implementation Status
- **Server location**: `crawler_agent/mcp_server.py` (518 lines)
- **Available tools**: `scrape`, `crawl`, `crawl_site`, `crawl_sitemap` (4 tools total)
- **Server command**: `python -m crawler_agent.mcp_server` (stdio mode)
- **Testing client**: `crawler_agent/smoke_client.py`

### Claude Code MCP Integration
- **Config file**: `/Users/sadiuysal/Library/Application Support/Claude/claude_desktop_config.json`
- **Server entry**: `crawl4ai-mcp` configured with venv Python path
- **Restart required**: Claude session must restart after config changes
- **Project config**: `.mcp.json` (optional, for project-scoped servers)

### Testing Protocol
1. **Activate venv first**: `source .venv/bin/activate`
2. **Smoke test**: `python -m crawler_agent.smoke_client`
3. **Full test**: Use test scripts for all 4 tools
4. **MCP verification**: Check tool availability post-restart

### Dependencies & Installation
- **Requirements**: `requirements.txt` (crawl4ai, mcp, pydantic, playwright, etc.)
- **Install command**: `pip install -r requirements.txt` (in venv)
- **Key packages**: crawl4ai>=0.7.0, mcp>=1.1.0, openai-agents>=0.1.0

### File Structure & Outputs
- **Crawl outputs**: `./crawls/` or `./test_crawls/` directories
- **Persistence**: JSON manifests, markdown files, CSV links
- **Run IDs**: Format `site_YYYYMMDD_HHMMSS_HASH`

### Common Issues & Solutions
- **ModuleNotFoundError**: Activate venv first
- **MCP tools not visible**: Restart Claude session after config
- **Path issues**: Use absolute paths in MCP config
- **Permission errors**: Check `.claude/settings.local.json`

### Development Commands (All require venv)
```bash
# Always start with:
source .venv/bin/activate

# Test MCP server:
python -m crawler_agent.smoke_client

# Run server directly:
python -m crawler_agent.mcp_server

# Install dependencies:
pip install -r requirements.txt
```

### MCP Tool Schemas (Current Implementation)
- `scrape(url, crawler?, browser?, script?, timeout_sec?, output_dir?)` → `{url, markdown, links, metadata}` OR `{run_id, file_path, manifest_path, bytes_written, ...}`
- `crawl(seed_url, max_depth?, max_pages?, same_domain_only?, patterns?, adaptive?, output_dir?)` → `{start_url, pages[], total_pages}` OR `{run_id, pages_ok, pages_failed, manifest_path, ...}`
- `crawl_site(entry_url, output_dir, config...)` → `{run_id, output_dir, manifest_path, stats}` (always persists)
- `crawl_sitemap(sitemap_url, output_dir, config...)` → `{run_id, output_dir, manifest_path, stats}` (always persists)

## Notes for Claude
- Prefer concise edits and high-signal summaries.
- If blocked on missing details (e.g., schema shape), propose 1–2 narrow options and proceed with the safest default.
- Avoid long-running crawls; provide budgets and timeouts by default.
