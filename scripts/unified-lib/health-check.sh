#!/bin/bash

# Health Check Library for MySwiftAgent Unified Start Script
# Provides health checking and service readiness verification functions

# Strict error handling
set -euo pipefail

# Source common library if not already loaded
if [[ -z "${PROJECT_ROOT:-}" ]]; then
    UNIFIED_LIB_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    source "${UNIFIED_LIB_DIR}/common.sh"
fi

# Default timeout for health checks (seconds)
readonly DEFAULT_HEALTH_CHECK_TIMEOUT=30
readonly DEFAULT_HEALTH_CHECK_INTERVAL=1

# Health check a single service via HTTP endpoint
# Args: service_name, port, [timeout], [endpoint]
# Returns: 0 if healthy, 1 otherwise
check_service_health() {
    local service_name="$1"
    local port="$2"
    local timeout="${3:-5}"
    local endpoint="${4:-/health}"
    local url="http://localhost:${port}${endpoint}"

    # Check if service has an HTTP endpoint (some services might not)
    if ! command_exists curl; then
        print_warning "${service_name}: curl not available, skipping HTTP health check"
        return 0
    fi

    # Try to reach the health endpoint
    local status_code
    status_code=$(curl -s -o /dev/null -w '%{http_code}' \
        --connect-timeout "$timeout" \
        --max-time "$timeout" \
        "$url" 2>/dev/null || echo "000")

    if [[ "$status_code" == "200" ]]; then
        return 0
    else
        return 1
    fi
}

# Get HTTP response time from service
# Args: service_name, port, [timeout], [endpoint]
# Returns: response time in seconds or "timeout"
get_response_time() {
    local service_name="$1"
    local port="$2"
    local timeout="${3:-5}"
    local endpoint="${4:-/health}"
    local url="http://localhost:${port}${endpoint}"

    local response_time
    response_time=$(curl -w '%{time_total}' -s \
        --connect-timeout "$timeout" \
        --max-time "$timeout" \
        "$url" -o /dev/null 2>/dev/null || echo "timeout")

    echo "$response_time"
}

# Get health status information from service
# Args: service_name, port, [timeout], [endpoint]
# Returns: JSON response or empty string
get_health_info() {
    local service_name="$1"
    local port="$2"
    local timeout="${3:-5}"
    local endpoint="${4:-/health}"
    local url="http://localhost:${port}${endpoint}"

    local health_info
    health_info=$(curl -s \
        --connect-timeout "$timeout" \
        --max-time "$timeout" \
        "$url" 2>/dev/null || echo "{}")

    echo "$health_info"
}

# Wait for a service to become healthy
# Args: service_name, port, [max_wait_seconds], [endpoint]
# Returns: 0 if service becomes healthy, 1 on timeout
wait_for_healthy() {
    local service_name="$1"
    local port="$2"
    local max_wait="${3:-$DEFAULT_HEALTH_CHECK_TIMEOUT}"
    local endpoint="${4:-/health}"
    local wait_time=0
    local interval=$DEFAULT_HEALTH_CHECK_INTERVAL

    print_info "${service_name}: Waiting for service to become healthy (max ${max_wait}s)..."

    while [[ $wait_time -lt $max_wait ]]; do
        if check_service_health "$service_name" "$port" 2 "$endpoint"; then
            local response_time
            response_time=$(get_response_time "$service_name" "$port" 2 "$endpoint")
            print_success "${service_name}: Service is healthy (${response_time}s response time)"
            return 0
        fi

        sleep "$interval"
        ((wait_time += interval))

        # Show progress every 5 seconds
        if (( wait_time % 5 == 0 )); then
            print_info "${service_name}: Still waiting... (${wait_time}s / ${max_wait}s)"
        fi
    done

    print_error "${service_name}: Timeout waiting for service to become healthy"
    return 1
}

# Check health status with detailed output
# Args: service_name, port, [timeout], [endpoint]
# Returns: 0 if healthy, 1 otherwise
check_health_detailed() {
    local service_name="$1"
    local port="$2"
    local timeout="${3:-5}"
    local endpoint="${4:-/health}"

    print_step "Checking ${service_name} health..."

    # Check if service is running via PID
    if ! is_service_running "$service_name"; then
        print_error "${service_name}: Process not running"
        return 1
    fi

    local pid
    pid=$(get_service_pid "$service_name")
    print_info "${service_name}: Process running (PID: ${pid})"

    # Check if port is listening
    if ! check_port "$port"; then
        print_error "${service_name}: Port ${port} not listening"
        return 1
    fi
    print_info "${service_name}: Port ${port} is listening"

    # Check HTTP health endpoint
    if check_service_health "$service_name" "$port" "$timeout" "$endpoint"; then
        local response_time
        response_time=$(get_response_time "$service_name" "$port" "$timeout" "$endpoint")
        print_success "${service_name}: Health endpoint responding (${response_time}s)"

        # Try to get and parse health info if jq is available
        if command_exists jq; then
            local health_info
            health_info=$(get_health_info "$service_name" "$port" "$timeout" "$endpoint")

            if echo "$health_info" | jq empty >/dev/null 2>&1; then
                local service_status
                service_status=$(echo "$health_info" | jq -r '.status // "unknown"')
                print_info "${service_name}: Service status: ${service_status}"
            fi
        fi

        return 0
    else
        print_error "${service_name}: Health endpoint not responding"
        return 1
    fi
}

# Check health of all services
# Args: Array of service specifications "service_name:port:endpoint" or "service_name:port"
# Returns: Number of failed health checks
check_all_services_health() {
    local services=("$@")
    local failed_count=0
    local total_count=${#services[@]}

    print_step "Running health checks for ${total_count} services..."
    echo ""

    local service_name port endpoint
    for service_spec in "${services[@]}"; do
        # Parse: service_name:port[:endpoint]
        IFS=':' read -r service_name port endpoint <<< "$service_spec"
        endpoint="${endpoint:-/health}"

        if check_health_detailed "$service_name" "$port" 5 "$endpoint"; then
            echo ""
        else
            ((failed_count++))
            echo ""
        fi
    done

    # Summary
    local passed_count=$((total_count - failed_count))
    echo -e "${WHITE}Health Check Summary:${NC}"
    echo -e "  ${GREEN}✅ Passed: ${passed_count}${NC}"
    if [[ $failed_count -gt 0 ]]; then
        echo -e "  ${RED}❌ Failed: ${failed_count}${NC}"
    fi
    echo ""

    return "$failed_count"
}

# Wait for all services to become healthy
# Args: Array of service specifications "service_name:port:endpoint" or "service_name:port"
# Optional: timeout (default: DEFAULT_HEALTH_CHECK_TIMEOUT)
# Returns: Number of services that failed to become healthy
wait_for_all_services_healthy() {
    local timeout="${1:-$DEFAULT_HEALTH_CHECK_TIMEOUT}"
    shift
    local services=("$@")
    local failed_count=0
    local total_count=${#services[@]}

    print_step "Waiting for ${total_count} services to become healthy (timeout: ${timeout}s)..."
    echo ""

    local service_name port endpoint
    for service_spec in "${services[@]}"; do
        # Parse: service_name:port[:endpoint]
        IFS=':' read -r service_name port endpoint <<< "$service_spec"
        endpoint="${endpoint:-/health}"

        if ! wait_for_healthy "$service_name" "$port" "$timeout" "$endpoint"; then
            ((failed_count++))
        fi
        echo ""
    done

    # Summary
    local passed_count=$((total_count - failed_count))
    echo -e "${WHITE}Health Wait Summary:${NC}"
    echo -e "  ${GREEN}✅ Ready: ${passed_count}${NC}"
    if [[ $failed_count -gt 0 ]]; then
        echo -e "  ${RED}❌ Not Ready: ${failed_count}${NC}"
    fi
    echo ""

    return "$failed_count"
}

# Quick health check (just HTTP status, no details)
# Args: service_name, port, [endpoint]
# Returns: 0 if healthy, 1 otherwise
quick_health_check() {
    local service_name="$1"
    local port="$2"
    local endpoint="${3:-/health}"

    if check_service_health "$service_name" "$port" 2 "$endpoint"; then
        echo -e "${GREEN}  ✅ ${service_name}: Healthy${NC}"
        return 0
    else
        echo -e "${RED}  ❌ ${service_name}: Unhealthy${NC}"
        return 1
    fi
}

# Export functions
export -f check_service_health
export -f get_response_time
export -f get_health_info
export -f wait_for_healthy
export -f check_health_detailed
export -f check_all_services_health
export -f wait_for_all_services_healthy
export -f quick_health_check

# Export constants
export DEFAULT_HEALTH_CHECK_TIMEOUT
export DEFAULT_HEALTH_CHECK_INTERVAL
