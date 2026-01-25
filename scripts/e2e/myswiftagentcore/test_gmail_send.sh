#!/bin/bash
# E2E Test: gmail_send capability
# TaskFlowEngine経由でGmailメール送信をテスト
# 注意: 実際にメールが送信されます

set -e

TASKFLOW_API="${TASKFLOW_API:-http://localhost:8006}"
PROJECT="${PROJECT:-default_project}"
WORKFLOW="gmail_send_example"

# 引数からメールアドレスを取得（必須）
TO_ADDRESS="${1}"
SUBJECT="${2:-TaskFlow E2E Test}"
BODY="${3:-This is an automated test email from mySwiftAgentCore TaskFlowEngine.}"

if [ -z "$TO_ADDRESS" ]; then
  echo "Usage: $0 <to_address> [subject] [body]"
  echo ""
  echo "Example:"
  echo "  $0 test@example.com"
  echo "  $0 test@example.com \"Test Subject\" \"Test body message\""
  exit 1
fi

echo "========================================"
echo "E2E Test: gmail_send"
echo "========================================"
echo "API: ${TASKFLOW_API}"
echo "Project: ${PROJECT}"
echo "Workflow: ${WORKFLOW}"
echo ""
echo "To: ${TO_ADDRESS}"
echo "Subject: ${SUBJECT}"
echo ""

# 確認プロンプト
read -p "メールを送信しますか？ (y/N): " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
  echo "キャンセルしました"
  exit 0
fi

# テスト実行
echo ""
echo "[TEST] メール送信中..."

# JSONエスケープ
ESCAPED_BODY=$(echo "$BODY" | sed 's/"/\\"/g' | sed ':a;N;$!ba;s/\n/\\n/g')

RESPONSE=$(curl -s -X POST "${TASKFLOW_API}/api/v1/taskflow/execute" \
  -H "Content-Type: application/json" \
  -d "{
    \"project\": \"${PROJECT}\",
    \"workflow\": \"${WORKFLOW}\",
    \"inputs\": {
      \"to\": \"${TO_ADDRESS}\",
      \"subject\": \"${SUBJECT}\",
      \"body\": \"${ESCAPED_BODY}\"
    }
  }")

# 結果確認
STATUS=$(echo "$RESPONSE" | jq -r '.status')
MESSAGE_ID=$(echo "$RESPONSE" | jq -r '.results.message_id')
DURATION=$(echo "$RESPONSE" | jq -r '.durationMs')

echo ""
echo "[RESULT]"
echo "  Status: ${STATUS}"
echo "  Message ID: ${MESSAGE_ID}"
echo "  Duration: ${DURATION}ms"
echo ""

if [ "$STATUS" = "success" ]; then
  echo "✅ TEST PASSED - メールが送信されました"
  exit 0
else
  echo "❌ TEST FAILED"
  echo "$RESPONSE" | jq '.'
  exit 1
fi
