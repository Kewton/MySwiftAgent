#!/bin/bash

# Manual test script for unified-start.sh error handling
# Tests Issue #143 implementation

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
UNIFIED_START="${PROJECT_ROOT}/scripts/unified-start.sh"

TESTS_PASSED=0
TESTS_FAILED=0

# Test helper functions
pass() {
    echo -e "${GREEN}✓ PASS:${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

fail() {
    echo -e "${RED}✗ FAIL:${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

test_header() {
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}TEST: $1${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Test 1: Check if all required files exist
test_header "Required files exist"

if [[ -f "$UNIFIED_START" ]]; then
    pass "unified-start.sh exists"
else
    fail "unified-start.sh not found"
fi

if [[ -f "${PROJECT_ROOT}/scripts/unified-lib/common.sh" ]]; then
    pass "common.sh exists"
else
    fail "common.sh not found"
fi

if [[ -f "${PROJECT_ROOT}/scripts/unified-lib/process-manager.sh" ]]; then
    pass "process-manager.sh exists"
else
    fail "process-manager.sh not found"
fi

if [[ -f "${PROJECT_ROOT}/scripts/unified-lib/error-catalog.sh" ]]; then
    pass "error-catalog.sh exists (NEW)"
else
    fail "error-catalog.sh not found (NEW)"
fi

# Test 2: Check if unified-start.sh is executable
test_header "Script is executable"

if [[ -x "$UNIFIED_START" ]]; then
    pass "unified-start.sh is executable"
else
    fail "unified-start.sh is not executable"
fi

# Test 3: Source libraries without errors
test_header "Libraries can be sourced"

if bash -c "source '${PROJECT_ROOT}/scripts/unified-lib/common.sh' 2>/dev/null"; then
    pass "common.sh sources without errors"
else
    fail "common.sh has syntax errors"
fi

if bash -c "source '${PROJECT_ROOT}/scripts/unified-lib/process-manager.sh' 2>/dev/null"; then
    pass "process-manager.sh sources without errors"
else
    fail "process-manager.sh has syntax errors"
fi

if bash -c "source '${PROJECT_ROOT}/scripts/unified-lib/error-catalog.sh' 2>/dev/null"; then
    pass "error-catalog.sh sources without errors (NEW)"
else
    fail "error-catalog.sh has syntax errors (NEW)"
fi

# Test 4: Check error codes and functions are defined
test_header "Error codes and functions are defined"

# Source the error catalog
set +u
source "${PROJECT_ROOT}/scripts/unified-lib/common.sh" 2>/dev/null || true
source "${PROJECT_ROOT}/scripts/unified-lib/error-catalog.sh" 2>/dev/null || true
set -u

if [[ -n "${EXIT_SUCCESS:-}" ]]; then
    pass "EXIT_SUCCESS is defined"
else
    fail "EXIT_SUCCESS is not defined"
fi

if [[ -n "${EXIT_DEPENDENCY_ERROR:-}" ]]; then
    pass "EXIT_DEPENDENCY_ERROR is defined (NEW)"
else
    fail "EXIT_DEPENDENCY_ERROR is not defined (NEW)"
fi

if [[ -n "${EXIT_PORT_CONFLICT:-}" ]]; then
    pass "EXIT_PORT_CONFLICT is defined (NEW)"
else
    fail "EXIT_PORT_CONFLICT is not defined (NEW)"
fi

if [[ -n "${EXIT_SERVICE_START_FAILED:-}" ]]; then
    pass "EXIT_SERVICE_START_FAILED is defined (NEW)"
else
    fail "EXIT_SERVICE_START_FAILED is not defined (NEW)"
fi

if [[ -n "${EXIT_PARTIAL_STARTUP_FAILED:-}" ]]; then
    pass "EXIT_PARTIAL_STARTUP_FAILED is defined (NEW)"
else
    fail "EXIT_PARTIAL_STARTUP_FAILED is not defined (NEW)"
fi

# Test error message functions
if declare -f get_error_message &>/dev/null; then
    test_msg=$(get_error_message "$EXIT_DEPENDENCY_ERROR" 2>/dev/null || echo "")
    if [[ -n "$test_msg" ]]; then
        pass "get_error_message function works (NEW)"
    else
        fail "get_error_message function doesn't return messages (NEW)"
    fi
else
    fail "get_error_message function not found (NEW)"
fi

if declare -f get_error_resolution &>/dev/null; then
    test_resolution=$(get_error_resolution "$EXIT_DEPENDENCY_ERROR" 2>/dev/null || echo "")
    if [[ -n "$test_resolution" ]]; then
        pass "get_error_resolution function works (NEW)"
    else
        fail "get_error_resolution function doesn't return resolutions (NEW)"
    fi
else
    fail "get_error_resolution function not found (NEW)"
fi

# Test 5: Check help message includes --force option
test_header "Help message includes --force option"

help_output=$(bash "$UNIFIED_START" --help 2>&1)

if echo "$help_output" | grep -q "\-\-force"; then
    pass "--force option is documented in help (NEW)"
else
    fail "--force option is not documented in help (NEW)"
fi

# Test 6: Check if --force option is accepted
test_header "Script accepts --force option"

# This should not error on option parsing
output=$(bash "$UNIFIED_START" start --force 2>&1 || true)

if echo "$output" | grep -q "Unknown option"; then
    fail "Script rejects --force option (NEW)"
else
    pass "Script accepts --force option (NEW)"
fi

# Test 7: Check functions exist
test_header "New functions are defined"

set +u
source "${PROJECT_ROOT}/scripts/unified-lib/common.sh" 2>/dev/null || true
source "${PROJECT_ROOT}/scripts/unified-lib/error-catalog.sh" 2>/dev/null || true
set -u

if declare -f cleanup_stale_pids &>/dev/null; then
    pass "cleanup_stale_pids function exists (NEW)"
else
    fail "cleanup_stale_pids function not found (NEW)"
fi

if declare -f cleanup_all &>/dev/null; then
    pass "cleanup_all function exists (NEW)"
else
    fail "cleanup_all function not found (NEW)"
fi

if declare -f show_error_report &>/dev/null; then
    pass "show_error_report function exists (NEW)"
else
    fail "show_error_report function not found (NEW)"
fi

if declare -f show_port_conflict_details &>/dev/null; then
    pass "show_port_conflict_details function exists (NEW)"
else
    fail "show_port_conflict_details function not found (NEW)"
fi

if declare -f show_service_failure_details &>/dev/null; then
    pass "show_service_failure_details function exists (NEW)"
else
    fail "show_service_failure_details function not found (NEW)"
fi

# Test 8: Check rollback function in unified-start.sh
test_header "Rollback mechanism is implemented"

if grep -q "rollback_services()" "$UNIFIED_START"; then
    pass "rollback_services function is defined (NEW)"
else
    fail "rollback_services function not found (NEW)"
fi

if grep -q "trap.*error_handler" "$UNIFIED_START"; then
    pass "Error trap is configured (NEW)"
else
    fail "Error trap not configured (NEW)"
fi

if grep -q "trap.*interrupt_handler" "$UNIFIED_START"; then
    pass "Interrupt trap is configured (NEW)"
else
    fail "Interrupt trap not configured (NEW)"
fi

if grep -q "STARTED_SERVICES" "$UNIFIED_START"; then
    pass "STARTED_SERVICES tracking array exists (NEW)"
else
    fail "STARTED_SERVICES tracking array not found (NEW)"
fi

# Test 9: Check cleanup in start flow
test_header "Cleanup is integrated in start flow"

if grep -q "cleanup_stale_pids" "$UNIFIED_START"; then
    pass "cleanup_stale_pids is called in start flow (NEW)"
else
    fail "cleanup_stale_pids not called in start flow (NEW)"
fi

# Summary
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}TEST SUMMARY${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Passed: ${TESTS_PASSED}${NC}"
echo -e "${RED}Failed: ${TESTS_FAILED}${NC}"
echo ""

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
