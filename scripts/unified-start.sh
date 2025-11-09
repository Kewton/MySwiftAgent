#!/bin/bash

# MySwiftAgent Unified Start Script
# Single command to start/stop/restart all microservices
#
# Usage:
#   ./scripts/unified-start.sh start [--env-file PATH] [--dry-run]   - Start all services
#   ./scripts/unified-start.sh stop                                  - Stop all services
#   ./scripts/unified-start.sh restart [--env-file PATH]             - Restart all services
#   ./scripts/unified-start.sh status                                - Check service status
#   ./scripts/unified-start.sh --help                                - Show help
#
# Options:
#   --env-file PATH  Load custom environment file (overrides .env and .env.local)
#   --dry-run        Show configuration without starting services

# Strict error handling (no -e to allow partial failures)
set -uo pipefail

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
export PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load libraries
source "${SCRIPT_DIR}/unified-lib/common.sh"
source "${SCRIPT_DIR}/unified-lib/process-manager.sh"
source "${SCRIPT_DIR}/unified-lib/error-catalog.sh"
source "${SCRIPT_DIR}/unified-lib/health-check.sh"
source "${SCRIPT_DIR}/unified-lib/worktree-utils.sh"
source "${SCRIPT_DIR}/unified-lib/port-manager.sh"
source "${SCRIPT_DIR}/lib/env-loader.sh"

# Global state for rollback (compatible with bash 3.2+)
STARTED_SERVICES=()
ROLLBACK_IN_PROGRESS=false
FORCE_MODE=false
WORKTREE_OVERRIDE=""  # Override worktree index for --worktree option

# Service definitions (using environment variables for ports)
# Format: "service_name:port:directory:start_command"
# Port numbers are read from environment variables set by env-loader.sh
# Fallback to default ports if environment variables are not set

# Initialize service arrays (will be populated after environment is loaded)
LAYER1_SERVICES=()
LAYER2_SERVICES=()
LAYER3_SERVICES=()

# Build service definitions from environment variables
# This function must be called AFTER load_env_files()
build_service_definitions() {
    # Layer 1: Infrastructure services
    LAYER1_SERVICES=(
        "myvault:${MYVAULT_PORT:-8003}:${PROJECT_ROOT}/myVault:uv run uvicorn app.main:app --host 0.0.0.0 --port ${MYVAULT_PORT:-8003}"
        "jobqueue:${JOBQUEUE_PORT:-8001}:${PROJECT_ROOT}/jobqueue:uv run uvicorn app.main:app --host 0.0.0.0 --port ${JOBQUEUE_PORT:-8001}"
    )

    # Layer 2: Middleware services
    LAYER2_SERVICES=(
        "myscheduler:${MYSCHEDULER_PORT:-8002}:${PROJECT_ROOT}/myscheduler:uv run uvicorn app.main:app --host 0.0.0.0 --port ${MYSCHEDULER_PORT:-8002}"
        "graphaiserver:${GRAPHAI_PORT:-8005}:${PROJECT_ROOT}/graphAiServer:PORT=${GRAPHAI_PORT:-8005} npm run dev"
    )

    # Layer 3: Application services
    LAYER3_SERVICES=(
        "expertagent:${EXPERTAGENT_PORT:-8004}:${PROJECT_ROOT}/expertAgent:uv run uvicorn app.main:app --host 0.0.0.0 --port ${EXPERTAGENT_PORT:-8004}"
        "myagentdesk:${VITE_PORT:-5173}:${PROJECT_ROOT}/myAgentDesk:npm run dev -- --host 0.0.0.0 --port ${VITE_PORT:-5173}"
        "commonui:8501:${PROJECT_ROOT}/commonUI:uv run streamlit run Home.py --server.port 8501"
    )
}

# All services list (for status and stop commands)
ALL_SERVICES=(
    "myvault" "jobqueue"
    "myscheduler" "graphaiserver"
    "expertagent" "myagentdesk" "commonui"
)

# Health check timeout (can be overridden via --timeout option)
HEALTH_CHECK_TIMEOUT=30

# Rollback function - stops all started services
rollback_services() {
    # Prevent recursive calls
    if [[ "$ROLLBACK_IN_PROGRESS" == "true" ]]; then
        return 0
    fi

    ROLLBACK_IN_PROGRESS=true

    if [[ ${#STARTED_SERVICES[@]} -eq 0 ]]; then
        print_info "No services to rollback"
        return 0
    fi

    echo ""
    print_warning "═══════════════════════════════════════════════════════════"
    print_warning "  ROLLBACK: Stopping ${#STARTED_SERVICES[@]} started service(s)"
    print_warning "═══════════════════════════════════════════════════════════"
    echo ""

    # Stop services in reverse order
    local i
    for ((i=${#STARTED_SERVICES[@]}-1; i>=0; i--)); do
        local service_name="${STARTED_SERVICES[$i]}"
        print_service "$service_name" "Rolling back..."
        stop_service "$service_name" || true
    done

    # Clear the list
    STARTED_SERVICES=()

    echo ""
    print_success "Rollback completed - all started services stopped"
    echo ""
}

# Error handler - called on script error or interruption
error_handler() {
    local exit_code=$?
    local line_number="${1:-unknown}"

    # Ignore exit code 0
    if [[ $exit_code -eq 0 ]]; then
        return 0
    fi

    echo ""
    print_error "═══════════════════════════════════════════════════════════"
    print_error "  ERROR DETECTED - Initiating rollback"
    print_error "═══════════════════════════════════════════════════════════"

    if [[ "$line_number" != "unknown" ]]; then
        print_error "Failed at line: ${line_number}"
    fi

    # Execute rollback
    rollback_services

    # Show error report based on exit code
    if [[ $exit_code -eq $EXIT_USER_INTERRUPTED ]]; then
        show_error_report "$EXIT_USER_INTERRUPTED"
    else
        show_error_report "$EXIT_PARTIAL_STARTUP_FAILED" "Startup interrupted with exit code: ${exit_code}"
    fi

    exit "$EXIT_PARTIAL_STARTUP_FAILED"
}

# Interrupt handler - called on SIGINT or SIGTERM
interrupt_handler() {
    echo ""
    print_warning "═══════════════════════════════════════════════════════════"
    print_warning "  INTERRUPTED - Cleaning up started services"
    print_warning "═══════════════════════════════════════════════════════════"

    rollback_services

    show_error_report "$EXIT_USER_INTERRUPTED"
    exit "$EXIT_USER_INTERRUPTED"
}

# Set up traps for error handling
trap 'error_handler $LINENO' ERR
trap 'interrupt_handler' INT TERM

# Show help
show_help() {
    cat << EOF
MySwiftAgent Unified Start Script

USAGE:
    ./scripts/unified-start.sh <command> [options]

COMMANDS:
    start [--force]    Start all microservices in dependency order
    stop               Stop all microservices
    restart            Restart all microservices
    status             Check status of all microservices
    health             Check health of all running services
    --help             Show this help message

OPTIONS:
    --worktree INDEX   Operate on specific worktree by index (e.g., --worktree 2)
    --force            Force start by killing any processes on required ports
    --timeout N        Set health check timeout in seconds (default: 30)
    --health-check-only  Only perform health checks without starting services
    --skip-health-check  Skip health checks after starting services
    --env-file PATH    Load custom environment file (overrides .env and .env.local)
    --dry-run          Show configuration without starting services (use with 'start')

DESCRIPTION:
    This script manages the lifecycle of all MySwiftAgent microservices:

    Layer 1 (Infrastructure):
        - myVault       (Port 8003) : Secrets management service
        - jobqueue      (Port 8001) : Job queue management API

    Layer 2 (Middleware):
        - myscheduler   (Port 8002) : Job scheduling service
        - graphAiServer (Port 8005) : Graph AI workflow service

    Layer 3 (Application):
        - expertAgent   (Port 8004) : AI agent service
        - myAgentDesk   (Port 5173) : Web interface
        - commonUI      (Port 8501) : Common UI components

EXAMPLES:
    # Start all services (loads .env and .env.local)
    ./scripts/unified-start.sh start

    # Start with custom environment file
    ./scripts/unified-start.sh start --env-file .env.production

    # Show configuration without starting (dry-run)
    ./scripts/unified-start.sh start --dry-run

    # Force start (kill conflicting processes)
    ./scripts/unified-start.sh start --force

    # Start services with custom health check timeout
    ./scripts/unified-start.sh start --timeout 60

    # Check service status
    ./scripts/unified-start.sh status

    # Check service health
    ./scripts/unified-start.sh health

    # Check health only (without starting)
    ./scripts/unified-start.sh --health-check-only

    # Operate on specific worktree (index 2)
    ./scripts/unified-start.sh status --worktree 2
    ./scripts/unified-start.sh start --worktree 2
    ./scripts/unified-start.sh stop --worktree 2

    # Stop all services
    ./scripts/unified-start.sh stop

    # Restart all services
    ./scripts/unified-start.sh restart

FILES:
    PID files: /tmp/myswiftagent/*.pid
    Log files: logs/*.log

EOF
}

# Start a layer of services
start_layer() {
    local layer_name="$1"
    shift
    local services=("$@")
    local failed_services=()

    print_step "Starting ${layer_name}..."

    for service_spec in "${services[@]}"; do
        # Parse service specification: name:port:directory:start_command
        IFS=':' read -r service_name port directory start_command <<< "$service_spec"

        if start_service "$service_name" "$directory" "$port" "$start_command"; then
            # Track successfully started service for rollback
            STARTED_SERVICES+=("$service_name")
        else
            failed_services+=("$service_name")
            # Trigger rollback on failure
            print_error "${service_name}: Failed to start - triggering rollback"
            rollback_services
            show_service_failure_details "$service_name"
            exit "$EXIT_SERVICE_START_FAILED"
        fi
    done

    if [[ ${#failed_services[@]} -eq 0 ]]; then
        print_success "${layer_name} started"
    else
        print_warning "${layer_name} started with failures: ${failed_services[*]}"
    fi
}

# Command: start
cmd_start() {
    local skip_health_check=false

    # Parse start-specific options
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --skip-health-check)
                skip_health_check=true
                shift
                ;;
            *)
                shift
                ;;
        esac
    done

    show_banner

    # Load environment variables
    print_step "Loading environment variables..."
    if ! load_env_files "$@"; then
        print_error "Failed to load environment variables"
        exit 1
    fi
    echo ""

    # Build service definitions from loaded environment variables
    build_service_definitions

    # If dry-run mode, exit after showing configuration
    if [[ "${DRY_RUN_MODE:-false}" == "true" ]]; then
        print_info "Dry-run mode: configuration displayed, exiting without starting services"
        exit 0
    fi

    # Check dependencies
    if ! check_dependencies; then
        show_error_report "$EXIT_DEPENDENCY_ERROR"
        exit "$EXIT_DEPENDENCY_ERROR"
    fi

    # Initialize directories
    init_directories

    # Clean up stale PID files before starting
    cleanup_stale_pids
    echo ""

    print_step "Starting all services in dependency order..."
    echo ""

    local all_failed_services=()

    # Start Layer 1: Infrastructure services
    start_layer "Layer 1 (Infrastructure)" "${LAYER1_SERVICES[@]}"

    # Wait a moment for infrastructure to be ready
    sleep 3

    # Start Layer 2: Middleware services
    start_layer "Layer 2 (Middleware)" "${LAYER2_SERVICES[@]}"

    # Wait a moment for middleware to be ready
    sleep 3

    # Start Layer 3: Application services
    start_layer "Layer 3 (Application)" "${LAYER3_SERVICES[@]}"

    echo ""
    # Check if any services failed by examining status
    local running_count=0
    local stopped_count=0
    for service_name in "${ALL_SERVICES[@]}"; do
        if is_service_running "$service_name"; then
            ((running_count++))
        else
            ((stopped_count++))
        fi
    done

    if [[ $stopped_count -eq 0 ]]; then
        print_success "All services started successfully"
    else
        print_warning "Startup completed with ${stopped_count} service(s) failed"
    fi

    # Perform health checks unless skipped
    if [[ "$skip_health_check" == false ]]; then
        echo ""
        print_step "Running health checks (timeout: ${HEALTH_CHECK_TIMEOUT}s)..."
        echo ""

        # Prepare service specs for health check
        local service_specs=()
        for service_spec in "${LAYER1_SERVICES[@]}" "${LAYER2_SERVICES[@]}" "${LAYER3_SERVICES[@]}"; do
            IFS=':' read -r service_name port directory start_command <<< "$service_spec"
            # Only check services that have HTTP health endpoints
            # Skip commonui as it doesn't have a /health endpoint
            if [[ "$service_name" != "commonui" && "$service_name" != "myagentdesk" ]]; then
                service_specs+=("${service_name}:${port}")
            fi
        done

        if wait_for_all_services_healthy "$HEALTH_CHECK_TIMEOUT" "${service_specs[@]}"; then
            print_success "All services are healthy"
        else
            print_warning "Some services failed health checks"
        fi
    fi

    echo ""
    print_info "Use './scripts/unified-start.sh status' to check service status"
    print_info "Use './scripts/unified-start.sh health' to check service health"
    print_info "Use './scripts/unified-start.sh stop' to stop all services"
}

# Command: stop
cmd_stop() {
    print_step "Stopping all services..."
    echo ""

    stop_all_services "${ALL_SERVICES[@]}"

    echo ""
    print_success "All services stopped"
}

# Command: restart
cmd_restart() {
    print_step "Restarting all services..."
    echo ""

    # Stop all services
    cmd_stop

    # Wait a moment
    sleep 2

    # Start all services
    cmd_start
}

# Command: status
cmd_status() {
    # Override .env.local path if --worktree is specified
    if [[ -n "${WORKTREE_OVERRIDE:-}" ]]; then
        # Find worktree directory with the specified index
        local target_worktree_dir=""
        local current_dir=$(pwd)
        local worktrees_dir=$(dirname "$current_dir")

        for worktree in "$worktrees_dir"/*/; do
            if [[ -f "${worktree}.env.local" ]]; then
                local wt_index=$(grep "^WORKTREE_INDEX=" "${worktree}.env.local" 2>/dev/null | cut -d'=' -f2)
                if [[ "$wt_index" == "$WORKTREE_OVERRIDE" ]]; then
                    target_worktree_dir="$worktree"
                    break
                fi
            fi
        done

        if [[ -n "$target_worktree_dir" ]]; then
            # Load environment from target worktree
            LOCAL_ENV_FILE="${target_worktree_dir}.env.local"
            load_env_files > /dev/null 2>&1 || true
        else
            print_warning "Worktree with index $WORKTREE_OVERRIDE not found"
            return 1
        fi
    else
        # Load environment variables (silent mode)
        load_env_files > /dev/null 2>&1 || true
    fi

    # Build service definitions
    build_service_definitions

    # Show worktree information if in a worktree
    if is_worktree; then
        echo ""
        echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║${NC}                    ${WHITE}Worktree Information${NC}                           ${CYAN}║${NC}"
        echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════╝${NC}"
        echo ""

        local worktree_name
        local worktree_index
        local main_repo
        worktree_name=$(get_worktree_name)
        worktree_index=$(get_current_worktree_index)
        main_repo=$(get_main_repo_path)

        echo -e "  ${BLUE}Worktree Name:${NC}    $worktree_name"
        echo -e "  ${BLUE}Worktree Index:${NC}   $worktree_index"
        echo -e "  ${BLUE}Main Repository:${NC}  $main_repo"
        echo ""

        # Show port assignments
        echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║${NC}                    ${WHITE}Port Assignments${NC}                              ${CYAN}║${NC}"
        echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        get_port_status_summary
        echo ""
    fi

    # Prepare service specs for status check
    local service_specs=()

    # Add Layer 1
    for service_spec in "${LAYER1_SERVICES[@]}"; do
        # Parse: name:port:directory:start_command
        IFS=':' read -r service_name port directory start_command <<< "$service_spec"
        service_specs+=("${service_name}:${port}")
    done

    # Add Layer 2
    for service_spec in "${LAYER2_SERVICES[@]}"; do
        IFS=':' read -r service_name port directory start_command <<< "$service_spec"
        service_specs+=("${service_name}:${port}")
    done

    # Add Layer 3
    for service_spec in "${LAYER3_SERVICES[@]}"; do
        IFS=':' read -r service_name port directory start_command <<< "$service_spec"
        service_specs+=("${service_name}:${port}")
    done

    check_all_services_status "${service_specs[@]}"
}

# Command: health
cmd_health() {
    # Load environment variables (silent mode)
    load_env_files > /dev/null 2>&1 || true

    # Build service definitions
    build_service_definitions

    # Prepare service specs for health check
    local service_specs=()

    for service_spec in "${LAYER1_SERVICES[@]}" "${LAYER2_SERVICES[@]}" "${LAYER3_SERVICES[@]}"; do
        IFS=':' read -r service_name port directory start_command <<< "$service_spec"
        # Only check services that have HTTP health endpoints
        # Skip commonui as it doesn't have a /health endpoint
        if [[ "$service_name" != "commonui" && "$service_name" != "myagentdesk" ]]; then
            service_specs+=("${service_name}:${port}")
        fi
    done

    if check_all_services_health "${service_specs[@]}"; then
        print_success "All services passed health checks"
        return 0
    else
        print_error "Some services failed health checks"
        return 1
    fi
}

# Main entry point
main() {
    # Parse global options first
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --timeout)
                HEALTH_CHECK_TIMEOUT="$2"
                shift 2
                ;;
            --health-check-only)
                cmd_health
                exit $?
                ;;
            --help|-h|help)
                show_help
                exit 0
                ;;
            start|stop|restart|status|health)
                local command="$1"
                shift

                # Parse command-specific options
                while [[ $# -gt 0 ]]; do
                    case "$1" in
                        --worktree)
                            WORKTREE_OVERRIDE="$2"
                            export WORKTREE_OVERRIDE
                            shift 2
                            ;;
                        --force)
                            FORCE_MODE=true
                            shift
                            ;;
                        --skip-health-check)
                            shift
                            # Pass to command if needed
                            ;;
                        --env-file|--dry-run)
                            # Keep env-related options for cmd_start
                            break
                            ;;
                        *)
                            break
                            ;;
                    esac
                done

                case "$command" in
                    start)
                        cmd_start "$@"
                        ;;
                    stop)
                        cmd_stop
                        ;;
                    restart)
                        # Load env for restart as well
                        print_step "Loading environment variables..."
                        if ! load_env_files "$@"; then
                            print_error "Failed to load environment variables"
                            exit 1
                        fi
                        echo ""
                        cmd_restart
                        ;;
                    status)
                        cmd_status
                        ;;
                    health)
                        cmd_health
                        ;;
                esac
                return $?
                ;;
            "")
                print_error "No command specified"
                echo ""
                show_help
                exit 1
                ;;
            *)
                print_error "Unknown option or command: $1"
                echo ""
                show_help
                exit 1
                ;;
        esac
    done

    # If we get here, no command was specified
    print_error "No command specified"
    echo ""
    show_help
    exit 1
}

# Run main
main "$@"
