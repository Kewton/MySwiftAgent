#!/bin/bash

# MySwiftAgent Multi-Service Startup Script
# This script starts JobQueue, MyScheduler, and CommonUI services for development

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default ports
JOBQUEUE_PORT=8001
MYSCHEDULER_PORT=8002
COMMONUI_PORT=8501

# Log files
LOG_DIR="$PROJECT_ROOT/logs"
JOBQUEUE_LOG="$LOG_DIR/jobqueue.log"
MYSCHEDULER_LOG="$LOG_DIR/myscheduler.log"
COMMONUI_LOG="$LOG_DIR/commonui.log"

# PID files for service management
PID_DIR="$PROJECT_ROOT/.pids"
JOBQUEUE_PID="$PID_DIR/jobqueue.pid"
MYSCHEDULER_PID="$PID_DIR/myscheduler.pid"
COMMONUI_PID="$PID_DIR/commonui.pid"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} ✅ $1"
}

print_warning() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')]${NC} ⚠️  $1"
}

print_error() {
    echo -e "${RED}[$(date '+%H:%M:%S')]${NC} ❌ $1"
}

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to wait for service to be ready
wait_for_service() {
    local name=$1
    local url=$2
    local max_attempts=30
    local attempt=1

    print_status "Waiting for $name to be ready..."

    while [ $attempt -le $max_attempts ]; do
        if curl -sf "$url/health" >/dev/null 2>&1; then
            print_success "$name is ready!"
            return 0
        fi

        if [ $attempt -eq 1 ]; then
            echo -n "    "
        fi
        echo -n "."

        sleep 1
        ((attempt++))
    done

    echo ""
    print_error "$name failed to start within $max_attempts seconds"
    return 1
}

# Function to start a service
start_service() {
    local name=$1
    local directory=$2
    local command=$3
    local port=$4
    local pid_file=$5
    local log_file=$6

    print_status "Starting $name..."

    # Check if service is already running
    if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        print_warning "$name is already running (PID: $(cat "$pid_file"))"
        return 0
    fi

    # Check if port is in use
    if check_port $port; then
        print_error "Port $port is already in use. Cannot start $name."
        return 1
    fi

    # Change to service directory
    if [ ! -d "$directory" ]; then
        print_error "Directory $directory does not exist"
        return 1
    fi

    cd "$directory"

    # Start the service in background
    nohup bash -c "$command" > "$log_file" 2>&1 &
    local service_pid=$!

    # Save PID
    echo $service_pid > "$pid_file"

    # Wait for service to be ready
    local health_url="http://localhost:$port"
    if wait_for_service "$name" "$health_url"; then
        print_success "$name started successfully (PID: $service_pid, Port: $port)"
        return 0
    else
        # Service failed to start, clean up
        if kill -0 $service_pid 2>/dev/null; then
            kill $service_pid
        fi
        rm -f "$pid_file"
        return 1
    fi
}

# Function to stop a service
stop_service() {
    local name=$1
    local pid_file=$2

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 $pid 2>/dev/null; then
            print_status "Stopping $name (PID: $pid)..."
            kill $pid
            sleep 2

            # Force kill if still running
            if kill -0 $pid 2>/dev/null; then
                print_warning "Force stopping $name..."
                kill -9 $pid
            fi

            print_success "$name stopped"
        fi
        rm -f "$pid_file"
    fi
}

# Function to check service status
check_status() {
    local name=$1
    local pid_file=$2
    local port=$3

    if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        local pid=$(cat "$pid_file")
        if check_port $port; then
            print_success "$name is running (PID: $pid, Port: $port)"
        else
            print_warning "$name process exists but port $port is not listening"
        fi
    else
        print_error "$name is not running"
        # Clean up stale PID file
        rm -f "$pid_file"
    fi
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [COMMAND]

Commands:
    start       Start all services (default)
    stop        Stop all services
    restart     Restart all services
    status      Show status of all services
    logs        Show logs for all services
    help        Show this help message

Options:
    --jobqueue-only     Only operate on JobQueue service
    --myscheduler-only  Only operate on MyScheduler service
    --commonui-only     Only operate on CommonUI service

Examples:
    $0                      # Start all services
    $0 start                # Start all services
    $0 stop                 # Stop all services
    $0 status               # Check status
    $0 start --jobqueue-only # Start only JobQueue
EOF
}

# Function to initialize directories
init_directories() {
    mkdir -p "$LOG_DIR" "$PID_DIR"
}

# Function to check dependencies
check_dependencies() {
    local missing_deps=0

    # Check if uv is installed
    if ! command -v uv &> /dev/null; then
        print_error "uv is not installed. Please install it first: https://docs.astral.sh/uv/"
        ((missing_deps++))
    fi

    # Check if curl is available for health checks
    if ! command -v curl &> /dev/null; then
        print_error "curl is not installed. Please install curl for health checks."
        ((missing_deps++))
    fi

    # Check if project directories exist
    for dir in "jobqueue" "myscheduler" "commonUI"; do
        if [ ! -d "$PROJECT_ROOT/$dir" ]; then
            print_error "Directory $PROJECT_ROOT/$dir does not exist"
            ((missing_deps++))
        fi
    done

    return $missing_deps
}

# Function to show logs
show_logs() {
    local service=$1

    if [ -z "$service" ]; then
        print_status "Showing logs for all services..."
        echo "=== JobQueue Logs ==="
        tail -n 20 "$JOBQUEUE_LOG" 2>/dev/null || echo "No logs available"
        echo ""
        echo "=== MyScheduler Logs ==="
        tail -n 20 "$MYSCHEDULER_LOG" 2>/dev/null || echo "No logs available"
        echo ""
        echo "=== CommonUI Logs ==="
        tail -n 20 "$COMMONUI_LOG" 2>/dev/null || echo "No logs available"
    else
        case $service in
            jobqueue)
                tail -f "$JOBQUEUE_LOG"
                ;;
            myscheduler)
                tail -f "$MYSCHEDULER_LOG"
                ;;
            commonui)
                tail -f "$COMMONUI_LOG"
                ;;
            *)
                print_error "Unknown service: $service"
                return 1
                ;;
        esac
    fi
}

# Main execution
main() {
    local command="start"
    local service_filter=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            start|stop|restart|status|logs|help)
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
                print_error "Unknown argument: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    # Handle help command
    if [ "$command" = "help" ]; then
        show_usage
        exit 0
    fi

    # Initialize
    init_directories

    # Check dependencies
    if [ "$command" != "stop" ] && [ "$command" != "status" ] && [ "$command" != "logs" ]; then
        if ! check_dependencies; then
            print_error "Dependency check failed. Please resolve the issues above."
            exit 1
        fi
    fi

    # Execute command
    case $command in
        start)
            print_status "🚀 Starting MySwiftAgent services..."
            echo ""

            if [ -z "$service_filter" ] || [ "$service_filter" = "jobqueue" ]; then
                start_service "JobQueue" "$PROJECT_ROOT/jobqueue" \
                    "uv run uvicorn app.main:app --host 0.0.0.0 --port $JOBQUEUE_PORT" \
                    $JOBQUEUE_PORT "$JOBQUEUE_PID" "$JOBQUEUE_LOG"
            fi

            if [ -z "$service_filter" ] || [ "$service_filter" = "myscheduler" ]; then
                start_service "MyScheduler" "$PROJECT_ROOT/myscheduler" \
                    "uv run uvicorn app.main:app --host 0.0.0.0 --port $MYSCHEDULER_PORT" \
                    $MYSCHEDULER_PORT "$MYSCHEDULER_PID" "$MYSCHEDULER_LOG"
            fi

            if [ -z "$service_filter" ] || [ "$service_filter" = "commonui" ]; then
                # Wait a bit for backend services to be ready
                if [ -z "$service_filter" ]; then
                    sleep 2
                fi

                cd "$PROJECT_ROOT/commonUI"
                print_status "Starting CommonUI..."
                nohup bash -c "uv run streamlit run Home.py --server.port $COMMONUI_PORT --server.headless true" > "$COMMONUI_LOG" 2>&1 &
                echo $! > "$COMMONUI_PID"

                # Wait for CommonUI to be ready (different check since it's Streamlit)
                sleep 5
                if check_port $COMMONUI_PORT; then
                    print_success "CommonUI started successfully (Port: $COMMONUI_PORT)"
                else
                    print_error "CommonUI failed to start"
                fi
            fi

            echo ""
            print_success "🎉 Startup complete!"
            echo ""
            echo "Access URLs:"
            if [ -z "$service_filter" ] || [ "$service_filter" = "jobqueue" ]; then
                echo "  📋 JobQueue API:    http://localhost:$JOBQUEUE_PORT"
            fi
            if [ -z "$service_filter" ] || [ "$service_filter" = "myscheduler" ]; then
                echo "  ⏰ MyScheduler API: http://localhost:$MYSCHEDULER_PORT"
            fi
            if [ -z "$service_filter" ] || [ "$service_filter" = "commonui" ]; then
                echo "  🎨 CommonUI:        http://localhost:$COMMONUI_PORT"
            fi
            echo ""
            echo "Use '$0 logs' to view logs or '$0 stop' to stop all services."
            ;;

        stop)
            print_status "🛑 Stopping MySwiftAgent services..."
            if [ -z "$service_filter" ] || [ "$service_filter" = "commonui" ]; then
                stop_service "CommonUI" "$COMMONUI_PID"
            fi
            if [ -z "$service_filter" ] || [ "$service_filter" = "myscheduler" ]; then
                stop_service "MyScheduler" "$MYSCHEDULER_PID"
            fi
            if [ -z "$service_filter" ] || [ "$service_filter" = "jobqueue" ]; then
                stop_service "JobQueue" "$JOBQUEUE_PID"
            fi
            print_success "All services stopped"
            ;;

        restart)
            print_status "🔄 Restarting MySwiftAgent services..."
            $0 stop $service_filter
            sleep 2
            $0 start $service_filter
            ;;

        status)
            print_status "📊 Service Status:"
            if [ -z "$service_filter" ] || [ "$service_filter" = "jobqueue" ]; then
                check_status "JobQueue" "$JOBQUEUE_PID" $JOBQUEUE_PORT
            fi
            if [ -z "$service_filter" ] || [ "$service_filter" = "myscheduler" ]; then
                check_status "MyScheduler" "$MYSCHEDULER_PID" $MYSCHEDULER_PORT
            fi
            if [ -z "$service_filter" ] || [ "$service_filter" = "commonui" ]; then
                check_status "CommonUI" "$COMMONUI_PID" $COMMONUI_PORT
            fi
            ;;

        logs)
            show_logs $service_filter
            ;;

        *)
            print_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Handle Ctrl+C gracefully
trap 'echo ""; print_status "Interrupted. Stopping services..."; $0 stop; exit 130' INT

# Run main function with all arguments
main "$@"