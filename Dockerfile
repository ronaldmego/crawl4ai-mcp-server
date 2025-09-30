# Multi-stage Dockerfile for Crawl4AI MCP Server
# Optimized for size and caching

# Stage 1: Base image with system dependencies
FROM python:3.11-slim as base

# Install system dependencies required for Playwright and crawl4ai
RUN apt-get update && apt-get install -y \
    # Essential build tools
    build-essential \
    # Required for Playwright
    libnss3-dev \
    libatk-bridge2.0-dev \
    libdrm2 \
    libgtk-3-dev \
    libgbm-dev \
    # Additional dependencies for browser automation
    libasound2 \
    libxrandr2 \
    libxss1 \
    libxcursor1 \
    libxi6 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    # Networking and SSL
    ca-certificates \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Python dependencies
FROM base as dependencies

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create app directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Stage 3: Install Playwright browsers
FROM dependencies as browsers

# Install Playwright browsers (specifically chromium)
RUN python -m playwright install chromium

# Stage 4: Final runtime image
FROM browsers as runtime

# Copy application code
COPY . .

# Create directories for outputs
RUN mkdir -p /app/crawls /app/test_crawls

# Create non-root user AFTER installing browsers
RUN adduser --disabled-password --gecos '' --uid 1000 appuser

# Install Playwright browsers for appuser
USER appuser
ENV PLAYWRIGHT_BROWSERS_PATH=/home/appuser/.cache/ms-playwright
RUN python -m playwright install chromium

# Set permissions
USER root
RUN chown -R appuser:appuser /app
USER appuser

# Set environment variables
ENV PYTHONPATH=/app \
    CRAWL4AI_MCP_LOG=INFO

# Expose volume mount points
VOLUME ["/app/crawls", "/app/test_crawls"]

# Default command runs the MCP server
CMD ["python", "-m", "crawler_agent.mcp_server"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import crawler_agent.mcp_server; print('OK')" || exit 1

# Labels for metadata
LABEL maintainer="crawler_agent" \
      description="Crawl4AI MCP Server - Web scraping and crawling tools for AI agents" \
      version="1.0.0"