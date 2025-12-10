#!/bin/bash
# Initialize LLM model settings in MyVault default_project
#
# Issue #269: LLM model settings management via MyVault
#
# This script registers default LLM model settings in MyVault's default_project.
# These settings can be modified via commonUI's MyVault management page.
#
# Usage:
#   ./scripts/init-model-settings.sh
#
# Prerequisites:
#   - MyVault container must be running (docker-compose up -d)
#   - .env.docker must contain MYVAULT_TOKEN_COMMONUI for authentication
#   - default_project must exist (run init-myvault-default-project.sh first)

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
MYVAULT_URL="${MYVAULT_URL:-http://localhost:8003}"
PROJECT_NAME="${PROJECT_NAME:-default_project}"
MAX_RETRIES=6
RETRY_INTERVAL=5

# Load authentication token from .env.docker
ENV_FILE="$PROJECT_ROOT/.env.docker"
if [ -f "$ENV_FILE" ]; then
    MYVAULT_TOKEN=$(grep -E "^MYVAULT_TOKEN_COMMONUI=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2 | tr -d '"' || echo "")
fi

# Fallback to environment variable
MYVAULT_TOKEN="${MYVAULT_TOKEN:-$MYVAULT_TOKEN_COMMONUI}"

echo "========================================"
echo "  Issue #269: LLM Model Settings Init"
echo "========================================"
echo ""
echo "MyVault URL: $MYVAULT_URL"
echo "Project: $PROJECT_NAME"
if [ -n "$MYVAULT_TOKEN" ]; then
    echo "Auth: Using commonui service token"
else
    echo "Auth: No token found (will try without authentication)"
fi
echo ""

# Wait for MyVault to be healthy
echo "Waiting for MyVault to be healthy..."
for i in $(seq 1 $MAX_RETRIES); do
    if curl -sf "$MYVAULT_URL/health" > /dev/null 2>&1; then
        echo "MyVault is healthy"
        break
    fi
    echo "Attempt $i/$MAX_RETRIES: MyVault not ready yet, waiting..."
    if [ $i -eq $MAX_RETRIES ]; then
        echo "ERROR: MyVault failed to become healthy after $((MAX_RETRIES * RETRY_INTERVAL)) seconds"
        exit 1
    fi
    sleep $RETRY_INTERVAL
done

# Build auth headers
AUTH_HEADERS=""
if [ -n "$MYVAULT_TOKEN" ]; then
    AUTH_HEADERS="-H X-Service:commonui -H X-Token:$MYVAULT_TOKEN"
fi

# Function to create or update a secret
create_or_update_secret() {
    local key="$1"
    local value="$2"
    local description="$3"

    echo -n "  $key: "

    # Check if secret exists
    EXISTING=$(curl -sf $AUTH_HEADERS "$MYVAULT_URL/api/secrets/$PROJECT_NAME/$key" 2>/dev/null || echo "")

    if [ -n "$EXISTING" ] && echo "$EXISTING" | grep -q '"path"'; then
        # Secret exists, skip (don't overwrite)
        echo "already exists (skipping)"
        return 0
    fi

    # Create new secret
    CREATE_RESULT=$(curl -s -w "\n%{http_code}" -X POST $AUTH_HEADERS \
        -H "Content-Type: application/json" \
        -d "{\"project\": \"$PROJECT_NAME\", \"path\": \"$key\", \"value\": \"$value\"}" \
        "$MYVAULT_URL/api/secrets" 2>/dev/null)

    HTTP_CODE=$(echo "$CREATE_RESULT" | tail -n1)

    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
        echo "created ($value)"
    elif [ "$HTTP_CODE" = "409" ]; then
        echo "already exists (skipping)"
    else
        echo "FAILED (HTTP $HTTP_CODE)"
        return 1
    fi
}

echo ""
echo "Registering LLM model settings..."
echo "========================================"

# Gemini models (Chat/Requirement related)
echo ""
echo "[Gemini Models - Chat/Requirement]"
create_or_update_secret "CHAT_CLARIFICATION_MODEL" "gemini-2.0-flash" "Model for requirement clarification chat"
create_or_update_secret "CANDIDATE_GENERATION_MODEL" "gemini-2.0-flash" "Model for candidate generation"
create_or_update_secret "REQUIREMENT_EXTRACTION_MODEL" "gemini-2.0-flash" "Model for requirement extraction"

# Claude models (Job Generator related)
echo ""
echo "[Claude Models - Job Generator]"
create_or_update_secret "JOB_GENERATOR_REQUIREMENT_ANALYSIS_MODEL" "claude-haiku-4-5" "Model for requirement analysis"
create_or_update_secret "JOB_GENERATOR_EVALUATOR_MODEL" "claude-haiku-4-5" "Model for job evaluation"
create_or_update_secret "JOB_GENERATOR_INTERFACE_DEFINITION_MODEL" "claude-haiku-4-5" "Model for interface definition"
create_or_update_secret "JOB_GENERATOR_VALIDATION_MODEL" "claude-haiku-4-5" "Model for validation"

# Workflow Generator
echo ""
echo "[Claude Models - Workflow Generator]"
create_or_update_secret "WORKFLOW_GENERATOR_MODEL" "claude-haiku-4-5" "Model for workflow generation"

echo ""
echo "========================================"
echo "LLM Model Settings initialization complete!"
echo ""
echo "Available models:"
echo "  - Claude: claude-haiku-4-5, claude-sonnet-4-20250514"
echo "  - Gemini: gemini-2.0-flash, gemini-1.5-pro"
echo "  - GPT: gpt-4o, gpt-4o-mini"
echo ""
echo "To modify these settings, use commonUI's MyVault management page."
echo "========================================"
