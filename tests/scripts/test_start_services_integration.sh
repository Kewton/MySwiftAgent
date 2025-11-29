#!/bin/bash
# Integration tests for start_services.sh enhancements
# Tests the bug fixes for PID file handling, port-based detection, and Docker checking

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test configuration
TEST_DIR="$(mktemp -d)"
TEST_PORT_BASE=19000
TEST_SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REPO_ROOT="$(dirname "$(dirname "$TEST_SCRIPT_DIR")")"
START_SERVICES="$REPO_ROOT/scripts/start_services.sh"

# Override directories for testing
export PID_DIR="$TEST_DIR/.pids"
export LOG_DIR="$TEST_DIR/logs"
mkdir -p "$PID_DIR" "$LOG_DIR"

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
print_test() {
    echo -e "${YELLOW}TEST $((TESTS_RUN + 1)):${NC} $1"
}

print_pass() {
    echo -e "${GREEN}✅ PASS:${NC} $1"
    ((TESTS_PASSED++))
}

print_fail() {
    echo -e "${RED}❌ FAIL:${NC} $1"
    ((TESTS_FAILED++))
}

cleanup() {
    # Kill any test processes (suppress job control messages)
    for port in $(seq $TEST_PORT_BASE $((TEST_PORT_BASE + 10))); do
        local pid=$(lsof -Pi :$port -sTCP:LISTEN -t 2>/dev/null | head -1)
        if [ -n "$pid" ]; then
            ( kill -9 $pid >/dev/null 2>&1 & )
        fi
    done

    # Wait a moment for processes to die
    sleep 0.5

    # Remove test directory
    rm -rf "$TEST_DIR"
} 2>/dev/null

trap cleanup EXIT

# Extract and source only the functions from start_services.sh
# We need to prevent the main execution while sourcing
(
    # Read the script and extract only function definitions
    sed -n '/^# Function to/,/^}/p' "$START_SERVICES"
    sed -n '/^check_port()/,/^}/p' "$START_SERVICES"
    sed -n '/^find_pid_by_port()/,/^}/p' "$START_SERVICES"
    sed -n '/^wait_for_service()/,/^}/p' "$START_SERVICES"
    sed -n '/^start_service()/,/^}/p' "$START_SERVICES"
    sed -n '/^stop_service()/,/^}/p' "$START_SERVICES"
    sed -n '/^check_status()/,/^}/p' "$START_SERVICES"
    sed -n '/^check_dependencies()/,/^}/p' "$START_SERVICES"
    sed -n '/^print_status()/,/^}/p' "$START_SERVICES"
    sed -n '/^print_success()/,/^}/p' "$START_SERVICES"
    sed -n '/^print_warning()/,/^}/p' "$START_SERVICES"
    sed -n '/^print_error()/,/^}/p' "$START_SERVICES"
) > "$TEST_DIR/functions.sh"

# Set color variables
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

source "$TEST_DIR/functions.sh"

# Test 1: find_pid_by_port function
test_find_pid_by_port() {
    ((TESTS_RUN++))
    print_test "find_pid_by_port returns correct PID"

    local test_port=$TEST_PORT_BASE

    # Start a test server
    python3 -m http.server $test_port > /dev/null 2>&1 &
    local expected_pid=$!
    sleep 1

    # Test the function
    local found_pid=$(find_pid_by_port $test_port)

    if [ "$found_pid" = "$expected_pid" ]; then
        print_pass "find_pid_by_port correctly found PID $expected_pid"
    else
        print_fail "find_pid_by_port returned $found_pid, expected $expected_pid"
    fi

    # Cleanup
    kill $expected_pid 2>/dev/null || true
}

# Test 2: stop_service with port-based detection
test_stop_service_port_detection() {
    ((TESTS_RUN++))
    print_test "stop_service can stop process using port when PID file is missing"

    local test_port=$((TEST_PORT_BASE + 1))
    local test_pid_file="$PID_DIR/test_service.pid"

    # Start a test server without creating PID file
    python3 -m http.server $test_port > /dev/null 2>&1 &
    local server_pid=$!
    sleep 1

    # Verify it's running
    if ! lsof -Pi :$test_port -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_fail "Test server failed to start"
        return
    fi

    # Call stop_service without PID file
    stop_service "TestService" "$test_pid_file" "$test_port" > /dev/null 2>&1

    # Verify it's stopped
    sleep 1
    if lsof -Pi :$test_port -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_fail "Process still running on port $test_port"
    else
        print_pass "stop_service successfully stopped process using port detection"
    fi
}

# Test 3: check_status detects PID/port mismatch
test_check_status_mismatch() {
    ((TESTS_RUN++))
    print_test "check_status detects PID/port mismatch"

    local test_port=$((TEST_PORT_BASE + 2))
    local test_pid_file="$PID_DIR/test_mismatch.pid"

    # Start a server
    python3 -m http.server $test_port > /dev/null 2>&1 &
    local real_pid=$!
    sleep 1

    # Create PID file with wrong PID
    echo "99999" > "$test_pid_file"

    # Check status - should detect mismatch or stale PID
    local output=$(check_status "TestService" "$test_pid_file" "$test_port" 2>&1)

    if [[ "$output" == *"stale"* ]] || [[ "$output" == *"different process"* ]]; then
        print_pass "check_status correctly detected stale PID file"
    else
        print_fail "check_status did not detect stale PID file"
    fi

    # Cleanup
    kill $real_pid 2>/dev/null || true
    rm -f "$test_pid_file"
}

# Test 4: check_status detects running service without PID file
test_check_status_no_pid_file() {
    ((TESTS_RUN++))
    print_test "check_status detects service running without PID file"

    local test_port=$((TEST_PORT_BASE + 3))
    local test_pid_file="$PID_DIR/test_no_pid.pid"

    # Start a server without PID file
    python3 -m http.server $test_port > /dev/null 2>&1 &
    local server_pid=$!
    sleep 1

    # Check status
    local output=$(check_status "TestService" "$test_pid_file" "$test_port" 2>&1)

    if [[ "$output" == *"running on port"* ]] && [[ "$output" == *"no PID file"* ]]; then
        print_pass "check_status correctly detected running service without PID file"
    else
        print_fail "check_status did not detect running service without PID file"
    fi

    # Cleanup
    kill $server_pid 2>/dev/null || true
}

# Test 5: check_dependencies verifies Docker daemon
test_check_dependencies_docker() {
    ((TESTS_RUN++))
    print_test "check_dependencies verifies Docker daemon status"

    if ! command -v docker &> /dev/null; then
        print_pass "check_dependencies skipped (Docker not installed)"
        return
    fi

    local output=$(check_dependencies 2>&1)

    if docker info &> /dev/null; then
        if [[ "$output" == *"Docker daemon is running"* ]]; then
            print_pass "check_dependencies correctly detected running Docker daemon"
        else
            print_fail "check_dependencies did not detect running Docker daemon"
        fi
    else
        if [[ "$output" == *"Docker"* ]] && [[ "$output" == *"not running"* ]]; then
            print_pass "check_dependencies correctly detected Docker daemon not running"
        else
            print_fail "check_dependencies did not properly check Docker daemon"
        fi
    fi
}

# Test 6: stop_service cleans up stale PID file
test_stop_service_stale_pid() {
    ((TESTS_RUN++))
    print_test "stop_service removes stale PID file"

    local test_pid_file="$PID_DIR/test_stale.pid"

    # Create stale PID file
    echo "99999" > "$test_pid_file"

    # Call stop_service
    stop_service "TestService" "$test_pid_file" > /dev/null 2>&1

    # Verify PID file is removed
    if [ ! -f "$test_pid_file" ]; then
        print_pass "stop_service correctly removed stale PID file"
    else
        print_fail "stop_service did not remove stale PID file"
    fi
}

# Test 7: Integration test - full lifecycle
test_full_lifecycle() {
    ((TESTS_RUN++))
    print_test "Full lifecycle: start with PID file verification, status check, stop with port detection"

    local test_port=$((TEST_PORT_BASE + 4))
    local test_pid_file="$PID_DIR/test_lifecycle.pid"

    # Start a service and create PID file
    python3 -m http.server $test_port > /dev/null 2>&1 &
    local server_pid=$!
    echo "$server_pid" > "$test_pid_file"
    sleep 1

    # Verify PID file exists and is correct
    if [ -f "$test_pid_file" ] && [ "$(cat "$test_pid_file")" = "$server_pid" ]; then
        # Check status - should show running
        local status_output=$(check_status "TestService" "$test_pid_file" "$test_port" 2>&1)

        if [[ "$status_output" == *"is running"* ]]; then
            # Remove PID file to simulate the bug scenario
            rm -f "$test_pid_file"

            # Stop using port-based detection
            stop_service "TestService" "$test_pid_file" "$test_port" > /dev/null 2>&1
            sleep 1

            # Verify stopped
            if ! lsof -Pi :$test_port -sTCP:LISTEN -t >/dev/null 2>&1; then
                print_pass "Full lifecycle test completed successfully"
            else
                print_fail "Service not stopped in full lifecycle test"
            fi
        else
            print_fail "Status check failed in full lifecycle test"
        fi
    else
        print_fail "PID file verification failed in full lifecycle test"
    fi
}

# Run all tests
echo "========================================="
echo "Starting start_services.sh Integration Tests"
echo "========================================="
echo ""

test_find_pid_by_port
test_stop_service_port_detection
test_check_status_mismatch
test_check_status_no_pid_file
test_check_dependencies_docker
test_stop_service_stale_pid
test_full_lifecycle

# Summary
echo ""
echo "========================================="
echo "Test Results Summary"
echo "========================================="
echo "Total Tests Run: $TESTS_RUN"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo "========================================="

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed!${NC}"
    exit 1
fi
