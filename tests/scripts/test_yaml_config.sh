#!/bin/bash

# Test script for YAML Configuration Loader (Issue #147)
# Tests the config-loader.sh module and YAML configuration files

set -euo pipefail

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Load the config loader
source "${PROJECT_ROOT}/scripts/config-loader.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

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
    echo -e "${CYAN}║${NC}         ${WHITE}YAML Configuration Loader Test Suite (Issue #147)${NC}         ${CYAN}║${NC}"
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
        echo -e "${RED}FAIL${NC} (expected: '$expected', got: '$actual')"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("$test_name")
        return 1
    fi
}

assert_contains() {
    local test_name="$1"
    local substring="$2"
    local full_string="$3"

    ((TESTS_RUN++))
    echo -n "  Testing: ${test_name}... "

    if [[ "$full_string" == *"$substring"* ]]; then
        echo -e "${GREEN}PASS${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}FAIL${NC} (substring '$substring' not found in '$full_string')"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("$test_name")
        return 1
    fi
}

# Print test results
print_test_results() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}                         ${WHITE}Test Results${NC}                              ${CYAN}║${NC}"
    echo -e "${CYAN}╠══════════════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  Total Tests:   ${WHITE}$TESTS_RUN${NC}                                                  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  Passed:        ${GREEN}$TESTS_PASSED${NC}                                                  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  Failed:        ${RED}$TESTS_FAILED${NC}                                                  ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════╝${NC}"

    if [[ $TESTS_FAILED -gt 0 ]]; then
        echo ""
        echo -e "${RED}Failed Tests:${NC}"
        for test in "${FAILED_TESTS[@]}"; do
            echo -e "  ${RED}✗${NC} $test"
        done
        echo ""
        return 1
    else
        echo ""
        echo -e "${GREEN}✓ All tests passed!${NC}"
        echo ""
        return 0
    fi
}

# =============================================================================
# Test Suite: YAML Parser Detection
# =============================================================================

test_yaml_parser_detection() {
    echo -e "${WHITE}Testing YAML Parser Detection...${NC}"

    # Test: Parser mode should be set
    assert_success "Parser mode is set" "[[ -n '$YAML_PARSER_MODE' ]]"

    # Test: Parser should be either 'yq' or 'python'
    assert_success "Parser mode is valid" "[[ '$YAML_PARSER_MODE' == 'yq' || '$YAML_PARSER_MODE' == 'python' ]]"

    echo ""
}

# =============================================================================
# Test Suite: YAML File Validation
# =============================================================================

test_yaml_file_validation() {
    echo -e "${WHITE}Testing YAML File Validation...${NC}"

    # Test: services.yaml exists
    assert_success "services.yaml exists" "[[ -f '$DEFAULT_SERVICES_CONFIG' ]]"

    # Test: dependencies.yaml exists
    assert_success "dependencies.yaml exists" "[[ -f '$DEFAULT_DEPENDENCIES_CONFIG' ]]"

    # Test: services.yaml is valid YAML
    assert_success "services.yaml is valid" "validate_yaml '$DEFAULT_SERVICES_CONFIG'"

    # Test: dependencies.yaml is valid YAML
    assert_success "dependencies.yaml is valid" "validate_yaml '$DEFAULT_DEPENDENCIES_CONFIG'"

    echo ""
}

# =============================================================================
# Test Suite: Service Configuration Loading
# =============================================================================

test_service_configuration_loading() {
    echo -e "${WHITE}Testing Service Configuration Loading...${NC}"

    # Test: Can load services configuration
    assert_success "Load services configuration" "load_services_config >/dev/null"

    # Test: Services count is correct (should be 7)
    local service_count
    service_count=$(get_service_count)
    assert_equals "Service count is 7" "7" "$service_count"

    # Test: Can get service by name (JobQueue)
    assert_success "Get JobQueue service" "get_service_by_name 'JobQueue' >/dev/null"

    # Test: JobQueue port is 8001
    local jobqueue_port
    jobqueue_port=$(get_service_property "JobQueue" "port")
    assert_equals "JobQueue port is 8001" "8001" "$jobqueue_port"

    # Test: MyScheduler port is 8002
    local myscheduler_port
    myscheduler_port=$(get_service_property "MyScheduler" "port")
    assert_equals "MyScheduler port is 8002" "8002" "$myscheduler_port"

    # Test: MyAgentDesk port is 8000
    local myagentdesk_port
    myagentdesk_port=$(get_service_property "MyAgentDesk" "port")
    assert_equals "MyAgentDesk port is 8000" "8000" "$myagentdesk_port"

    # Test: CommonUI port is 8501
    local commonui_port
    commonui_port=$(get_service_property "CommonUI" "port")
    assert_equals "CommonUI port is 8501" "8501" "$commonui_port"

    echo ""
}

# =============================================================================
# Test Suite: Dependencies Configuration
# =============================================================================

test_dependencies_configuration() {
    echo -e "${WHITE}Testing Dependencies Configuration...${NC}"

    # Test: Can load dependencies configuration
    assert_success "Load dependencies configuration" "load_dependencies_config >/dev/null"

    # Test: Can get startup order
    assert_success "Get startup order" "get_startup_order >/dev/null"

    # Test: Startup order includes all services
    local startup_order
    startup_order=$(get_startup_order | tr '\n' ' ')
    assert_contains "Startup order includes JobQueue" "JobQueue" "$startup_order"
    assert_contains "Startup order includes MyScheduler" "MyScheduler" "$startup_order"
    assert_contains "Startup order includes MyAgentDesk" "MyAgentDesk" "$startup_order"
    assert_contains "Startup order includes CommonUI" "CommonUI" "$startup_order"

    # Test: UI services start last (depends on all backend services)
    local last_two_services
    last_two_services=$(get_startup_order | tail -2 | tr '\n' ' ')
    if [[ "$last_two_services" == *"MyAgentDesk"* ]] && [[ "$last_two_services" == *"CommonUI"* ]]; then
        echo -e "  ${GREEN}✓${NC} UI services (MyAgentDesk, CommonUI) start last"
        ((TESTS_PASSED++))
        ((TESTS_RUN++))
    else
        echo -e "  ${RED}✗${NC} UI services should start last (got: $last_two_services)"
        ((TESTS_FAILED++))
        ((TESTS_RUN++))
        FAILED_TESTS+=("UI services start last")
    fi

    echo ""
}

# =============================================================================
# Test Suite: Error Handling
# =============================================================================

test_error_handling() {
    echo -e "${WHITE}Testing Error Handling...${NC}"

    # Test: Invalid YAML file path returns error
    assert_success "Invalid file path returns error" "! validate_yaml '/nonexistent/file.yaml' 2>/dev/null"

    # Test: Malformed YAML is detected
    local temp_yaml="/tmp/malformed_$$.yaml"
    echo "invalid: yaml: syntax: [broken" > "$temp_yaml"
    assert_success "Malformed YAML detected" "! validate_yaml '$temp_yaml' 2>/dev/null"
    rm -f "$temp_yaml"

    echo ""
}

# =============================================================================
# Test Suite: Backward Compatibility
# =============================================================================

test_backward_compatibility() {
    echo -e "${WHITE}Testing Backward Compatibility...${NC}"

    # Test: Default ports match hardcoded values from dev-start.sh
    local jobqueue_port=$(get_service_property "JobQueue" "port")
    assert_equals "JobQueue default port matches" "8001" "$jobqueue_port"

    local myscheduler_port=$(get_service_property "MyScheduler" "port")
    assert_equals "MyScheduler default port matches" "8002" "$myscheduler_port"

    local myvault_port=$(get_service_property "MyVault" "port")
    assert_equals "MyVault default port matches" "8003" "$myvault_port"

    local expertagent_port=$(get_service_property "ExpertAgent" "port")
    assert_equals "ExpertAgent default port matches" "8004" "$expertagent_port"

    local graphaiserver_port=$(get_service_property "GraphAiServer" "port")
    assert_equals "GraphAiServer default port matches" "8005" "$graphaiserver_port"

    local myagentdesk_port=$(get_service_property "MyAgentDesk" "port")
    assert_equals "MyAgentDesk default port matches" "8000" "$myagentdesk_port"

    local commonui_port=$(get_service_property "CommonUI" "port")
    assert_equals "CommonUI default port matches" "8501" "$commonui_port"

    echo ""
}

# =============================================================================
# Main Test Runner
# =============================================================================

main() {
    print_test_header

    # Check prerequisites
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    if ! check_yaml_parser; then
        echo -e "${RED}Error: YAML parser not available${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ YAML Parser available: $YAML_PARSER_MODE${NC}"
    echo ""

    # Run test suites
    test_yaml_parser_detection
    test_yaml_file_validation
    test_service_configuration_loading
    test_dependencies_configuration
    test_error_handling
    test_backward_compatibility

    # Print results and exit
    print_test_results
}

# Run tests
main "$@"
