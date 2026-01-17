#!/bin/bash
#
# MyVault Connection Diagnostic Script
# Issue #364 - ANTHROPIC_API_KEY retrieval verification
#
# Usage: ./check-myvault-connection.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MYVAULT_URL="http://localhost:8003"
SERVICE_NAME="myswiftagentcore"
SERVICE_TOKEN="v6MimHlAk2e3p1j3XbSC4jfPniL1B_3gLkIOBbUhHMw"
PROJECT="default"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  MyVault Connection Diagnostic${NC}"
echo -e "${BLUE}  Issue #364 - ANTHROPIC_API_KEY Check${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Test 1: MyVault Health Check
echo -e "${YELLOW}[Test 1] MyVault Health Check${NC}"
echo "GET ${MYVAULT_URL}/health"
echo ""

HEALTH_RESPONSE=$(curl -s "${MYVAULT_URL}/health" 2>/dev/null || echo '{"error": "Connection failed"}')
echo "Response: ${HEALTH_RESPONSE}"

if echo "$HEALTH_RESPONSE" | grep -q '"status"'; then
    echo -e "${GREEN}✅ MyVault is running${NC}"
else
    echo -e "${RED}❌ MyVault is not responding${NC}"
    echo ""
    echo "Please start MyVault:"
    echo "  docker compose up -d myvault"
    echo "  # or"
    echo "  ./scripts/dev-hybrid.sh start"
    exit 1
fi
echo ""

# Test 2: Service Authentication
echo -e "${YELLOW}[Test 2] Service Authentication Test${NC}"
echo "Testing authentication as '${SERVICE_NAME}'..."
echo ""

AUTH_RESPONSE=$(curl -s "${MYVAULT_URL}/api/secrets/${PROJECT}" \
    -H "X-Service: ${SERVICE_NAME}" \
    -H "X-Token: ${SERVICE_TOKEN}" 2>/dev/null || echo '{"error": "Request failed"}')

echo "Response: ${AUTH_RESPONSE}"

if echo "$AUTH_RESPONSE" | grep -q '"error"'; then
    if echo "$AUTH_RESPONSE" | grep -q "Invalid token\|Unauthorized\|Authentication"; then
        echo -e "${RED}❌ Authentication failed${NC}"
        echo ""
        echo "Possible causes:"
        echo "  1. myswiftagentcore service not registered in myVault/config.yaml"
        echo "  2. Token mismatch in myVault/.env (TOKEN_myswiftagentcore)"
        echo "  3. MyVault needs restart after config change"
        echo ""
        echo "Solution:"
        echo "  docker compose restart myvault"
    else
        echo -e "${YELLOW}⚠️ Request returned error (may be normal if no secrets exist)${NC}"
    fi
else
    echo -e "${GREEN}✅ Authentication successful${NC}"
fi
echo ""

# Test 3: Check ANTHROPIC_API_KEY
echo -e "${YELLOW}[Test 3] ANTHROPIC_API_KEY Retrieval${NC}"
echo "GET ${MYVAULT_URL}/api/secrets/${PROJECT}/ANTHROPIC_API_KEY"
echo ""

KEY_RESPONSE=$(curl -s "${MYVAULT_URL}/api/secrets/${PROJECT}/ANTHROPIC_API_KEY" \
    -H "X-Service: ${SERVICE_NAME}" \
    -H "X-Token: ${SERVICE_TOKEN}" 2>/dev/null || echo '{"error": "Request failed"}')

echo "Response: ${KEY_RESPONSE}"

if echo "$KEY_RESPONSE" | grep -q '"value"'; then
    # Mask the actual key value for security
    echo -e "${GREEN}✅ ANTHROPIC_API_KEY is registered in MyVault${NC}"
    KEY_VALUE=$(echo "$KEY_RESPONSE" | grep -o '"value":"[^"]*"' | cut -d'"' -f4)
    KEY_PREFIX="${KEY_VALUE:0:10}"
    echo "   Key prefix: ${KEY_PREFIX}..."
elif echo "$KEY_RESPONSE" | grep -q "not found\|Not found\|404"; then
    echo -e "${RED}❌ ANTHROPIC_API_KEY is NOT registered in MyVault${NC}"
    echo ""
    echo -e "${YELLOW}To register the key, run:${NC}"
    echo ""
    echo 'curl -s -X POST "http://localhost:8003/api/secrets/default/ANTHROPIC_API_KEY" \'
    echo '  -H "X-Service: commonui" \'
    echo '  -H "X-Token: L8Z7mbEqJLHITqXn6SnOBOYZnmnfnSpC8Lebetpvmu8" \'
    echo '  -H "Content-Type: application/json" \'
    echo '  -d '"'"'{"value": "sk-ant-api03-YOUR-KEY-HERE"}'"'"
    echo ""
else
    echo -e "${YELLOW}⚠️ Unexpected response${NC}"
fi
echo ""

# Test 4: List all secrets in project
echo -e "${YELLOW}[Test 4] List Secrets in '${PROJECT}' Project${NC}"
echo ""

LIST_RESPONSE=$(curl -s "${MYVAULT_URL}/api/secrets/${PROJECT}" \
    -H "X-Service: ${SERVICE_NAME}" \
    -H "X-Token: ${SERVICE_TOKEN}" 2>/dev/null || echo '{"error": "Request failed"}')

if echo "$LIST_RESPONSE" | grep -q "secrets\|keys"; then
    echo "Registered secrets:"
    echo "$LIST_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'secrets' in data:
        for s in data['secrets']:
            name = s.get('key', s.get('name', 'unknown'))
            print(f'  - {name}')
    elif 'keys' in data:
        for k in data['keys']:
            print(f'  - {k}')
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                name = item.get('key', item.get('name', str(item)))
                print(f'  - {name}')
            else:
                print(f'  - {item}')
    else:
        print(json.dumps(data, indent=2))
except:
    print(sys.stdin.read())
" 2>/dev/null || echo "$LIST_RESPONSE"
else
    echo "Response: ${LIST_RESPONSE}"
fi
echo ""

# Test 5: Check environment variables in current shell
echo -e "${YELLOW}[Test 5] Environment Variables Check${NC}"
echo ""

echo "MYVAULT_ENABLED: ${MYVAULT_ENABLED:-<not set>}"
echo "MYVAULT_BASE_URL: ${MYVAULT_BASE_URL:-<not set>}"
echo "MYVAULT_SERVICE_NAME: ${MYVAULT_SERVICE_NAME:-<not set>}"
echo "MYVAULT_SERVICE_TOKEN: ${MYVAULT_SERVICE_TOKEN:+<set>}${MYVAULT_SERVICE_TOKEN:-<not set>}"
echo "MYVAULT_DEFAULT_PROJECT: ${MYVAULT_DEFAULT_PROJECT:-<not set>}"
echo ""

# Summary
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Diagnostic Summary${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

if echo "$KEY_RESPONSE" | grep -q '"value"'; then
    echo -e "${GREEN}✅ All checks passed${NC}"
    echo ""
    echo "ANTHROPIC_API_KEY is available in MyVault."
    echo "If E2E test still fails, restart mySwiftAgentCore:"
    echo ""
    echo "  ./scripts/dev-hybrid.sh stop --local-only"
    echo "  ./scripts/dev-hybrid.sh start --local-only"
else
    echo -e "${RED}❌ ANTHROPIC_API_KEY not found${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Register ANTHROPIC_API_KEY in MyVault (see command above)"
    echo "2. Restart mySwiftAgentCore"
    echo "3. Re-run E2E test"
fi
echo ""
