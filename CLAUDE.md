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

## MCP tool surface (initial)
- `crawl_url(args) -> { markdown, links, metadata }`
- `deep_crawl(args) -> { markdown, links, metadata }` (enable via config: depth, link selection)
- `adaptive_crawl(args) -> { markdown, links, metadata }` (enable adaptive strategy)
- Inputs include `url`, optional `crawler_config`, `browser_config`, `script` (C4A-Script), `timeout_sec`.

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

## Notes for Claude
- Prefer concise edits and high-signal summaries.
- If blocked on missing details (e.g., schema shape), propose 1–2 narrow options and proceed with the safest default.
- Avoid long-running crawls; provide budgets and timeouts by default.
