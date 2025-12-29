#!/bin/bash

# MySwiftAgent Hybrid Development Environment Startup Script
# Platform layer: Docker containers
# Agent layer: Local processes (expertAgent, GraphAiServer, myAgentDesk)

set -e

# Colors for output
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

# Load project-level .env files
for project in myVault jobqueue myscheduler expertAgent graphAiServer commonUI myAgentDesk; do
    if [[ -f "$PROJECT_ROOT/$project/.env" ]]; then
        set -a
        source "$PROJECT_ROOT/$project/.env"
        set +a
    fi
done

# Service ports
VALKEY_PORT="${VALKEY_PORT:-6380}"
JOBQUEUE_PORT="${JOBQUEUE_PORT:-8001}"
MYSCHEDULER_PORT="${MYSCHEDULER_PORT:-8002}"
MYVAULT_PORT="${MYVAULT_PORT:-8003}"
EXPERTAGENT_PORT="${EXPERTAGENT_PORT:-8004}"
GRAPHAISERVER_PORT="${GRAPHAISERVER_PORT:-8005}"
MYAGENTDESK_PORT="${MYAGENTDESK_PORT:-8000}"
COMMONUI_PORT="${COMMONUI_PORT:-8501}"
LANGFUSE_PORT="${LANGFUSE_PORT:-3001}"

# Service URLs for local services
export MYVAULT_BASE_URL="http://localhost:${MYVAULT_PORT}"
export JOBQUEUE_BASE_URL="http://localhost:${JOBQUEUE_PORT}"
export MYSCHEDULER_BASE_URL="http://localhost:${MYSCHEDULER_PORT}"
export EXPERTAGENT_BASE_URL="http://localhost:${EXPERTAGENT_PORT}"
export GRAPHAISERVER_BASE_URL="http://localhost:${GRAPHAISERVER_PORT}"

# Directories
JOBQUEUE_DIR="$PROJECT_ROOT/jobqueue"
MYSCHEDULER_DIR="$PROJECT_ROOT/myscheduler"
EXPERTAGENT_DIR="$PROJECT_ROOT/expertAgent"
GRAPHAISERVER_DIR="$PROJECT_ROOT/graphAiServer"
MYAGENTDESK_DIR="$PROJECT_ROOT/myAgentDesk"
COMMONUI_DIR="$PROJECT_ROOT/commonUI"

# Log and PID directories
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/.pids"

# Log files
JOBQUEUE_LOG="$LOG_DIR/jobqueue.log"
MYSCHEDULER_LOG="$LOG_DIR/myscheduler.log"
EXPERTAGENT_LOG="$LOG_DIR/expertagent.log"
GRAPHAISERVER_LOG="$LOG_DIR/graphaiserver.log"
MYAGENTDESK_LOG="$LOG_DIR/myagentdesk.log"
COMMONUI_LOG="$LOG_DIR/commonui.log"

# PID files
JOBQUEUE_PID="$PID_DIR/jobqueue.pid"
MYSCHEDULER_PID="$PID_DIR/myscheduler.pid"
EXPERTAGENT_PID="$PID_DIR/expertagent.pid"
GRAPHAISERVER_PID="$PID_DIR/graphaiserver.pid"
MYAGENTDESK_PID="$PID_DIR/myagentdesk.pid"
COMMONUI_PID="$PID_DIR/commonui.pid"

# Docker services (Platform layer only)
DOCKER_SERVICES="valkey myvault langfuse-db langfuse-clickhouse langfuse-redis langfuse-minio langfuse-worker langfuse-server"

# Banner
show_banner() {
    echo -e "${CYAN}"
    cat << 'EOF'
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   🚀 MySwiftAgent Hybrid Development Environment                              ║
║   ══════════════════════════════════════════════                              ║
║                                                                               ║
║   🐳 Docker (Platform):                                                       ║
║      Valkey, MyVault, Langfuse                                                ║
║                                                                               ║
║   💻 Local (Agent):                                                           ║
║      JobQueue, MyScheduler, ExpertAgent, GraphAiServer, MyAgentDesk, CommonUI ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# Print functions
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
    mkdir -p "$LOG_DIR" "$PID_DIR"
    > "$JOBQUEUE_LOG" 2>/dev/null || true
    > "$MYSCHEDULER_LOG" 2>/dev/null || true
    > "$EXPERTAGENT_LOG" 2>/dev/null || true
    > "$GRAPHAISERVER_LOG" 2>/dev/null || true
    > "$MYAGENTDESK_LOG" 2>/dev/null || true
    > "$COMMONUI_LOG" 2>/dev/null || true
}

# Check if port is in use
check_port() {
    local port=$1
    lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1
}

# Check if PID is a Docker-related process (should not be killed)
is_docker_process() {
    local pid=$1
    local proc_name=$(ps -p "$pid" -o comm= 2>/dev/null || echo "")
    local proc_cmd=$(ps -p "$pid" -o command= 2>/dev/null || echo "")
    # Check process name and command for Docker-related patterns
    [[ "$proc_name" == *"docker"* || "$proc_name" == *"Docker"* || \
       "$proc_name" == "com.docker"* || "$proc_name" == "vpnkit"* || \
       "$proc_cmd" == *"docker"* || "$proc_cmd" == *"Docker"* ]]
}

# Kill process on port (safely, avoiding Docker processes)
kill_port() {
    local port=$1
    local service_name=$2

    if check_port $port; then
        local pid=$(lsof -ti:$port 2>/dev/null | head -1)
        if [[ -n "$pid" ]]; then
            # Safety check: Don't kill Docker processes
            if is_docker_process "$pid"; then
                print_info "$service_name: Port $port is used by Docker container, skipping kill"
                return 0
            fi

            print_warning "$service_name: Port $port is in use (PID: $pid), attempting to free it..."
            kill -TERM $pid 2>/dev/null || true
            sleep 2
            if check_port $port; then
                # Re-check if it's now a Docker process (in case of race condition)
                local new_pid=$(lsof -ti:$port 2>/dev/null | head -1)
                if [[ -n "$new_pid" ]] && is_docker_process "$new_pid"; then
                    print_info "$service_name: Port $port is now used by Docker, skipping"
                    return 0
                fi
                kill -KILL $pid 2>/dev/null || true
                sleep 1
            fi
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

    while [[ $attempt -le $max_attempts ]]; do
        if curl -sf "$url" >/dev/null 2>&1; then
            return 0
        fi
        echo -n "."
        sleep 1
        ((attempt++))
    done
    echo ""
    return 1
}

# Start Docker platform services
start_docker_services() {
    print_step "Starting Platform layer (Docker)..."

    cd "$PROJECT_ROOT"

    # Start Docker services
    docker-compose up -d $DOCKER_SERVICES

    if [ $? -ne 0 ]; then
        print_error "Failed to start Docker services"
        return 1
    fi

    # Wait for essential services
    print_info "Waiting for Docker services to be ready..."

    # Wait for MyVault
    echo -n "    MyVault"
    if wait_for_service "MyVault" "http://localhost:$MYVAULT_PORT/health" 30; then
        print_success "MyVault: Ready"
    else
        print_warning "MyVault: May still be starting"
    fi

    print_success "Platform layer started"
}

# Stop Docker platform services
stop_docker_services() {
    print_step "Stopping Platform layer (Docker)..."
    cd "$PROJECT_ROOT"
    docker-compose stop $DOCKER_SERVICES
    print_success "Platform layer stopped"
}

# Install dependencies for a service
install_deps() {
    local name=$1
    local dir=$2

    print_service "📦" "$name" "Installing dependencies..."

    cd "$dir"

    if [[ -f "pyproject.toml" ]]; then
        uv sync --extra dev >/dev/null 2>&1
    elif [[ -f "package.json" ]]; then
        if [[ -f "package-lock.json" ]]; then
            NODE_ENV=development npm ci >/dev/null 2>&1
        else
            NODE_ENV=development npm install >/dev/null 2>&1
        fi
    fi

    cd "$PROJECT_ROOT"
    print_success "$name: Dependencies ready"
}

# Check if PID belongs to a specific service
is_service_pid() {
    local pid=$1
    local service_pattern=$2
    local cmd=$(ps -p "$pid" -o command= 2>/dev/null || echo "")
    [[ "$cmd" == *"$service_pattern"* ]]
}

# Start JobQueue
start_jobqueue() {
    print_service "📦" "JobQueue" "Starting on port $JOBQUEUE_PORT..."

    # Check if already running (verify it's actually JobQueue, not a stale PID)
    if [[ -f "$JOBQUEUE_PID" ]]; then
        local saved_pid=$(cat "$JOBQUEUE_PID")
        if kill -0 "$saved_pid" 2>/dev/null && is_service_pid "$saved_pid" "jobqueue"; then
            print_warning "JobQueue: Already running (PID: $saved_pid)"
            return 0
        else
            rm -f "$JOBQUEUE_PID"
        fi
    fi

    kill_port $JOBQUEUE_PORT "JobQueue"

    install_deps "JobQueue" "$JOBQUEUE_DIR"

    cd "$JOBQUEUE_DIR"

    # Start service
    nohup bash -c "JOBQUEUE_DB_URL=sqlite+aiosqlite:///./data/jobqueue.db \
        LOG_DIR=$LOG_DIR \
        uv run uvicorn app.main:app --host 0.0.0.0 --port $JOBQUEUE_PORT --reload" > "$JOBQUEUE_LOG" 2>&1 &

    echo $! > "$JOBQUEUE_PID"

    cd "$PROJECT_ROOT"

    # Wait for service
    echo -n "    Waiting"
    if wait_for_service "JobQueue" "http://localhost:$JOBQUEUE_PORT/health" 30; then
        print_success "JobQueue: Started (PID: $(cat "$JOBQUEUE_PID"), Port: $JOBQUEUE_PORT)"
    else
        print_error "JobQueue: Failed to start (check $JOBQUEUE_LOG)"
        return 1
    fi
}

# Start MyScheduler
start_myscheduler() {
    print_service "📅" "MyScheduler" "Starting on port $MYSCHEDULER_PORT..."

    # Check if already running (verify it's actually MyScheduler, not a stale PID)
    if [[ -f "$MYSCHEDULER_PID" ]]; then
        local saved_pid=$(cat "$MYSCHEDULER_PID")
        if kill -0 "$saved_pid" 2>/dev/null && is_service_pid "$saved_pid" "myscheduler"; then
            print_warning "MyScheduler: Already running (PID: $saved_pid)"
            return 0
        else
            rm -f "$MYSCHEDULER_PID"
        fi
    fi

    kill_port $MYSCHEDULER_PORT "MyScheduler"

    install_deps "MyScheduler" "$MYSCHEDULER_DIR"

    cd "$MYSCHEDULER_DIR"

    # Start service
    nohup bash -c "JOBQUEUE_API_URL=http://localhost:$JOBQUEUE_PORT \
        DATABASE_URL=sqlite:///./data/jobs.db \
        LOG_DIR=$LOG_DIR \
        uv run uvicorn app.main:app --host 0.0.0.0 --port $MYSCHEDULER_PORT --reload" > "$MYSCHEDULER_LOG" 2>&1 &

    echo $! > "$MYSCHEDULER_PID"

    cd "$PROJECT_ROOT"

    # Wait for service
    echo -n "    Waiting"
    if wait_for_service "MyScheduler" "http://localhost:$MYSCHEDULER_PORT/health" 30; then
        print_success "MyScheduler: Started (PID: $(cat "$MYSCHEDULER_PID"), Port: $MYSCHEDULER_PORT)"
    else
        print_error "MyScheduler: Failed to start (check $MYSCHEDULER_LOG)"
        return 1
    fi
}

# Start ExpertAgent
start_expertagent() {
    print_service "🤖" "ExpertAgent" "Starting on port $EXPERTAGENT_PORT..."

    # Check if already running (verify it's actually ExpertAgent, not a stale PID)
    if [[ -f "$EXPERTAGENT_PID" ]]; then
        local saved_pid=$(cat "$EXPERTAGENT_PID")
        if kill -0 "$saved_pid" 2>/dev/null && is_service_pid "$saved_pid" "expertAgent"; then
            print_warning "ExpertAgent: Already running (PID: $saved_pid)"
            return 0
        else
            rm -f "$EXPERTAGENT_PID"
        fi
    fi

    kill_port $EXPERTAGENT_PORT "ExpertAgent"

    install_deps "ExpertAgent" "$EXPERTAGENT_DIR"

    cd "$EXPERTAGENT_DIR"

    # Get MyVault token - always read from myVault/.env to avoid conflicts with other service tokens
    local expertagent_token=$(grep -E "^TOKEN_expertagent=" "$PROJECT_ROOT/myVault/.env" 2>/dev/null | cut -d'=' -f2 | tr -d '"' || echo "")
    if [[ -z "$expertagent_token" ]]; then
        expertagent_token="${MYVAULT_TOKEN_EXPERTAGENT:-}"
    fi

    # Start service
    nohup bash -c "MYVAULT_ENABLED=True \
        MYVAULT_BASE_URL=http://localhost:$MYVAULT_PORT \
        MYVAULT_SERVICE_NAME=expertagent \
        MYVAULT_SERVICE_TOKEN=$expertagent_token \
        MYVAULT_DEFAULT_PROJECT=default_project \
        EXPERTAGENT_BASE_URL=http://localhost:$EXPERTAGENT_PORT \
        GRAPHAISERVER_BASE_URL=http://localhost:$GRAPHAISERVER_PORT \
        LOG_DIR=$LOG_DIR \
        uv run uvicorn app.main:app --host 0.0.0.0 --port $EXPERTAGENT_PORT --reload" > "$EXPERTAGENT_LOG" 2>&1 &

    echo $! > "$EXPERTAGENT_PID"

    cd "$PROJECT_ROOT"

    # Wait for service
    echo -n "    Waiting"
    if wait_for_service "ExpertAgent" "http://localhost:$EXPERTAGENT_PORT/health" 30; then
        print_success "ExpertAgent: Started (PID: $(cat "$EXPERTAGENT_PID"), Port: $EXPERTAGENT_PORT)"
    else
        print_error "ExpertAgent: Failed to start (check $EXPERTAGENT_LOG)"
        return 1
    fi
}

# Start GraphAiServer
start_graphaiserver() {
    print_service "🔄" "GraphAiServer" "Starting on port $GRAPHAISERVER_PORT..."

    # Check if already running (verify it's actually GraphAiServer, not a stale PID)
    if [[ -f "$GRAPHAISERVER_PID" ]]; then
        local saved_pid=$(cat "$GRAPHAISERVER_PID")
        if kill -0 "$saved_pid" 2>/dev/null && is_service_pid "$saved_pid" "graphAiServer"; then
            print_warning "GraphAiServer: Already running (PID: $saved_pid)"
            return 0
        else
            rm -f "$GRAPHAISERVER_PID"
        fi
    fi

    kill_port $GRAPHAISERVER_PORT "GraphAiServer"

    install_deps "GraphAiServer" "$GRAPHAISERVER_DIR"

    cd "$GRAPHAISERVER_DIR"

    # Start service
    nohup bash -c "PORT=$GRAPHAISERVER_PORT npm start" > "$GRAPHAISERVER_LOG" 2>&1 &

    echo $! > "$GRAPHAISERVER_PID"

    cd "$PROJECT_ROOT"

    # Wait for service
    echo -n "    Waiting"
    if wait_for_service "GraphAiServer" "http://localhost:$GRAPHAISERVER_PORT/health" 30; then
        print_success "GraphAiServer: Started (PID: $(cat "$GRAPHAISERVER_PID"), Port: $GRAPHAISERVER_PORT)"
    else
        print_error "GraphAiServer: Failed to start (check $GRAPHAISERVER_LOG)"
        return 1
    fi
}

# Start MyAgentDesk
start_myagentdesk() {
    print_service "🖥️ " "MyAgentDesk" "Starting on port $MYAGENTDESK_PORT..."

    # Check if already running (verify it's actually MyAgentDesk, not a stale PID)
    if [[ -f "$MYAGENTDESK_PID" ]]; then
        local saved_pid=$(cat "$MYAGENTDESK_PID")
        if kill -0 "$saved_pid" 2>/dev/null && is_service_pid "$saved_pid" "myAgentDesk"; then
            print_warning "MyAgentDesk: Already running (PID: $saved_pid)"
            return 0
        else
            # Stale PID file, remove it
            rm -f "$MYAGENTDESK_PID"
        fi
    fi

    kill_port $MYAGENTDESK_PORT "MyAgentDesk"

    install_deps "MyAgentDesk" "$MYAGENTDESK_DIR"

    cd "$MYAGENTDESK_DIR"

    # Start service
    nohup bash -c "PORT=$MYAGENTDESK_PORT EXPERT_AGENT_URL=http://localhost:$EXPERTAGENT_PORT npm run dev -- --port $MYAGENTDESK_PORT --host 0.0.0.0" > "$MYAGENTDESK_LOG" 2>&1 &

    echo $! > "$MYAGENTDESK_PID"

    cd "$PROJECT_ROOT"

    # Wait for service (SvelteKit doesn't have /health, check port)
    print_info "MyAgentDesk: Waiting for service to start..."
    local attempt=1
    local max_attempts=30
    while [[ $attempt -le $max_attempts ]]; do
        if check_port $MYAGENTDESK_PORT; then
            print_success "MyAgentDesk: Started (PID: $(cat "$MYAGENTDESK_PID"), Port: $MYAGENTDESK_PORT)"
            return 0
        fi
        echo -n "."
        sleep 1
        ((attempt++))
    done

    echo ""
    print_error "MyAgentDesk: Failed to start (check $MYAGENTDESK_LOG)"
    return 1
}

# Start CommonUI
start_commonui() {
    print_service "🖥️ " "CommonUI" "Starting on port $COMMONUI_PORT..."

    # Check if already running (verify it's actually CommonUI, not a stale PID)
    if [[ -f "$COMMONUI_PID" ]]; then
        local saved_pid=$(cat "$COMMONUI_PID")
        if kill -0 "$saved_pid" 2>/dev/null && is_service_pid "$saved_pid" "commonUI"; then
            print_warning "CommonUI: Already running (PID: $saved_pid)"
            return 0
        else
            # Stale PID file, remove it
            rm -f "$COMMONUI_PID"
        fi
    fi

    kill_port $COMMONUI_PORT "CommonUI"

    install_deps "CommonUI" "$COMMONUI_DIR"

    cd "$COMMONUI_DIR"

    # Start service with local service URLs
    nohup bash -c "PORT=$COMMONUI_PORT \
        MYVAULT_BASE_URL=http://localhost:$MYVAULT_PORT \
        JOBQUEUE_BASE_URL=http://localhost:$JOBQUEUE_PORT \
        MYSCHEDULER_BASE_URL=http://localhost:$MYSCHEDULER_PORT \
        EXPERTAGENT_BASE_URL=http://localhost:$EXPERTAGENT_PORT \
        GRAPHAISERVER_BASE_URL=http://localhost:$GRAPHAISERVER_PORT \
        LOG_DIR=$LOG_DIR \
        uv run streamlit run Home.py --server.port $COMMONUI_PORT --server.address 0.0.0.0" > "$COMMONUI_LOG" 2>&1 &

    echo $! > "$COMMONUI_PID"

    cd "$PROJECT_ROOT"

    # Wait for service (Streamlit health check)
    print_info "CommonUI: Waiting for service to start..."
    local attempt=1
    local max_attempts=30
    while [[ $attempt -le $max_attempts ]]; do
        if check_port $COMMONUI_PORT; then
            print_success "CommonUI: Started (PID: $(cat "$COMMONUI_PID"), Port: $COMMONUI_PORT)"
            return 0
        fi
        echo -n "."
        sleep 1
        ((attempt++))
    done

    echo ""
    print_error "CommonUI: Failed to start (check $COMMONUI_LOG)"
    return 1
}

# Stop a local service
stop_local_service() {
    local name=$1
    local pid_file=$2
    local port=$3

    if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        local pid=$(cat "$pid_file")

        # Safety check: Don't kill Docker processes
        if is_docker_process "$pid"; then
            print_warning "$name: PID $pid is a Docker process, skipping (stale PID file)"
            rm -f "$pid_file"
            return 0
        fi

        print_service "🛑" "$name" "Stopping (PID: $pid)..."
        kill -TERM $pid 2>/dev/null || true
        sleep 2
        if kill -0 $pid 2>/dev/null; then
            kill -KILL $pid 2>/dev/null || true
        fi
        rm -f "$pid_file"
        print_success "$name: Stopped"
    else
        # Try to find by port - but be careful not to kill Docker processes
        if check_port $port; then
            local pid=$(lsof -ti:$port 2>/dev/null | head -1)
            if [[ -n "$pid" ]]; then
                # Safety check: Don't kill Docker processes
                if is_docker_process "$pid"; then
                    print_info "$name: Port $port is used by Docker, skipping"
                else
                    print_service "🛑" "$name" "Stopping (detected on port $port, PID: $pid)..."
                    kill -TERM $pid 2>/dev/null || true
                    sleep 2
                    kill -KILL $pid 2>/dev/null || true
                    print_success "$name: Stopped"
                fi
            fi
        else
            print_info "$name: Not running"
        fi
        rm -f "$pid_file" 2>/dev/null || true
    fi
}

# Check service status
check_status() {
    print_step "Service Status:"
    echo ""

    # Docker services
    echo -e "${CYAN}=== Platform Layer (Docker) ===${NC}"

    # Valkey
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "valkey"; then
        print_success "Valkey: Running (Port: $VALKEY_PORT)"
    else
        print_error "Valkey: Not running"
    fi

    # MyVault
    if curl -sf "http://localhost:$MYVAULT_PORT/health" >/dev/null 2>&1; then
        print_success "MyVault: Running (Port: $MYVAULT_PORT)"
    else
        print_error "MyVault: Not running"
    fi

    # Langfuse
    if curl -sf "http://localhost:$LANGFUSE_PORT/api/public/health" >/dev/null 2>&1; then
        print_success "Langfuse: Running (Port: $LANGFUSE_PORT)"
    else
        print_error "Langfuse: Not running"
    fi

    echo ""
    echo -e "${CYAN}=== Agent Layer (Local) ===${NC}"

    # JobQueue
    if [[ -f "$JOBQUEUE_PID" ]] && kill -0 "$(cat "$JOBQUEUE_PID")" 2>/dev/null; then
        if curl -sf "http://localhost:$JOBQUEUE_PORT/health" >/dev/null 2>&1; then
            print_success "JobQueue: Running (PID: $(cat "$JOBQUEUE_PID"), Port: $JOBQUEUE_PORT)"
        else
            print_warning "JobQueue: Running but unhealthy (PID: $(cat "$JOBQUEUE_PID"))"
        fi
    else
        print_error "JobQueue: Not running"
    fi

    # MyScheduler
    if [[ -f "$MYSCHEDULER_PID" ]] && kill -0 "$(cat "$MYSCHEDULER_PID")" 2>/dev/null; then
        if curl -sf "http://localhost:$MYSCHEDULER_PORT/health" >/dev/null 2>&1; then
            print_success "MyScheduler: Running (PID: $(cat "$MYSCHEDULER_PID"), Port: $MYSCHEDULER_PORT)"
        else
            print_warning "MyScheduler: Running but unhealthy (PID: $(cat "$MYSCHEDULER_PID"))"
        fi
    else
        print_error "MyScheduler: Not running"
    fi

    # ExpertAgent
    if [[ -f "$EXPERTAGENT_PID" ]] && kill -0 "$(cat "$EXPERTAGENT_PID")" 2>/dev/null; then
        if curl -sf "http://localhost:$EXPERTAGENT_PORT/health" >/dev/null 2>&1; then
            print_success "ExpertAgent: Running (PID: $(cat "$EXPERTAGENT_PID"), Port: $EXPERTAGENT_PORT)"
        else
            print_warning "ExpertAgent: Running but unhealthy (PID: $(cat "$EXPERTAGENT_PID"))"
        fi
    else
        print_error "ExpertAgent: Not running"
    fi

    # GraphAiServer
    if [[ -f "$GRAPHAISERVER_PID" ]] && kill -0 "$(cat "$GRAPHAISERVER_PID")" 2>/dev/null; then
        if curl -sf "http://localhost:$GRAPHAISERVER_PORT/health" >/dev/null 2>&1; then
            print_success "GraphAiServer: Running (PID: $(cat "$GRAPHAISERVER_PID"), Port: $GRAPHAISERVER_PORT)"
        else
            print_warning "GraphAiServer: Running but unhealthy (PID: $(cat "$GRAPHAISERVER_PID"))"
        fi
    else
        print_error "GraphAiServer: Not running"
    fi

    # MyAgentDesk
    if [[ -f "$MYAGENTDESK_PID" ]] && kill -0 "$(cat "$MYAGENTDESK_PID")" 2>/dev/null; then
        if check_port $MYAGENTDESK_PORT; then
            print_success "MyAgentDesk: Running (PID: $(cat "$MYAGENTDESK_PID"), Port: $MYAGENTDESK_PORT)"
        else
            print_warning "MyAgentDesk: Process exists but port not listening"
        fi
    else
        print_error "MyAgentDesk: Not running"
    fi

    # CommonUI
    if [[ -f "$COMMONUI_PID" ]] && kill -0 "$(cat "$COMMONUI_PID")" 2>/dev/null; then
        if check_port $COMMONUI_PORT; then
            print_success "CommonUI: Running (PID: $(cat "$COMMONUI_PID"), Port: $COMMONUI_PORT)"
        else
            print_warning "CommonUI: Process exists but port not listening"
        fi
    else
        print_error "CommonUI: Not running"
    fi

    echo ""
}

# Show logs
show_logs() {
    local service=$1

    case $service in
        jobqueue)
            print_info "Following JobQueue logs (Ctrl+C to stop):"
            tail -f "$JOBQUEUE_LOG"
            ;;
        myscheduler)
            print_info "Following MyScheduler logs (Ctrl+C to stop):"
            tail -f "$MYSCHEDULER_LOG"
            ;;
        expertagent)
            print_info "Following ExpertAgent logs (Ctrl+C to stop):"
            tail -f "$EXPERTAGENT_LOG"
            ;;
        graphaiserver)
            print_info "Following GraphAiServer logs (Ctrl+C to stop):"
            tail -f "$GRAPHAISERVER_LOG"
            ;;
        myagentdesk)
            print_info "Following MyAgentDesk logs (Ctrl+C to stop):"
            tail -f "$MYAGENTDESK_LOG"
            ;;
        commonui)
            print_info "Following CommonUI logs (Ctrl+C to stop):"
            tail -f "$COMMONUI_LOG"
            ;;
        docker)
            print_info "Following Docker logs (Ctrl+C to stop):"
            docker-compose logs -f $DOCKER_SERVICES
            ;;
        *)
            print_step "Recent logs (last 20 lines each):"
            echo ""
            echo -e "${YELLOW}=== JobQueue ===${NC}"
            tail -n 20 "$JOBQUEUE_LOG" 2>/dev/null || echo "No logs"
            echo ""
            echo -e "${YELLOW}=== MyScheduler ===${NC}"
            tail -n 20 "$MYSCHEDULER_LOG" 2>/dev/null || echo "No logs"
            echo ""
            echo -e "${YELLOW}=== ExpertAgent ===${NC}"
            tail -n 20 "$EXPERTAGENT_LOG" 2>/dev/null || echo "No logs"
            echo ""
            echo -e "${YELLOW}=== GraphAiServer ===${NC}"
            tail -n 20 "$GRAPHAISERVER_LOG" 2>/dev/null || echo "No logs"
            echo ""
            echo -e "${YELLOW}=== MyAgentDesk ===${NC}"
            tail -n 20 "$MYAGENTDESK_LOG" 2>/dev/null || echo "No logs"
            echo ""
            echo -e "${YELLOW}=== CommonUI ===${NC}"
            tail -n 20 "$COMMONUI_LOG" 2>/dev/null || echo "No logs"
            echo ""
            print_info "Use '$0 logs <service>' to follow specific logs"
            print_info "Services: jobqueue, myscheduler, expertagent, graphaiserver, myagentdesk, commonui, docker"
            ;;
    esac
}

# Show service URLs
show_urls() {
    echo ""
    echo -e "${CYAN}┌────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│                        Service URLs                                │${NC}"
    echo -e "${CYAN}├────────────────────────────────────────────────────────────────────┤${NC}"
    echo -e "${CYAN}│${NC} 🐳 ${WHITE}Platform Layer (Docker)${NC}                                         ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}    Valkey:          ${WHITE}redis://localhost:$VALKEY_PORT${NC}                          ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}    MyVault:         ${WHITE}http://localhost:$MYVAULT_PORT${NC}                           ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}    Langfuse:        ${WHITE}http://localhost:$LANGFUSE_PORT${NC}                          ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}                                                                    ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC} 💻 ${WHITE}Agent Layer (Local)${NC}                                             ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}    JobQueue:        ${WHITE}http://localhost:$JOBQUEUE_PORT${NC}                          ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}    MyScheduler:     ${WHITE}http://localhost:$MYSCHEDULER_PORT${NC}                          ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}    ExpertAgent:     ${WHITE}http://localhost:$EXPERTAGENT_PORT${NC}                          ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}    GraphAiServer:   ${WHITE}http://localhost:$GRAPHAISERVER_PORT${NC}                          ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}    MyAgentDesk:     ${WHITE}http://localhost:$MYAGENTDESK_PORT${NC}                          ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}    CommonUI:        ${WHITE}http://localhost:$COMMONUI_PORT${NC}                          ${CYAN}│${NC}"
    echo -e "${CYAN}└────────────────────────────────────────────────────────────────────┘${NC}"
    echo ""
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [COMMAND] [OPTIONS]

Commands:
    start       Start all services (Docker + Local)
    stop        Stop all services
    restart     Restart all services
    status      Show status of all services
    logs        Show logs (optionally for specific service)
    urls        Show service URLs
    help        Show this help message

Options:
    --docker-only   Only operate on Docker services
    --local-only    Only operate on local services

Log services:
    jobqueue, myscheduler, expertagent, graphaiserver, myagentdesk, commonui, docker

Examples:
    $0                      # Start all services
    $0 start                # Start all services
    $0 start --local-only   # Start only local Agent services
    $0 stop                 # Stop all services
    $0 status               # Check all service status
    $0 logs jobqueue        # Follow JobQueue logs
    $0 logs expertagent     # Follow ExpertAgent logs
    $0 logs docker          # Follow Docker service logs
EOF
}

# Main function
main() {
    local command="start"
    local docker_only=false
    local local_only=false
    local log_service=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            start|stop|restart|status|logs|urls|help)
                command=$1
                shift
                ;;
            --docker-only)
                docker_only=true
                shift
                ;;
            --local-only)
                local_only=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                if [[ "$command" == "logs" ]]; then
                    log_service=$1
                fi
                shift
                ;;
        esac
    done

    # Show banner
    if [[ "$command" != "logs" ]]; then
        show_banner
    fi

    # Initialize
    init_directories
    cd "$PROJECT_ROOT"

    case $command in
        start)
            if [[ "$local_only" != true ]]; then
                start_docker_services || exit 1
            fi

            if [[ "$docker_only" != true ]]; then
                echo ""
                print_step "Starting Agent layer (Local)..."
                start_jobqueue || exit 1
                start_myscheduler || exit 1
                start_expertagent || exit 1
                start_graphaiserver || exit 1
                start_myagentdesk || exit 1
                start_commonui || exit 1
            fi

            echo ""
            print_success "🎉 All services started!"
            show_urls
            print_info "Use '$0 status' to check health"
            print_info "Use '$0 logs <service>' for logs"
            print_info "Use '$0 stop' to stop all services"
            ;;

        stop)
            if [[ "$docker_only" != true ]]; then
                print_step "Stopping Agent layer (Local)..."
                stop_local_service "CommonUI" "$COMMONUI_PID" $COMMONUI_PORT
                stop_local_service "MyAgentDesk" "$MYAGENTDESK_PID" $MYAGENTDESK_PORT
                stop_local_service "GraphAiServer" "$GRAPHAISERVER_PID" $GRAPHAISERVER_PORT
                stop_local_service "ExpertAgent" "$EXPERTAGENT_PID" $EXPERTAGENT_PORT
                stop_local_service "MyScheduler" "$MYSCHEDULER_PID" $MYSCHEDULER_PORT
                stop_local_service "JobQueue" "$JOBQUEUE_PID" $JOBQUEUE_PORT
            fi

            if [[ "$local_only" != true ]]; then
                echo ""
                stop_docker_services
            fi

            print_success "All services stopped"
            ;;

        restart)
            $0 stop
            sleep 3
            $0 start
            ;;

        status)
            check_status
            ;;

        logs)
            show_logs "$log_service"
            ;;

        urls)
            show_urls
            ;;

        help)
            show_usage
            ;;

        *)
            print_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Handle Ctrl+C
trap 'echo ""; print_warning "Interrupted."; exit 130' INT

# Run
main "$@"
