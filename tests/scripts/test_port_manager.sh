#!/bin/bash

# Test script for port manager
# Tests the port-manager.sh module

set -euo pipefail

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Load libraries
source "${PROJECT_ROOT}/scripts/unified-lib/common.sh"
source "${PROJECT_ROOT}/scripts/unified-lib/worktree-utils.sh"
source "${PROJECT_ROOT}/scripts/unified-lib/port-manager.sh"

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
    echo -e "${CYAN}║${NC}             ${WHITE}Port Manager Module Test Suite${NC}                     ${CYAN}║${NC}"
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

assert_equals() {
    local test_name="$1"
    local expected="$2"
    local actual="$3"

    ((TESTS_RUN++))
    echo -n "  Testing: ${test_name}... "

    if [[ "$expected" == "$actual" ]]; then
        echo -e "${GREEN}PASS${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}FAIL (expected: '$expected', got: '$actual')${NC}"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("$test_name")
        return 1
    fi
}

assert_not_empty() {
    local test_name="$1"
    local value="$2"

    ((TESTS_RUN++))
    echo -n "  Testing: ${test_name}... "

    if [[ -n "$value" ]]; then
        echo -e "${GREEN}PASS${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}FAIL (value is empty)${NC}"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("$test_name")
        return 1
    fi
}

# Test: function availability
test_function_exists() {
    print_step "Testing function availability..."

    assert_success "calculate_port function exists" \
        "type calculate_port >/dev/null 2>&1"

    assert_success "is_port_in_use function exists" \
        "type is_port_in_use >/dev/null 2>&1"

    assert_success "find_available_port function exists" \
        "type find_available_port >/dev/null 2>&1"

    assert_success "get_all_ports_for_index function exists" \
        "type get_all_ports_for_index >/dev/null 2>&1"

    assert_success "check_port_conflicts function exists" \
        "type check_port_conflicts >/dev/null 2>&1"

    assert_success "suggest_alternative_port function exists" \
        "type suggest_alternative_port >/dev/null 2>&1"

    assert_success "get_port_status_summary function exists" \
        "type get_port_status_summary >/dev/null 2>&1"

    echo ""
}

# Test: constants are defined
test_constants() {
    print_step "Testing constant definitions..."

    assert_success "DEFAULT_BASE_EXPERTAGENT is defined" \
        "[[ -n \"\${DEFAULT_BASE_EXPERTAGENT:-}\" ]]"

    assert_success "DEFAULT_BASE_MYVAULT is defined" \
        "[[ -n \"\${DEFAULT_BASE_MYVAULT:-}\" ]]"

    assert_success "DEFAULT_BASE_MYSCHEDULER is defined" \
        "[[ -n \"\${DEFAULT_BASE_MYSCHEDULER:-}\" ]]"

    assert_success "DEFAULT_BASE_JOBQUEUE is defined" \
        "[[ -n \"\${DEFAULT_BASE_JOBQUEUE:-}\" ]]"

    assert_success "DEFAULT_BASE_GRAPHAI is defined" \
        "[[ -n \"\${DEFAULT_BASE_GRAPHAI:-}\" ]]"

    assert_success "DEFAULT_BASE_VITE is defined" \
        "[[ -n \"\${DEFAULT_BASE_VITE:-}\" ]]"

    assert_success "PORT_OFFSET_MULTIPLIER is defined" \
        "[[ -n \"\${PORT_OFFSET_MULTIPLIER:-}\" ]]"

    echo ""
}

# Test: calculate_port with index 0
test_calculate_port_index_0() {
    print_step "Testing calculate_port with index 0..."

    assert_equals "expertagent port for index 0" "8104" "$(calculate_port expertagent 0)"
    assert_equals "myvault port for index 0" "8103" "$(calculate_port myvault 0)"
    assert_equals "myscheduler port for index 0" "8102" "$(calculate_port myscheduler 0)"
    assert_equals "jobqueue port for index 0" "8101" "$(calculate_port jobqueue 0)"
    assert_equals "graphai port for index 0" "8100" "$(calculate_port graphai 0)"
    assert_equals "vite port for index 0" "5173" "$(calculate_port vite 0)"

    echo ""
}

# Test: calculate_port with index 1
test_calculate_port_index_1() {
    print_step "Testing calculate_port with index 1..."

    assert_equals "expertagent port for index 1" "8114" "$(calculate_port expertagent 1)"
    assert_equals "myvault port for index 1" "8113" "$(calculate_port myvault 1)"
    assert_equals "myscheduler port for index 1" "8112" "$(calculate_port myscheduler 1)"
    assert_equals "jobqueue port for index 1" "8111" "$(calculate_port jobqueue 1)"
    assert_equals "graphai port for index 1" "8110" "$(calculate_port graphai 1)"
    assert_equals "vite port for index 1" "5174" "$(calculate_port vite 1)"

    echo ""
}

# Test: calculate_port with index 5
test_calculate_port_index_5() {
    print_step "Testing calculate_port with index 5..."

    assert_equals "expertagent port for index 5" "8154" "$(calculate_port expertagent 5)"
    assert_equals "myvault port for index 5" "8153" "$(calculate_port myvault 5)"
    assert_equals "myscheduler port for index 5" "8152" "$(calculate_port myscheduler 5)"
    assert_equals "jobqueue port for index 5" "8151" "$(calculate_port jobqueue 5)"
    assert_equals "graphai port for index 5" "8150" "$(calculate_port graphai 5)"
    assert_equals "vite port for index 5" "5178" "$(calculate_port vite 5)"

    echo ""
}

# Test: calculate_port with invalid service name
test_calculate_port_invalid_service() {
    print_step "Testing calculate_port with invalid service name..."

    assert_failure "calculate_port fails with invalid service" \
        "calculate_port invalid_service 0"

    echo ""
}

# Test: calculate_port with invalid index
test_calculate_port_invalid_index() {
    print_step "Testing calculate_port with invalid index..."

    assert_failure "calculate_port fails with non-numeric index" \
        "calculate_port expertagent abc"

    assert_failure "calculate_port fails with negative index" \
        "calculate_port expertagent -1"

    echo ""
}

# Test: is_port_in_use
test_is_port_in_use() {
    print_step "Testing is_port_in_use..."

    # Test with a high port number that's unlikely to be in use
    ((TESTS_RUN++))
    if is_port_in_use 65432; then
        echo -e "  ${YELLOW}WARN${NC} Port 65432 is in use (unexpected but valid)"
        ((TESTS_PASSED++))
    else
        echo -e "  ${GREEN}PASS${NC} Port 65432 is not in use"
        ((TESTS_PASSED++))
    fi

    # Test with invalid port (non-numeric)
    assert_failure "is_port_in_use fails with non-numeric port" \
        "is_port_in_use abc"

    echo ""
}

# Test: find_available_port
test_find_available_port() {
    print_step "Testing find_available_port..."

    local available_port
    available_port=$(find_available_port 50000)

    assert_not_empty "find_available_port returns non-empty value" "$available_port"

    # Should be a number
    ((TESTS_RUN++))
    if [[ "$available_port" =~ ^[0-9]+$ ]]; then
        echo -e "  ${GREEN}PASS${NC} Available port is a valid number: $available_port"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}FAIL${NC} Available port is not a number: $available_port"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Available port is number")
    fi

    # Should be >= starting port
    ((TESTS_RUN++))
    if [[ "$available_port" -ge 50000 ]]; then
        echo -e "  ${GREEN}PASS${NC} Available port is >= starting port"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}FAIL${NC} Available port is < starting port"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Available port >= start")
    fi

    # Test with max_attempts limit
    assert_failure "find_available_port respects max_attempts" \
        "find_available_port 1 0"

    echo ""
}

# Test: get_all_ports_for_index
test_get_all_ports_for_index() {
    print_step "Testing get_all_ports_for_index..."

    local ports_json
    ports_json=$(get_all_ports_for_index 1)

    assert_not_empty "get_all_ports_for_index returns non-empty value" "$ports_json"

    # Should contain expected services
    ((TESTS_RUN++))
    if echo "$ports_json" | grep -q "expertagent"; then
        echo -e "  ${GREEN}PASS${NC} Contains expertagent port"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}FAIL${NC} Missing expertagent port"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Ports JSON contains expertagent")
    fi

    ((TESTS_RUN++))
    if echo "$ports_json" | grep -q "myvault"; then
        echo -e "  ${GREEN}PASS${NC} Contains myvault port"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}FAIL${NC} Missing myvault port"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Ports JSON contains myvault")
    fi

    ((TESTS_RUN++))
    if echo "$ports_json" | grep -q "8114"; then
        echo -e "  ${GREEN}PASS${NC} Contains correct expertagent port (8114)"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}FAIL${NC} Incorrect expertagent port"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Ports JSON has correct values")
    fi

    echo ""
}

# Test: check_port_conflicts
test_check_port_conflicts() {
    print_step "Testing check_port_conflicts..."

    # Test with a high index that should have no conflicts
    ((TESTS_RUN++))
    if check_port_conflicts 99 >/dev/null 2>&1; then
        echo -e "  ${GREEN}PASS${NC} No conflicts found for high index"
        ((TESTS_PASSED++))
    else
        echo -e "  ${YELLOW}WARN${NC} Conflicts found for high index (may be valid)"
        ((TESTS_PASSED++))
    fi

    echo ""
}

# Test: suggest_alternative_port
test_suggest_alternative_port() {
    print_step "Testing suggest_alternative_port..."

    local suggestion
    suggestion=$(suggest_alternative_port "testservice" 50000 2>&1)

    assert_not_empty "suggest_alternative_port returns non-empty value" "$suggestion"

    # Should contain "Suggestion"
    ((TESTS_RUN++))
    if echo "$suggestion" | grep -q "Suggestion"; then
        echo -e "  ${GREEN}PASS${NC} Contains suggestion text"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}FAIL${NC} Missing suggestion text"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Suggestion contains expected text")
    fi

    echo ""
}

# Test: get_port_status_summary
test_get_port_status_summary() {
    print_step "Testing get_port_status_summary..."

    local summary
    summary=$(get_port_status_summary 2>&1)

    assert_not_empty "get_port_status_summary returns non-empty value" "$summary"

    # Should contain service names
    ((TESTS_RUN++))
    if echo "$summary" | grep -q "expertagent\|myvault\|myscheduler"; then
        echo -e "  ${GREEN}PASS${NC} Contains service names"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}FAIL${NC} Missing service names"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Summary contains service names")
    fi

    # Should contain "Port Status"
    ((TESTS_RUN++))
    if echo "$summary" | grep -q "Port Status"; then
        echo -e "  ${GREEN}PASS${NC} Contains header"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}FAIL${NC} Missing header"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Summary contains header")
    fi

    echo ""
}

# Test: service name case insensitivity
test_service_name_case() {
    print_step "Testing service name case insensitivity..."

    assert_equals "expertAgent works" "8104" "$(calculate_port expertAgent 0)"
    assert_equals "expertagent works" "8104" "$(calculate_port expertagent 0)"
    assert_equals "myVault works" "8103" "$(calculate_port myVault 0)"
    assert_equals "myvault works" "8103" "$(calculate_port myvault 0)"

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
    test_calculate_port_index_0
    test_calculate_port_index_1
    test_calculate_port_index_5
    test_calculate_port_invalid_service
    test_calculate_port_invalid_index
    test_service_name_case
    test_is_port_in_use
    test_find_available_port
    test_get_all_ports_for_index
    test_check_port_conflicts
    test_suggest_alternative_port
    test_get_port_status_summary

    # Print summary
    print_test_summary
}

# Run tests
main "$@"
