#!/bin/bash
# Issue #349 L3 Acceptance Test Script (Strengthened)
# TaskFlow V2: Transform/Conditional Improvements
#
# Target Project: graphAiServer
# Test Level: L3 (Local Acceptance Test)
# Requires: graphAiServer running on http://localhost:8000
#
# Acceptance Criteria:
#   AC-1: Map mode with @index, @first, @last helpers
#   AC-2: Merge mode with automatic JSON parsing
#   AC-3: Coalesce chain for conditional output
#   AC-4: Tutorial 9, 11, 12 execute successfully
#
# Usage:
#   ./graphAiServer/tests/acceptance/test_issue_349_acceptance.sh
#
# Environment Variables:
#   GRAPHAI_SERVER_URL: Override default server URL (default: http://localhost:8000)

set -e

# Configuration
BASE_URL="${GRAPHAI_SERVER_URL:-http://localhost:8000}"
API_V2_URL="${BASE_URL}/api/v2"
EVIDENCE_DIR="/tmp/issue349_acceptance"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TUTORIAL_DIR="${SCRIPT_DIR}/../../config/taskflow/tutorial"

PASSED=0
FAILED=0
SKIPPED=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${NC}[INFO] $1${NC}"
}

log_pass() {
    echo -e "${GREEN}[PASS] $1${NC}"
    ((PASSED++))
}

log_fail() {
    echo -e "${RED}[FAIL] $1${NC}"
    ((FAILED++))
}

log_skip() {
    echo -e "${YELLOW}[SKIP] $1${NC}"
    ((SKIPPED++))
}

# Execute workflow with definition from file
execute_workflow() {
    local tutorial_name="$1"
    local inputs="$2"
    local tutorial_file="${TUTORIAL_DIR}/${tutorial_name}.json"

    if [[ ! -f "$tutorial_file" ]]; then
        echo '{"error": "Tutorial file not found: '"$tutorial_file"'"}'
        return 1
    fi

    local definition
    definition=$(cat "$tutorial_file")

    curl -s -X POST "${API_V2_URL}/workflows/" \
        -H "Content-Type: application/json" \
        -d "{\"definition\": $definition, \"inputs\": $inputs}" 2>/dev/null || echo '{"error": "Request failed"}'
}

# Create evidence directory
mkdir -p "$EVIDENCE_DIR"

echo "============================================================"
echo "Issue #349 L3 Acceptance Test"
echo "Server: ${BASE_URL}"
echo "============================================================"
echo ""

# =================================================================
# Step 1: Service Health Check
# =================================================================
log_info "Step 1: Checking graphAiServer health..."

HEALTH_RESPONSE=$(curl -sf "${BASE_URL}/health" 2>/dev/null || echo "FAILED")

if [[ "$HEALTH_RESPONSE" == "FAILED" ]]; then
    log_fail "graphAiServer is not running at ${BASE_URL}"
    echo ""
    echo "Please start the service with one of:"
    echo "  cd graphAiServer && npm run start"
    echo "  ./scripts/dev-hybrid.sh"
    echo "  make dev-all"
    echo ""
    exit 1
fi

HEALTH_STATUS=$(echo "$HEALTH_RESPONSE" | jq -r '.status // "unknown"')
if [[ "$HEALTH_STATUS" == "healthy" ]]; then
    log_pass "graphAiServer is healthy at ${BASE_URL}"
else
    log_fail "graphAiServer health check returned unexpected status: $HEALTH_STATUS"
    exit 1
fi

echo "$HEALTH_RESPONSE" > "${EVIDENCE_DIR}/health_response.json"

# =================================================================
# Step 2: AC-1 - Tutorial 9: Map @index Helper Test (STRICT)
# =================================================================
log_info "Step 2: AC-1 - Testing Tutorial 9 (Map @index helper)..."

TUTORIAL9_RESPONSE=$(execute_workflow "9_transform_map" '{"products": [{"name": "apple", "price": 150}, {"name": "orange", "price": 100}, {"name": "banana", "price": 200}]}')

echo "$TUTORIAL9_RESPONSE" > "${EVIDENCE_DIR}/tutorial9_result.json"

if echo "$TUTORIAL9_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    ERROR_MSG=$(echo "$TUTORIAL9_RESPONSE" | jq -r '.error // "Unknown error"')
    log_fail "Tutorial 9 execution failed: $ERROR_MSG"
else
    WORKFLOW_ERRORS=$(echo "$TUTORIAL9_RESPONSE" | jq -r '.errors // {} | keys | length')
    if [[ "$WORKFLOW_ERRORS" != "0" ]]; then
        log_fail "Tutorial 9 had execution errors"
    else
        # STRICT: Verify @index produces numbered output (0., 1., 2.)
        NUMBERED_LIST=$(echo "$TUTORIAL9_RESPONSE" | jq -r '.results._output.numbered_list | if type == "array" then join("\n") else . end // ""')

        HAS_ZERO=$(echo "$NUMBERED_LIST" | grep -q "0\." && echo "yes" || echo "no")
        HAS_ONE=$(echo "$NUMBERED_LIST" | grep -q "1\." && echo "yes" || echo "no")
        HAS_TWO=$(echo "$NUMBERED_LIST" | grep -q "2\." && echo "yes" || echo "no")

        if [[ "$HAS_ZERO" == "yes" && "$HAS_ONE" == "yes" && "$HAS_TWO" == "yes" ]]; then
            log_pass "AC-1: @index produces numbered list (0., 1., 2. found)"
        else
            log_fail "AC-1: @index not producing correct numbered list"
            echo "  Expected: 0., 1., 2. in output"
            echo "  Got: $NUMBERED_LIST"
        fi

        # STRICT: Verify @last marks final item
        HAS_LAST=$(echo "$NUMBERED_LIST" | grep -q "最後" && echo "yes" || echo "no")
        if [[ "$HAS_LAST" == "yes" ]]; then
            log_pass "AC-1: @last helper marks final item (最後 found)"
        else
            log_fail "AC-1: @last helper not marking final item"
            echo "  Expected: 最後 in output"
            echo "  Got: $NUMBERED_LIST"
        fi
    fi
fi

# =================================================================
# Step 3: AC-2 - Tutorial 11: Merge JSON Parse Test (STRICT)
# =================================================================
log_info "Step 3: AC-2 - Testing Tutorial 11 (Merge JSON auto-parse)..."

TUTORIAL11_RESPONSE=$(execute_workflow "11_transform_merge" '{"user_settings": {"theme": "dark", "notifications": {"push": true}}}')

echo "$TUTORIAL11_RESPONSE" > "${EVIDENCE_DIR}/tutorial11_result.json"

if echo "$TUTORIAL11_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    ERROR_MSG=$(echo "$TUTORIAL11_RESPONSE" | jq -r '.error // "Unknown error"')
    log_fail "Tutorial 11 execution failed: $ERROR_MSG"
else
    WORKFLOW_ERRORS=$(echo "$TUTORIAL11_RESPONSE" | jq -r '.errors // {} | keys | length')
    if [[ "$WORKFLOW_ERRORS" != "0" ]]; then
        log_fail "Tutorial 11 had execution errors"
    else
        # STRICT: Verify shallow merge applied user theme
        SHALLOW_THEME=$(echo "$TUTORIAL11_RESPONSE" | jq -r '.results._output.shallow_config.theme // ""')
        SHALLOW_LANG=$(echo "$TUTORIAL11_RESPONSE" | jq -r '.results._output.shallow_config.language // ""')

        if [[ "$SHALLOW_THEME" == "dark" && "$SHALLOW_LANG" == "ja" ]]; then
            log_pass "AC-2: Shallow merge works (theme=dark, language=ja)"
        else
            log_fail "AC-2: Shallow merge incorrect"
            echo "  Expected: theme=dark, language=ja"
            echo "  Got: theme=$SHALLOW_THEME, language=$SHALLOW_LANG"
        fi

        # STRICT: Verify deep merge preserves nested defaults
        DEEP_EMAIL=$(echo "$TUTORIAL11_RESPONSE" | jq -r '.results._output.deep_config.notifications.email // ""')
        DEEP_PUSH=$(echo "$TUTORIAL11_RESPONSE" | jq -r '.results._output.deep_config.notifications.push // ""')

        if [[ "$DEEP_EMAIL" == "true" && "$DEEP_PUSH" == "true" ]]; then
            log_pass "AC-2: Deep merge preserves nested defaults (email=true preserved, push=true applied)"
        else
            log_fail "AC-2: Deep merge not preserving nested defaults"
            echo "  Expected: email=true, push=true"
            echo "  Got: email=$DEEP_EMAIL, push=$DEEP_PUSH"
        fi
    fi
fi

# =================================================================
# Step 4: AC-3 - Tutorial 12: Coalesce Chain (score=85 -> A)
# =================================================================
log_info "Step 4: AC-3 - Testing Tutorial 12 (score=85 -> A grade)..."

TUTORIAL12_85_RESPONSE=$(execute_workflow "12_conditional_basic" '{"score": 85}')

echo "$TUTORIAL12_85_RESPONSE" > "${EVIDENCE_DIR}/tutorial12_score85_result.json"

if echo "$TUTORIAL12_85_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    ERROR_MSG=$(echo "$TUTORIAL12_85_RESPONSE" | jq -r '.error // "Unknown error"')
    log_fail "Tutorial 12 (score=85) execution failed: $ERROR_MSG"
else
    WORKFLOW_ERRORS=$(echo "$TUTORIAL12_85_RESPONSE" | jq -r '.errors // {} | keys | length')
    if [[ "$WORKFLOW_ERRORS" != "0" ]]; then
        log_fail "Tutorial 12 (score=85) had execution errors"
    else
        GRADE=$(echo "$TUTORIAL12_85_RESPONSE" | jq -r '.results._output.grade // ""')
        MESSAGE=$(echo "$TUTORIAL12_85_RESPONSE" | jq -r '.results._output.message // ""')

        if [[ "$GRADE" == "A (優秀)" ]]; then
            log_pass "AC-3: Coalesce chain returns 'A (優秀)' for score=85"
        else
            log_fail "AC-3: Coalesce chain incorrect for score=85"
            echo "  Expected: A (優秀)"
            echo "  Got: $GRADE"
        fi

        if echo "$MESSAGE" | grep -q "85" && echo "$MESSAGE" | grep -q "合格"; then
            log_pass "AC-3: Message contains score (85) and pass indicator (合格)"
        else
            log_fail "AC-3: Message incorrect for score=85"
            echo "  Expected: contains '85' and '合格'"
            echo "  Got: $MESSAGE"
        fi
    fi
fi

# =================================================================
# Step 5: AC-3 - Tutorial 12: Coalesce Chain (score=45 -> C)
# =================================================================
log_info "Step 5: AC-3 - Testing Tutorial 12 (score=45 -> C grade)..."

TUTORIAL12_45_RESPONSE=$(execute_workflow "12_conditional_basic" '{"score": 45}')

echo "$TUTORIAL12_45_RESPONSE" > "${EVIDENCE_DIR}/tutorial12_score45_result.json"

if echo "$TUTORIAL12_45_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    ERROR_MSG=$(echo "$TUTORIAL12_45_RESPONSE" | jq -r '.error // "Unknown error"')
    log_fail "Tutorial 12 (score=45) execution failed: $ERROR_MSG"
else
    WORKFLOW_ERRORS=$(echo "$TUTORIAL12_45_RESPONSE" | jq -r '.errors // {} | keys | length')
    if [[ "$WORKFLOW_ERRORS" != "0" ]]; then
        log_fail "Tutorial 12 (score=45) had execution errors"
    else
        GRADE=$(echo "$TUTORIAL12_45_RESPONSE" | jq -r '.results._output.grade // ""')
        MESSAGE=$(echo "$TUTORIAL12_45_RESPONSE" | jq -r '.results._output.message // ""')

        if [[ "$GRADE" == "C (不合格)" ]]; then
            log_pass "AC-3: Coalesce chain returns 'C (不合格)' for score=45"
        else
            log_fail "AC-3: Coalesce chain incorrect for score=45"
            echo "  Expected: C (不合格)"
            echo "  Got: $GRADE"
        fi

        if echo "$MESSAGE" | grep -q "45" && echo "$MESSAGE" | grep -q "不合格"; then
            log_pass "AC-3: Message contains score (45) and fail indicator (不合格)"
        else
            log_fail "AC-3: Message incorrect for score=45"
            echo "  Expected: contains '45' and '不合格'"
            echo "  Got: $MESSAGE"
        fi
    fi
fi

# =================================================================
# Step 6: AC-3 - Tutorial 12: Boundary Test (score=70 -> B)
# =================================================================
log_info "Step 6: AC-3 - Testing Tutorial 12 (score=70 -> B grade)..."

TUTORIAL12_70_RESPONSE=$(execute_workflow "12_conditional_basic" '{"score": 70}')

echo "$TUTORIAL12_70_RESPONSE" > "${EVIDENCE_DIR}/tutorial12_score70_result.json"

if echo "$TUTORIAL12_70_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    log_fail "Tutorial 12 (score=70) execution failed"
else
    WORKFLOW_ERRORS=$(echo "$TUTORIAL12_70_RESPONSE" | jq -r '.errors // {} | keys | length')
    if [[ "$WORKFLOW_ERRORS" != "0" ]]; then
        log_fail "Tutorial 12 (score=70) had execution errors"
    else
        GRADE=$(echo "$TUTORIAL12_70_RESPONSE" | jq -r '.results._output.grade // ""')

        if [[ "$GRADE" == "B (合格)" ]]; then
            log_pass "AC-3: Coalesce chain returns 'B (合格)' for score=70"
        else
            log_fail "AC-3: Coalesce chain incorrect for score=70"
            echo "  Expected: B (合格)"
            echo "  Got: $GRADE"
        fi
    fi
fi

# =================================================================
# Step 7: AC-4 - Regression Tests
# =================================================================
log_info "Step 7: AC-4 - Regression tests (Tutorial 1)..."

TUTORIAL1_RESPONSE=$(execute_workflow "1_hello" '{}')

echo "$TUTORIAL1_RESPONSE" > "${EVIDENCE_DIR}/tutorial1_result.json"

if echo "$TUTORIAL1_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    log_fail "AC-4: Tutorial 1 regression failed"
else
    WORKFLOW_ERRORS=$(echo "$TUTORIAL1_RESPONSE" | jq -r '.errors // {} | keys | length')
    if [[ "$WORKFLOW_ERRORS" == "0" ]]; then
        log_pass "AC-4: Tutorial 1 regression passed"
    else
        log_fail "AC-4: Tutorial 1 regression has errors"
    fi
fi

# =================================================================
# Summary
# =================================================================
echo ""
echo "============================================================"
echo "Issue #349 L3 Acceptance Test Results"
echo "============================================================"
echo ""
echo -e "  ${GREEN}PASSED${NC}: $PASSED"
echo -e "  ${RED}FAILED${NC}: $FAILED"
echo -e "  ${YELLOW}SKIPPED${NC}: $SKIPPED"
echo ""
echo "Evidence files saved to: $EVIDENCE_DIR"
ls -la "$EVIDENCE_DIR"
echo ""

if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}All acceptance tests PASSED${NC}"
    exit 0
else
    echo -e "${RED}Some acceptance tests FAILED${NC}"
    exit 1
fi
