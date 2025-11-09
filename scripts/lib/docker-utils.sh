#!/bin/bash

# Docker Utilities for MySwiftAgent
# Provides Docker Compose integration and container management

set -euo pipefail

# Get script directory and project root
if [[ -z "${PROJECT_ROOT:-}" ]]; then
    # Use ${BASH_SOURCE[0]} for bash, ${(%):-%x} for zsh
    if [[ -n "${BASH_SOURCE:-}" ]]; then
        DOCKER_UTILS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    elif [[ -n "${ZSH_VERSION:-}" ]]; then
        DOCKER_UTILS_DIR="$( cd "$( dirname "${(%):-%x}" )" &> /dev/null && pwd )"
    else
        # Fallback: assume script is in PROJECT_ROOT/scripts/lib/
        DOCKER_UTILS_DIR="$(cd "$(dirname "$0")" &> /dev/null && pwd)"
    fi
    PROJECT_ROOT="$(dirname "$(dirname "$DOCKER_UTILS_DIR")")"
fi

# Docker Compose file path
DOCKER_COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"
DOCKER_COMPOSE_DEV_FILE="${PROJECT_ROOT}/docker-compose.dev.yml"

# Color definitions (if not already defined)
if [[ -z "${RED:-}" ]]; then
    readonly RED='\033[0;31m'
    readonly GREEN='\033[0;32m'
    readonly YELLOW='\033[1;33m'
    readonly BLUE='\033[0;34m'
    readonly CYAN='\033[0;36m'
    readonly WHITE='\033[1;37m'
    readonly NC='\033[0m'
fi

# Print functions (lightweight versions if not already defined)
docker_print_info() {
    echo -e "${BLUE}[DOCKER-UTILS] INFO: $1${NC}"
}

docker_print_success() {
    echo -e "${GREEN}[DOCKER-UTILS] SUCCESS: $1${NC}"
}

docker_print_warning() {
    echo -e "${YELLOW}[DOCKER-UTILS] WARNING: $1${NC}"
}

docker_print_error() {
    echo -e "${RED}[DOCKER-UTILS] ERROR: $1${NC}" >&2
}

docker_print_step() {
    echo -e "${WHITE}[DOCKER-UTILS] STEP: $1${NC}"
}

# Check if Docker is available and running
# Returns: 0 if Docker is available, 1 otherwise
check_docker_available() {
    docker_print_step "Checking Docker availability..."

    # Check if docker command exists
    if ! command -v docker &> /dev/null; then
        docker_print_error "Docker not found. Please install Docker Desktop."
        docker_print_info "Visit: https://www.docker.com/products/docker-desktop"
        return 1
    fi

    # Check if Docker daemon is running
    if ! docker info > /dev/null 2>&1; then
        docker_print_error "Docker daemon not running. Please start Docker Desktop."
        return 1
    fi

    # Check if docker-compose command exists
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        docker_print_error "docker-compose not found."
        return 1
    fi

    docker_print_success "Docker is available and running"
    return 0
}

# Get worktree-specific project name for Docker Compose
# This enables multiple worktrees to run isolated Docker environments
# Returns: Project name based on worktree path
get_worktree_project_name() {
    local project_base="myswiftagent"

    # Get current directory
    local current_dir="$(pwd)"

    # Extract worktree identifier from path
    # Example: /path/MySwiftAgent-worktrees/feature-issue-148 → feature-issue-148
    # Using grep + sed for shell compatibility (bash/zsh)
    local worktree_id=$(echo "$current_dir" | grep -o 'worktrees/[^/]*$' | sed 's|worktrees/||')

    if [[ -n "$worktree_id" ]]; then
        # Sanitize: replace slashes and special chars with dashes
        worktree_id=$(echo "$worktree_id" | tr '/' '-' | tr '_' '-' | tr -cd '[:alnum:]-')
        echo "${project_base}-${worktree_id}"
    else
        # Fallback: use base project name
        echo "$project_base"
    fi
}

# Start Docker Compose services
# Args:
#   $1 (optional): Service name to start (default: all services)
# Returns: 0 on success, 1 on failure
start_docker_compose() {
    local service_name="${1:-}"

    docker_print_step "Starting Docker Compose services..."

    # Check Docker availability
    if ! check_docker_available; then
        return 1
    fi

    # Check if docker-compose.yml exists
    if [[ ! -f "$DOCKER_COMPOSE_FILE" ]]; then
        docker_print_error "docker-compose.yml not found: $DOCKER_COMPOSE_FILE"
        return 1
    fi

    # Get project name for worktree isolation
    local project_name=$(get_worktree_project_name)
    docker_print_info "Using project name: $project_name"

    # Determine compose command (docker-compose or docker compose)
    local compose_cmd=""
    if command -v docker-compose &> /dev/null; then
        compose_cmd="docker-compose"
    elif docker compose version &> /dev/null 2>&1; then
        compose_cmd="docker compose"
    else
        docker_print_error "docker-compose command not available"
        return 1
    fi

    # Build compose command
    local compose_args="-p $project_name -f $DOCKER_COMPOSE_FILE"

    # Add dev override file if it exists
    if [[ -f "$DOCKER_COMPOSE_DEV_FILE" ]]; then
        compose_args="$compose_args -f $DOCKER_COMPOSE_DEV_FILE"
        docker_print_info "Using dev override: docker-compose.dev.yml"
    fi

    # Start services
    if [[ -n "$service_name" ]]; then
        docker_print_info "Starting service: $service_name"
        $compose_cmd $compose_args up -d "$service_name"
    else
        docker_print_info "Starting all services"
        $compose_cmd $compose_args up -d
    fi

    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        docker_print_success "Docker Compose services started successfully"
        return 0
    else
        docker_print_error "Failed to start Docker Compose services (exit code: $exit_code)"
        return 1
    fi
}

# Stop Docker Compose services
# Args:
#   $1 (optional): Service name to stop (default: all services)
# Returns: 0 on success, 1 on failure
stop_docker_compose() {
    local service_name="${1:-}"

    docker_print_step "Stopping Docker Compose services..."

    # Check if docker command exists
    if ! command -v docker &> /dev/null; then
        docker_print_warning "Docker not found, skipping Docker Compose stop"
        return 0
    fi

    # Get project name for worktree isolation
    local project_name=$(get_worktree_project_name)
    docker_print_info "Using project name: $project_name"

    # Determine compose command
    local compose_cmd=""
    if command -v docker-compose &> /dev/null; then
        compose_cmd="docker-compose"
    elif docker compose version &> /dev/null 2>&1; then
        compose_cmd="docker compose"
    else
        docker_print_warning "docker-compose command not available, skipping stop"
        return 0
    fi

    # Build compose command
    local compose_args="-p $project_name -f $DOCKER_COMPOSE_FILE"
    if [[ -f "$DOCKER_COMPOSE_DEV_FILE" ]]; then
        compose_args="$compose_args -f $DOCKER_COMPOSE_DEV_FILE"
    fi

    # Stop services
    if [[ -n "$service_name" ]]; then
        docker_print_info "Stopping service: $service_name"
        $compose_cmd $compose_args stop "$service_name"
    else
        docker_print_info "Stopping all services"
        $compose_cmd $compose_args down
    fi

    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        docker_print_success "Docker Compose services stopped successfully"
        return 0
    else
        docker_print_error "Failed to stop Docker Compose services (exit code: $exit_code)"
        return 1
    fi
}

# Check Docker service health
# Args:
#   $1: Service name (e.g., "jobqueue", "myscheduler")
# Returns: 0 if healthy, 1 otherwise
check_docker_service_health() {
    local service_name="$1"

    if [[ -z "$service_name" ]]; then
        docker_print_error "Service name required for health check"
        return 1
    fi

    # Get project name for worktree isolation
    local project_name=$(get_worktree_project_name)

    # Get container name (compose uses project-service format)
    local container_name="${project_name}-${service_name}-1"

    # Check if container exists
    if ! docker ps -a --format '{{.Names}}' | grep -q "^${container_name}$"; then
        docker_print_warning "Container not found: $container_name"
        return 1
    fi

    # Check container health status
    local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "unknown")

    case "$health_status" in
        healthy)
            docker_print_success "Service $service_name is healthy"
            return 0
            ;;
        unhealthy)
            docker_print_error "Service $service_name is unhealthy"
            return 1
            ;;
        starting)
            docker_print_info "Service $service_name is starting..."
            return 1
            ;;
        *)
            # No healthcheck defined or container not running with healthcheck
            # Check if container is running
            local container_state=$(docker inspect --format='{{.State.Status}}' "$container_name" 2>/dev/null || echo "unknown")
            if [[ "$container_state" == "running" ]]; then
                docker_print_info "Service $service_name is running (no healthcheck defined)"
                return 0
            else
                docker_print_warning "Service $service_name is not running (state: $container_state)"
                return 1
            fi
            ;;
    esac
}

# Export functions for use in other scripts
export -f check_docker_available
export -f get_worktree_project_name
export -f start_docker_compose
export -f stop_docker_compose
export -f check_docker_service_health

# Export variables
export PROJECT_ROOT
export DOCKER_COMPOSE_FILE
export DOCKER_COMPOSE_DEV_FILE
