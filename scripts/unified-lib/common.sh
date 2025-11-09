#!/bin/bash

# Common Functions Library for MySwiftAgent Unified Start Script
# Provides color output, logging, and utility functions

# Strict error handling (disabled for sourcing in tests)
# set -euo pipefail is disabled to allow this library to be sourced in test environments
# Individual functions handle their own errors appropriately

# Color definitions
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m' # No Color

# Global configuration
# Only set if not already set (allow parent script to define)
if [[ -z "${PROJECT_ROOT:-}" ]]; then
    UNIFIED_LIB_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    readonly PROJECT_ROOT="$(dirname "$(dirname "$UNIFIED_LIB_DIR")")"
fi

# Detect worktree index for directory isolation
# Note: worktree-utils.sh must be sourced before this, or we use index 0 as default
if command -v get_current_worktree_index &> /dev/null; then
    WORKTREE_INDEX=$(get_current_worktree_index 2>/dev/null || echo "0")
else
    # Fallback: try to get from .env.local if worktree-utils not loaded yet
    if [[ -f "${PROJECT_ROOT}/.env.local" ]]; then
        WORKTREE_INDEX=$(grep "^WORKTREE_INDEX=" "${PROJECT_ROOT}/.env.local" 2>/dev/null | cut -d'=' -f2 || echo "0")
    else
        WORKTREE_INDEX="0"
    fi
fi

# Worktree-specific directories for process isolation
readonly LOG_DIR="${PROJECT_ROOT}/logs/wt${WORKTREE_INDEX}"
readonly PID_DIR="/tmp/myswiftagent-wt${WORKTREE_INDEX}"

# Timestamp function
get_timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

# Print functions with timestamps and colors

# Print informational message
print_info() {
    local message="$1"
    echo -e "${BLUE}[$(get_timestamp)] INFO: ${message}${NC}"
}

# Print success message
print_success() {
    local message="$1"
    echo -e "${GREEN}[$(get_timestamp)] SUCCESS: ${message}${NC}"
}

# Print warning message
print_warning() {
    local message="$1"
    echo -e "${YELLOW}[$(get_timestamp)] WARNING: ${message}${NC}"
}

# Print error message to stderr
print_error() {
    local message="$1"
    echo -e "${RED}[$(get_timestamp)] ERROR: ${message}${NC}" >&2
}

# Print step message
print_step() {
    local message="$1"
    echo -e "${WHITE}[$(get_timestamp)] STEP: ${message}${NC}"
}

# Print service-specific message
print_service() {
    local service_name="$1"
    local message="$2"
    echo -e "${PURPLE}[$(get_timestamp)] [${service_name}] ${message}${NC}"
}

# Initialize directories
init_directories() {
    print_step "Initializing directories..."

    # Create log directory if not exists
    if [[ ! -d "$LOG_DIR" ]]; then
        mkdir -p "$LOG_DIR"
        print_info "Created log directory: $LOG_DIR"
    fi

    # Create PID directory if not exists
    if [[ ! -d "$PID_DIR" ]]; then
        mkdir -p "$PID_DIR"
        print_info "Created PID directory: $PID_DIR"
    fi

    print_success "Directories initialized"
}

# Show banner
show_banner() {
    echo -e "${CYAN}"
    cat << 'EOF'
================================================================================

   MySwiftAgent - Unified Start Script
   =========================================

   Services:
   - myVault       : Secrets management service
   - jobqueue      : Job queue management API
   - myscheduler   : Job scheduling service
   - graphAiServer : Graph AI workflow service
   - expertAgent   : AI agent service
   - myAgentDesk   : Web interface
   - commonUI      : Common UI components

================================================================================
EOF
    echo -e "${NC}"
}

# Check if command exists
command_exists() {
    local cmd="$1"
    command -v "$cmd" &> /dev/null
}

# Check dependencies
check_dependencies() {
    print_step "Checking dependencies..."

    local missing_deps=0

    # Check uv
    if ! command_exists uv; then
        print_error "uv package manager not found"
        print_info "Install uv: https://docs.astral.sh/uv/"
        ((missing_deps++))
    else
        print_info "uv found: $(uv --version)"
    fi

    # Check npm
    if ! command_exists npm; then
        print_warning "npm not found (may be required for some services)"
    else
        print_info "npm found: $(npm --version)"
    fi

    # Check curl
    if ! command_exists curl; then
        print_error "curl not found (required for health checks)"
        ((missing_deps++))
    else
        print_info "curl found"
    fi

    if [[ $missing_deps -gt 0 ]]; then
        print_error "Missing $missing_deps required dependencies"
        return 1
    fi

    print_success "All required dependencies found"
    return 0
}

# Clean up stale PID files
cleanup_stale_pids() {
    if [[ ! -d "$PID_DIR" ]]; then
        return 0
    fi

    local cleaned=0

    for pid_file in "$PID_DIR"/*.pid; do
        # Skip if no pid files exist
        if [[ ! -f "$pid_file" ]]; then
            continue
        fi

        local pid
        pid=$(cat "$pid_file" 2>/dev/null || echo "")

        if [[ -z "$pid" ]] || ! kill -0 "$pid" 2>/dev/null; then
            # Process is not running, remove stale PID file
            local service_name
            service_name=$(basename "$pid_file" .pid)
            print_info "Cleaning stale PID file for: ${service_name}"
            rm -f "$pid_file"
            ((cleaned++))
        fi
    done

    if [[ $cleaned -gt 0 ]]; then
        print_success "Cleaned up ${cleaned} stale PID file(s)"
    fi
}

# Find orphaned processes (processes that have PID files but shouldn't be running)
find_orphaned_processes() {
    if [[ ! -d "$PID_DIR" ]]; then
        return 0
    fi

    local orphaned=0

    for pid_file in "$PID_DIR"/*.pid; do
        if [[ ! -f "$pid_file" ]]; then
            continue
        fi

        local pid
        pid=$(cat "$pid_file" 2>/dev/null || echo "")

        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            local service_name
            service_name=$(basename "$pid_file" .pid)
            echo "${service_name}:${pid}"
            ((orphaned++))
        fi
    done

    return $orphaned
}

# Clean up all temporary files and directories
cleanup_all() {
    print_step "Cleaning up temporary files..."

    # Clean stale PID files
    cleanup_stale_pids

    # Remove empty log files
    if [[ -d "$LOG_DIR" ]]; then
        find "$LOG_DIR" -type f -name "*.log" -size 0 -delete 2>/dev/null || true
    fi

    print_success "Cleanup completed"
}

# Cleanup function for trap
cleanup_on_exit() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        print_error "Script exited with error code: $exit_code"
    fi
}

# Set trap for cleanup
trap cleanup_on_exit EXIT

# Export functions for use in other scripts
export -f get_timestamp
export -f print_info
export -f print_success
export -f print_warning
export -f print_error
export -f print_step
export -f print_service
export -f init_directories
export -f show_banner
export -f command_exists
export -f check_dependencies
export -f cleanup_stale_pids
export -f find_orphaned_processes
export -f cleanup_all

# Export color variables
export RED GREEN YELLOW BLUE PURPLE CYAN WHITE NC

# Export global configuration
export PROJECT_ROOT LOG_DIR PID_DIR WORKTREE_INDEX
