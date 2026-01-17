#!/bin/bash
# E2E Test: google_search capability
# expertAgent API経由でGoogle検索をテスト（LLMナレッジ抽出あり）
# 注意: このテストは180秒程度かかる場合があります

set -e

EXPERT_AGENT_API="${EXPERT_AGENT_API:-http://localhost:8004}"
SEARCH_QUERY="${1:-TypeScript 5.0 features}"
NUM_RESULTS="${2:-3}"
TIMEOUT="${TIMEOUT:-180}"

echo "========================================"
echo "E2E Test: google_search"
echo "========================================"
echo "API: ${EXPERT_AGENT_API}"
echo "Query: ${SEARCH_QUERY}"
echo "Results: ${NUM_RESULTS}"
echo "Timeout: ${TIMEOUT}s"
echo ""
echo "[NOTE] LLMナレッジ抽出のため、完了まで1-3分かかります..."
echo ""

# テスト実行
echo "[TEST] Google検索実行中..."
START_TIME=$(date +%s)

RESPONSE=$(curl -s -X POST "${EXPERT_AGENT_API}/v1/utility/google_search" \
  -H "Content-Type: application/json" \
  -d "{
    \"queries\": [\"${SEARCH_QUERY}\"],
    \"num\": ${NUM_RESULTS}
  }" \
  --max-time "${TIMEOUT}")

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

# 結果確認
STATUS=$(echo "$RESPONSE" | jq -r '.status')
RESULTS_COUNT=$(echo "$RESPONSE" | jq -r '.search_results_count')

echo ""
echo "[RESULT]"
echo "  Status: ${STATUS}"
echo "  Results Count: ${RESULTS_COUNT}"
echo "  Elapsed Time: ${ELAPSED}s"
echo ""

if [ "$STATUS" = "ok" ]; then
  echo "[SEARCH RESULTS]"
  echo "$RESPONSE" | jq -r '.search_results[] | "  - \(.title)\n    URL: \(.link)\n"'
  echo "✅ TEST PASSED"
  exit 0
else
  echo "❌ TEST FAILED"
  echo "$RESPONSE" | jq '.'
  exit 1
fi
