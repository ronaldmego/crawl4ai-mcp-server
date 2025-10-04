# Technology Stack

## Core Technologies
- **Python 3.11+**: Main programming language
- **Crawl4AI**: Web scraping and crawling engine (v0.7.x)
- **Playwright**: Browser automation for rendering JavaScript
- **MCP (Model Context Protocol)**: Communication protocol for AI tools
- **Pydantic**: Data validation and JSON schema generation
- **Docker**: Containerization and deployment

## Key Dependencies
```
mcp>=1.1.0,<2.0.0
crawl4ai>=0.7.0,<0.8.0
pydantic>=2.7,<3.0
playwright>=1.44,<2.0
openai-agents>=0.1.0,<1.0.0
httpx>=0.27,<1.0
```

## Build System
- **Package Management**: pip with requirements.txt
- **Virtual Environment**: `.venv` or `venv` (project-specific)
- **Docker**: Multi-stage Dockerfile with Playwright browser installation
- **Container Registry**: Published to Docker Hub as `uysalsadi/crawl4ai-mcp-server`

## Common Commands

### Development Setup
```bash
# Virtual environment (required for all operations)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
python -m playwright install chromium
```

### Testing & Validation
```bash
# Test MCP server functionality
python -m crawler_agent.smoke_client

# Test adaptive crawling
python test_adaptive.py

# Test with OpenAI Agents (requires OPENAI_API_KEY)
python -m crawler_agent.agents_example
```

### Docker Operations (Recommended)
```bash
# Build and test
./docker-run.sh build
./docker-run.sh test

# Run MCP server
./docker-run.sh run

# Development mode
./docker-run.sh dev
```

### MCP Server Operations
```bash
# Run stdio MCP server directly
python -m crawler_agent.mcp_server

# With logging
CRAWL4AI_MCP_LOG=DEBUG python -m crawler_agent.mcp_server
```

## Environment Variables
- `CRAWL4AI_MCP_LOG`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `TARGET_URL`: Default URL for smoke testing
- `OPENAI_API_KEY`: Required for OpenAI Agents SDK integration
- `RESEARCH_TASK`: Custom research task for agents example