#!/bin/bash

# MySwiftAgent Development Environment Startup Script
# Comprehensive script to start JobQueue, MyScheduler, and CommonUI services

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load project-level .env files (new policy)
# Each service has its own .env file with minimal configuration
for project in myVault jobqueue myscheduler expertAgent graphAiServer commonUI; do
    if [[ -f "$PROJECT_ROOT/$project/.env" ]]; then
        set -a
        source "$PROJECT_ROOT/$project/.env"
        set +a
    fi
done

# Service ports (can be overridden via environment variables)
JOBQUEUE_PORT="${JOBQUEUE_PORT:-8001}"
MYSCHEDULER_PORT="${MYSCHEDULER_PORT:-8002}"
MYVAULT_PORT="${MYVAULT_PORT:-8003}"
EXPERTAGENT_PORT="${EXPERTAGENT_PORT:-8004}"
GRAPHAISERVER_PORT="${GRAPHAISERVER_PORT:-8005}"
COMMONUI_PORT="${COMMONUI_PORT:-8501}"

# Automatically configure service URLs (new policy)
export JOBQUEUE_API_URL="http://localhost:${JOBQUEUE_PORT}"
export JOBQUEUE_BASE_URL="http://localhost:${JOBQUEUE_PORT}"
export MYSCHEDULER_BASE_URL="http://localhost:${MYSCHEDULER_PORT}"
export MYVAULT_BASE_URL="http://localhost:${MYVAULT_PORT}"
export EXPERTAGENT_BASE_URL="http://localhost:${EXPERTAGENT_PORT}"
export GRAPHAISERVER_BASE_URL="http://localhost:${GRAPHAISERVER_PORT}"

# Note: GraphAI workflow environment variables are automatically available from above exports

# Service directories
JOBQUEUE_DIR="$PROJECT_ROOT/jobqueue"
MYSCHEDULER_DIR="$PROJECT_ROOT/myscheduler"
MYVAULT_DIR="$PROJECT_ROOT/myVault"
EXPERTAGENT_DIR="$PROJECT_ROOT/expertAgent"
GRAPHAISERVER_DIR="$PROJECT_ROOT/graphAiServer"
COMMONUI_DIR="$PROJECT_ROOT/commonUI"

# Log and PID directories
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/.pids"

# Log files
JOBQUEUE_LOG="$LOG_DIR/jobqueue.log"
MYSCHEDULER_LOG="$LOG_DIR/myscheduler.log"
MYVAULT_LOG="$LOG_DIR/myvault.log"
EXPERTAGENT_LOG="$LOG_DIR/expertagent.log"
GRAPHAISERVER_LOG="$LOG_DIR/graphaiserver.log"
COMMONUI_LOG="$LOG_DIR/commonui.log"
SETUP_LOG="$LOG_DIR/setup.log"

# PID files
JOBQUEUE_PID="$PID_DIR/jobqueue.pid"
MYSCHEDULER_PID="$PID_DIR/myscheduler.pid"
MYVAULT_PID="$PID_DIR/myvault.pid"
EXPERTAGENT_PID="$PID_DIR/expertagent.pid"
GRAPHAISERVER_PID="$PID_DIR/graphaiserver.pid"
COMMONUI_PID="$PID_DIR/commonui.pid"

# API tokens for development
DEV_JOBQUEUE_TOKEN="dev-jobqueue-token-$(date +%s)"
DEV_MYSCHEDULER_TOKEN="dev-myscheduler-token-$(date +%s)"

# Banner
show_banner() {
    echo -e "${CYAN}"
    cat << 'EOF'
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   🚀 MySwiftAgent Development Environment                                      ║
║   ═══════════════════════════════════════                                    ║
║                                                                               ║
║   📋 JobQueue      - Job queue management API                                 ║
║   ⏰ MyScheduler   - Job scheduling service                                   ║
║   🔐 MyVault       - Secrets management service                               ║
║   🤖 ExpertAgent   - AI agent service                                         ║
║   🔄 GraphAiServer - Graph AI workflow service                                ║
║   🎨 CommonUI      - Web interface                                            ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# Print functions with timestamps and colors
print_step() {
    echo -e "${WHITE}[$(date '+%H:%M:%S')] 📋 $1${NC}"
}

print_info() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')] ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')] ✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] ⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}[$(date '+%H:%M:%S')] ❌ $1${NC}"
}

print_service() {
    local icon=$1
    local name=$2
    local message=$3
    echo -e "${PURPLE}[$(date '+%H:%M:%S')] $icon $name${NC} - $message"
}

# Initialize directories
init_directories() {
    print_step "Initializing directories..."
    mkdir -p "$LOG_DIR" "$PID_DIR"

    # Clear old logs
    > "$SETUP_LOG"
    > "$JOBQUEUE_LOG" 2>/dev/null || true
    > "$MYSCHEDULER_LOG" 2>/dev/null || true
    > "$MYVAULT_LOG" 2>/dev/null || true
    > "$EXPERTAGENT_LOG" 2>/dev/null || true
    > "$GRAPHAISERVER_LOG" 2>/dev/null || true
    > "$COMMONUI_LOG" 2>/dev/null || true

    print_success "Directories initialized"
}

# Check dependencies
check_dependencies() {
    print_step "Checking dependencies..."
    local missing_deps=0

    # Check uv
    if ! command -v uv &> /dev/null; then
        print_error "uv package manager not found"
        echo "  Install uv: https://docs.astral.sh/uv/"
        ((missing_deps++))
    else
        print_info "uv found: $(uv --version)"
    fi

    # Check npm for Node-based services
    if [[ -f "$GRAPHAISERVER_DIR/package.json" ]]; then
        if ! command -v npm &> /dev/null; then
            print_error "npm not found (required for GraphAiServer)"
            ((missing_deps++))
        else
            print_info "npm found: $(npm --version)"
        fi
    fi

    # Check curl
    if ! command -v curl &> /dev/null; then
        print_error "curl not found (needed for health checks)"
        ((missing_deps++))
    fi

    # Check project directories
    local projects=("jobqueue" "myscheduler" "commonUI" "graphAiServer")
    for project in "${projects[@]}"; do
        if [[ ! -d "$PROJECT_ROOT/$project" ]]; then
            print_error "Project directory not found: $project"
            ((missing_deps++))
        else
            print_info "Found project: $project"
        fi
    done

    if [[ $missing_deps -gt 0 ]]; then
        print_error "Missing $missing_deps dependencies. Please resolve and try again."
        return 1
    fi

    print_success "All dependencies found"
    return 0
}

# Setup development environment files
setup_dev_environment() {
    print_step "Setting up development environment..."

    # Note: CommonUI/.env is now managed as a project-level .env file
    # Service URLs are automatically configured via environment variables (see above)
    # No need to regenerate CommonUI/.env on every startup

    # Setup development tokens for APIs (if they support it)
    echo "DEV_MODE=true" > "$LOG_DIR/dev_tokens.txt"
    echo "JOBQUEUE_TOKEN=$DEV_JOBQUEUE_TOKEN" >> "$LOG_DIR/dev_tokens.txt"
    echo "MYSCHEDULER_TOKEN=$DEV_MYSCHEDULER_TOKEN" >> "$LOG_DIR/dev_tokens.txt"

    print_success "Development environment setup complete"
}

# Install dependencies for a service
install_service_deps() {
    local service=$1
    local dir=$2

    print_service "📦" "$service" "Installing dependencies..."

    if [[ ! -d "$dir" ]]; then
        print_error "$service: Directory not found ($dir)"
        return 1
    fi

    cd "$dir" || {
        print_error "$service: Cannot change to directory $dir"
        return 1
    }

    if [[ -f "pyproject.toml" ]]; then
        # Python project handled via uv
        if [[ -f "uv.lock" && -f ".venv/pyvenv.cfg" ]]; then
            print_info "$service: Dependencies already installed, checking for updates..."
            uv sync --extra dev >> "$SETUP_LOG" 2>&1 || {
                print_error "$service: Failed to sync dependencies"
                cd "$PROJECT_ROOT"
                return 1
            }
        else
            print_info "$service: Installing dependencies..."
            uv sync --extra dev >> "$SETUP_LOG" 2>&1 || {
                print_error "$service: Failed to install dependencies"
                cd "$PROJECT_ROOT"
                return 1
            }
        fi
    elif [[ -f "package.json" ]]; then
        # Node.js project handled via npm
        if ! command -v npm &> /dev/null; then
            print_error "$service: npm not found"
            cd "$PROJECT_ROOT"
            return 1
        fi

        if [[ -d "node_modules" ]]; then
            print_info "$service: Node dependencies already installed, checking for updates..."
            npm install >> "$SETUP_LOG" 2>&1 || {
                print_error "$service: Failed to install Node dependencies"
                cd "$PROJECT_ROOT"
                return 1
            }
        else
            print_info "$service: Installing Node dependencies..."
            if [[ -f "package-lock.json" ]]; then
                npm ci >> "$SETUP_LOG" 2>&1 || {
                    print_error "$service: Failed to run npm ci"
                    cd "$PROJECT_ROOT"
                    return 1
                }
            else
                npm install >> "$SETUP_LOG" 2>&1 || {
                    print_error "$service: Failed to run npm install"
                    cd "$PROJECT_ROOT"
                    return 1
                }
            fi
        fi
    else
        print_error "$service: No supported dependency manifest found (pyproject.toml or package.json)"
        cd "$PROJECT_ROOT"
        return 1
    fi

    print_success "$service: Dependencies ready"
    cd "$PROJECT_ROOT"
}

# Check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Kill process on port
kill_port() {
    local port=$1
    local service_name=$2

    if check_port $port; then
        print_warning "$service_name: Port $port is in use, attempting to free it..."
        local pid=$(lsof -ti:$port)
        if [[ -n "$pid" ]]; then
            kill -TERM $pid 2>/dev/null || true
            sleep 2
            if check_port $port; then
                kill -KILL $pid 2>/dev/null || true
                sleep 1
            fi
        fi

        if check_port $port; then
            print_error "$service_name: Could not free port $port"
            return 1
        else
            print_success "$service_name: Port $port freed"
        fi
    fi

    return 0
}

# Wait for service health check
wait_for_service() {
    local name=$1
    local url=$2
    local max_attempts=${3:-30}
    local attempt=1

    print_service "🔍" "$name" "Waiting for service to be ready..."

    while [[ $attempt -le $max_attempts ]]; do
        if curl -sf "$url/health" >/dev/null 2>&1; then
            print_success "$name: Service is ready! (attempt $attempt)"
            return 0
        fi

        if [[ $attempt -eq 1 ]]; then
            echo -n "    Checking"
        fi
        echo -n "."

        sleep 1
        ((attempt++))
    done

    echo ""
    print_error "$name: Service failed to start within $max_attempts seconds"
    return 1
}

# Start a service
start_service() {
    local name=$1
    local directory=$2
    local port=$3
    local pid_file=$4
    local log_file=$5
    local start_command=$6
    local health_endpoint=${7:-"http://localhost:$port"}

    print_service "🚀" "$name" "Starting service on port $port..."

    # Check if already running
    if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        print_warning "$name: Already running (PID: $(cat "$pid_file"))"
        return 0
    fi

    # Kill any process on the port
    if ! kill_port $port "$name"; then
        return 1
    fi

    # Change to service directory
    cd "$directory" || {
        print_error "$name: Cannot change to directory $directory"
        return 1
    }

    # Start the service
    print_info "$name: Executing: $start_command"
    nohup bash -c "$start_command" > "$log_file" 2>&1 &
    local service_pid=$!

    # Save PID
    echo $service_pid > "$pid_file"

    # Wait for service to be ready
    if wait_for_service "$name" "$health_endpoint"; then
        print_success "$name: Started successfully (PID: $service_pid, Port: $port)"
        return 0
    else
        # Service failed to start, clean up
        if kill -0 $service_pid 2>/dev/null; then
            kill -TERM $service_pid 2>/dev/null || true
            sleep 2
            kill -KILL $service_pid 2>/dev/null || true
        fi
        rm -f "$pid_file"
        print_error "$name: Failed to start"
        return 1
    fi
}

# Stop a service
stop_service() {
    local name=$1
    local pid_file=$2

    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if kill -0 $pid 2>/dev/null; then
            print_service "🛑" "$name" "Stopping service (PID: $pid)..."
            kill -TERM $pid 2>/dev/null || true

            # Wait for graceful shutdown
            local attempts=0
            while kill -0 $pid 2>/dev/null && [[ $attempts -lt 10 ]]; do
                sleep 1
                ((attempts++))
            done

            # Force kill if still running
            if kill -0 $pid 2>/dev/null; then
                print_warning "$name: Force stopping..."
                kill -KILL $pid 2>/dev/null || true
            fi

            print_success "$name: Stopped"
        else
            print_info "$name: Process not running"
        fi
        rm -f "$pid_file"
    else
        print_info "$name: PID file not found"
    fi
}

# Check service status
check_service_status() {
    local name=$1
    local pid_file=$2
    local port=$3
    local health_url="http://localhost:$port"

    if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        local pid=$(cat "$pid_file")
        if check_port $port; then
            if curl -sf "$health_url/health" >/dev/null 2>&1; then
                print_success "$name: Running healthy (PID: $pid, Port: $port)"
            else
                print_warning "$name: Running but health check failed (PID: $pid, Port: $port)"
            fi
        else
            print_warning "$name: Process exists but port $port not listening (PID: $pid)"
        fi
    else
        print_error "$name: Not running"
        rm -f "$pid_file" 2>/dev/null || true
    fi
}

# Show service URLs
show_service_urls() {
    echo ""
    print_step "Service Access URLs:"
    echo ""
    echo -e "${CYAN}┌────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│                        Service URLs                                │${NC}"
    echo -e "${CYAN}├────────────────────────────────────────────────────────────────────┤${NC}"
    echo -e "${CYAN}│${NC} 📋 JobQueue API:      ${WHITE}http://localhost:$JOBQUEUE_PORT${NC}${CYAN}                          │${NC}"
    echo -e "${CYAN}│${NC}    ↳ Health:          ${WHITE}http://localhost:$JOBQUEUE_PORT/health${NC}${CYAN}                  │${NC}"
    echo -e "${CYAN}│${NC}    ↳ Docs:            ${WHITE}http://localhost:$JOBQUEUE_PORT/docs${NC}${CYAN}                    │${NC}"
    echo -e "${CYAN}│${NC}                                                                    ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC} ⏰ MyScheduler API:   ${WHITE}http://localhost:$MYSCHEDULER_PORT${NC}${CYAN}                          │${NC}"
    echo -e "${CYAN}│${NC}    ↳ Health:          ${WHITE}http://localhost:$MYSCHEDULER_PORT/health${NC}${CYAN}                  │${NC}"
    echo -e "${CYAN}│${NC}    ↳ Docs:            ${WHITE}http://localhost:$MYSCHEDULER_PORT/docs${NC}${CYAN}                    │${NC}"
    echo -e "${CYAN}│${NC}                                                                    ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC} 🔐 MyVault API:       ${WHITE}http://localhost:$MYVAULT_PORT${NC}${CYAN}                           │${NC}"
    echo -e "${CYAN}│${NC}    ↳ Health:          ${WHITE}http://localhost:$MYVAULT_PORT/health${NC}${CYAN}                   │${NC}"
    echo -e "${CYAN}│${NC}    ↳ Docs:            ${WHITE}http://localhost:$MYVAULT_PORT/docs${NC}${CYAN}                     │${NC}"
    echo -e "${CYAN}│${NC}                                                                    ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC} 🤖 ExpertAgent API:   ${WHITE}http://localhost:$EXPERTAGENT_PORT${NC}${CYAN}                          │${NC}"
    echo -e "${CYAN}│${NC}    ↳ Health:          ${WHITE}http://localhost:$EXPERTAGENT_PORT/health${NC}${CYAN}                  │${NC}"
    echo -e "${CYAN}│${NC}    ↳ Docs:            ${WHITE}http://localhost:$EXPERTAGENT_PORT/aiagent-api/docs${NC}${CYAN}        │${NC}"
    echo -e "${CYAN}│${NC}                                                                    ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC} 🔄 GraphAiServer API: ${WHITE}http://localhost:$GRAPHAISERVER_PORT${NC}${CYAN}                          │${NC}"
    echo -e "${CYAN}│${NC}    ↳ Health:          ${WHITE}http://localhost:$GRAPHAISERVER_PORT/health${NC}${CYAN}                  │${NC}"
    echo -e "${CYAN}│${NC}                                                                    ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC} 🎨 CommonUI:          ${WHITE}http://localhost:$COMMONUI_PORT${NC}${CYAN}                           │${NC}"
    echo -e "${CYAN}└────────────────────────────────────────────────────────────────────┘${NC}"
    echo ""
}

# Show logs
show_logs() {
    local service=$1

    if [[ -z "$service" ]]; then
        print_step "Showing all service logs (last 20 lines each):"
        echo ""

        echo -e "${YELLOW}=== JobQueue Logs ===${NC}"
        tail -n 20 "$JOBQUEUE_LOG" 2>/dev/null || echo "No logs available"
        echo ""

        echo -e "${YELLOW}=== MyScheduler Logs ===${NC}"
        tail -n 20 "$MYSCHEDULER_LOG" 2>/dev/null || echo "No logs available"
        echo ""

        echo -e "${YELLOW}=== MyVault Logs ===${NC}"
        tail -n 20 "$MYVAULT_LOG" 2>/dev/null || echo "No logs available"
        echo ""

        echo -e "${YELLOW}=== ExpertAgent Logs ===${NC}"
        tail -n 20 "$EXPERTAGENT_LOG" 2>/dev/null || echo "No logs available"
        echo ""

        echo -e "${YELLOW}=== GraphAiServer Logs ===${NC}"
        tail -n 20 "$GRAPHAISERVER_LOG" 2>/dev/null || echo "No logs available"
        echo ""

        echo -e "${YELLOW}=== CommonUI Logs ===${NC}"
        tail -n 20 "$COMMONUI_LOG" 2>/dev/null || echo "No logs available"
        echo ""

        echo -e "${BLUE}Use '$0 logs <service>' to follow specific service logs${NC}"
    else
        case $service in
            jobqueue)
                print_info "Following JobQueue logs (Ctrl+C to stop):"
                tail -f "$JOBQUEUE_LOG"
                ;;
            myscheduler)
                print_info "Following MyScheduler logs (Ctrl+C to stop):"
                tail -f "$MYSCHEDULER_LOG"
                ;;
            myvault)
                print_info "Following MyVault logs (Ctrl+C to stop):"
                tail -f "$MYVAULT_LOG"
                ;;
            expertagent)
                print_info "Following ExpertAgent logs (Ctrl+C to stop):"
                tail -f "$EXPERTAGENT_LOG"
                ;;
            graphaiserver)
                print_info "Following GraphAiServer logs (Ctrl+C to stop):"
                tail -f "$GRAPHAISERVER_LOG"
                ;;
            commonui)
                print_info "Following CommonUI logs (Ctrl+C to stop):"
                tail -f "$COMMONUI_LOG"
                ;;
            setup)
                print_info "Following setup logs (Ctrl+C to stop):"
                tail -f "$SETUP_LOG"
                ;;
            *)
                print_error "Unknown service: $service"
                echo "Available services: jobqueue, myscheduler, myvault, expertagent, graphaiserver, commonui, setup"
                return 1
                ;;
        esac
    fi
}

# Run basic API tests
run_api_tests() {
    print_step "Running basic API tests..."

    # Test JobQueue
    print_info "Testing JobQueue API..."
    if curl -sf "http://localhost:$JOBQUEUE_PORT/health" >/dev/null; then
        local jobqueue_health=$(curl -s "http://localhost:$JOBQUEUE_PORT/health")
        print_success "JobQueue health check: $jobqueue_health"
    else
        print_error "JobQueue health check failed"
    fi

    # Test MyScheduler
    print_info "Testing MyScheduler API..."
    if curl -sf "http://localhost:$MYSCHEDULER_PORT/health" >/dev/null; then
        local myscheduler_health=$(curl -s "http://localhost:$MYSCHEDULER_PORT/health")
        print_success "MyScheduler health check: $myscheduler_health"
    else
        print_error "MyScheduler health check failed"
    fi

    # Test CommonUI (different approach since it's Streamlit)
    print_info "Testing CommonUI availability..."
    if check_port $COMMONUI_PORT; then
        print_success "CommonUI is responding on port $COMMONUI_PORT"
    else
        print_error "CommonUI is not responding"
    fi
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [COMMAND] [OPTIONS]

Commands:
    start       Start all services (default)
    stop        Stop all services
    restart     Restart all services
    status      Show status of all services
    logs        Show logs for all services (or specific service)
    test        Run basic API tests
    setup       Setup development environment only
    clean       Clean logs and PID files
    help        Show this help message

Service-specific commands:
    --jobqueue-only     Only operate on JobQueue service
    --myscheduler-only  Only operate on MyScheduler service
    --commonui-only     Only operate on CommonUI service

Examples:
    $0                           # Start all services
    $0 start                     # Start all services
    $0 start --jobqueue-only     # Start only JobQueue
    $0 stop                      # Stop all services
    $0 status                    # Check all service status
    $0 logs jobqueue            # Follow JobQueue logs
    $0 test                     # Run API health tests
    $0 clean                    # Clean temporary files

Development tokens:
    JobQueue:    $DEV_JOBQUEUE_TOKEN
    MyScheduler: $DEV_MYSCHEDULER_TOKEN
EOF
}

# Clean temporary files
clean_temp_files() {
    print_step "Cleaning temporary files..."

    # Stop all services first
    stop_service "CommonUI" "$COMMONUI_PID"
    stop_service "GraphAiServer" "$GRAPHAISERVER_PID"
    stop_service "ExpertAgent" "$EXPERTAGENT_PID"
    stop_service "MyVault" "$MYVAULT_PID"
    stop_service "MyScheduler" "$MYSCHEDULER_PID"
    stop_service "JobQueue" "$JOBQUEUE_PID"

    # Clean logs
    rm -f "$LOG_DIR"/*.log 2>/dev/null || true

    # Clean PID files
    rm -f "$PID_DIR"/*.pid 2>/dev/null || true

    # Note: CommonUI/.env is now managed as a project-level .env file (not auto-generated)

    print_success "Temporary files cleaned"
}

# Main execution function
main() {
    local command="start"
    local service_filter=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            start|stop|restart|status|logs|test|setup|clean|help)
                command=$1
                shift
                ;;
            --jobqueue-only)
                service_filter="jobqueue"
                shift
                ;;
            --myscheduler-only)
                service_filter="myscheduler"
                shift
                ;;
            --commonui-only)
                service_filter="commonui"
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                if [[ "$command" == "logs" && -z "$service_filter" ]]; then
                    service_filter=$1
                else
                    print_error "Unknown argument: $1"
                    show_usage
                    exit 1
                fi
                shift
                ;;
        esac
    done

    # Show banner (except for logs command)
    if [[ "$command" != "logs" ]]; then
        show_banner
    fi

    # Handle help command
    if [[ "$command" == "help" ]]; then
        show_usage
        exit 0
    fi

    # Initialize directories
    if [[ "$command" != "logs" ]]; then
        init_directories
    fi

    # Execute command
    case $command in
        setup)
            check_dependencies || exit 1
            setup_dev_environment

            # Install dependencies for all services
            if [[ -z "$service_filter" || "$service_filter" == "jobqueue" ]]; then
                install_service_deps "JobQueue" "$JOBQUEUE_DIR" || exit 1
            fi
            if [[ -z "$service_filter" || "$service_filter" == "myscheduler" ]]; then
                install_service_deps "MyScheduler" "$MYSCHEDULER_DIR" || exit 1
            fi
            if [[ -z "$service_filter" || "$service_filter" == "myvault" ]]; then
                install_service_deps "MyVault" "$MYVAULT_DIR" || exit 1
                mkdir -p "$MYVAULT_DIR/data"
            fi
            if [[ -z "$service_filter" || "$service_filter" == "expertagent" ]]; then
                install_service_deps "ExpertAgent" "$EXPERTAGENT_DIR" || exit 1
            fi
            if [[ -z "$service_filter" || "$service_filter" == "graphaiserver" ]]; then
                install_service_deps "GraphAiServer" "$GRAPHAISERVER_DIR" || exit 1
            fi
            if [[ -z "$service_filter" || "$service_filter" == "commonui" ]]; then
                install_service_deps "CommonUI" "$COMMONUI_DIR" || exit 1
            fi

            print_success "Development environment setup complete!"
            ;;

        start)
            check_dependencies || exit 1
            setup_dev_environment

            print_step "Installing dependencies and starting services..."
            echo ""

            # Start JobQueue
            if [[ -z "$service_filter" || "$service_filter" == "jobqueue" ]]; then
                install_service_deps "JobQueue" "$JOBQUEUE_DIR" || exit 1
                start_service "JobQueue" "$JOBQUEUE_DIR" $JOBQUEUE_PORT "$JOBQUEUE_PID" "$JOBQUEUE_LOG" \
                    "uv run uvicorn app.main:app --host 0.0.0.0 --port $JOBQUEUE_PORT" || exit 1
            fi

            # Start MyScheduler
            if [[ -z "$service_filter" || "$service_filter" == "myscheduler" ]]; then
                install_service_deps "MyScheduler" "$MYSCHEDULER_DIR" || exit 1
                # Note: Most env vars are loaded from myscheduler/.env
                # Override JOBQUEUE_API_URL to use local port
                start_service "MyScheduler" "$MYSCHEDULER_DIR" $MYSCHEDULER_PORT "$MYSCHEDULER_PID" "$MYSCHEDULER_LOG" \
                    "JOBQUEUE_API_URL='http://localhost:$JOBQUEUE_PORT' uv run uvicorn app.main:app --host 0.0.0.0 --port $MYSCHEDULER_PORT" || exit 1
            fi

            # Start MyVault
            if [[ -z "$service_filter" || "$service_filter" == "myvault" ]]; then
                # Check if master key is set
                if [[ -z "${MSA_MASTER_KEY}" ]]; then
                    print_warning "MyVault: MSA_MASTER_KEY not set, skipping startup"
                    print_info "MyVault: Create myVault/.env and set MSA_MASTER_KEY to enable MyVault service"
                else
                    install_service_deps "MyVault" "$MYVAULT_DIR" || exit 1
                    # Create data directory
                    mkdir -p "$MYVAULT_DIR/data"
                    # Note: Most env vars (MSA_MASTER_KEY, TOKEN_*) are loaded from myVault/.env
                    # Only override DATABASE_URL here
                    start_service "MyVault" "$MYVAULT_DIR" $MYVAULT_PORT "$MYVAULT_PID" "$MYVAULT_LOG" \
                        "DATABASE_URL='sqlite:///./data/myvault.db' uv run uvicorn app.main:app --host 0.0.0.0 --port $MYVAULT_PORT" || print_warning "MyVault: Failed to start (check logs for details)"
                fi
            fi

            # Start ExpertAgent
            if [[ -z "$service_filter" || "$service_filter" == "expertagent" ]]; then
                install_service_deps "ExpertAgent" "$EXPERTAGENT_DIR" || exit 1
                # Note: Most env vars are loaded from expertAgent/.env
                # Only override MYVAULT_BASE_URL and PORT here
                start_service "ExpertAgent" "$EXPERTAGENT_DIR" $EXPERTAGENT_PORT "$EXPERTAGENT_PID" "$EXPERTAGENT_LOG" \
                    "MYVAULT_BASE_URL='http://localhost:$MYVAULT_PORT' uv run uvicorn app.main:app --host 0.0.0.0 --port $EXPERTAGENT_PORT --workers 4" || exit 1
            fi

            # Start GraphAiServer
            if [[ -z "$service_filter" || "$service_filter" == "graphaiserver" ]]; then
                install_service_deps "GraphAiServer" "$GRAPHAISERVER_DIR" || exit 1
                start_service "GraphAiServer" "$GRAPHAISERVER_DIR" $GRAPHAISERVER_PORT "$GRAPHAISERVER_PID" "$GRAPHAISERVER_LOG" \
                    "PORT=$GRAPHAISERVER_PORT npm start" || exit 1
            fi

            # Start CommonUI
            if [[ -z "$service_filter" || "$service_filter" == "commonui" ]]; then
                install_service_deps "CommonUI" "$COMMONUI_DIR" || exit 1

                # Wait a bit for backend services
                if [[ -z "$service_filter" ]]; then
                    print_info "Waiting for backend services to stabilize..."
                    sleep 3
                fi

                print_service "🎨" "CommonUI" "Starting Streamlit application..."
                cd "$COMMONUI_DIR"
                nohup bash -c "uv run streamlit run Home.py --server.port $COMMONUI_PORT --server.headless true" > "$COMMONUI_LOG" 2>&1 &
                echo $! > "$COMMONUI_PID"
                cd "$PROJECT_ROOT"

                # Wait for CommonUI (different check)
                sleep 5
                if check_port $COMMONUI_PORT; then
                    print_success "CommonUI: Started successfully (Port: $COMMONUI_PORT)"
                else
                    print_error "CommonUI: Failed to start"
                fi
            fi

            echo ""
            print_success "🎉 All services started successfully!"
            show_service_urls

            print_info "Use '$0 status' to check service health"
            print_info "Use '$0 logs' to view all logs or '$0 logs <service>' for specific service"
            print_info "Use '$0 stop' to stop all services"
            ;;

        stop)
            print_step "Stopping all services..."
            if [[ -z "$service_filter" || "$service_filter" == "commonui" ]]; then
                stop_service "CommonUI" "$COMMONUI_PID"
            fi
            if [[ -z "$service_filter" || "$service_filter" == "graphaiserver" ]]; then
                stop_service "GraphAiServer" "$GRAPHAISERVER_PID"
            fi
            if [[ -z "$service_filter" || "$service_filter" == "expertagent" ]]; then
                stop_service "ExpertAgent" "$EXPERTAGENT_PID"
            fi
            if [[ -z "$service_filter" || "$service_filter" == "myvault" ]]; then
                stop_service "MyVault" "$MYVAULT_PID"
            fi
            if [[ -z "$service_filter" || "$service_filter" == "myscheduler" ]]; then
                stop_service "MyScheduler" "$MYSCHEDULER_PID"
            fi
            if [[ -z "$service_filter" || "$service_filter" == "jobqueue" ]]; then
                stop_service "JobQueue" "$JOBQUEUE_PID"
            fi
            print_success "All services stopped"
            ;;

        restart)
            print_step "Restarting services..."
            $0 stop $service_filter
            sleep 3
            $0 start $service_filter
            ;;

        status)
            print_step "Service Status Check:"
            echo ""
            if [[ -z "$service_filter" || "$service_filter" == "jobqueue" ]]; then
                check_service_status "JobQueue" "$JOBQUEUE_PID" $JOBQUEUE_PORT
            fi
            if [[ -z "$service_filter" || "$service_filter" == "myscheduler" ]]; then
                check_service_status "MyScheduler" "$MYSCHEDULER_PID" $MYSCHEDULER_PORT
            fi
            if [[ -z "$service_filter" || "$service_filter" == "myvault" ]]; then
                check_service_status "MyVault" "$MYVAULT_PID" $MYVAULT_PORT
            fi
            if [[ -z "$service_filter" || "$service_filter" == "expertagent" ]]; then
                check_service_status "ExpertAgent" "$EXPERTAGENT_PID" $EXPERTAGENT_PORT
            fi
            if [[ -z "$service_filter" || "$service_filter" == "graphaiserver" ]]; then
                check_service_status "GraphAiServer" "$GRAPHAISERVER_PID" $GRAPHAISERVER_PORT
            fi
            if [[ -z "$service_filter" || "$service_filter" == "commonui" ]]; then
                check_service_status "CommonUI" "$COMMONUI_PID" $COMMONUI_PORT
            fi
            echo ""
            ;;

        test)
            run_api_tests
            ;;

        logs)
            show_logs $service_filter
            ;;

        clean)
            clean_temp_files
            ;;

        *)
            print_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Handle Ctrl+C gracefully
trap 'echo ""; print_warning "Interrupted. Stopping services..."; $0 stop; exit 130' INT

# Change to project root
cd "$PROJECT_ROOT"

# Run main function with all arguments
main "$@"