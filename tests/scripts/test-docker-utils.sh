#!/bin/bash

# Unit Tests for docker-utils.sh (Issue #148)
# Tests Docker Compose integration functionality

set -euo pipefail

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Path to docker-utils.sh
DOCKER_UTILS_SCRIPT="${PROJECT_ROOT}/scripts/lib/docker-utils.sh"

# Test counter
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Colors
TEST_GREEN='\033[0;32m'
TEST_RED='\033[0;31m'
TEST_YELLOW='\033[1;33m'
TEST_NC='\033[0m'

# Test result reporting
assert_equals() {
    local expected="$1"
    local actual="$2"
    local test_name="$3"

    ((TESTS_RUN++))

    if [[ "$expected" == "$actual" ]]; then
        echo -e "${TEST_GREEN}✓${TEST_NC} PASS: $test_name"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${TEST_RED}✗${TEST_NC} FAIL: $test_name"
        echo -e "  Expected: $expected"
        echo -e "  Got:      $actual"
        ((TESTS_FAILED++))
        return 1
    fi
}

assert_file_exists() {
    local file_path="$1"
    local test_name="$2"

    ((TESTS_RUN++))

    if [[ -f "$file_path" ]]; then
        echo -e "${TEST_GREEN}✓${TEST_NC} PASS: $test_name"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${TEST_RED}✗${TEST_NC} FAIL: $test_name (file not found: $file_path)"
        ((TESTS_FAILED++))
        return 1
    fi
}

assert_function_exists() {
    local function_name="$1"
    local test_name="$2"

    ((TESTS_RUN++))

    # Check if function is defined after sourcing the script
    if declare -F "$function_name" > /dev/null 2>&1; then
        echo -e "${TEST_GREEN}✓${TEST_NC} PASS: $test_name"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${TEST_RED}✗${TEST_NC} FAIL: $test_name (function not found: $function_name)"
        ((TESTS_FAILED++))
        return 1
    fi
}

assert_true() {
    local condition="$1"
    local test_name="$2"

    ((TESTS_RUN++))

    if [[ "$condition" == "true" ]]; then
        echo -e "${TEST_GREEN}✓${TEST_NC} PASS: $test_name"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${TEST_RED}✗${TEST_NC} FAIL: $test_name"
        ((TESTS_FAILED++))
        return 1
    fi
}

# ============================================================================
# Test Suite 1: Script Existence and Structure
# ============================================================================

test_script_existence() {
    echo ""
    echo "=== Test Suite 1: Script Existence and Structure ==="

    # Test 1: docker-utils.sh exists
    assert_file_exists "$DOCKER_UTILS_SCRIPT" "docker-utils.sh script exists"

    # Test 2: docker-utils.sh is executable
    ((TESTS_RUN++))
    if [[ -x "$DOCKER_UTILS_SCRIPT" ]]; then
        echo -e "${TEST_GREEN}✓${TEST_NC} PASS: docker-utils.sh is executable"
        ((TESTS_PASSED++))
    else
        echo -e "${TEST_RED}✗${TEST_NC} FAIL: docker-utils.sh is not executable"
        ((TESTS_FAILED++))
    fi
}

# ============================================================================
# Test Suite 2: Function Definitions
# ============================================================================

test_function_definitions() {
    echo ""
    echo "=== Test Suite 2: Function Definitions ==="

    # Source the docker-utils.sh script
    if [[ -f "$DOCKER_UTILS_SCRIPT" ]]; then
        source "$DOCKER_UTILS_SCRIPT" 2>/dev/null || true
    fi

    # Test 1: check_docker_available function exists
    assert_function_exists "check_docker_available" "check_docker_available function defined"

    # Test 2: start_docker_compose function exists
    assert_function_exists "start_docker_compose" "start_docker_compose function defined"

    # Test 3: stop_docker_compose function exists
    assert_function_exists "stop_docker_compose" "stop_docker_compose function defined"

    # Test 4: check_docker_service_health function exists
    assert_function_exists "check_docker_service_health" "check_docker_service_health function defined"

    # Test 5: get_worktree_project_name function exists
    assert_function_exists "get_worktree_project_name" "get_worktree_project_name function defined"
}

# ============================================================================
# Test Suite 3: Worktree Project Name Generation
# ============================================================================

test_worktree_project_name() {
    echo ""
    echo "=== Test Suite 3: Worktree Project Name Generation ==="

    # Source the script
    if [[ -f "$DOCKER_UTILS_SCRIPT" ]]; then
        source "$DOCKER_UTILS_SCRIPT" 2>/dev/null || true
    fi

    # Test 1: get_worktree_project_name returns non-empty string
    if declare -F get_worktree_project_name > /dev/null 2>&1; then
        local project_name=$(get_worktree_project_name)
        ((TESTS_RUN++))
        if [[ -n "$project_name" ]]; then
            echo -e "${TEST_GREEN}✓${TEST_NC} PASS: get_worktree_project_name returns non-empty string"
            ((TESTS_PASSED++))
        else
            echo -e "${TEST_RED}✗${TEST_NC} FAIL: get_worktree_project_name returns empty string"
            ((TESTS_FAILED++))
        fi

        # Test 2: Project name contains 'myswiftagent'
        ((TESTS_RUN++))
        if [[ "$project_name" =~ myswiftagent ]]; then
            echo -e "${TEST_GREEN}✓${TEST_NC} PASS: Project name contains 'myswiftagent'"
            ((TESTS_PASSED++))
        else
            echo -e "${TEST_RED}✗${TEST_NC} FAIL: Project name does not contain 'myswiftagent' (got: $project_name)"
            ((TESTS_FAILED++))
        fi
    fi
}

# ============================================================================
# Run All Tests
# ============================================================================

main() {
    echo "========================================================================"
    echo "  docker-utils.sh Unit Test Suite (Issue #148)"
    echo "========================================================================"

    test_script_existence
    test_function_definitions
    test_worktree_project_name

    echo ""
    echo "========================================================================"
    echo "  Test Results"
    echo "========================================================================"
    echo -e "Total tests:  $TESTS_RUN"
    echo -e "${TEST_GREEN}Passed:       $TESTS_PASSED${TEST_NC}"
    echo -e "${TEST_RED}Failed:       $TESTS_FAILED${TEST_NC}"
    echo "========================================================================"

    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "${TEST_GREEN}All tests passed!${TEST_NC}"
        exit 0
    else
        echo -e "${TEST_RED}Some tests failed!${TEST_NC}"
        exit 1
    fi
}

# Run main
main
