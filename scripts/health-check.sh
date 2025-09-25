#!/bin/bash

# MySwiftAgent Health Check and Monitoring Script
# Comprehensive health monitoring for all services

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Service ports
JOBQUEUE_PORT=8001
MYSCHEDULER_PORT=8002
COMMONUI_PORT=8501

# PID files
PID_DIR="$PROJECT_ROOT/.pids"
JOBQUEUE_PID="$PID_DIR/jobqueue.pid"
MYSCHEDULER_PID="$PID_DIR/myscheduler.pid"
COMMONUI_PID="$PID_DIR/commonui.pid"

# Health check endpoints
JOBQUEUE_HEALTH="http://localhost:$JOBQUEUE_PORT/health"
MYSCHEDULER_HEALTH="http://localhost:$MYSCHEDULER_PORT/health"
JOBQUEUE_DOCS="http://localhost:$JOBQUEUE_PORT/docs"
MYSCHEDULER_DOCS="http://localhost:$MYSCHEDULER_PORT/docs"
COMMONUI_URL="http://localhost:$COMMONUI_PORT"

print_header() {
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}                    ${WHITE}MySwiftAgent Health Check${NC}                       ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_service_header() {
    local service_name=$1
    local icon=$2
    echo -e "${BLUE}┌─ $icon $service_name ─────────────────────────────────────────────┐${NC}"
}

print_service_footer() {
    echo -e "${BLUE}└───────────────────────────────────────────────────────────────────────┘${NC}"
    echo ""
}

check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

check_process() {
    local pid_file=$1
    if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        return 0  # Process is running
    else
        return 1  # Process is not running
    fi
}

check_http_endpoint() {
    local url=$1
    local timeout=${2:-5}
    if curl -sf --connect-timeout "$timeout" --max-time "$timeout" "$url" >/dev/null 2>&1; then
        return 0  # Endpoint is responding
    else
        return 1  # Endpoint is not responding
    fi
}

get_response_time() {
    local url=$1
    local timeout=${2:-5}
    curl -w '%{time_total}' -s --connect-timeout "$timeout" --max-time "$timeout" "$url" -o /dev/null 2>/dev/null || echo "timeout"
}

get_http_status() {
    local url=$1
    local timeout=${2:-5}
    curl -w '%{http_code}' -s --connect-timeout "$timeout" --max-time "$timeout" "$url" -o /dev/null 2>/dev/null || echo "000"
}

get_service_info() {
    local url=$1
    local timeout=${2:-5}
    curl -s --connect-timeout "$timeout" --max-time "$timeout" "$url" 2>/dev/null || echo "{}"
}

print_status() {
    local status=$1
    local message=$2
    case $status in
        "healthy")
            echo -e "  ${GREEN}✅ $message${NC}"
            ;;
        "warning")
            echo -e "  ${YELLOW}⚠️  $message${NC}"
            ;;
        "error")
            echo -e "  ${RED}❌ $message${NC}"
            ;;
        "info")
            echo -e "  ${BLUE}ℹ️  $message${NC}"
            ;;
    esac
}

check_jobqueue() {
    print_service_header "JobQueue API" "📋"

    # Process check
    if check_process "$JOBQUEUE_PID"; then
        local pid=$(cat "$JOBQUEUE_PID")
        print_status "healthy" "Process running (PID: $pid)"
    else
        print_status "error" "Process not running"
        print_service_footer
        return 1
    fi

    # Port check
    if check_port $JOBQUEUE_PORT; then
        print_status "healthy" "Port $JOBQUEUE_PORT is listening"
    else
        print_status "error" "Port $JOBQUEUE_PORT is not listening"
        print_service_footer
        return 1
    fi

    # Health endpoint check
    if check_http_endpoint "$JOBQUEUE_HEALTH"; then
        local response_time=$(get_response_time "$JOBQUEUE_HEALTH")
        local health_info=$(get_service_info "$JOBQUEUE_HEALTH")
        print_status "healthy" "Health endpoint responding (${response_time}s)"

        # Parse health info if available
        if command -v jq >/dev/null 2>&1 && echo "$health_info" | jq empty >/dev/null 2>&1; then
            local service_status=$(echo "$health_info" | jq -r '.status // "unknown"')
            local service_name=$(echo "$health_info" | jq -r '.service // "unknown"')
            print_status "info" "Service status: $service_status"
        fi
    else
        local status_code=$(get_http_status "$JOBQUEUE_HEALTH")
        print_status "error" "Health endpoint not responding (HTTP $status_code)"
    fi

    # Documentation check
    if check_http_endpoint "$JOBQUEUE_DOCS"; then
        print_status "info" "Documentation available at $JOBQUEUE_DOCS"
    else
        print_status "warning" "Documentation not accessible"
    fi

    print_service_footer
    return 0
}

check_myscheduler() {
    print_service_header "MyScheduler API" "⏰"

    # Process check
    if check_process "$MYSCHEDULER_PID"; then
        local pid=$(cat "$MYSCHEDULER_PID")
        print_status "healthy" "Process running (PID: $pid)"
    else
        print_status "error" "Process not running"
        print_service_footer
        return 1
    fi

    # Port check
    if check_port $MYSCHEDULER_PORT; then
        print_status "healthy" "Port $MYSCHEDULER_PORT is listening"
    else
        print_status "error" "Port $MYSCHEDULER_PORT is not listening"
        print_service_footer
        return 1
    fi

    # Health endpoint check
    if check_http_endpoint "$MYSCHEDULER_HEALTH"; then
        local response_time=$(get_response_time "$MYSCHEDULER_HEALTH")
        local health_info=$(get_service_info "$MYSCHEDULER_HEALTH")
        print_status "healthy" "Health endpoint responding (${response_time}s)"

        # Parse health info if available
        if command -v jq >/dev/null 2>&1 && echo "$health_info" | jq empty >/dev/null 2>&1; then
            local service_status=$(echo "$health_info" | jq -r '.status // "unknown"')
            local service_name=$(echo "$health_info" | jq -r '.service // "unknown"')
            print_status "info" "Service status: $service_status"
        fi
    else
        local status_code=$(get_http_status "$MYSCHEDULER_HEALTH")
        print_status "error" "Health endpoint not responding (HTTP $status_code)"
    fi

    # Documentation check
    if check_http_endpoint "$MYSCHEDULER_DOCS"; then
        print_status "info" "Documentation available at $MYSCHEDULER_DOCS"
    else
        print_status "warning" "Documentation not accessible"
    fi

    print_service_footer
    return 0
}

check_commonui() {
    print_service_header "CommonUI (Streamlit)" "🎨"

    # Process check
    if check_process "$COMMONUI_PID"; then
        local pid=$(cat "$COMMONUI_PID")
        print_status "healthy" "Process running (PID: $pid)"
    else
        print_status "error" "Process not running"
        print_service_footer
        return 1
    fi

    # Port check
    if check_port $COMMONUI_PORT; then
        print_status "healthy" "Port $COMMONUI_PORT is listening"
    else
        print_status "error" "Port $COMMONUI_PORT is not listening"
        print_service_footer
        return 1
    fi

    # HTTP check (Streamlit doesn't have /health endpoint)
    local status_code=$(get_http_status "$COMMONUI_URL")
    if [[ "$status_code" == "200" ]]; then
        local response_time=$(get_response_time "$COMMONUI_URL")
        print_status "healthy" "Web interface responding (${response_time}s)"
        print_status "info" "Access at $COMMONUI_URL"
    else
        print_status "error" "Web interface not responding (HTTP $status_code)"
    fi

    print_service_footer
    return 0
}

run_integration_tests() {
    echo -e "${PURPLE}🔗 Integration Tests${NC}"
    echo -e "${PURPLE}────────────────────${NC}"

    local tests_passed=0
    local tests_total=0

    # Test 1: JobQueue -> MyScheduler connectivity
    ((tests_total++))
    echo -n "  Testing JobQueue availability... "
    if check_http_endpoint "$JOBQUEUE_HEALTH"; then
        echo -e "${GREEN}PASS${NC}"
        ((tests_passed++))
    else
        echo -e "${RED}FAIL${NC}"
    fi

    # Test 2: MyScheduler availability
    ((tests_total++))
    echo -n "  Testing MyScheduler availability... "
    if check_http_endpoint "$MYSCHEDULER_HEALTH"; then
        echo -e "${GREEN}PASS${NC}"
        ((tests_passed++))
    else
        echo -e "${RED}FAIL${NC}"
    fi

    # Test 3: CommonUI can reach both APIs (simulate)
    ((tests_total++))
    echo -n "  Testing CommonUI backend connectivity... "
    if check_http_endpoint "$JOBQUEUE_HEALTH" && check_http_endpoint "$MYSCHEDULER_HEALTH"; then
        echo -e "${GREEN}PASS${NC}"
        ((tests_passed++))
    else
        echo -e "${RED}FAIL${NC}"
    fi

    echo ""
    echo -e "  Results: ${GREEN}$tests_passed${NC}/$tests_total tests passed"
    echo ""

    return $((tests_total - tests_passed))
}

show_system_info() {
    echo -e "${CYAN}💻 System Information${NC}"
    echo -e "${CYAN}─────────────────────${NC}"

    # OS Information
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  OS: macOS $(sw_vers -productVersion)"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "  OS: $(lsb_release -d -s 2>/dev/null || echo "Linux")"
    else
        echo "  OS: $OSTYPE"
    fi

    # Python version
    if command -v python3 >/dev/null 2>&1; then
        echo "  Python: $(python3 --version)"
    fi

    # uv version
    if command -v uv >/dev/null 2>&1; then
        echo "  uv: $(uv --version)"
    fi

    # Available memory
    if command -v free >/dev/null 2>&1; then
        local mem_info=$(free -h | grep '^Mem:' | awk '{print $3 "/" $2}')
        echo "  Memory: $mem_info used"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS memory info is more complex, simplified version
        echo "  Memory: Available"
    fi

    # Disk space
    local disk_usage=$(df -h . | tail -1 | awk '{print $4 " available"}')
    echo "  Disk: $disk_usage"

    echo ""
}

show_service_urls() {
    echo -e "${CYAN}🔗 Service URLs${NC}"
    echo -e "${CYAN}──────────────────${NC}"
    echo "  📋 JobQueue:    http://localhost:$JOBQUEUE_PORT"
    echo "     • Health:    http://localhost:$JOBQUEUE_PORT/health"
    echo "     • Docs:      http://localhost:$JOBQUEUE_PORT/docs"
    echo ""
    echo "  ⏰ MyScheduler: http://localhost:$MYSCHEDULER_PORT"
    echo "     • Health:    http://localhost:$MYSCHEDULER_PORT/health"
    echo "     • Docs:      http://localhost:$MYSCHEDULER_PORT/docs"
    echo ""
    echo "  🎨 CommonUI:    http://localhost:$COMMONUI_PORT"
    echo ""
}

monitor_services() {
    local interval=${1:-10}

    echo -e "${BLUE}🔍 Monitoring services (Ctrl+C to stop)${NC}"
    echo -e "${BLUE}Refresh interval: ${interval}s${NC}"
    echo ""

    while true; do
        clear
        print_header

        local failures=0

        check_jobqueue || ((failures++))
        check_myscheduler || ((failures++))
        check_commonui || ((failures++))

        if [[ $failures -eq 0 ]]; then
            echo -e "${GREEN}🎉 All services healthy${NC}"
        else
            echo -e "${RED}⚠️  $failures service(s) have issues${NC}"
        fi

        echo ""
        echo -e "${BLUE}Last updated: $(date)${NC}"
        echo -e "${BLUE}Next update in ${interval}s... (Ctrl+C to stop)${NC}"

        sleep "$interval"
    done
}

show_usage() {
    cat << EOF
Usage: $0 [COMMAND] [OPTIONS]

Commands:
    check       Run health checks for all services (default)
    monitor     Monitor services continuously
    test        Run integration tests
    info        Show system information
    urls        Show service URLs
    help        Show this help message

Options:
    --interval N    Monitoring refresh interval in seconds (default: 10)

Examples:
    $0                    # Run basic health check
    $0 check             # Run basic health check
    $0 monitor           # Monitor services continuously
    $0 monitor --interval 5  # Monitor with 5s refresh
    $0 test              # Run integration tests
    $0 info              # Show system information
EOF
}

main() {
    local command="check"
    local interval=10

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            check|monitor|test|info|urls|help)
                command=$1
                shift
                ;;
            --interval)
                interval=$2
                shift 2
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                echo -e "${RED}Unknown argument: $1${NC}"
                show_usage
                exit 1
                ;;
        esac
    done

    case $command in
        help)
            show_usage
            ;;
        info)
            print_header
            show_system_info
            show_service_urls
            ;;
        urls)
            show_service_urls
            ;;
        monitor)
            monitor_services "$interval"
            ;;
        test)
            print_header
            run_integration_tests
            ;;
        check)
            print_header

            local failures=0
            check_jobqueue || ((failures++))
            check_myscheduler || ((failures++))
            check_commonui || ((failures++))

            run_integration_tests || true  # Don't fail on integration tests

            if [[ $failures -eq 0 ]]; then
                echo -e "${GREEN}🎉 All services are healthy!${NC}"
                exit 0
            else
                echo -e "${RED}⚠️  $failures service(s) have issues${NC}"
                echo ""
                echo "Use './scripts/dev-start.sh status' for detailed status"
                echo "Use './scripts/dev-start.sh logs' to view logs"
                exit 1
            fi
            ;;
        *)
            echo -e "${RED}Unknown command: $command${NC}"
            show_usage
            exit 1
            ;;
    esac
}

# Handle Ctrl+C gracefully in monitor mode
trap 'echo ""; echo "Monitoring stopped."; exit 0' INT

# Run main function
main "$@"