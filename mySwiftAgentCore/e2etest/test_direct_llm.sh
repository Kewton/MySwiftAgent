#!/bin/bash
# E2E Test: direct_llm capability
# TaskFlowEngine経由でDirect LLMをテスト

set -e

TASKFLOW_API="${TASKFLOW_API:-http://localhost:8006}"
PROJECT="${PROJECT:-default_project}"
WORKFLOW="direct_llm_example"

echo "========================================"
echo "E2E Test: direct_llm"
echo "========================================"
echo "API: ${TASKFLOW_API}"
echo "Project: ${PROJECT}"
echo "Workflow: ${WORKFLOW}"
echo ""

# テスト実行
echo "[TEST] GPT-4o-miniでテキスト生成..."
RESPONSE=$(curl -s -X POST "${TASKFLOW_API}/api/v1/taskflow/execute" \
  -H "Content-Type: application/json" \
  -d "{
    \"project\": \"${PROJECT}\",
    \"workflow\": \"${WORKFLOW}\",
    \"inputs\": {
      \"prompt\": \"Hello, please respond with exactly one word: OK\"
    }
  }")

# 結果確認
STATUS=$(echo "$RESPONSE" | jq -r '.status')
RESULT=$(echo "$RESPONSE" | jq -r '.results.response')
DURATION=$(echo "$RESPONSE" | jq -r '.durationMs')

echo ""
echo "[RESULT]"
echo "  Status: ${STATUS}"
echo "  Response: ${RESULT}"
echo "  Duration: ${DURATION}ms"
echo ""

if [ "$STATUS" = "success" ]; then
  echo "✅ TEST PASSED"
  exit 0
else
  echo "❌ TEST FAILED"
  echo "$RESPONSE" | jq '.'
  exit 1
fi
