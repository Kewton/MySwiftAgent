#!/bin/bash

# MyVault Service Restart Script
# Stops and restarts MyVault service to reload configuration changes

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MYVAULT_DIR="$PROJECT_ROOT/myVault"
MYVAULT_PORT="${MYVAULT_PORT:-8000}"
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/.pids"
MYVAULT_LOG="$LOG_DIR/myvault.log"
MYVAULT_PID="$PID_DIR/myvault.pid"

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

# Initialize directories
init_directories() {
    mkdir -p "$LOG_DIR" "$PID_DIR"
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
        print_warning "$service_name: Port $port is in use, stopping existing process..."
        local pid=$(lsof -ti:$port)
        if [[ -n "$pid" ]]; then
            print_info "Sending TERM signal to process $pid..."
            kill -TERM $pid 2>/dev/null || true
            sleep 3

            # Check if process is still running
            if check_port $port; then
                print_warning "Process still running, sending KILL signal..."
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
    else
        print_info "$service_name: Port $port is already free"
    fi

    return 0
}

# Wait for service health check
wait_for_service() {
    local name=$1
    local url=$2
    local max_attempts=${3:-30}
    local attempt=1

    print_info "$name: Waiting for service to be ready..."

    while [[ $attempt -le $max_attempts ]]; do
        if curl -sf "$url/health" >/dev/null 2>&1; then
            print_success "$name: Service is ready! (attempt $attempt/$max_attempts)"
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

# Stop MyVault service
stop_myvault() {
    print_step "Stopping MyVault service..."

    # Try to stop using PID file first
    if [[ -f "$MYVAULT_PID" ]]; then
        local pid=$(cat "$MYVAULT_PID")
        if kill -0 $pid 2>/dev/null; then
            print_info "MyVault: Stopping process (PID: $pid)..."
            kill -TERM $pid 2>/dev/null || true

            # Wait for graceful shutdown
            local attempts=0
            while kill -0 $pid 2>/dev/null && [[ $attempts -lt 10 ]]; do
                sleep 1
                ((attempts++))
            done

            # Force kill if still running
            if kill -0 $pid 2>/dev/null; then
                print_warning "MyVault: Force stopping..."
                kill -KILL $pid 2>/dev/null || true
            fi
        fi
        rm -f "$MYVAULT_PID"
    fi

    # Kill any process on the port (fallback)
    if ! kill_port $MYVAULT_PORT "MyVault"; then
        print_error "Failed to free MyVault port"
        return 1
    fi

    print_success "MyVault: Stopped successfully"
}

# Start MyVault service
start_myvault() {
    print_step "Starting MyVault service..."

    # Check if MyVault directory exists
    if [[ ! -d "$MYVAULT_DIR" ]]; then
        print_error "MyVault directory not found: $MYVAULT_DIR"
        return 1
    fi

    # Check if config files exist
    if [[ ! -f "$MYVAULT_DIR/config.yaml" ]]; then
        print_error "MyVault config.yaml not found"
        return 1
    fi

    if [[ ! -f "$MYVAULT_DIR/.env" ]]; then
        print_error "MyVault .env not found"
        return 1
    fi

    # Check if uv is installed
    if ! command -v uv &> /dev/null; then
        print_error "uv package manager not found"
        print_info "Install uv: https://docs.astral.sh/uv/"
        return 1
    fi

    # Change to MyVault directory
    cd "$MYVAULT_DIR" || {
        print_error "Cannot change to directory $MYVAULT_DIR"
        return 1
    }

    # Install/update dependencies
    print_info "MyVault: Syncing dependencies..."
    if ! uv sync --extra dev >/dev/null 2>&1; then
        print_error "Failed to sync MyVault dependencies"
        cd "$PROJECT_ROOT"
        return 1
    fi

    # Clear old log
    > "$MYVAULT_LOG"

    # Start the service
    print_info "MyVault: Starting uvicorn on port $MYVAULT_PORT..."
    nohup bash -c "uv run uvicorn app.main:app --host 0.0.0.0 --port $MYVAULT_PORT" > "$MYVAULT_LOG" 2>&1 &
    local service_pid=$!

    # Save PID
    echo $service_pid > "$MYVAULT_PID"

    cd "$PROJECT_ROOT"

    # Wait for service to be ready
    if wait_for_service "MyVault" "http://localhost:$MYVAULT_PORT"; then
        print_success "MyVault: Started successfully (PID: $service_pid, Port: $MYVAULT_PORT)"
        print_info "MyVault API: http://localhost:$MYVAULT_PORT"
        print_info "MyVault Docs: http://localhost:$MYVAULT_PORT/docs"
        print_info "MyVault Health: http://localhost:$MYVAULT_PORT/health"
        return 0
    else
        # Service failed to start, clean up
        if kill -0 $service_pid 2>/dev/null; then
            kill -TERM $service_pid 2>/dev/null || true
            sleep 2
            kill -KILL $service_pid 2>/dev/null || true
        fi
        rm -f "$MYVAULT_PID"
        print_error "MyVault: Failed to start"
        print_info "Check logs: tail -f $MYVAULT_LOG"
        return 1
    fi
}

# Show MyVault status
show_status() {
    print_step "MyVault Service Status:"
    echo ""

    if [[ -f "$MYVAULT_PID" ]] && kill -0 "$(cat "$MYVAULT_PID")" 2>/dev/null; then
        local pid=$(cat "$MYVAULT_PID")
        if check_port $MYVAULT_PORT; then
            if curl -sf "http://localhost:$MYVAULT_PORT/health" >/dev/null 2>&1; then
                print_success "MyVault: Running healthy (PID: $pid, Port: $MYVAULT_PORT)"
            else
                print_warning "MyVault: Running but health check failed (PID: $pid, Port: $MYVAULT_PORT)"
            fi
        else
            print_warning "MyVault: Process exists but port $MYVAULT_PORT not listening (PID: $pid)"
        fi
    else
        print_error "MyVault: Not running"
        rm -f "$MYVAULT_PID" 2>/dev/null || true
    fi

    echo ""
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [COMMAND]

Commands:
    restart     Restart MyVault service (default)
    start       Start MyVault service
    stop        Stop MyVault service
    status      Show MyVault service status
    logs        Show MyVault logs (follow with -f)
    help        Show this help message

Examples:
    $0                  # Restart MyVault
    $0 restart          # Restart MyVault
    $0 start            # Start MyVault only
    $0 stop             # Stop MyVault only
    $0 status           # Check MyVault status
    $0 logs             # Show last 50 lines of logs
    $0 logs -f          # Follow logs

Environment Variables:
    MYVAULT_PORT        MyVault port (default: 8000)

EOF
}

# Show logs
show_logs() {
    local follow=$1

    if [[ ! -f "$MYVAULT_LOG" ]]; then
        print_error "Log file not found: $MYVAULT_LOG"
        return 1
    fi

    if [[ "$follow" == "-f" ]]; then
        print_info "Following MyVault logs (Ctrl+C to stop):"
        tail -f "$MYVAULT_LOG"
    else
        print_info "MyVault logs (last 50 lines):"
        tail -n 50 "$MYVAULT_LOG"
    fi
}

# Main execution
main() {
    local command="${1:-restart}"

    # Show banner
    echo -e "${CYAN}"
    cat << 'EOF'
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🔐 MyVault Service Manager                              ║
║   ══════════════════════════                              ║
║                                                           ║
║   Secure secret and project management service            ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"

    # Initialize directories
    init_directories

    # Execute command
    case $command in
        restart)
            stop_myvault || true
            sleep 2
            start_myvault || exit 1
            echo ""
            show_status
            ;;

        start)
            start_myvault || exit 1
            echo ""
            show_status
            ;;

        stop)
            stop_myvault || exit 1
            echo ""
            ;;

        status)
            show_status
            ;;

        logs)
            shift
            show_logs "$@"
            ;;

        help|-h|--help)
            show_usage
            exit 0
            ;;

        *)
            print_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Handle Ctrl+C gracefully
trap 'echo ""; print_warning "Interrupted. Exiting..."; exit 130' INT

# Change to project root
cd "$PROJECT_ROOT"

# Run main function with all arguments
main "$@"
