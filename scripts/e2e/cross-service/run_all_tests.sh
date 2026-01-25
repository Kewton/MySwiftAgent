#!/bin/bash
# ============================================
# Run All Cross-Service E2E Tests
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║        Cross-Service E2E Tests Runner                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 引数解析
KEYWORD="${1:-AI技術の最新動向}"
EMAIL="${2}"

if [ -z "$EMAIL" ]; then
    echo "Usage: $0 <keyword> <email>"
    echo ""
    echo "Example:"
    echo "  $0 \"大谷翔平の妻\" test@example.com"
    exit 1
fi

echo "Running all cross-service E2E tests..."
echo ""

# Full Workflow E2E Test
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test: Full Workflow E2E"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

"${SCRIPT_DIR}/test_full_workflow_e2e.sh" \
    --keyword "$KEYWORD" \
    --email "$EMAIL" \
    --no-confirm

TEST_RESULT=$?

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "All tests completed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

exit $TEST_RESULT
