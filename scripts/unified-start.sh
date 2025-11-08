#!/bin/bash

# MySwiftAgent Unified Start Script
# Single command to start/stop/restart all microservices
#
# Usage:
#   ./scripts/unified-start.sh start   - Start all services
#   ./scripts/unified-start.sh stop    - Stop all services
#   ./scripts/unified-start.sh restart - Restart all services
#   ./scripts/unified-start.sh status  - Check service status
#   ./scripts/unified-start.sh --help  - Show help

# Strict error handling (no -e to allow partial failures)
set -uo pipefail

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
export PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load libraries
source "${SCRIPT_DIR}/unified-lib/common.sh"
source "${SCRIPT_DIR}/unified-lib/process-manager.sh"
source "${SCRIPT_DIR}/unified-lib/health-check.sh"

# Service definitions (hardcoded for Phase 1)
# Format: "service_name:port:directory:start_command"

# Layer 1: Infrastructure services
LAYER1_SERVICES=(
    "myvault:8003:${PROJECT_ROOT}/myVault:uv run uvicorn app.main:app --host 0.0.0.0 --port 8003"
    "jobqueue:8001:${PROJECT_ROOT}/jobqueue:uv run uvicorn app.main:app --host 0.0.0.0 --port 8001"
)

# Layer 2: Middleware services
LAYER2_SERVICES=(
    "myscheduler:8002:${PROJECT_ROOT}/myscheduler:uv run uvicorn app.main:app --host 0.0.0.0 --port 8002"
    "graphaiserver:8005:${PROJECT_ROOT}/graphAiServer:PORT=8005 npm run dev"
)

# Layer 3: Application services
LAYER3_SERVICES=(
    "expertagent:8004:${PROJECT_ROOT}/expertAgent:uv run uvicorn app.main:app --host 0.0.0.0 --port 8004"
    "myagentdesk:5173:${PROJECT_ROOT}/myAgentDesk:npm run dev -- --host 0.0.0.0 --port 5173"
    "commonui:8501:${PROJECT_ROOT}/commonUI:uv run streamlit run Home.py --server.port 8501"
)

# All services list (for status and stop commands)
ALL_SERVICES=(
    "myvault" "jobqueue"
    "myscheduler" "graphaiserver"
    "expertagent" "myagentdesk" "commonui"
)

# Health check timeout (can be overridden via --timeout option)
HEALTH_CHECK_TIMEOUT=30

# Show help
show_help() {
    cat << EOF
MySwiftAgent Unified Start Script

USAGE:
    ./scripts/unified-start.sh <command> [options]

COMMANDS:
    start              Start all microservices in dependency order
    stop               Stop all microservices
    restart            Restart all microservices
    status             Check status of all microservices
    health             Check health of all running services
    --help             Show this help message

OPTIONS:
    --timeout N        Set health check timeout in seconds (default: 30)
    --health-check-only  Only perform health checks without starting services
    --skip-health-check  Skip health checks after starting services

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
    # Start all services
    ./scripts/unified-start.sh start

    # Start services with custom health check timeout
    ./scripts/unified-start.sh start --timeout 60

    # Check service status
    ./scripts/unified-start.sh status

    # Check service health
    ./scripts/unified-start.sh health

    # Check health only (without starting)
    ./scripts/unified-start.sh --health-check-only

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

        if ! start_service "$service_name" "$directory" "$port" "$start_command"; then
            failed_services+=("$service_name")
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

    # Check dependencies
    if ! check_dependencies; then
        print_error "Please install missing dependencies and try again"
        exit 1
    fi

    # Initialize directories
    init_directories

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
                case "$command" in
                    start)
                        cmd_start "$@"
                        ;;
                    stop)
                        cmd_stop
                        ;;
                    restart)
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
