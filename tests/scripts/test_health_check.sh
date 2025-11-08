#!/bin/bash

# Test script for health check functionality
# Tests the health-check.sh module and unified-start.sh health features

set -euo pipefail

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Load libraries
source "${PROJECT_ROOT}/scripts/unified-lib/common.sh"
source "${PROJECT_ROOT}/scripts/unified-lib/process-manager.sh"
source "${PROJECT_ROOT}/scripts/unified-lib/health-check.sh"

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test result tracking
declare -a FAILED_TESTS

# Print test header
print_test_header() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}              ${WHITE}Health Check Module Test Suite${NC}                      ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Test assertion helpers
assert_success() {
    local test_name="$1"
    local command="$2"

    ((TESTS_RUN++))
    echo -n "  Testing: ${test_name}... "

    if eval "$command" >/dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}FAIL${NC}"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("$test_name")
        return 1
    fi
}

assert_failure() {
    local test_name="$1"
    local command="$2"

    ((TESTS_RUN++))
    echo -n "  Testing: ${test_name}... "

    if eval "$command" >/dev/null 2>&1; then
        echo -e "${RED}FAIL (expected failure, got success)${NC}"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("$test_name")
        return 1
    else
        echo -e "${GREEN}PASS${NC}"
        ((TESTS_PASSED++))
        return 0
    fi
}

# Test: check_service_health function exists
test_function_exists() {
    print_step "Testing function availability..."

    assert_success "check_service_health function exists" \
        "type check_service_health >/dev/null 2>&1"

    assert_success "wait_for_healthy function exists" \
        "type wait_for_healthy >/dev/null 2>&1"

    assert_success "check_all_services_health function exists" \
        "type check_all_services_health >/dev/null 2>&1"

    assert_success "get_response_time function exists" \
        "type get_response_time >/dev/null 2>&1"

    assert_success "get_health_info function exists" \
        "type get_health_info >/dev/null 2>&1"

    echo ""
}

# Test: health check with non-existent service
test_nonexistent_service() {
    print_step "Testing with non-existent service..."

    assert_failure "Health check fails for non-existent service" \
        "check_service_health 'nonexistent' 9999 2"

    echo ""
}

# Test: health check with running service (if available)
test_running_services() {
    print_step "Testing with potentially running services..."

    # Check if myVault is running
    if is_service_running "myvault"; then
        assert_success "Health check for running myVault service" \
            "check_service_health 'myvault' 8003 5"

        # Test response time
        local response_time
        response_time=$(get_response_time "myvault" 8003 5)
        if [[ "$response_time" != "timeout" ]]; then
            echo -e "  ${GREEN}✓${NC} Response time: ${response_time}s"
            ((TESTS_PASSED++))
        else
            echo -e "  ${RED}✗${NC} Response time: timeout"
            ((TESTS_FAILED++))
        fi
        ((TESTS_RUN++))
    else
        echo -e "  ${YELLOW}⊘${NC} myVault not running, skipping live tests"
    fi

    # Check if jobqueue is running
    if is_service_running "jobqueue"; then
        assert_success "Health check for running jobqueue service" \
            "check_service_health 'jobqueue' 8001 5"
    else
        echo -e "  ${YELLOW}⊘${NC} jobqueue not running, skipping live tests"
    fi

    # Check if myscheduler is running
    if is_service_running "myscheduler"; then
        assert_success "Health check for running myscheduler service" \
            "check_service_health 'myscheduler' 8002 5"
    else
        echo -e "  ${YELLOW}⊘${NC} myscheduler not running, skipping live tests"
    fi

    echo ""
}

# Test: timeout behavior
test_timeout_behavior() {
    print_step "Testing timeout behavior..."

    # Test with very short timeout on non-existent service
    local start_time
    local end_time
    local elapsed

    start_time=$(date +%s)
    check_service_health "nonexistent" 9999 1 >/dev/null 2>&1 || true
    end_time=$(date +%s)
    elapsed=$((end_time - start_time))

    ((TESTS_RUN++))
    if [[ $elapsed -le 3 ]]; then
        echo -e "  ${GREEN}PASS${NC} Timeout respected (${elapsed}s <= 3s)"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}FAIL${NC} Timeout not respected (${elapsed}s > 3s)"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Timeout behavior")
    fi

    echo ""
}

# Test: unified-start.sh health command
test_unified_start_health_command() {
    print_step "Testing unified-start.sh health command..."

    # Test --help includes health command
    ((TESTS_RUN++))
    if "${PROJECT_ROOT}/scripts/unified-start.sh" --help | grep -q "health"; then
        echo -e "  ${GREEN}PASS${NC} Health command documented in help"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}FAIL${NC} Health command not in help"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Health command in help")
    fi

    # Test --timeout option in help
    ((TESTS_RUN++))
    if "${PROJECT_ROOT}/scripts/unified-start.sh" --help | grep -q "\-\-timeout"; then
        echo -e "  ${GREEN}PASS${NC} --timeout option documented in help"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}FAIL${NC} --timeout option not in help"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("--timeout option in help")
    fi

    # Test --health-check-only option in help
    ((TESTS_RUN++))
    if "${PROJECT_ROOT}/scripts/unified-start.sh" --help | grep -q "\-\-health-check-only"; then
        echo -e "  ${GREEN}PASS${NC} --health-check-only option documented in help"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}FAIL${NC} --health-check-only option not in help"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("--health-check-only option in help")
    fi

    echo ""
}

# Test: constants are defined
test_constants() {
    print_step "Testing constant definitions..."

    assert_success "DEFAULT_HEALTH_CHECK_TIMEOUT is defined" \
        "[[ -n \"\${DEFAULT_HEALTH_CHECK_TIMEOUT:-}\" ]]"

    assert_success "DEFAULT_HEALTH_CHECK_INTERVAL is defined" \
        "[[ -n \"\${DEFAULT_HEALTH_CHECK_INTERVAL:-}\" ]]"

    echo ""
}

# Print test summary
print_test_summary() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}                       ${WHITE}Test Summary${NC}                                ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  Total tests run:     ${WHITE}${TESTS_RUN}${NC}"
    echo -e "  Tests passed:        ${GREEN}${TESTS_PASSED}${NC}"
    echo -e "  Tests failed:        ${RED}${TESTS_FAILED}${NC}"
    echo ""

    if [[ $TESTS_FAILED -gt 0 ]]; then
        echo -e "${RED}Failed tests:${NC}"
        for test_name in "${FAILED_TESTS[@]}"; do
            echo -e "  ${RED}✗${NC} $test_name"
        done
        echo ""
    fi

    local pass_rate=0
    if [[ $TESTS_RUN -gt 0 ]]; then
        pass_rate=$((TESTS_PASSED * 100 / TESTS_RUN))
    fi

    echo -e "  Pass rate:           ${WHITE}${pass_rate}%${NC}"
    echo ""

    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}✅ All tests passed!${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}❌ Some tests failed${NC}"
        echo ""
        return 1
    fi
}

# Main test execution
main() {
    print_test_header

    # Run test suites
    test_function_exists
    test_constants
    test_nonexistent_service
    test_timeout_behavior
    test_running_services
    test_unified_start_health_command

    # Print summary
    print_test_summary
}

# Run tests
main "$@"
