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

set -e

# Configuration
MYVAULT_URL="${MYVAULT_URL:-http://localhost:8003}"
MAX_RETRIES=12
RETRY_INTERVAL=5

echo "🔄 Initializing MyVault default project..."
echo "   MyVault URL: $MYVAULT_URL"

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

# Check if default_project exists
echo ""
echo "🔍 Checking if default_project exists..."
RESPONSE=$(curl -sf "$MYVAULT_URL/api/projects" 2>/dev/null || echo "[]")
if echo "$RESPONSE" | grep -q '"name":"default_project"'; then
    echo "✅ default_project already exists"

    # Check if it's set as default
    if echo "$RESPONSE" | grep -q '"name":"default_project".*"is_default":true'; then
        echo "✅ default_project is already set as default"
    else
        echo "🔄 Setting default_project as default..."
        curl -sf -X PUT "$MYVAULT_URL/api/projects/default_project/set-default" > /dev/null 2>&1 || {
            echo "⚠️  Failed to set default_project as default via API"
            echo "   This may require manual intervention"
        }
        echo "✅ default_project is now set as default"
    fi
else
    echo "🔄 Creating default_project..."
    CREATE_RESPONSE=$(curl -sf -X POST "$MYVAULT_URL/api/projects" \
        -H "Content-Type: application/json" \
        -d '{"name": "default_project", "description": "Default project for storing secrets"}' 2>/dev/null || echo "")

    if [ -n "$CREATE_RESPONSE" ]; then
        echo "✅ default_project created successfully"

        echo "🔄 Setting default_project as default..."
        curl -sf -X PUT "$MYVAULT_URL/api/projects/default_project/set-default" > /dev/null 2>&1 || {
            echo "⚠️  Failed to set default_project as default via API"
        }
        echo "✅ default_project is now set as default"
    else
        echo "❌ Failed to create default_project"
        exit 1
    fi
fi

# Show current projects
echo ""
echo "📦 Current projects:"
curl -sf "$MYVAULT_URL/api/projects" 2>/dev/null | python3 -c "
import sys, json
try:
    projects = json.load(sys.stdin)
    for p in projects:
        default = '⭐ (default)' if p.get('is_default') else ''
        print(f\"  - {p['name']} {default}\")
except:
    print('  (Unable to parse projects)')
" 2>/dev/null || echo "  (Unable to fetch projects)"

echo ""
echo "✅ MyVault initialization complete!"
