#!/bin/bash
# Docker Registry Push Script for Crawl4AI MCP Server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOCKER_REPO="uysalsadi/crawl4ai-mcp-server"
VERSION="v1.0.0"

# Helper function for logging
log() {
    echo -e "${BLUE}[docker-push]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Show usage
show_usage() {
    cat << EOF
Docker Registry Push Script for Crawl4AI MCP Server

Usage: $0 <command>

Commands:
    login           Login to Docker Hub
    build           Build and tag Docker image
    push            Push image to Docker Hub
    test            Test the pushed image
    all             Do everything (build, push, test)
    help            Show this help message

Examples:
    $0 login        # Login to Docker Hub first
    $0 all          # Build, push, and test everything
    
Before running:
    1. Make sure you have a Docker Hub account
    2. Run: $0 login
    3. Run: $0 all

EOF
}

# Docker login
docker_login() {
    log "Logging in to Docker Hub..."
    log "Please enter your Docker Hub credentials when prompted"
    docker login
    success "Docker login successful!"
}

# Build and tag image
build_image() {
    log "Building Docker image..."
    
    # Build using the simplified Dockerfile
    docker build -f Dockerfile.simple \
        -t ${DOCKER_REPO}:latest \
        -t ${DOCKER_REPO}:${VERSION} \
        .
    
    success "Docker image built and tagged successfully!"
    log "Tags created:"
    log "  - ${DOCKER_REPO}:latest"
    log "  - ${DOCKER_REPO}:${VERSION}"
}

# Push to registry
push_image() {
    log "Pushing image to Docker Hub..."
    
    # Push both tags
    docker push ${DOCKER_REPO}:latest
    docker push ${DOCKER_REPO}:${VERSION}
    
    success "Docker image pushed successfully!"
    log "Available at:"
    log "  - docker pull ${DOCKER_REPO}:latest"
    log "  - docker pull ${DOCKER_REPO}:${VERSION}"
}

# Test the pushed image
test_image() {
    log "Testing the pushed image..."
    
    # Pull and test the latest image
    docker pull ${DOCKER_REPO}:latest
    
    # Test basic functionality
    log "Testing MCP server initialization..."
    init_request='{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}'
    
    response=$(echo "$init_request" | docker run --rm -i ${DOCKER_REPO}:latest | head -1)
    
    if echo "$response" | grep -q '"name":"crawl4ai-mcp"'; then
        success "✅ Pushed image works correctly!"
        log "Response: $response"
    else
        error "❌ Pushed image test failed"
        log "Response: $response"
        return 1
    fi
}

# Do everything
do_all() {
    log "Building, pushing, and testing Docker image..."
    build_image
    push_image
    test_image
    success "🎉 All operations completed successfully!"
    
    cat << EOF

🐳 Your Docker image is now available publicly!

📦 To use it:
   docker pull ${DOCKER_REPO}:latest
   docker run --rm -i ${DOCKER_REPO}:latest

🔧 For MCP integration, use the provided config files:
   - .mcp.json (project-scoped)
   - claude-desktop-config.json (global Claude Desktop)

EOF
}

# Main execution
main() {
    if [ $# -eq 0 ]; then
        show_usage
        exit 1
    fi
    
    case "$1" in
        "login")
            docker_login
            ;;
        "build")
            build_image
            ;;
        "push")
            push_image
            ;;
        "test")
            test_image
            ;;
        "all")
            do_all
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

main "$@"