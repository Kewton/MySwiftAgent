#!/bin/bash
# Initialize MyVault default project after docker-compose startup
#
# This script waits for MyVault to be healthy, then creates the default_project
# if it doesn't exist and sets it as the default project.
#
# Usage:
#   ./scripts/init-myvault-default-project.sh
#
# Prerequisites:
#   - MyVault container must be running (docker-compose up -d)
#   - .env.docker must contain MYVAULT_TOKEN_COMMONUI for authentication

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
MYVAULT_URL="${MYVAULT_URL:-http://localhost:8003}"
MAX_RETRIES=12
RETRY_INTERVAL=5

# Load authentication token from .env.docker
ENV_FILE="$PROJECT_ROOT/.env.docker"
if [ -f "$ENV_FILE" ]; then
    MYVAULT_TOKEN=$(grep -E "^MYVAULT_TOKEN_COMMONUI=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2 | tr -d '"' || echo "")
fi

# Fallback to environment variable
MYVAULT_TOKEN="${MYVAULT_TOKEN:-$MYVAULT_TOKEN_COMMONUI}"

echo "🔄 Initializing MyVault default project..."
echo "   MyVault URL: $MYVAULT_URL"
if [ -n "$MYVAULT_TOKEN" ]; then
    echo "   Auth: Using commonui service token"
else
    echo "   Auth: No token found (will try without authentication)"
fi

# Wait for MyVault to be healthy
echo ""
echo "⏳ Waiting for MyVault to be healthy..."
for i in $(seq 1 $MAX_RETRIES); do
    if curl -sf "$MYVAULT_URL/health" > /dev/null 2>&1; then
        echo "✅ MyVault is healthy after $((i * RETRY_INTERVAL)) seconds"
        break
    fi
    echo "⏳ Attempt $i/$MAX_RETRIES: MyVault not ready yet, waiting..."
    if [ $i -eq $MAX_RETRIES ]; then
        echo "❌ MyVault failed to become healthy after $((MAX_RETRIES * RETRY_INTERVAL)) seconds"
        exit 1
    fi
    sleep $RETRY_INTERVAL
done

# Build auth headers
AUTH_HEADERS=""
if [ -n "$MYVAULT_TOKEN" ]; then
    AUTH_HEADERS="-H X-Service:commonui -H X-Token:$MYVAULT_TOKEN"
fi

# Check if default_project exists
echo ""
echo "🔍 Checking if default_project exists..."
RESPONSE=$(curl -sf $AUTH_HEADERS "$MYVAULT_URL/api/projects" 2>/dev/null || echo "")

# Handle API response
if [ -z "$RESPONSE" ]; then
    echo "⚠️  Unable to fetch projects from MyVault API"
    echo "   This may be due to authentication issues or API unavailability"
    echo "   Attempting to create project anyway..."
    RESPONSE="[]"
fi

# Check if default_project exists in response
if echo "$RESPONSE" | grep -q '"name"[[:space:]]*:[[:space:]]*"default_project"'; then
    echo "✅ default_project already exists (skipping creation)"

    # Check if it's set as default
    if echo "$RESPONSE" | python3 -c "
import sys, json
try:
    projects = json.load(sys.stdin)
    for p in projects:
        if p.get('name') == 'default_project' and p.get('is_default'):
            sys.exit(0)
    sys.exit(1)
except:
    sys.exit(1)
" 2>/dev/null; then
        echo "✅ default_project is already set as default"
    else
        echo "🔄 Setting default_project as default..."
        SET_RESULT=$(curl -s -w "\n%{http_code}" -X PUT $AUTH_HEADERS "$MYVAULT_URL/api/projects/default_project/set-default" 2>/dev/null)
        HTTP_CODE=$(echo "$SET_RESULT" | tail -n1)
        if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
            echo "✅ default_project is now set as default"
        else
            echo "⚠️  Failed to set default_project as default (HTTP $HTTP_CODE)"
            echo "   You may need to set it manually"
        fi
    fi
else
    echo "🔄 Creating default_project..."
    CREATE_RESULT=$(curl -s -w "\n%{http_code}" -X POST $AUTH_HEADERS \
        -H "Content-Type: application/json" \
        -d '{"name": "default_project", "description": "Default project for storing secrets"}' \
        "$MYVAULT_URL/api/projects" 2>/dev/null)

    HTTP_CODE=$(echo "$CREATE_RESULT" | tail -n1)
    BODY=$(echo "$CREATE_RESULT" | sed '$d')

    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
        echo "✅ default_project created successfully"

        echo "🔄 Setting default_project as default..."
        SET_RESULT=$(curl -s -w "\n%{http_code}" -X PUT $AUTH_HEADERS "$MYVAULT_URL/api/projects/default_project/set-default" 2>/dev/null)
        SET_HTTP_CODE=$(echo "$SET_RESULT" | tail -n1)
        if [ "$SET_HTTP_CODE" = "200" ] || [ "$SET_HTTP_CODE" = "204" ]; then
            echo "✅ default_project is now set as default"
        else
            echo "⚠️  Failed to set default_project as default (HTTP $SET_HTTP_CODE)"
        fi
    elif [ "$HTTP_CODE" = "409" ] || [ "$HTTP_CODE" = "400" ]; then
        # Project already exists (conflict) or validation error
        if echo "$BODY" | grep -qi "already exists\|duplicate"; then
            echo "✅ default_project already exists (detected from error response)"
        else
            echo "❌ Failed to create default_project (HTTP $HTTP_CODE)"
            echo "   Response: $BODY"
            exit 1
        fi
    else
        echo "❌ Failed to create default_project (HTTP $HTTP_CODE)"
        echo "   Response: $BODY"
        exit 1
    fi
fi

# Show current projects
echo ""
echo "📦 Current projects:"
PROJECTS_RESPONSE=$(curl -sf $AUTH_HEADERS "$MYVAULT_URL/api/projects" 2>/dev/null || echo "")
if [ -n "$PROJECTS_RESPONSE" ]; then
    echo "$PROJECTS_RESPONSE" | python3 -c "
import sys, json
try:
    projects = json.load(sys.stdin)
    for p in projects:
        default = '⭐ (default)' if p.get('is_default') else ''
        print(f\"  - {p['name']} {default}\")
except Exception as e:
    print(f'  (Unable to parse projects: {e})')
" 2>/dev/null || echo "  (Unable to parse projects)"
else
    echo "  (Unable to fetch projects - authentication may be required)"
fi

echo ""
echo "✅ MyVault initialization complete!"
