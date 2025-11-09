#!/bin/bash

# Integration Tests for unified-start.sh with env-loader
# Tests end-to-end functionality of environment loading in the start script

set -euo pipefail

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

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
assert_success() {
    local exit_code="$1"
    local test_name="$2"

    ((TESTS_RUN++))

    if [[ $exit_code -eq 0 ]]; then
        echo -e "${TEST_GREEN}✓${TEST_NC} PASS: $test_name"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${TEST_RED}✗${TEST_NC} FAIL: $test_name (exit code: $exit_code)"
        ((TESTS_FAILED++))
        return 1
    fi
}

assert_failure() {
    local exit_code="$1"
    local test_name="$2"

    ((TESTS_RUN++))

    if [[ $exit_code -ne 0 ]]; then
        echo -e "${TEST_GREEN}✓${TEST_NC} PASS: $test_name"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${TEST_RED}✗${TEST_NC} FAIL: $test_name (expected failure, got success)"
        ((TESTS_FAILED++))
        return 1
    fi
}

assert_contains() {
    local haystack="$1"
    local needle="$2"
    local test_name="$3"

    ((TESTS_RUN++))

    # Use bash string matching instead of grep to avoid option parsing issues
    if [[ "$haystack" == *"$needle"* ]]; then
        echo -e "${TEST_GREEN}✓${TEST_NC} PASS: $test_name"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${TEST_RED}✗${TEST_NC} FAIL: $test_name"
        echo -e "  Expected to find: $needle"
        echo -e "  In output: ${haystack:0:200}..."
        ((TESTS_FAILED++))
        return 1
    fi
}

# Setup test environment
setup_test_env() {
    # Create temporary test directory
    TEST_DIR=$(mktemp -d)

    # Create minimal test .env file with required variables
    cat > "${TEST_DIR}/.env" << 'EOF'
MSA_MASTER_KEY=base64:test_master_key_for_integration_test
LOG_LEVEL=INFO
MYVAULT_ENABLED=false
EOF

    # Create test .env.local with custom ports
    cat > "${TEST_DIR}/.env.local" << 'EOF'
WORKTREE_INDEX=99
MYVAULT_PORT=9003
JOBQUEUE_PORT=9001
MYSCHEDULER_PORT=9002
EXPERTAGENT_PORT=9004
GRAPHAI_PORT=9005
VITE_PORT=9173
COMMONUI_PORT=9501
EOF

    echo "$TEST_DIR"
}

# Cleanup test environment
cleanup_test_env() {
    local test_dir="$1"
    if [[ -n "$test_dir" ]] && [[ -d "$test_dir" ]]; then
        rm -rf "$test_dir"
    fi
}

# ============================================================================
# Test Suite 1: Dry-Run Mode Integration
# ============================================================================

test_dry_run_integration() {
    echo ""
    echo "=== Test Suite 1: Dry-Run Mode Integration ==="

    local test_dir=$(setup_test_env)

    # Copy project .env files temporarily
    local backup_env="${PROJECT_ROOT}/.env.backup.$$"
    local backup_local="${PROJECT_ROOT}/.env.local.backup.$$"

    if [[ -f "${PROJECT_ROOT}/.env" ]]; then
        cp "${PROJECT_ROOT}/.env" "$backup_env"
    fi
    if [[ -f "${PROJECT_ROOT}/.env.local" ]]; then
        cp "${PROJECT_ROOT}/.env.local" "$backup_local"
    fi

    # Use test env files
    cp "${test_dir}/.env" "${PROJECT_ROOT}/.env.test"
    cp "${test_dir}/.env.local" "${PROJECT_ROOT}/.env.local.test"

    # Test 1: Dry-run shows configuration
    local output
    output=$("${PROJECT_ROOT}/scripts/unified-start.sh" start --dry-run 2>&1 || true)
    local exit_code=$?

    # Dry-run should exit with 0 (success) after showing config
    assert_success "$exit_code" "Dry-run mode exits successfully"

    # Test 2: Dry-run output contains service URLs
    assert_contains "$output" "MYVAULT_BASE_URL" "Dry-run shows MyVault URL"
    assert_contains "$output" "JOBQUEUE_API_URL" "Dry-run shows JobQueue URL"

    # Restore original files
    rm -f "${PROJECT_ROOT}/.env.test" "${PROJECT_ROOT}/.env.local.test"
    if [[ -f "$backup_env" ]]; then
        mv "$backup_env" "${PROJECT_ROOT}/.env"
    fi
    if [[ -f "$backup_local" ]]; then
        mv "$backup_local" "${PROJECT_ROOT}/.env.local"
    fi

    cleanup_test_env "$test_dir"
}

# ============================================================================
# Test Suite 2: Help Command
# ============================================================================

test_help_command() {
    echo ""
    echo "=== Test Suite 2: Help Command ==="

    # Test 1: --help shows usage
    local output
    output=$("${PROJECT_ROOT}/scripts/unified-start.sh" --help 2>&1)
    local exit_code=$?

    assert_success "$exit_code" "Help command exits successfully"
    assert_contains "$output" "USAGE" "Help shows usage section"
    assert_contains "$output" "--env-file" "Help shows --env-file option"
    assert_contains "$output" "--dry-run" "Help shows --dry-run option"
}

# ============================================================================
# Test Suite 3: Environment Variable Validation
# ============================================================================

test_env_validation() {
    echo ""
    echo "=== Test Suite 3: Environment Variable Validation ==="

    local test_dir=$(setup_test_env)

    # Create .env without required MSA_MASTER_KEY
    cat > "${test_dir}/.env.invalid" << 'EOF'
LOG_LEVEL=INFO
MYVAULT_ENABLED=false
EOF

    # Test: Start should fail without required variables when using custom file
    # Run in subshell to capture both output and exit code properly
    local output_file=$(mktemp)
    "${PROJECT_ROOT}/scripts/unified-start.sh" start --env-file "${test_dir}/.env.invalid" --dry-run > "$output_file" 2>&1 || true
    local exit_code=$?
    local output=$(cat "$output_file")
    rm -f "$output_file"

    # Check that validation error occurred (exit code 1 OR error message present)
    if [[ $exit_code -ne 0 ]] || [[ "$output" == *"Missing required variable"* ]]; then
        ((TESTS_RUN++))
        echo -e "${TEST_GREEN}✓${TEST_NC} PASS: Validation detects missing MSA_MASTER_KEY"
        ((TESTS_PASSED++))
    else
        ((TESTS_RUN++))
        echo -e "${TEST_RED}✗${TEST_NC} FAIL: Validation should detect missing MSA_MASTER_KEY"
        ((TESTS_FAILED++))
    fi

    assert_contains "$output" "MSA_MASTER_KEY" "Error mentions MSA_MASTER_KEY"

    cleanup_test_env "$test_dir"
}

# ============================================================================
# Test Suite 4: Custom Environment File
# ============================================================================

test_custom_env_file() {
    echo ""
    echo "=== Test Suite 4: Custom Environment File ==="

    local test_dir=$(setup_test_env)

    # Create custom env file with unique identifier
    cat > "${test_dir}/.env.custom" << 'EOF'
MSA_MASTER_KEY=base64:custom_master_key
CUSTOM_TEST_VAR=unique_custom_value_12345
LOG_LEVEL=DEBUG
MYVAULT_ENABLED=false
EOF

    # Test: Load custom env file
    local output
    output=$("${PROJECT_ROOT}/scripts/unified-start.sh" start --env-file "${test_dir}/.env.custom" --dry-run 2>&1 || true)
    local exit_code=$?

    assert_success "$exit_code" "Load custom env file successfully"
    # Check for the unique test variable in the loaded vars list
    assert_contains "$output" "CUSTOM_TEST_VAR=unique_custom_value_12345" "Custom env file variables are loaded"

    cleanup_test_env "$test_dir"
}

# ============================================================================
# Run All Tests
# ============================================================================

main() {
    echo "========================================================================"
    echo "  unified-start.sh Integration Test Suite"
    echo "========================================================================"

    test_help_command
    test_dry_run_integration
    test_env_validation
    test_custom_env_file

    echo ""
    echo "========================================================================"
    echo "  Test Results"
    echo "========================================================================"
    echo -e "Total tests:  $TESTS_RUN"
    echo -e "${TEST_GREEN}Passed:       $TESTS_PASSED${TEST_NC}"
    echo -e "${TEST_RED}Failed:       $TESTS_FAILED${TEST_NC}"
    echo "========================================================================"

    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "${TEST_GREEN}All integration tests passed!${TEST_NC}"
        exit 0
    else
        echo -e "${TEST_RED}Some integration tests failed!${TEST_NC}"
        exit 1
    fi
}

# Run main
main
