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

### Docker Integration (Recommended Approach)
The project now supports Docker for simplified setup and deployment:

#### Docker Benefits
- **Zero Setup**: No manual venv, pip, or Playwright installation required
- **Consistent Environment**: Same behavior across all platforms  
- **Isolation**: No conflicts with system Python or dependencies
- **Portability**: Works anywhere Docker runs
- **Easy Updates**: Simple image rebuilds for new versions

#### Docker Files Structure
- `Dockerfile`: Multi-stage build with Python 3.11, dependencies, and Playwright browsers
- `docker-compose.yml`: Service definitions for production, development, and testing
- `docker-run.sh`: Helper script with common commands
- `.dockerignore`: Optimized build context

#### Docker Commands Reference
```bash
# Build and test
./docker-run.sh build      # Build Docker image
./docker-run.sh test       # Run smoke tests
./docker-run.sh run        # Run MCP server
./docker-run.sh dev        # Development shell
./docker-run.sh stop       # Stop containers
./docker-run.sh clean      # Clean up images
```

#### MCP Integration with Docker
Claude Code can use the Docker container directly:
```json
{
  "mcpServers": {
    "crawl4ai-mcp": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "crawl4ai-mcp-server:latest"],
      "cwd": "/path/to/crawl4ai-mcp-server"
    }
  }
}
```

### Virtual Environment Protocol (CRITICAL - Manual Setup Only)
- **ALWAYS activate virtual environment before ANY operation**: `source .venv/bin/activate` or `source venv/bin/activate`
- **Required for**: package installation, running servers, testing, development commands
- **Location**: `<project_root>/.venv` or `<project_root>/venv` (project-specific)
- **Never run Python commands without venv activation** - this causes ModuleNotFoundError

### Remote Repository Setup (For using in other projects)
When using this MCP server from another repository:

#### Option 1: Direct Git Installation
```bash
# From your target repository
git clone https://github.com/uysalsadi/crawl4ai-mcp-server.git
cd crawl4ai-mcp-server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium

# Test the installation
python -m crawler_agent.smoke_client
```

#### Option 2: Global MCP Server Configuration
```bash
# Install in a global location
mkdir -p ~/.local/mcp-servers
cd ~/.local/mcp-servers
git clone https://github.com/uysalsadi/crawl4ai-mcp-server.git
cd crawl4ai-mcp-server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

#### Claude Code Configuration (Remote)

#### Option 1: Docker (Recommended)
Add to `~/.claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "crawl4ai-mcp": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--volume", "/path/to/crawl4ai-mcp-server/crawls:/app/crawls",
        "crawl4ai-mcp-server:latest"
      ],
      "cwd": "/path/to/crawl4ai-mcp-server"
    }
  }
}
```

#### Option 2: Manual Virtual Environment
Add to `~/.claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "crawl4ai-mcp": {
      "command": "/path/to/crawler_agent/.venv/bin/python",
      "args": ["-m", "crawler_agent.mcp_server"],
      "cwd": "/path/to/crawler_agent"
    }
  }
}
```

#### Project-Scoped Configuration (.mcp.json)
For project-specific MCP servers, add to target repository:
```json
{
  "mcpServers": {
    "crawl4ai": {
      "command": "python",
      "args": ["-m", "crawler_agent.mcp_server"],
      "cwd": "/path/to/crawler_agent",
      "env": {
        "PATH": "/path/to/crawler_agent/.venv/bin:${PATH}"
      }
    }
  }
}
```

### MCP Server Implementation Status
- **Server location**: `crawler_agent/mcp_server.py` (518 lines)
- **Available tools**: `scrape`, `crawl`, `crawl_site`, `crawl_sitemap` (4 tools total)
- **Server command**: `python -m crawler_agent.mcp_server` (stdio mode)
- **Testing client**: `crawler_agent/smoke_client.py`

### Claude Code MCP Integration
- **Config file**: `~/.claude/claude_desktop_config.json`
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

### Development Commands

#### Docker Commands (Recommended)
```bash
# Build and test:
./docker-run.sh build
./docker-run.sh test

# Run MCP server:
./docker-run.sh run

# Development mode:
./docker-run.sh dev
```

#### Manual Commands (Require venv)
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

## Documentation Memory Rule (CRITICAL)
**ALWAYS remember**: When ANY documentation file is modified (CLAUDE.md, README.md, .cursorrules, etc.), you MUST:
1. **Read the current version** of all related documentation files first
2. **Synchronize changes** across Claude Code (CLAUDE.md) and Cursor (.cursorrules) configurations  
3. **Update project knowledge** in this memory bank section to reflect any new patterns, tools, or workflows
4. **Verify consistency** between documentation and actual implementation
5. **Document the change** in git commit messages as a documentation update

This ensures both Claude Code and Cursor users have consistent, up-to-date guidance.

## Cursor Integration & Dual Environment Support

### Configuration Files
- **Claude Code**: Uses `CLAUDE.md` (this file) for project context and rules
- **Cursor**: Uses `.cursorrules` for AI assistant behavior and project-specific guidance
- **Both**: Share common MCP integration via `.mcp.json` (project-scoped servers)

### Synchronized Rules & Standards
The following rules are maintained across both environments:

#### Development Protocol
- **Virtual Environment**: ALWAYS activate `.venv` before ANY Python operation
- **MCP Server**: Located at `crawler_agent/mcp_server.py` with 4 tools (`scrape`, `crawl`, `crawl_site`, `crawl_sitemap`)
- **Testing**: Use `python -m crawler_agent.smoke_client` for validation
- **Code Style**: Python 3.11+, strict typing, guard clauses, minimal diffs

#### Tool Surface (Current Implementation)
- `scrape(url, output_dir?)` → Returns content OR persists with metadata
- `crawl(seed_url, max_depth?, max_pages?, output_dir?)` → Multi-page crawling
- `crawl_site(entry_url, output_dir, ...)` → Full site crawling (always persists)
- `crawl_sitemap(sitemap_url, output_dir, ...)` → Sitemap-based crawling (always persists)

#### Security & Safety (Shared)
- Block internal networks, localhost, RFC1918 addresses
- Respect robots.txt modes and domain policies
- Never log credentials/PII; sanitize outputs

### Environment-Specific Features

#### Claude Code Only
- **MCP Integration**: Native tool calling via `mcp__crawl4ai-mcp__*` functions
- **Config Location**: `~/.claude/claude_desktop_config.json` (global) or `.mcp.json` (project)
- **Session Management**: Restart required after config changes

#### Cursor Only  
- **Project Rules**: `.cursorrules` defines behavior and workflow
- **Inline Documentation**: Uses `@CLAUDE.md` references for context
- **Git Integration**: Automatic commit message enhancement

### Workflow Synchronization
1. **Planning**: Both environments use todo lists and short numbered plans
2. **Validation**: Run smoke tests and basic validation after changes
3. **Documentation**: Update both CLAUDE.md and .cursorrules when changing workflows
4. **Commits**: Use consistent commit message format with proper attribution

## Development Learnings & Memory Bank (CRITICAL)

### Docker MCP Server Lessons Learned

#### Key Success Factors
1. **Docker Image Publishing**: Always rebuild and push Docker image after any code changes
   - Use `./docker-push.sh build && ./docker-push.sh push` workflow
   - Published image: `uysalsadi/crawl4ai-mcp-server:latest`
   - Test published image: `python test-config.py`

2. **MCP Protocol Requirements**:
   - MCP servers need proper `initialize` → `notifications/initialized` → `tools/list` sequence
   - Claude Code handles this automatically, manual testing requires full sequence
   - Docker MCP server exposes 4 tools: `scrape`, `crawl`, `crawl_site`, `crawl_sitemap`

3. **Configuration Management**:
   - **Global Cursor**: `~/.cursor/mcp.json` - use Docker command
   - **Project Cursor**: `.mcp.json` - use Docker with volume mounting
   - **Claude Code**: `claude-desktop-config.example.json` - use published Docker image
   - **Always restart** Cursor/Claude Code after config changes

#### Critical Docker Configuration (TESTED & WORKING)
```json
{
  "mcpServers": {
    "crawl4ai-mcp": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--volume", "./crawls:/app/crawls",
        "uysalsadi/crawl4ai-mcp-server:latest"
      ],
      "env": {
        "CRAWL4AI_MCP_LOG": "INFO"
      }
    }
  }
}
```

#### Repository Cleanup Best Practices
1. **Remove Legacy Files**: Debug scripts, old test files, temp configs
2. **Standardize Naming**: Use consistent `crawl4ai-mcp` server name across all configs
3. **Update Documentation**: Synchronize README.md, CLAUDE.md, .cursorrules after changes
4. **Version Docker Images**: Tag and push both `:latest` and versioned tags

#### Common Failure Patterns (AVOID)
❌ **Using local venv paths in global configs** - breaks portability  
❌ **Forgetting to rebuild Docker image** - users get outdated tools  
❌ **Inconsistent server names** - causes confusion between environments  
❌ **Not testing published Docker image** - deployment failures  
❌ **Missing volume mounts** - crawl results lost  

#### Validation Checklist
✅ **Docker image rebuilt and pushed** after code changes  
✅ **Test script confirms 4 tools available** (`python test-config.py`)  
✅ **Global Cursor config uses Docker** (not local venv)  
✅ **Project .mcp.json uses published image** with volume mount  
✅ **Claude Code config example updated** with working Docker setup  
✅ **Documentation synchronized** across all files  

#### Quick Recovery Commands
```bash
# Rebuild and republish Docker image
./docker-push.sh build && ./docker-push.sh push

# Test published image works
python test-config.py

# Update global Cursor config (manual edit required)
# ~/.cursor/mcp.json - change to Docker command

# Verify tools available (should show 4 tools)
# Restart Cursor/Claude Code to reload config
```

## Notes for Claude
- Prefer concise edits and high-signal summaries.
- If blocked on missing details (e.g., schema shape), propose 1–2 narrow options and proceed with the safest default.
- Avoid long-running crawls; provide budgets and timeouts by default.
- **When modifying documentation**: Apply changes to both CLAUDE.md and .cursorrules for consistency.
- **ALWAYS validate Docker configs** with `test-config.py` before recommending to users.
