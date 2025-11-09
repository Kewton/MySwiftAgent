#!/bin/bash

# Error Catalog Library for MySwiftAgent Unified Start Script
# Provides error code definitions, messages, and resolution suggestions

# Strict error handling (disabled for sourcing in tests)
# set -euo pipefail is disabled to allow this library to be sourced in test environments
# Individual functions handle their own errors appropriately

# Source common library if not already loaded
if [[ -z "${PROJECT_ROOT:-}" ]]; then
    UNIFIED_LIB_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    source "${UNIFIED_LIB_DIR}/common.sh"
fi

# Exit codes
readonly EXIT_SUCCESS=0
readonly EXIT_DEPENDENCY_ERROR=1
readonly EXIT_PORT_CONFLICT=2
readonly EXIT_SERVICE_START_FAILED=3
readonly EXIT_DIRECTORY_NOT_FOUND=4
readonly EXIT_PARTIAL_STARTUP_FAILED=5
readonly EXIT_USER_INTERRUPTED=130

# Get error message for code (bash 3.2 compatible)
get_error_message() {
    local error_code="$1"

    case "$error_code" in
        ${EXIT_DEPENDENCY_ERROR})
            echo "Required dependencies are missing"
            ;;
        ${EXIT_PORT_CONFLICT})
            echo "Port conflict detected"
            ;;
        ${EXIT_SERVICE_START_FAILED})
            echo "Service failed to start"
            ;;
        ${EXIT_DIRECTORY_NOT_FOUND})
            echo "Service directory not found"
            ;;
        ${EXIT_PARTIAL_STARTUP_FAILED})
            echo "Partial startup failed - rollback executed"
            ;;
        ${EXIT_USER_INTERRUPTED})
            echo "Operation interrupted by user"
            ;;
        *)
            echo "Unknown error"
            ;;
    esac
}

# Get error resolution for code (bash 3.2 compatible)
get_error_resolution() {
    local error_code="$1"

    case "$error_code" in
        ${EXIT_DEPENDENCY_ERROR})
            cat << 'EOF'
Install missing dependencies:
  - uv: curl -LsSf https://astral.sh/uv/install.sh | sh
  - npm: https://nodejs.org/
  - curl: Install via system package manager (apt/brew/yum)
EOF
            ;;
        ${EXIT_PORT_CONFLICT})
            cat << 'EOF'
Resolve port conflicts:
  1. Stop the conflicting process manually
  2. Use './scripts/unified-start.sh start --force' to kill conflicting processes
  3. Check if another instance of services is running
EOF
            ;;
        ${EXIT_SERVICE_START_FAILED})
            cat << 'EOF'
Troubleshoot service startup:
  1. Check service logs in logs/<service-name>.log
  2. Verify service dependencies are installed (uv sync / npm install)
  3. Check if required configuration files exist
  4. Try running the service manually in its directory
EOF
            ;;
        ${EXIT_DIRECTORY_NOT_FOUND})
            cat << 'EOF'
Verify project structure:
  1. Ensure all service directories exist
  2. Check if you're running from the correct worktree
  3. Run 'git status' to verify branch state
EOF
            ;;
        ${EXIT_PARTIAL_STARTUP_FAILED})
            cat << 'EOF'
Investigate failed services:
  1. Check logs for failed services in logs/ directory
  2. Run './scripts/unified-start.sh status' after cleanup
  3. Try starting failed services individually for debugging
  4. Use './scripts/unified-start.sh start --force' to force restart
EOF
            ;;
        ${EXIT_USER_INTERRUPTED})
            cat << 'EOF'
Operation was cancelled:
  - All started services have been stopped
  - System is in clean state
  - You can safely retry the operation
EOF
            ;;
    esac
}

# Print error with code and message
print_error_with_code() {
    local error_code="$1"
    local context="${2:-}"

    print_error "Error Code: ${error_code}"

    local message
    message=$(get_error_message "$error_code")
    if [[ -n "$message" ]]; then
        print_error "Message: ${message}"
    fi

    if [[ -n "$context" ]]; then
        print_error "Context: ${context}"
    fi

    echo ""
}

# Print error resolution
print_error_resolution() {
    local error_code="$1"
    local resolution
    resolution=$(get_error_resolution "$error_code")

    if [[ -n "$resolution" ]]; then
        echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
        echo -e "${YELLOW}How to resolve:${NC}"
        echo -e "${WHITE}${resolution}${NC}"
        echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
        echo ""
    fi
}

# Show full error report
show_error_report() {
    local error_code="$1"
    local context="${2:-}"

    echo ""
    echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}           ERROR REPORT${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"

    print_error_with_code "$error_code" "$context"
    print_error_resolution "$error_code"

    echo -e "${CYAN}For more help, see: docs/unified-start-troubleshooting.md${NC}"
    echo ""
}

# Detect error type from context
detect_error_type() {
    local error_message="$1"

    if [[ "$error_message" =~ "command not found" ]] || [[ "$error_message" =~ "not found" ]]; then
        echo "$EXIT_DEPENDENCY_ERROR"
    elif [[ "$error_message" =~ "port" ]] || [[ "$error_message" =~ "address already in use" ]]; then
        echo "$EXIT_PORT_CONFLICT"
    elif [[ "$error_message" =~ "directory" ]] || [[ "$error_message" =~ "No such file" ]]; then
        echo "$EXIT_DIRECTORY_NOT_FOUND"
    else
        echo "$EXIT_SERVICE_START_FAILED"
    fi
}

# Port conflict details
show_port_conflict_details() {
    local port="$1"
    local service_name="${2:-unknown}"

    print_error_with_code "$EXIT_PORT_CONFLICT" "Port ${port} required by ${service_name}"

    # Get process details
    if command -v lsof &> /dev/null; then
        local process_info
        if process_info=$(lsof -ti:"$port" 2>/dev/null); then
            echo -e "${YELLOW}Process using port ${port}:${NC}"

            for pid in $process_info; do
                local cmd user
                cmd=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
                user=$(ps -p "$pid" -o user= 2>/dev/null || echo "unknown")

                echo -e "  ${WHITE}PID:${NC}     $pid"
                echo -e "  ${WHITE}Command:${NC} $cmd"
                echo -e "  ${WHITE}User:${NC}    $user"
                echo ""
            done
        fi
    fi

    print_error_resolution "$EXIT_PORT_CONFLICT"
}

# Service startup failure details
show_service_failure_details() {
    local service_name="$1"
    local log_file="${LOG_DIR}/${service_name}.log"

    print_error_with_code "$EXIT_SERVICE_START_FAILED" "Service: ${service_name}"

    if [[ -f "$log_file" ]]; then
        echo -e "${YELLOW}Last 10 lines of ${service_name} log:${NC}"
        echo -e "${WHITE}───────────────────────────────────────────────────────────${NC}"
        tail -n 10 "$log_file" 2>/dev/null || echo "Unable to read log file"
        echo -e "${WHITE}───────────────────────────────────────────────────────────${NC}"
        echo ""
    fi

    print_error_resolution "$EXIT_SERVICE_START_FAILED"
}

# Export error codes
export EXIT_SUCCESS
export EXIT_DEPENDENCY_ERROR
export EXIT_PORT_CONFLICT
export EXIT_SERVICE_START_FAILED
export EXIT_DIRECTORY_NOT_FOUND
export EXIT_PARTIAL_STARTUP_FAILED
export EXIT_USER_INTERRUPTED

# Export functions
export -f get_error_message
export -f get_error_resolution
export -f print_error_with_code
export -f print_error_resolution
export -f show_error_report
export -f detect_error_type
export -f show_port_conflict_details
export -f show_service_failure_details
