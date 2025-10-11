#!/bin/bash
# Reload secrets cache for all services connected to MyVault
# Usage: ./scripts/reload-secrets.sh [service_name] [project_name]
#   service_name: graphaiserver, expertagent, or "all" (default)
#   project_name: specific project or empty for all projects

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load environment variables
if [ -f "$PROJECT_ROOT/graphAiServer/.env" ]; then
    export $(grep "^ADMIN_TOKEN=" "$PROJECT_ROOT/graphAiServer/.env" | xargs)
fi

SERVICE="${1:-all}"
PROJECT="${2:-}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================"
echo "🔄 MyVault Secrets Cache Reload"
echo "================================"
echo ""

# Function to reload cache for a service
reload_cache() {
    local service_name=$1
    local service_url=$2
    local admin_token=$3
    local project_param=$4

    echo -n "Reloading cache for ${service_name}... "

    local response=$(curl -s -X POST "${service_url}" \
        -H 'Content-Type: application/json' \
        -H "X-Admin-Token: ${admin_token}" \
        -d "${project_param}" \
        -w "\n%{http_code}")

    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ Success${NC}"
        echo "  Response: $body"
    else
        echo -e "${RED}✗ Failed (HTTP $http_code)${NC}"
        echo "  Response: $body"
        return 1
    fi
}

# Build project parameter
PROJECT_JSON="{}"
if [ -n "$PROJECT" ]; then
    PROJECT_JSON="{\"project\": \"$PROJECT\"}"
    echo "Target project: ${PROJECT}"
else
    echo "Target: All projects"
fi
echo ""

# Reload graphAiServer
if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "graphaiserver" ]; then
    GRAPHAI_TOKEN=$(grep "^ADMIN_TOKEN=" "$PROJECT_ROOT/graphAiServer/.env" | cut -d'=' -f2)
    reload_cache "graphAiServer" "http://localhost:8104/api/v1/admin/reload-secrets" "$GRAPHAI_TOKEN" "$PROJECT_JSON"
    echo ""
fi

# Reload expertAgent
if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "expertagent" ]; then
    EXPERT_TOKEN=$(grep "^ADMIN_TOKEN=" "$PROJECT_ROOT/expertAgent/.env" | cut -d'=' -f2)
    reload_cache "expertAgent" "http://localhost:8103/aiagent-api/v1/admin/reload-secrets" "$EXPERT_TOKEN" "$PROJECT_JSON"
    echo ""
fi

echo "================================"
echo -e "${GREEN}✓ Cache reload completed${NC}"
echo "================================"
