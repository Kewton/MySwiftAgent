#!/bin/bash

# MySwiftAgent Quick Start Script
# Simple one-command startup for immediate development

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load project-level .env files (new policy)
echo -e "${BLUE}📋 Loading project-level environment variables${NC}"
for project in myVault jobqueue myscheduler expertAgent graphAiServer commonUI; do
    if [[ -f "$PROJECT_ROOT/$project/.env" ]]; then
        echo -e "${BLUE}  ✓ Loading $project/.env${NC}"
        set -a
        source "$PROJECT_ROOT/$project/.env"
        set +a
    else
        echo -e "${YELLOW}  ⚠️  $project/.env not found (will use defaults)${NC}"
    fi
done

echo -e "${BLUE}🚀 MySwiftAgent Quick Start${NC}"
echo -e "${BLUE}═══════════════════════════${NC}"
echo ""

# Check if dev-start.sh exists
if [[ ! -f "$SCRIPT_DIR/dev-start.sh" ]]; then
    echo -e "${RED}❌ dev-start.sh not found${NC}"
    exit 1
fi

# Make sure it's executable
chmod +x "$SCRIPT_DIR/dev-start.sh"

# Allocate local ports that avoid docker-compose collisions (override with env vars if needed)
: "${JOBQUEUE_PORT:=8101}"
: "${MYSCHEDULER_PORT:=8102}"
: "${MYVAULT_PORT:=8103}"
: "${EXPERTAGENT_PORT:=8104}"
: "${GRAPHAISERVER_PORT:=8105}"
: "${COMMONUI_PORT:=8601}"
export JOBQUEUE_PORT MYSCHEDULER_PORT MYVAULT_PORT EXPERTAGENT_PORT GRAPHAISERVER_PORT COMMONUI_PORT

# Automatically configure service URLs (new policy - no manual configuration needed)
export JOBQUEUE_API_URL="http://localhost:${JOBQUEUE_PORT}"
export MYSCHEDULER_BASE_URL="http://localhost:${MYSCHEDULER_PORT}"
export MYVAULT_BASE_URL="http://localhost:${MYVAULT_PORT}"
export EXPERTAGENT_BASE_URL="http://localhost:${EXPERTAGENT_PORT}"
export GRAPHAISERVER_BASE_URL="http://localhost:${GRAPHAISERVER_PORT}/api"

# CommonUI specific URLs
export JOBQUEUE_BASE_URL="http://localhost:${JOBQUEUE_PORT}"

echo -e "${BLUE}Using local ports${NC}: JobQueue=${JOBQUEUE_PORT}, MyScheduler=${MYSCHEDULER_PORT}, MyVault=${MYVAULT_PORT}, ExpertAgent=${EXPERTAGENT_PORT}, GraphAiServer=${GRAPHAISERVER_PORT}, CommonUI=${COMMONUI_PORT}"
echo -e "${GREEN}✓ Service URLs configured automatically${NC}"

echo -e "${YELLOW}⚡ Starting all services...${NC}"
echo ""

# Run the full development startup
"$SCRIPT_DIR/dev-start.sh" start

echo ""
echo -e "${GREEN}🎉 Quick start complete!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "• Open your browser to http://localhost:${COMMONUI_PORT} for the web interface"
echo "• Use './scripts/dev-start.sh status' to check service health"
echo "• Use './scripts/dev-start.sh logs' to view logs"
echo "• Use './scripts/dev-start.sh stop' to stop all services"
echo ""