#!/bin/bash
# E2E Test: json_output_agent capability
# TaskFlowEngine経由でJSON Output Agentをテスト

set -e

TASKFLOW_API="${TASKFLOW_API:-http://localhost:8006}"
PROJECT="${PROJECT:-default_project}"
WORKFLOW="json_output_agent_example"

echo "========================================"
echo "E2E Test: json_output_agent"
echo "========================================"
echo "API: ${TASKFLOW_API}"
echo "Project: ${PROJECT}"
echo "Workflow: ${WORKFLOW}"
echo ""

# テスト実行
echo "[TEST] 自然言語からJSON変換..."
RESPONSE=$(curl -s -X POST "${TASKFLOW_API}/api/v1/taskflow/execute" \
  -H "Content-Type: application/json" \
  -d "{
    \"project\": \"${PROJECT}\",
    \"workflow\": \"${WORKFLOW}\",
    \"inputs\": {
      \"text\": \"Name: John Doe, Age: 30, Job: Engineer\",
      \"schema_instruction\": \"Convert the input to JSON format with fields: name, age, occupation\"
    }
  }")

# 結果確認
STATUS=$(echo "$RESPONSE" | jq -r '.status')
JSON_RESULT=$(echo "$RESPONSE" | jq '.results.json_result')
DURATION=$(echo "$RESPONSE" | jq -r '.durationMs')

echo ""
echo "[RESULT]"
echo "  Status: ${STATUS}"
echo "  JSON Result:"
echo "$JSON_RESULT" | jq '.'
echo "  Duration: ${DURATION}ms"
echo ""

if [ "$STATUS" = "success" ]; then
  # JSON構造の検証
  NAME=$(echo "$JSON_RESULT" | jq -r '.name // empty')
  if [ -n "$NAME" ]; then
    echo "✅ TEST PASSED"
    exit 0
  else
    echo "❌ TEST FAILED: JSON structure invalid"
    exit 1
  fi
else
  echo "❌ TEST FAILED"
  echo "$RESPONSE" | jq '.'
  exit 1
fi
