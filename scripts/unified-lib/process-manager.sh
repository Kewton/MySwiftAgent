#!/bin/bash

# Process Manager Library for MySwiftAgent Unified Start Script
# Provides service lifecycle management functions

# Strict error handling (disabled for sourcing in tests)
# set -euo pipefail is disabled to allow this library to be sourced in test environments
# Individual functions handle their own errors appropriately

# Source common library if not already loaded
if [[ -z "${PROJECT_ROOT:-}" ]]; then
    UNIFIED_LIB_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    source "${UNIFIED_LIB_DIR}/common.sh"
fi

# Check if a service is running by PID file
is_service_running() {
    local service_name="$1"
    local pid_file="${PID_DIR}/${service_name}.pid"

    if [[ ! -f "$pid_file" ]]; then
        return 1
    fi

    local pid
    pid=$(cat "$pid_file")

    if kill -0 "$pid" 2>/dev/null; then
        return 0
    else
        # PID file exists but process is not running - clean up
        rm -f "$pid_file"
        return 1
    fi
}

# Get service PID
get_service_pid() {
    local service_name="$1"
    local pid_file="${PID_DIR}/${service_name}.pid"

    if [[ -f "$pid_file" ]]; then
        cat "$pid_file"
    else
        echo ""
    fi
}

# Check if port is in use
check_port() {
    local port="$1"
    if lsof -Pi :"$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Get detailed port conflict information
get_port_conflict_info() {
    local port="$1"

    if ! check_port "$port"; then
        return 1
    fi

    local pids
    pids=$(lsof -ti:"$port" -sTCP:LISTEN 2>/dev/null || echo "")

    if [[ -z "$pids" ]]; then
        return 1
    fi

    for pid in $pids; do
        local cmd user
        cmd=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
        user=$(ps -p "$pid" -o user= 2>/dev/null || echo "unknown")

        echo "PID:$pid|CMD:$cmd|USER:$user"
    done
}

# Kill process on port
kill_port() {
    local port="$1"
    local service_name="$2"
    local force_mode="${3:-false}"

    if check_port "$port"; then
        local conflict_info
        conflict_info=$(get_port_conflict_info "$port")

        if [[ -n "$conflict_info" ]]; then
            print_warning "${service_name}: Port ${port} is in use"

            # Show detailed conflict information
            while IFS='|' read -r pid_info cmd_info user_info; do
                local pid="${pid_info#PID:}"
                local cmd="${cmd_info#CMD:}"
                local user="${user_info#USER:}"

                echo -e "  ${YELLOW}Conflicting process:${NC}"
                echo -e "    ${WHITE}PID:${NC}     $pid"
                echo -e "    ${WHITE}Command:${NC} $cmd"
                echo -e "    ${WHITE}User:${NC}    $user"
            done <<< "$conflict_info"

            if [[ "$force_mode" == "true" ]]; then
                print_info "${service_name}: Force mode enabled - killing process(es) on port ${port}..."
                local pid
                pid=$(lsof -ti:"$port" -sTCP:LISTEN)
                kill -9 $pid 2>/dev/null || true
                sleep 1

                # Verify port is free
                if check_port "$port"; then
                    print_error "${service_name}: Failed to free port ${port}"
                    return 1
                else
                    print_success "${service_name}: Port ${port} freed"
                fi
            else
                print_error "${service_name}: Port ${port} is in use. Use --force to kill conflicting processes"
                # Show error from catalog if available
                if declare -f show_port_conflict_details &>/dev/null; then
                    show_port_conflict_details "$port" "$service_name"
                fi
                return 1
            fi
        fi
    fi

    return 0
}

# Start a service
start_service() {
    local service_name="$1"
    local service_dir="$2"
    local port="$3"
    local start_command="$4"
    local log_file="${LOG_DIR}/${service_name}.log"
    local pid_file="${PID_DIR}/${service_name}.pid"

    print_service "$service_name" "Starting service on port ${port}..."

    # Check if already running
    if is_service_running "$service_name"; then
        local pid
        pid=$(get_service_pid "$service_name")
        print_warning "${service_name}: Already running (PID: ${pid})"
        return 0
    fi

    # Kill any process on the port (pass FORCE_MODE)
    if ! kill_port "$port" "$service_name" "${FORCE_MODE:-false}"; then
        return 1
    fi

    # Check if service directory exists
    if [[ ! -d "$service_dir" ]]; then
        print_error "${service_name}: Directory not found: ${service_dir}"
        return 1
    fi

    # Change to service directory
    cd "$service_dir" || {
        print_error "${service_name}: Cannot change to directory ${service_dir}"
        return 1
    }

    # Clear log file
    > "$log_file"

    # Start the service in background with nohup
    print_info "${service_name}: Executing: ${start_command}"
    nohup bash -c "$start_command" > "$log_file" 2>&1 &
    local service_pid=$!

    # Save PID
    echo "$service_pid" > "$pid_file"

    # Wait a moment for the service to start
    sleep 2

    # Verify service is still running
    if kill -0 "$service_pid" 2>/dev/null; then
        print_success "${service_name}: Started successfully (PID: ${service_pid}, Port: ${port})"
        return 0
    else
        print_error "${service_name}: Failed to start (process died immediately)"
        rm -f "$pid_file"
        return 1
    fi
}

# Stop a service
stop_service() {
    local service_name="$1"
    local pid_file="${PID_DIR}/${service_name}.pid"

    if [[ ! -f "$pid_file" ]]; then
        print_info "${service_name}: Not running (no PID file)"
        return 0
    fi

    local pid
    pid=$(cat "$pid_file")

    if ! kill -0 "$pid" 2>/dev/null; then
        print_info "${service_name}: Process not running (stale PID file)"
        rm -f "$pid_file"
        return 0
    fi

    print_service "$service_name" "Stopping service (PID: ${pid})..."

    # Send SIGTERM for graceful shutdown
    kill -TERM "$pid" 2>/dev/null || true

    # Wait for graceful shutdown (max 10 seconds)
    local attempts=0
    while kill -0 "$pid" 2>/dev/null && [[ $attempts -lt 10 ]]; do
        sleep 1
        ((attempts++))
    done

    # Force kill if still running
    if kill -0 "$pid" 2>/dev/null; then
        print_warning "${service_name}: Force stopping (SIGKILL)..."
        kill -KILL "$pid" 2>/dev/null || true
        sleep 1
    fi

    # Remove PID file
    rm -f "$pid_file"

    print_success "${service_name}: Stopped"
    return 0
}

# Restart a service
restart_service() {
    local service_name="$1"
    local service_dir="$2"
    local port="$3"
    local start_command="$4"

    print_service "$service_name" "Restarting service..."

    # Stop the service
    stop_service "$service_name"

    # Wait a moment before restarting
    sleep 2

    # Start the service
    start_service "$service_name" "$service_dir" "$port" "$start_command"
}

# Check service status
check_service_status() {
    local service_name="$1"
    local port="$2"
    local pid_file="${PID_DIR}/${service_name}.pid"

    if [[ ! -f "$pid_file" ]]; then
        echo -e "${RED}  ${service_name}: Not running${NC}"
        return 1
    fi

    local pid
    pid=$(cat "$pid_file")

    if kill -0 "$pid" 2>/dev/null; then
        if check_port "$port"; then
            echo -e "${GREEN}  ${service_name}: Running (PID: ${pid}, Port: ${port})${NC}"
            return 0
        else
            echo -e "${YELLOW}  ${service_name}: Running but port ${port} not responding (PID: ${pid})${NC}"
            return 2
        fi
    else
        echo -e "${RED}  ${service_name}: Not running (stale PID: ${pid})${NC}"
        rm -f "$pid_file"
        return 1
    fi
}

# Wait for service to be ready (basic check - just verify process is alive)
wait_for_service() {
    local service_name="$1"
    local max_wait="${2:-30}"
    local wait_time=0

    while [[ $wait_time -lt $max_wait ]]; do
        if is_service_running "$service_name"; then
            return 0
        fi
        sleep 1
        ((wait_time++))
    done

    print_error "${service_name}: Timeout waiting for service to start"
    return 1
}

# Stop all services
stop_all_services() {
    local services=("$@")

    # Stop in reverse order
    local i
    for ((i=${#services[@]}-1; i>=0; i--)); do
        local service_name="${services[$i]}"
        stop_service "$service_name"
    done
}

# Check status of all services
check_all_services_status() {
    local services=("$@")

    print_step "Checking service status..."
    echo ""

    local running_count=0
    local stopped_count=0

    local service_name port
    for service_spec in "${services[@]}"; do
        IFS=':' read -r service_name port <<< "$service_spec"
        if check_service_status "$service_name" "$port"; then
            ((running_count++))
        else
            ((stopped_count++))
        fi
    done

    echo ""
    echo -e "${WHITE}Summary: ${running_count} running, ${stopped_count} stopped${NC}"
}

# Export functions
export -f is_service_running
export -f get_service_pid
export -f check_port
export -f get_port_conflict_info
export -f kill_port
export -f start_service
export -f stop_service
export -f restart_service
export -f check_service_status
export -f wait_for_service
export -f stop_all_services
export -f check_all_services_status
