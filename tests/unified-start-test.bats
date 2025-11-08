#!/usr/bin/env bats

# Test suite for unified-start.sh error handling and rollback features
# Tests Issue #143 implementation

setup() {
    # Set up test environment
    export PROJECT_ROOT="${BATS_TEST_DIRNAME}/.."
    export SCRIPT_DIR="${PROJECT_ROOT}/scripts"
    export UNIFIED_START="${SCRIPT_DIR}/unified-start.sh"
    export TEST_PID_DIR="/tmp/myswiftagent-test-$$"
    export TEST_LOG_DIR="${PROJECT_ROOT}/logs-test-$$"

    # Create test directories
    mkdir -p "$TEST_PID_DIR"
    mkdir -p "$TEST_LOG_DIR"

    # Source libraries for testing
    source "${SCRIPT_DIR}/unified-lib/common.sh"
    source "${SCRIPT_DIR}/unified-lib/error-catalog.sh"
    source "${SCRIPT_DIR}/unified-lib/process-manager.sh"

    # Override directories for testing
    export PID_DIR="$TEST_PID_DIR"
    export LOG_DIR="$TEST_LOG_DIR"
}

teardown() {
    # Clean up test environment
    rm -rf "$TEST_PID_DIR"
    rm -rf "$TEST_LOG_DIR"
}

# Test: Error catalog exists and exports error codes
@test "error catalog defines exit codes" {
    [ -n "$EXIT_SUCCESS" ]
    [ -n "$EXIT_DEPENDENCY_ERROR" ]
    [ -n "$EXIT_PORT_CONFLICT" ]
    [ -n "$EXIT_SERVICE_START_FAILED" ]
    [ -n "$EXIT_DIRECTORY_NOT_FOUND" ]
    [ -n "$EXIT_PARTIAL_STARTUP_FAILED" ]
    [ -n "$EXIT_USER_INTERRUPTED" ]
}

# Test: Error catalog provides messages
@test "error catalog provides error messages" {
    [ -n "${ERROR_MESSAGES[$EXIT_DEPENDENCY_ERROR]}" ]
    [ -n "${ERROR_MESSAGES[$EXIT_PORT_CONFLICT]}" ]
    [ -n "${ERROR_MESSAGES[$EXIT_SERVICE_START_FAILED]}" ]
}

# Test: Error catalog provides resolutions
@test "error catalog provides error resolutions" {
    [ -n "${ERROR_RESOLUTIONS[$EXIT_DEPENDENCY_ERROR]}" ]
    [ -n "${ERROR_RESOLUTIONS[$EXIT_PORT_CONFLICT]}" ]
    [ -n "${ERROR_RESOLUTIONS[$EXIT_SERVICE_START_FAILED]}" ]
}

# Test: Cleanup stale PID files
@test "cleanup_stale_pids removes stale PID files" {
    # Create a stale PID file with non-existent PID
    echo "999999" > "${TEST_PID_DIR}/test-service.pid"

    # Run cleanup
    run cleanup_stale_pids

    # Verify stale PID file was removed
    [ ! -f "${TEST_PID_DIR}/test-service.pid" ]
}

# Test: Cleanup preserves valid PID files
@test "cleanup_stale_pids preserves valid PID files" {
    # Create a valid PID file with our own PID
    echo "$$" > "${TEST_PID_DIR}/test-service.pid"

    # Run cleanup
    run cleanup_stale_pids

    # Verify valid PID file was preserved
    [ -f "${TEST_PID_DIR}/test-service.pid" ]
}

# Test: Port conflict detection
@test "check_port detects port in use" {
    # Start a test server on port 9999
    nc -l 9999 &
    local test_pid=$!
    sleep 1

    # Check if port is detected as in use
    run check_port 9999
    local result=$?

    # Clean up
    kill $test_pid 2>/dev/null || true

    # Verify detection
    [ $result -eq 0 ]
}

# Test: Port conflict detection for free port
@test "check_port returns false for free port" {
    # Use an unlikely port
    run check_port 54321
    [ $? -ne 0 ]
}

# Test: Get port conflict info
@test "get_port_conflict_info returns process information" {
    # Start a test server
    nc -l 9998 &
    local test_pid=$!
    sleep 1

    # Get conflict info
    run get_port_conflict_info 9998

    # Clean up
    kill $test_pid 2>/dev/null || true

    # Verify we got process info
    [ $status -eq 0 ]
    [[ "$output" =~ "PID:" ]]
}

# Test: Unified-start.sh help message
@test "unified-start.sh --help shows force option" {
    run bash "$UNIFIED_START" --help

    [ $status -eq 0 ]
    [[ "$output" =~ "--force" ]]
}

# Test: Unified-start.sh accepts --force option
@test "unified-start.sh accepts --force option" {
    # This should not error on option parsing
    # We expect dependency error instead
    run bash "$UNIFIED_START" start --force

    # Should fail on dependency check or service start, not option parsing
    [ $status -ne 0 ]
    # Should NOT contain "Unknown option"
    [[ ! "$output" =~ "Unknown option" ]]
}

# Test: Error report function exists
@test "show_error_report function exists" {
    run type show_error_report
    [ $status -eq 0 ]
}

# Test: Service failure details function exists
@test "show_service_failure_details function exists" {
    run type show_service_failure_details
    [ $status -eq 0 ]
}

# Test: Port conflict details function exists
@test "show_port_conflict_details function exists" {
    run type show_port_conflict_details
    [ $status -eq 0 ]
}

# Test: Cleanup all function
@test "cleanup_all removes empty log files" {
    # Create an empty log file
    touch "${TEST_LOG_DIR}/empty.log"

    # Create a non-empty log file
    echo "test content" > "${TEST_LOG_DIR}/nonempty.log"

    # Run cleanup
    run cleanup_all

    # Verify empty log was removed and non-empty preserved
    [ ! -f "${TEST_LOG_DIR}/empty.log" ]
    [ -f "${TEST_LOG_DIR}/nonempty.log" ]
}

# Test: Find orphaned processes
@test "find_orphaned_processes detects running services" {
    # Create a PID file with our own PID
    echo "$$" > "${TEST_PID_DIR}/test-orphan.pid"

    # Run find_orphaned_processes
    run find_orphaned_processes

    # Should find our process
    [[ "$output" =~ "test-orphan" ]]
}

# Test: Error code values are unique
@test "error codes are unique" {
    local codes=(
        "$EXIT_SUCCESS"
        "$EXIT_DEPENDENCY_ERROR"
        "$EXIT_PORT_CONFLICT"
        "$EXIT_SERVICE_START_FAILED"
        "$EXIT_DIRECTORY_NOT_FOUND"
        "$EXIT_PARTIAL_STARTUP_FAILED"
        "$EXIT_USER_INTERRUPTED"
    )

    # Count unique values
    local unique_count=$(printf '%s\n' "${codes[@]}" | sort -u | wc -l)
    local total_count=${#codes[@]}

    [ $unique_count -eq $total_count ]
}

# Test: Main script exists and is executable
@test "unified-start.sh is executable" {
    [ -x "$UNIFIED_START" ]
}

# Test: All library files exist
@test "all required library files exist" {
    [ -f "${SCRIPT_DIR}/unified-lib/common.sh" ]
    [ -f "${SCRIPT_DIR}/unified-lib/process-manager.sh" ]
    [ -f "${SCRIPT_DIR}/unified-lib/error-catalog.sh" ]
}

# Test: Libraries are sourceable
@test "libraries can be sourced without errors" {
    run bash -c "source '${SCRIPT_DIR}/unified-lib/common.sh' && \
                 source '${SCRIPT_DIR}/unified-lib/process-manager.sh' && \
                 source '${SCRIPT_DIR}/unified-lib/error-catalog.sh'"
    [ $status -eq 0 ]
}
