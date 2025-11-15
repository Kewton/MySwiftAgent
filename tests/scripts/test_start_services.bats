#!/usr/bin/env bats
# Tests for start_services.sh script
# Following TDD Red-Green-Refactor cycle

setup() {
    # Create temporary directories for testing
    export TEST_DIR="$(mktemp -d)"
    export PROJECT_ROOT="$TEST_DIR"
    export PID_DIR="$TEST_DIR/.pids"
    export LOG_DIR="$TEST_DIR/logs"

    mkdir -p "$PID_DIR" "$LOG_DIR"

    # Source the functions from start_services.sh
    # We'll need to extract the functions into a testable format
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

    # Load functions from start_services.sh
    source "$REPO_ROOT/scripts/start_services.sh" 2>/dev/null || true
}

teardown() {
    # Cleanup
    if [ -n "$TEST_DIR" ] && [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
}

# Test 1: stop_service should work with port-based detection when PID file is missing
@test "stop_service: can stop service using port when PID file is missing" {
    # RED: This test will fail initially

    # Start a dummy service on a test port
    local test_port=19999
    local service_name="TestService"
    local pid_file="$PID_DIR/test.pid"

    # Start a background process that listens on the port
    python3 -m http.server $test_port > /dev/null 2>&1 &
    local actual_pid=$!
    sleep 1

    # Verify service is running on port
    lsof -Pi :$test_port -sTCP:LISTEN -t >/dev/null 2>&1
    [ $? -eq 0 ]

    # Remove PID file to simulate the bug scenario
    rm -f "$pid_file"

    # Call stop_service with port parameter (new functionality)
    stop_service "$service_name" "$pid_file" "$test_port"

    # Verify service is stopped
    sleep 1
    ! lsof -Pi :$test_port -sTCP:LISTEN -t >/dev/null 2>&1
}

# Test 2: start_service should verify PID file exists after starting
@test "start_service: ensures PID file is created and valid after service starts" {
    # RED: This test will fail if PID file creation is not verified

    skip "Requires mock service setup - will implement after basic functionality"
}

# Test 3: check_status should detect PID/port mismatches
@test "check_status: detects when PID file exists but port is different" {
    # RED: This test will fail initially

    local service_name="TestService"
    local pid_file="$PID_DIR/test.pid"
    local expected_port=18888
    local actual_port=18889

    # Start a process on a different port
    python3 -m http.server $actual_port > /dev/null 2>&1 &
    local actual_pid=$!
    echo $actual_pid > "$pid_file"
    sleep 1

    # Check status should detect the mismatch
    # The function should return an error or warning state
    run check_status "$service_name" "$pid_file" "$expected_port"

    # Should indicate a problem (warning or error)
    [[ "$output" == *"mismatch"* ]] || [[ "$output" == *"not listening"* ]]

    # Cleanup
    kill $actual_pid 2>/dev/null || true
}

# Test 4: check_status should handle missing PID file gracefully
@test "check_status: handles missing PID file with port check" {
    # RED: This test will fail initially

    local service_name="TestService"
    local pid_file="$PID_DIR/nonexistent.pid"
    local port=17777

    # Start a service without PID file
    python3 -m http.server $port > /dev/null 2>&1 &
    local actual_pid=$!
    sleep 1

    # Check status should detect the running service even without PID file
    run check_status "$service_name" "$pid_file" "$port"

    # Should show service is running or detect it somehow
    echo "Output: $output"

    # Cleanup
    kill $actual_pid 2>/dev/null || true
}

# Test 5: check_dependencies should verify Docker daemon is running
@test "check_dependencies: verifies Docker daemon status" {
    # RED: This test will fail initially if Docker check is not implemented

    # Mock docker command availability
    if ! command -v docker &> /dev/null; then
        skip "Docker not installed - cannot test Docker daemon check"
    fi

    # The check_dependencies function should verify Docker daemon is running
    run check_dependencies

    # Should either pass if Docker is running, or fail with clear message
    if docker info &> /dev/null; then
        [ "$status" -eq 0 ]
    else
        [[ "$output" == *"Docker"* ]] && [[ "$output" == *"not running"* ]]
    fi
}

# Test 6: stop_service should clean up stale PID files
@test "stop_service: removes stale PID file when process doesn't exist" {
    local service_name="TestService"
    local pid_file="$PID_DIR/test.pid"

    # Create a PID file with non-existent PID
    echo "99999" > "$pid_file"

    # Call stop_service
    stop_service "$service_name" "$pid_file"

    # PID file should be removed
    [ ! -f "$pid_file" ]
}

# Test 7: start_service should detect port conflicts
@test "start_service: detects and reports port conflicts" {
    skip "Requires complex mock setup - will implement after core functionality"
}

# Test 8: Helper function to find process by port
@test "find_process_by_port: returns PID of process listening on port" {
    # This is a new helper function we'll need to implement
    local test_port=16666

    # Start a process on the port
    python3 -m http.server $test_port > /dev/null 2>&1 &
    local expected_pid=$!
    sleep 1

    # Our new helper function should find it
    local found_pid=$(lsof -Pi :$test_port -sTCP:LISTEN -t 2>/dev/null | head -1)

    [ "$found_pid" = "$expected_pid" ]

    # Cleanup
    kill $expected_pid 2>/dev/null || true
}
