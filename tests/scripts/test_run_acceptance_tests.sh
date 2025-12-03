#!/bin/bash
# Functional tests for run-acceptance-tests.sh
# Tests acceptance criteria for Issue #215

# Do not use set -e as we need to handle test failures gracefully

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Script location
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
TARGET_SCRIPT="$PROJECT_ROOT/scripts/run-acceptance-tests.sh"

# Test helper functions
print_test() {
    local test_name=$1
    echo -n "  Testing: $test_name... "
    ((TESTS_TOTAL++))
}

pass() {
    echo -e "${GREEN}PASS${NC}"
    ((TESTS_PASSED++))
}

fail() {
    local reason=${1:-""}
    echo -e "${RED}FAIL${NC}"
    if [[ -n "$reason" ]]; then
        echo -e "    ${YELLOW}Reason: $reason${NC}"
    fi
    ((TESTS_FAILED++))
}

# ============================================================================
# TEST CASES
# ============================================================================

test_script_exists() {
    print_test "Script exists"
    if [[ -f "$TARGET_SCRIPT" ]]; then
        pass
    else
        fail "Script not found at $TARGET_SCRIPT"
    fi
}

test_script_is_executable() {
    print_test "Script is executable"
    if [[ -x "$TARGET_SCRIPT" ]]; then
        pass
    else
        fail "Script is not executable"
    fi
}

test_script_has_shebang() {
    print_test "Script has valid shebang"
    if [[ ! -f "$TARGET_SCRIPT" ]]; then
        fail "Script does not exist"
        return
    fi
    if head -1 "$TARGET_SCRIPT" 2>/dev/null | grep -q "^#!/bin/bash"; then
        pass
    else
        fail "Missing or invalid shebang"
    fi
}

test_help_option_short() {
    print_test "Help option (-h) works"
    if [[ ! -x "$TARGET_SCRIPT" ]]; then
        fail "Script not executable or does not exist"
        return
    fi
    if "$TARGET_SCRIPT" -h 2>&1 | grep -q -i "usage\|help\|options"; then
        pass
    else
        fail "Help output not found with -h"
    fi
}

test_help_option_long() {
    print_test "Help option (--help) works"
    if [[ ! -x "$TARGET_SCRIPT" ]]; then
        fail "Script not executable or does not exist"
        return
    fi
    if "$TARGET_SCRIPT" --help 2>&1 | grep -q -i "usage\|help\|options"; then
        pass
    else
        fail "Help output not found with --help"
    fi
}

test_help_shows_layer_options() {
    print_test "Help shows layer options"
    if [[ ! -x "$TARGET_SCRIPT" ]]; then
        fail "Script not executable or does not exist"
        return
    fi
    local help_output
    help_output=$("$TARGET_SCRIPT" --help 2>&1)
    if echo "$help_output" | grep -q "platform" && echo "$help_output" | grep -q "agent"; then
        pass
    else
        fail "Help should mention 'platform' and 'agent' layers"
    fi
}

test_shellcheck_passes() {
    print_test "ShellCheck passes with no errors"
    if [[ ! -f "$TARGET_SCRIPT" ]]; then
        fail "Script does not exist"
        return
    fi
    if command -v shellcheck &> /dev/null; then
        local shellcheck_output
        if shellcheck_output=$(shellcheck -x "$TARGET_SCRIPT" 2>&1); then
            pass
        else
            fail "ShellCheck found errors: $shellcheck_output"
        fi
    else
        fail "ShellCheck not installed"
    fi
}

test_makefile_has_acceptance_test_platform() {
    print_test "Makefile has acceptance-test-platform target"
    if grep -q "^acceptance-test-platform:" "$PROJECT_ROOT/Makefile"; then
        pass
    else
        fail "Target acceptance-test-platform not found in Makefile"
    fi
}

test_makefile_has_acceptance_test_agent() {
    print_test "Makefile has acceptance-test-agent target"
    if grep -q "^acceptance-test-agent:" "$PROJECT_ROOT/Makefile"; then
        pass
    else
        fail "Target acceptance-test-agent not found in Makefile"
    fi
}

test_makefile_help_shows_acceptance_tests() {
    print_test "Makefile help shows acceptance test commands"
    local make_help
    make_help=$(make -C "$PROJECT_ROOT" help 2>&1)
    if echo "$make_help" | grep -q -i "acceptance"; then
        pass
    else
        fail "Makefile help does not show acceptance test commands"
    fi
}

test_report_directory_exists() {
    print_test "Report directory exists or created"
    local report_dir="$PROJECT_ROOT/test-reports/acceptance"
    if [[ -d "$report_dir" ]] || mkdir -p "$report_dir"; then
        pass
    else
        fail "Cannot create report directory"
    fi
}

test_script_has_layer_option() {
    print_test "Script accepts --layer option"
    if [[ ! -x "$TARGET_SCRIPT" ]]; then
        fail "Script not executable or does not exist"
        return
    fi
    local help_output
    help_output=$("$TARGET_SCRIPT" --help 2>&1)
    if echo "$help_output" | grep -q "\-\-layer"; then
        pass
    else
        fail "Script should accept --layer option"
    fi
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    echo ""
    echo "============================================"
    echo "  Acceptance Tests for run-acceptance-tests.sh"
    echo "  Issue #215 Functional Tests"
    echo "============================================"
    echo ""

    # Run all tests
    test_script_exists
    test_script_is_executable
    test_script_has_shebang
    test_help_option_short
    test_help_option_long
    test_help_shows_layer_options
    test_shellcheck_passes
    test_makefile_has_acceptance_test_platform
    test_makefile_has_acceptance_test_agent
    test_makefile_help_shows_acceptance_tests
    test_report_directory_exists
    test_script_has_layer_option

    echo ""
    echo "============================================"
    echo "  Results: $TESTS_PASSED/$TESTS_TOTAL passed"
    echo "============================================"
    echo ""

    if [[ $TESTS_FAILED -gt 0 ]]; then
        echo -e "${RED}$TESTS_FAILED test(s) failed${NC}"
        exit 1
    else
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    fi
}

main "$@"
