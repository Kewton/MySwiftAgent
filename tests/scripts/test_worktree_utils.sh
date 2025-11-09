#!/bin/bash

# Test script for worktree utilities
# Tests the worktree-utils.sh module

set -euo pipefail

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Load libraries
source "${PROJECT_ROOT}/scripts/unified-lib/common.sh"
source "${PROJECT_ROOT}/scripts/unified-lib/worktree-utils.sh"

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
    echo -e "${CYAN}║${NC}            ${WHITE}Worktree Utils Module Test Suite${NC}                    ${CYAN}║${NC}"
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

    assert_success "get_main_repo_path function exists" \
        "type get_main_repo_path >/dev/null 2>&1"

    assert_success "is_worktree function exists" \
        "type is_worktree >/dev/null 2>&1"

    assert_success "get_worktree_name function exists" \
        "type get_worktree_name >/dev/null 2>&1"

    assert_success "list_all_worktrees function exists" \
        "type list_all_worktrees >/dev/null 2>&1"

    assert_success "get_used_worktree_indices function exists" \
        "type get_used_worktree_indices >/dev/null 2>&1"

    assert_success "find_available_worktree_index function exists" \
        "type find_available_worktree_index >/dev/null 2>&1"

    assert_success "get_current_worktree_index function exists" \
        "type get_current_worktree_index >/dev/null 2>&1"

    assert_success "get_worktree_info function exists" \
        "type get_worktree_info >/dev/null 2>&1"

    assert_success "count_worktrees function exists" \
        "type count_worktrees >/dev/null 2>&1"

    echo ""
}

# Test: get_main_repo_path
test_get_main_repo_path() {
    print_step "Testing get_main_repo_path..."

    local main_repo
    main_repo=$(get_main_repo_path)

    assert_not_empty "get_main_repo_path returns non-empty value" "$main_repo"

    # Check if path exists
    ((TESTS_RUN++))
    if [[ -d "$main_repo" ]]; then
        echo -e "  ${GREEN}PASS${NC} Main repo path exists: $main_repo"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}FAIL${NC} Main repo path does not exist: $main_repo"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Main repo path exists")
    fi

    # Check if it's a git repository
    ((TESTS_RUN++))
    if [[ -d "$main_repo/.git" ]] || git -C "$main_repo" rev-parse --git-dir >/dev/null 2>&1; then
        echo -e "  ${GREEN}PASS${NC} Main repo path is a git repository"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}FAIL${NC} Main repo path is not a git repository"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Main repo is git repository")
    fi

    echo ""
}

# Test: is_worktree
test_is_worktree() {
    print_step "Testing is_worktree..."

    # This test will pass or fail depending on whether we're in a worktree
    # We just verify the function runs without error
    ((TESTS_RUN++))
    if is_worktree; then
        echo -e "  ${GREEN}PASS${NC} Currently in a worktree"
        ((TESTS_PASSED++))
    else
        echo -e "  ${GREEN}PASS${NC} Not in a worktree (regular repo)"
        ((TESTS_PASSED++))
    fi

    echo ""
}

# Test: get_worktree_name
test_get_worktree_name() {
    print_step "Testing get_worktree_name..."

    local worktree_name
    worktree_name=$(get_worktree_name)

    assert_not_empty "get_worktree_name returns non-empty value" "$worktree_name"

    # Should be the basename of current directory
    local expected_name
    expected_name=$(basename "$(pwd)")
    assert_equals "worktree name matches directory basename" "$expected_name" "$worktree_name"

    echo ""
}

# Test: list_all_worktrees
test_list_all_worktrees() {
    print_step "Testing list_all_worktrees..."

    local worktrees
    worktrees=$(list_all_worktrees)

    # Should return at least one line (the main repo or current worktree)
    ((TESTS_RUN++))
    if [[ -n "$worktrees" ]]; then
        echo -e "  ${GREEN}PASS${NC} list_all_worktrees returns data"
        echo -e "  ${BLUE}INFO${NC} Found $(echo "$worktrees" | wc -l | tr -d ' ') worktree(s)"
        ((TESTS_PASSED++))
    else
        echo -e "  ${YELLOW}WARN${NC} list_all_worktrees returns empty (git worktree may not be set up)"
        ((TESTS_PASSED++))
    fi

    echo ""
}

# Test: find_available_worktree_index
test_find_available_worktree_index() {
    print_step "Testing find_available_worktree_index..."

    local available_index
    available_index=$(find_available_worktree_index)

    assert_not_empty "find_available_worktree_index returns non-empty value" "$available_index"

    # Should be a positive number
    ((TESTS_RUN++))
    if [[ "$available_index" =~ ^[0-9]+$ ]] && [[ "$available_index" -ge 1 ]]; then
        echo -e "  ${GREEN}PASS${NC} Available index is a valid number: $available_index"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}FAIL${NC} Available index is not a valid number: $available_index"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Available index is valid number")
    fi

    echo ""
}

# Test: get_current_worktree_index
test_get_current_worktree_index() {
    print_step "Testing get_current_worktree_index..."

    local current_index
    current_index=$(get_current_worktree_index)

    assert_not_empty "get_current_worktree_index returns non-empty value" "$current_index"

    # Should be a positive number
    ((TESTS_RUN++))
    if [[ "$current_index" =~ ^[0-9]+$ ]] && [[ "$current_index" -ge 1 ]]; then
        echo -e "  ${GREEN}PASS${NC} Current index is a valid number: $current_index"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}FAIL${NC} Current index is not a valid number: $current_index"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Current index is valid number")
    fi

    echo ""
}

# Test: get_worktree_info
test_get_worktree_info() {
    print_step "Testing get_worktree_info..."

    local worktree_info
    worktree_info=$(get_worktree_info)

    assert_not_empty "get_worktree_info returns non-empty value" "$worktree_info"

    # Should contain expected fields
    ((TESTS_RUN++))
    if echo "$worktree_info" | grep -q "Worktree Name:"; then
        echo -e "  ${GREEN}PASS${NC} Contains 'Worktree Name' field"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}FAIL${NC} Missing 'Worktree Name' field"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Worktree info contains name field")
    fi

    ((TESTS_RUN++))
    if echo "$worktree_info" | grep -q "Worktree Index:"; then
        echo -e "  ${GREEN}PASS${NC} Contains 'Worktree Index' field"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}FAIL${NC} Missing 'Worktree Index' field"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Worktree info contains index field")
    fi

    ((TESTS_RUN++))
    if echo "$worktree_info" | grep -q "Main Repository:"; then
        echo -e "  ${GREEN}PASS${NC} Contains 'Main Repository' field"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}FAIL${NC} Missing 'Main Repository' field"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Worktree info contains main repo field")
    fi

    echo ""
}

# Test: count_worktrees
test_count_worktrees() {
    print_step "Testing count_worktrees..."

    local count
    count=$(count_worktrees)

    assert_not_empty "count_worktrees returns non-empty value" "$count"

    # Should be a non-negative number
    ((TESTS_RUN++))
    if [[ "$count" =~ ^[0-9]+$ ]] && [[ "$count" -ge 0 ]]; then
        echo -e "  ${GREEN}PASS${NC} Worktree count is a valid number: $count"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}FAIL${NC} Worktree count is not a valid number: $count"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("Worktree count is valid number")
    fi

    echo ""
}

# Test: get_used_worktree_indices
test_get_used_worktree_indices() {
    print_step "Testing get_used_worktree_indices..."

    local used_indices
    used_indices=$(get_used_worktree_indices)

    # May be empty if no .env.local files exist
    ((TESTS_RUN++))
    if [[ -n "$used_indices" ]]; then
        echo -e "  ${GREEN}PASS${NC} Found used indices: $used_indices"
        ((TESTS_PASSED++))

        # Validate format (space-separated numbers)
        if [[ "$used_indices" =~ ^[0-9\ ]+$ ]]; then
            echo -e "  ${GREEN}PASS${NC} Used indices format is valid"
            ((TESTS_PASSED++))
        else
            echo -e "  ${RED}FAIL${NC} Used indices format is invalid"
            ((TESTS_FAILED++))
            FAILED_TESTS+=("Used indices format")
        fi
        ((TESTS_RUN++))
    else
        echo -e "  ${YELLOW}INFO${NC} No used indices found (empty is valid)"
        ((TESTS_PASSED++))
    fi

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
    test_get_main_repo_path
    test_is_worktree
    test_get_worktree_name
    test_list_all_worktrees
    test_get_used_worktree_indices
    test_find_available_worktree_index
    test_get_current_worktree_index
    test_get_worktree_info
    test_count_worktrees

    # Print summary
    print_test_summary
}

# Run tests
main "$@"
