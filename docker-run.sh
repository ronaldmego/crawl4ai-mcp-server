#!/bin/bash
# Crawl4AI MCP Server Docker Runner
# Provides easy commands for running the Docker container

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper function for logging
log() {
    echo -e "${BLUE}[crawl4ai-mcp]${NC} $1"
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
Crawl4AI MCP Server Docker Runner

Usage: $0 <command> [options]

Commands:
    build           Build the Docker image
    run             Run the MCP server (stdio mode)
    test            Run smoke tests
    dev             Start development container with shell access
    stop            Stop running containers
    clean           Remove containers and images
    logs            Show container logs
    help            Show this help message

Examples:
    $0 build                    # Build the image
    $0 run                      # Run MCP server
    $0 test                     # Run smoke tests
    $0 dev                      # Development mode
    
Environment Variables:
    OPENAI_API_KEY             OpenAI API key for agents example
    TARGET_URL                 URL for testing (default: https://modelcontextprotocol.io/docs)
    CRAWL4AI_MCP_LOG          Log level (DEBUG, INFO, WARN, ERROR)

EOF
}

# Build the Docker image
build_image() {
    log "Building Crawl4AI MCP Server image..."
    docker compose build
    success "Image built successfully!"
}

# Run the MCP server
run_server() {
    log "Starting Crawl4AI MCP Server..."
    log "Container will run in stdio mode for MCP communication"
    log "Use Ctrl+C to stop the server"
    docker compose up crawl4ai-mcp
}

# Run smoke tests
run_tests() {
    log "Running smoke tests..."
    docker compose run --rm crawl4ai-mcp-test
    success "Tests completed!"
}

# Development mode
dev_mode() {
    log "Starting development container with shell access..."
    docker compose run --rm crawl4ai-mcp-dev
}

# Stop containers
stop_containers() {
    log "Stopping containers..."
    docker compose down
    success "Containers stopped!"
}

# Clean up
clean_up() {
    log "Cleaning up containers and images..."
    docker compose down --rmi all --volumes --remove-orphans
    success "Cleanup completed!"
}

# Show logs
show_logs() {
    log "Showing container logs..."
    docker compose logs -f crawl4ai-mcp
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker compose version &> /dev/null; then
        error "docker compose is not available. Please install Docker Compose plugin."
        exit 1
    fi
}

# Main execution
main() {
    check_docker
    
    if [ $# -eq 0 ]; then
        show_usage
        exit 1
    fi
    
    case "$1" in
        "build")
            build_image
            ;;
        "run")
            run_server
            ;;
        "test")
            run_tests
            ;;
        "dev")
            dev_mode
            ;;
        "stop")
            stop_containers
            ;;
        "clean")
            clean_up
            ;;
        "logs")
            show_logs
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