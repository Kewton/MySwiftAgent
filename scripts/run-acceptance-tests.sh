#!/bin/bash
# =============================================================================
# MySwiftAgent Python Acceptance Test Runner
# =============================================================================
#
# This script runs Python acceptance tests for the MySwiftAgent project.
# It supports layer-based test execution (platform, agent, e2e) with
# automatic service dependency management.
#
# Usage:
#   ./scripts/run-acceptance-tests.sh --layer platform
#   ./scripts/run-acceptance-tests.sh --layer agent
#   ./scripts/run-acceptance-tests.sh --layer e2e
#   ./scripts/run-acceptance-tests.sh --all
#
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

# Script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Test configuration
TEST_BASE_DIR="$PROJECT_ROOT/tests/acceptance/python"
REPORT_DIR="$PROJECT_ROOT/test-reports/acceptance"
PYTEST_INI="$TEST_BASE_DIR/pytest.ini"

# Service ports
MYVAULT_PORT="${MYVAULT_PORT:-8003}"
JOBQUEUE_PORT="${JOBQUEUE_PORT:-8001}"
EXPERTAGENT_PORT="${EXPERTAGENT_PORT:-8004}"

# Health check configuration
HEALTH_CHECK_TIMEOUT="${HEALTH_CHECK_TIMEOUT:-60}"
HEALTH_CHECK_INTERVAL="${HEALTH_CHECK_INTERVAL:-5}"

# Default values
LAYER=""
RUN_ALL=false
SKIP_HEALTH_CHECK=false
AUTO_START_SERVICES=false
VERBOSE=false
DRY_RUN=false
PYTEST_EXTRA_ARGS=""

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo -e "${CYAN}"
    echo "=============================================="
    echo "  MySwiftAgent Acceptance Test Runner"
    echo "=============================================="
    echo -e "${NC}"
}

print_step() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')] >>> $1${NC}"
}

print_info() {
    echo -e "${CYAN}[$(date '+%H:%M:%S')] $1${NC}"
}

print_success() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')] $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] $1${NC}"
}

print_error() {
    echo -e "${RED}[$(date '+%H:%M:%S')] $1${NC}"
}

# =============================================================================
# Health Check Functions
# =============================================================================

check_service_health() {
    local service_name=$1
    local url=$2
    local timeout=${3:-5}

    if curl -sf --connect-timeout "$timeout" --max-time "$timeout" "$url" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

wait_for_service() {
    local service_name=$1
    local health_url=$2
    local max_wait=${3:-$HEALTH_CHECK_TIMEOUT}

    local elapsed=0
    print_info "Waiting for $service_name to be healthy..."

    while [ $elapsed -lt "$max_wait" ]; do
        if check_service_health "$service_name" "$health_url"; then
            print_success "$service_name is healthy"
            return 0
        fi
        sleep "$HEALTH_CHECK_INTERVAL"
        elapsed=$((elapsed + HEALTH_CHECK_INTERVAL))
        echo -n "."
    done

    echo ""
    print_error "$service_name health check timeout after ${max_wait}s"
    return 1
}

check_platform_services() {
    print_step "Checking Platform layer services..."

    local services_healthy=true

    # Check MyVault
    if check_service_health "MyVault" "http://localhost:$MYVAULT_PORT/health"; then
        print_success "MyVault is healthy (port $MYVAULT_PORT)"
    else
        print_warning "MyVault is not responding (port $MYVAULT_PORT)"
        services_healthy=false
    fi

    # Check JobQueue
    if check_service_health "JobQueue" "http://localhost:$JOBQUEUE_PORT/health"; then
        print_success "JobQueue is healthy (port $JOBQUEUE_PORT)"
    else
        print_warning "JobQueue is not responding (port $JOBQUEUE_PORT)"
        services_healthy=false
    fi

    if [ "$services_healthy" = false ]; then
        return 1
    fi

    return 0
}

check_agent_services() {
    print_step "Checking Agent layer services..."

    # First check platform services
    if ! check_platform_services; then
        print_error "Platform services are required for Agent layer tests"
        return 1
    fi

    # Check ExpertAgent
    if check_service_health "ExpertAgent" "http://localhost:$EXPERTAGENT_PORT/health"; then
        print_success "ExpertAgent is healthy (port $EXPERTAGENT_PORT)"
    else
        print_warning "ExpertAgent is not responding (port $EXPERTAGENT_PORT)"
        return 1
    fi

    return 0
}

# =============================================================================
# Service Management Functions
# =============================================================================

start_platform_services() {
    print_step "Starting Platform layer services..."

    if [ -f "$PROJECT_ROOT/Makefile" ]; then
        make -C "$PROJECT_ROOT" dev-platform
        wait_for_service "MyVault" "http://localhost:$MYVAULT_PORT/health"
        wait_for_service "JobQueue" "http://localhost:$JOBQUEUE_PORT/health"
    else
        print_error "Makefile not found. Cannot start services."
        return 1
    fi
}

start_agent_services() {
    print_step "Starting Agent layer services..."

    # Ensure platform is running first
    if ! check_platform_services; then
        start_platform_services
    fi

    if [ -f "$PROJECT_ROOT/Makefile" ]; then
        make -C "$PROJECT_ROOT" dev-agent
        wait_for_service "ExpertAgent" "http://localhost:$EXPERTAGENT_PORT/health"
    else
        print_error "Makefile not found. Cannot start services."
        return 1
    fi
}

# =============================================================================
# Test Execution Functions
# =============================================================================

setup_report_directory() {
    print_step "Setting up report directory..."
    mkdir -p "$REPORT_DIR"
    print_info "Reports will be saved to: $REPORT_DIR"
}

run_pytest() {
    local test_path=$1
    local marker=${2:-""}
    local report_name=${3:-"test-report"}

    local pytest_args=(
        "-c" "$PYTEST_INI"
        "--tb=short"
        "-v"
        "--junitxml=$REPORT_DIR/${report_name}.xml"
        "--html=$REPORT_DIR/${report_name}.html"
        "--self-contained-html"
    )

    if [ -n "$marker" ]; then
        pytest_args+=("-m" "$marker")
    fi

    if [ "$VERBOSE" = true ]; then
        pytest_args+=("-vv")
    fi

    # shellcheck disable=SC2206
    if [ -n "$PYTEST_EXTRA_ARGS" ]; then
        pytest_args+=($PYTEST_EXTRA_ARGS)
    fi

    pytest_args+=("$test_path")

    print_info "Running: uv run pytest ${pytest_args[*]}"

    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY RUN] Would execute pytest with above arguments"
        return 0
    fi

    cd "$PROJECT_ROOT"
    uv run pytest "${pytest_args[@]}" || return $?
}

test_platform() {
    print_step "Running Platform layer tests..."

    if [ "$SKIP_HEALTH_CHECK" = false ]; then
        if ! check_platform_services; then
            if [ "$AUTO_START_SERVICES" = true ]; then
                start_platform_services
            else
                print_error "Platform services are not running."
                print_info "Start services with: make dev-platform"
                print_info "Or use --auto-start to start them automatically"
                return 1
            fi
        fi
    fi

    run_pytest "$TEST_BASE_DIR/platform" "platform" "platform-tests"
}

test_agent() {
    print_step "Running Agent layer tests..."

    if [ "$SKIP_HEALTH_CHECK" = false ]; then
        if ! check_agent_services; then
            if [ "$AUTO_START_SERVICES" = true ]; then
                start_agent_services
            else
                print_error "Agent services are not running."
                print_info "Start services with: make dev-agent"
                print_info "Or use --auto-start to start them automatically"
                return 1
            fi
        fi
    fi

    run_pytest "$TEST_BASE_DIR/agent" "agent" "agent-tests"
}

test_e2e() {
    print_step "Running E2E tests..."

    if [ "$SKIP_HEALTH_CHECK" = false ]; then
        if ! check_agent_services; then
            if [ "$AUTO_START_SERVICES" = true ]; then
                start_agent_services
            else
                print_error "All services are required for E2E tests."
                print_info "Start services with: make dev-all"
                print_info "Or use --auto-start to start them automatically"
                return 1
            fi
        fi
    fi

    run_pytest "$TEST_BASE_DIR/e2e" "e2e" "e2e-tests"
}

run_all_tests() {
    print_step "Running all acceptance tests..."

    local exit_code=0

    # Run platform tests
    if ! test_platform; then
        print_warning "Platform tests failed"
        exit_code=1
    fi

    # Run agent tests
    if ! test_agent; then
        print_warning "Agent tests failed"
        exit_code=1
    fi

    # Run e2e tests
    if ! test_e2e; then
        print_warning "E2E tests failed"
        exit_code=1
    fi

    return $exit_code
}

# =============================================================================
# Help and Usage
# =============================================================================

show_usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

MySwiftAgent Python Acceptance Test Runner

This script runs Python acceptance tests with automatic service health checks
and optional service management.

Options:
    -l, --layer LAYER     Run tests for specified layer (platform, agent, e2e)
    -a, --all             Run all acceptance tests
    -s, --skip-health     Skip service health checks
    --auto-start          Automatically start required services
    -v, --verbose         Enable verbose output
    --dry-run             Show what would be run without executing
    --pytest-args ARGS    Additional arguments to pass to pytest
    -h, --help            Show this help message

Layers:
    platform    Platform layer tests (MyVault, JobQueue, MyScheduler)
    agent       Agent layer tests (ExpertAgent, GraphAiServer)
    e2e         End-to-end tests (full stack)

Examples:
    $(basename "$0") --layer platform
    $(basename "$0") --layer agent --auto-start
    $(basename "$0") --all --verbose
    $(basename "$0") -l platform --skip-health
    $(basename "$0") --layer e2e --pytest-args "-k test_specific"

Environment Variables:
    MYVAULT_PORT            MyVault service port (default: 8003)
    JOBQUEUE_PORT           JobQueue service port (default: 8001)
    EXPERTAGENT_PORT        ExpertAgent service port (default: 8004)
    HEALTH_CHECK_TIMEOUT    Health check timeout in seconds (default: 60)
    HEALTH_CHECK_INTERVAL   Health check interval in seconds (default: 5)

Reports:
    Test reports are saved to: test-reports/acceptance/
    - JUnit XML format for CI integration
    - HTML format for human-readable reports
EOF
}

# =============================================================================
# Argument Parsing
# =============================================================================

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -l|--layer)
                LAYER="$2"
                shift 2
                ;;
            -a|--all)
                RUN_ALL=true
                shift
                ;;
            -s|--skip-health)
                SKIP_HEALTH_CHECK=true
                shift
                ;;
            --auto-start)
                AUTO_START_SERVICES=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --pytest-args)
                PYTEST_EXTRA_ARGS="$2"
                shift 2
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    # Validate layer if specified
    if [ -n "$LAYER" ]; then
        case "$LAYER" in
            platform|agent|e2e)
                ;;
            *)
                print_error "Invalid layer: $LAYER"
                print_info "Valid layers: platform, agent, e2e"
                exit 1
                ;;
        esac
    fi

    # Check if at least one option is specified
    if [ -z "$LAYER" ] && [ "$RUN_ALL" = false ]; then
        print_error "No test layer specified"
        show_usage
        exit 1
    fi
}

# =============================================================================
# Main
# =============================================================================

main() {
    print_header

    parse_arguments "$@"

    setup_report_directory

    local exit_code=0

    if [ "$RUN_ALL" = true ]; then
        run_all_tests || exit_code=$?
    elif [ -n "$LAYER" ]; then
        case "$LAYER" in
            platform)
                test_platform || exit_code=$?
                ;;
            agent)
                test_agent || exit_code=$?
                ;;
            e2e)
                test_e2e || exit_code=$?
                ;;
        esac
    fi

    echo ""
    if [ $exit_code -eq 0 ]; then
        print_success "All tests completed successfully!"
    else
        print_error "Some tests failed (exit code: $exit_code)"
    fi

    print_info "Reports available at: $REPORT_DIR"

    exit $exit_code
}

# Run main function
main "$@"
