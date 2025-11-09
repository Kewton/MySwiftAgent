#!/bin/bash

# Port Manager Library for MySwiftAgent
# Provides port calculation and availability checking functions

# Strict error handling (disabled for sourcing in tests)
# Individual functions handle their own errors appropriately

# Default base ports for each service
readonly DEFAULT_BASE_EXPERTAGENT=8104
readonly DEFAULT_BASE_MYVAULT=8103
readonly DEFAULT_BASE_MYSCHEDULER=8102
readonly DEFAULT_BASE_JOBQUEUE=8101
readonly DEFAULT_BASE_GRAPHAI=8100
readonly DEFAULT_BASE_VITE=5173

# Port offset multiplier (base_port + index * multiplier)
readonly PORT_OFFSET_MULTIPLIER=10

# Calculate port number based on service and worktree index
# Args: $1 = service_name, $2 = worktree_index
# Returns: calculated port number
calculate_port() {
    local service_name="$1"
    local worktree_index="${2:-0}"

    # Validate worktree_index is a number
    if ! [[ "$worktree_index" =~ ^[0-9]+$ ]]; then
        echo "Error: worktree_index must be a number" >&2
        return 1
    fi

    local base_port
    case "$service_name" in
        expertagent|expertAgent)
            base_port=$DEFAULT_BASE_EXPERTAGENT
            ;;
        myvault|myVault)
            base_port=$DEFAULT_BASE_MYVAULT
            ;;
        myscheduler|myScheduler)
            base_port=$DEFAULT_BASE_MYSCHEDULER
            ;;
        jobqueue|jobQueue)
            base_port=$DEFAULT_BASE_JOBQUEUE
            ;;
        graphai|graphAiServer)
            base_port=$DEFAULT_BASE_GRAPHAI
            ;;
        vite|myAgentDesk)
            # Vite uses +1 instead of +10
            echo $((DEFAULT_BASE_VITE + worktree_index))
            return 0
            ;;
        *)
            echo "Error: unknown service name: $service_name" >&2
            return 1
            ;;
    esac

    echo $((base_port + (worktree_index * PORT_OFFSET_MULTIPLIER)))
}

# Check if a port is in use
# Args: $1 = port_number
# Returns: 0 if port is in use, 1 if available
is_port_in_use() {
    local port="$1"

    # Validate port is a number
    if ! [[ "$port" =~ ^[0-9]+$ ]]; then
        echo "Error: port must be a number" >&2
        return 2
    fi

    # Check using lsof (macOS/Linux compatible)
    if command -v lsof &> /dev/null; then
        lsof -i ":$port" -sTCP:LISTEN -t >/dev/null 2>&1
        return $?
    fi

    # Fallback: check using netstat (cross-platform)
    if command -v netstat &> /dev/null; then
        netstat -an | grep -q "[\\.:]$port .* LISTEN"
        return $?
    fi

    # If no tools available, assume port is available (conservative)
    echo "Warning: Neither lsof nor netstat available, cannot check port status" >&2
    return 1
}

# Find next available port starting from a given port
# Args: $1 = starting_port, $2 = max_attempts (default: 100)
# Returns: next available port number
find_available_port() {
    local start_port="$1"
    local max_attempts="${2:-100}"

    # Validate inputs
    if ! [[ "$start_port" =~ ^[0-9]+$ ]]; then
        echo "Error: start_port must be a number" >&2
        return 1
    fi

    local port=$start_port
    local attempts=0

    while [[ $attempts -lt $max_attempts ]]; do
        if ! is_port_in_use "$port"; then
            echo "$port"
            return 0
        fi
        port=$((port + 1))
        attempts=$((attempts + 1))
    done

    echo "Error: no available port found after $max_attempts attempts" >&2
    return 1
}

# Get all ports for a worktree index
# Args: $1 = worktree_index
# Returns: JSON-like output with all service ports
get_all_ports_for_index() {
    local worktree_index="${1:-0}"

    local port_expertagent
    local port_myvault
    local port_myscheduler
    local port_jobqueue
    local port_graphai
    local port_vite

    port_expertagent=$(calculate_port "expertagent" "$worktree_index")
    port_myvault=$(calculate_port "myvault" "$worktree_index")
    port_myscheduler=$(calculate_port "myscheduler" "$worktree_index")
    port_jobqueue=$(calculate_port "jobqueue" "$worktree_index")
    port_graphai=$(calculate_port "graphai" "$worktree_index")
    port_vite=$(calculate_port "vite" "$worktree_index")

    cat <<EOF
{
  "worktree_index": $worktree_index,
  "ports": {
    "expertagent": $port_expertagent,
    "myvault": $port_myvault,
    "myscheduler": $port_myscheduler,
    "jobqueue": $port_jobqueue,
    "graphai": $port_graphai,
    "vite": $port_vite
  }
}
EOF
}

# Check port conflicts for a worktree index
# Args: $1 = worktree_index
# Returns: list of services with port conflicts
check_port_conflicts() {
    local worktree_index="${1:-0}"

    local conflicts=()
    local services=("expertagent" "myvault" "myscheduler" "jobqueue" "graphai" "vite")

    for service in "${services[@]}"; do
        local port
        port=$(calculate_port "$service" "$worktree_index")
        if is_port_in_use "$port"; then
            conflicts+=("$service:$port")
        fi
    done

    if [[ ${#conflicts[@]} -gt 0 ]]; then
        printf '%s\n' "${conflicts[@]}"
        return 1
    fi

    return 0
}

# Suggest alternative ports for conflicts
# Args: $1 = service_name, $2 = conflicted_port
# Returns: suggested alternative port
suggest_alternative_port() {
    local service_name="$1"
    local conflicted_port="$2"

    local alternative_port
    alternative_port=$(find_available_port "$conflicted_port")

    if [[ $? -eq 0 ]]; then
        echo "Suggestion for $service_name: use port $alternative_port instead of $conflicted_port"
    else
        echo "Error: could not find alternative port for $service_name" >&2
        return 1
    fi
}

# Get port status summary for current worktree
# Requires worktree-utils.sh to be sourced
# Returns: formatted status report
get_port_status_summary() {
    # Check if get_current_worktree_index is available
    if ! command -v get_current_worktree_index &> /dev/null; then
        echo "Error: worktree-utils.sh must be sourced first" >&2
        return 1
    fi

    local worktree_index
    worktree_index=$(get_current_worktree_index)

    echo "Port Status for Worktree Index: $worktree_index"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    local services=("expertagent" "myvault" "myscheduler" "jobqueue" "graphai" "vite")

    for service in "${services[@]}"; do
        local port
        port=$(calculate_port "$service" "$worktree_index")
        local status="Available"
        if is_port_in_use "$port"; then
            status="In Use"
        fi
        printf "  %-15s : %-6d (%s)\n" "$service" "$port" "$status"
    done
}

# Export functions for use in other scripts
export -f calculate_port
export -f is_port_in_use
export -f find_available_port
export -f get_all_ports_for_index
export -f check_port_conflicts
export -f suggest_alternative_port
export -f get_port_status_summary

# Export constants
export DEFAULT_BASE_EXPERTAGENT
export DEFAULT_BASE_MYVAULT
export DEFAULT_BASE_MYSCHEDULER
export DEFAULT_BASE_JOBQUEUE
export DEFAULT_BASE_GRAPHAI
export DEFAULT_BASE_VITE
export PORT_OFFSET_MULTIPLIER
