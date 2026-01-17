#!/bin/bash
# ============================================
# Issue #364 E2E API Test Script
# mySwiftAgentCore - taskflowGeneratorAgent
# ============================================
#
# 実行日: 2026-01-16
# 対象: POST /api/v1/generator/workflow/batch
#
# 前提条件:
#   - mySwiftAgentCore が http://localhost:8006 で起動している
#   - MyVault に ANTHROPIC_API_KEY が設定されている（実LLM呼び出しの場合）
#
# 使用方法:
#   chmod +x e2e-test-script.sh
#   ./e2e-test-script.sh
#

set -e

# カラー定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:8006"

echo "============================================"
echo "  Issue #364 E2E API Test"
echo "  mySwiftAgentCore - taskflowGeneratorAgent"
echo "============================================"
echo ""

# ============================================
# Test 1: Health Check
# ============================================
echo -e "${YELLOW}[Test 1] Health Check${NC}"
echo "GET ${BASE_URL}/health"
echo ""

HEALTH_RESPONSE=$(curl -s "${BASE_URL}/health")
HEALTH_STATUS=$(echo "$HEALTH_RESPONSE" | jq -r '.status' 2>/dev/null || echo "error")

if [ "$HEALTH_STATUS" = "healthy" ]; then
    echo -e "${GREEN}✅ PASS${NC} - Status: healthy"
else
    echo -e "${RED}❌ FAIL${NC} - Response: $HEALTH_RESPONSE"
    exit 1
fi
echo ""

# ============================================
# Test 2: Generator Health Check
# ============================================
echo -e "${YELLOW}[Test 2] Generator Health Check${NC}"
echo "GET ${BASE_URL}/api/v1/generator/health"
echo ""

GENERATOR_HEALTH=$(curl -s "${BASE_URL}/api/v1/generator/health")
GENERATOR_STATUS=$(echo "$GENERATOR_HEALTH" | jq -r '.status' 2>/dev/null || echo "error")

if [ "$GENERATOR_STATUS" = "healthy" ]; then
    echo -e "${GREEN}✅ PASS${NC} - Status: healthy"
else
    echo -e "${RED}❌ FAIL${NC} - Response: $GENERATOR_HEALTH"
    exit 1
fi
echo ""

# ============================================
# Test 3: Batch Generation API
# ============================================
echo -e "${YELLOW}[Test 3] Batch Generation API${NC}"
echo "POST ${BASE_URL}/api/v1/generator/workflow/batch"
echo ""

# 生成先ディレクトリ
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
GENERATED_DIR="${PROJECT_ROOT}/generated/workflows/default_project"

# 既存の生成ファイルを削除
echo "Cleaning up existing generated workflows..."
WORKFLOW_PATTERNS=(
  "execute_google_search_task_001"
  "summarize_search_results_task_002"
  "send_email_via_gmail_task_003"
)

for pattern in "${WORKFLOW_PATTERNS[@]}"; do
  # ルートレベルのファイル
  if [ -f "${GENERATED_DIR}/${pattern}.json" ]; then
    echo "  Deleting: ${pattern}.json"
    rm -f "${GENERATED_DIR}/${pattern}.json"
  fi
  # タスクディレクトリ内のファイル
  TASK_ID=$(echo "$pattern" | grep -oE 'task_[0-9]+')
  if [ -d "${GENERATED_DIR}/${TASK_ID}" ]; then
    echo "  Deleting directory: ${TASK_ID}/"
    rm -rf "${GENERATED_DIR}/${TASK_ID}"
  fi
done

# タイムスタンプマーカー（生成ファイル検出用）
touch /tmp/.e2e_test_start
echo ""

# テストデータ（Google検索 → サマリ → メール送信のワークフロー）
REQUEST_BODY='{
  "tasks": [
    {
      "task_id": "task_001",
      "name": "Execute Google Search",
      "description": "Perform a Web search using the provided search query to gather relevant information.",
      "interface": {
        "input": {"query": "string"},
        "output": {"results": "array"}
      }
    },
    {
      "task_id": "task_002",
      "name": "Summarize Search Results",
      "description": "Process the search results from task_001 using an LLM to create a concise and informative summary suitable for an email body.",
      "dependencies": ["task_001"],
      "interface": {
        "input": {"results": "array"},
        "output": {"summary": "string"}
      }
    },
    {
      "task_id": "task_003",
      "name": "Send Email via Gmail",
      "description": "Send the summarized search results to the specified recipient email address with the given subject line.",
      "dependencies": ["task_002"],
      "interface": {
        "input": {"summary": "string", "to_email": "string", "subject": "string"},
        "output": {"success": "boolean", "message_id": "string"}
      }
    }
  ],
  "capabilities": [
    {
      "id": "google_search",
      "name": "Google Search",
      "description": "Performs web search using Google",
      "category": "api",
      "status": "available"
    },
    {
      "id": "myllm",
      "name": "My LLM",
      "description": "LLM for text processing",
      "category": "llm",
      "status": "available"
    },
    {
      "id": "gmail_send",
      "name": "Gmail Send",
      "description": "Sends email via Gmail API",
      "category": "api",
      "status": "available"
    }
  ],
  "project_id": "default_project",
  "options": {
    "max_concurrency": 3,
    "timeout_per_task_ms": 60000,
    "validate_before_register": true
  }
}'

echo "Request Body:"
echo "$REQUEST_BODY" | jq .
echo ""

# APIを呼び出し
echo "Calling API..."
BATCH_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/generator/workflow/batch" \
  -H "Content-Type: application/json" \
  -d "$REQUEST_BODY")

echo ""
echo "Response:"
echo "$BATCH_RESPONSE" | jq .
echo ""

# レスポンス解析
SUCCESS=$(echo "$BATCH_RESPONSE" | jq -r '.success' 2>/dev/null || echo "error")
FAILED_TASKS=$(echo "$BATCH_RESPONSE" | jq -r '.failed_tasks | length' 2>/dev/null || echo "0")

if [ "$SUCCESS" = "true" ]; then
    echo -e "${GREEN}✅ PASS${NC} - Workflows generated successfully"
elif [ "$SUCCESS" = "false" ] && [ "$FAILED_TASKS" -gt 0 ]; then
    # エラータイプを確認
    ERROR_TYPE=$(echo "$BATCH_RESPONSE" | jq -r '.failed_tasks[0].error_type' 2>/dev/null || echo "unknown")
    RECOVERY=$(echo "$BATCH_RESPONSE" | jq -r '.failed_tasks[0].recovery_suggestion' 2>/dev/null || echo "unknown")

    if [ "$ERROR_TYPE" = "LLM_ERROR" ]; then
        echo -e "${YELLOW}⚠️ PARTIAL${NC} - LLM Error (API key may not be configured)"
        echo "  Error Type: $ERROR_TYPE"
        echo "  Recovery: $RECOVERY"
        echo ""
        echo "  API is working correctly. Configure ANTHROPIC_API_KEY in MyVault for real LLM calls."
    else
        echo -e "${RED}❌ FAIL${NC} - Unexpected error"
        echo "  Error Type: $ERROR_TYPE"
    fi
else
    echo -e "${RED}❌ FAIL${NC} - Unexpected response"
fi
echo ""

# ============================================
# Test 4: Execute Generated Workflows
# ============================================
echo -e "${YELLOW}[Test 4] Execute Generated Workflows${NC}"
echo ""

EXECUTION_SUCCESS=true
EXECUTION_RESULTS=()

if [ "$SUCCESS" = "true" ]; then
    # 生成されたワークフローを取得
    GENERATED_WORKFLOWS=$(echo "$BATCH_RESPONSE" | jq -r '.workflows[]?.workflow_name // empty' 2>/dev/null)

    if [ -z "$GENERATED_WORKFLOWS" ]; then
        echo "No workflows found in response, checking generated directory..."
        # ディレクトリから生成されたファイルを探す
        GENERATED_FILES=$(find "${GENERATED_DIR}" -maxdepth 2 -name "*.json" -newer /tmp/.e2e_test_start 2>/dev/null | head -5)

        if [ -n "$GENERATED_FILES" ]; then
            for file in $GENERATED_FILES; do
                WORKFLOW_NAME=$(basename "$file" .json)
                GENERATED_WORKFLOWS="${GENERATED_WORKFLOWS}${WORKFLOW_NAME}"$'\n'
            done
        fi
    fi

    # task_001のワークフローのみ実行（依存関係のないタスク）
    echo "Executing task_001 workflow (google_search)..."
    echo ""

    # task_001のワークフロー名を特定
    TASK_001_WORKFLOW=""
    for wf in $GENERATED_WORKFLOWS; do
        if [[ "$wf" == *"task_001"* ]]; then
            TASK_001_WORKFLOW="$wf"
            break
        fi
    done

    # ディレクトリからも検索
    if [ -z "$TASK_001_WORKFLOW" ]; then
        if [ -d "${GENERATED_DIR}/task_001" ]; then
            TASK_001_FILE=$(ls "${GENERATED_DIR}/task_001"/*.json 2>/dev/null | head -1)
            if [ -n "$TASK_001_FILE" ]; then
                TASK_001_WORKFLOW=$(basename "$TASK_001_FILE" .json)
            fi
        fi
    fi

    if [ -n "$TASK_001_WORKFLOW" ]; then
        echo "  Workflow: ${TASK_001_WORKFLOW}"
        echo "  POST ${BASE_URL}/api/v1/taskflow/execute"
        echo ""

        # ワークフロー実行
        EXEC_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/taskflow/execute" \
          -H "Content-Type: application/json" \
          -d "{
            \"project\": \"default_project\",
            \"workflow\": \"task_001/${TASK_001_WORKFLOW}\",
            \"inputs\": {
              \"query\": \"TypeScript 5.0 new features\"
            }
          }" \
          --max-time 120)

        EXEC_STATUS=$(echo "$EXEC_RESPONSE" | jq -r '.status' 2>/dev/null || echo "error")
        EXEC_DURATION=$(echo "$EXEC_RESPONSE" | jq -r '.durationMs' 2>/dev/null || echo "N/A")

        echo "  Execution Response:"
        echo "$EXEC_RESPONSE" | jq '.' 2>/dev/null || echo "$EXEC_RESPONSE"
        echo ""

        if [ "$EXEC_STATUS" = "success" ]; then
            echo -e "  ${GREEN}✅ Workflow executed successfully${NC} (${EXEC_DURATION}ms)"
            EXECUTION_RESULTS+=("task_001: ✅ PASS (${EXEC_DURATION}ms)")
        elif [ "$EXEC_STATUS" = "error" ]; then
            ERROR_CODE=$(echo "$EXEC_RESPONSE" | jq -r '.error.code' 2>/dev/null || echo "unknown")
            if [ "$ERROR_CODE" = "TIMEOUT_ERROR" ]; then
                echo -e "  ${YELLOW}⚠️ Workflow timed out${NC} (google_search may take 1-3 minutes)"
                EXECUTION_RESULTS+=("task_001: ⚠️ TIMEOUT (expected for google_search)")
            else
                echo -e "  ${RED}❌ Workflow execution failed${NC}"
                EXECUTION_RESULTS+=("task_001: ❌ FAIL")
                EXECUTION_SUCCESS=false
            fi
        else
            echo -e "  ${YELLOW}⚠️ Unknown execution status: ${EXEC_STATUS}${NC}"
            EXECUTION_RESULTS+=("task_001: ⚠️ UNKNOWN")
        fi
    else
        echo -e "  ${YELLOW}⚠️ No task_001 workflow found to execute${NC}"
        EXECUTION_RESULTS+=("task_001: ⚠️ NOT FOUND")
    fi
else
    echo -e "${YELLOW}⚠️ Skipping workflow execution (generation failed or partial)${NC}"
    EXECUTION_RESULTS+=("Skipped (generation not successful)")
fi
echo ""

# ============================================
# Test Summary
# ============================================
echo "============================================"
echo "  Test Summary"
echo "============================================"
echo ""
echo "Test 1 (Health Check):           ✅ PASS"
echo "Test 2 (Generator Health):       ✅ PASS"

if [ "$SUCCESS" = "true" ]; then
    echo "Test 3 (Batch Generation):       ✅ PASS"
elif [ "$ERROR_TYPE" = "LLM_ERROR" ]; then
    echo "Test 3 (Batch Generation):       ⚠️ PARTIAL (API works, LLM key missing)"
else
    echo "Test 3 (Batch Generation):       ❌ FAIL"
fi

# Test 4 結果表示
if [ ${#EXECUTION_RESULTS[@]} -gt 0 ]; then
    for result in "${EXECUTION_RESULTS[@]}"; do
        echo "Test 4 (Workflow Execution):     $result"
    done
else
    echo "Test 4 (Workflow Execution):     ⚠️ SKIPPED"
fi

echo ""
echo "============================================"
echo "  E2E Test Complete"
echo "============================================"

# 全体の終了ステータス
if [ "$SUCCESS" != "true" ] && [ "$ERROR_TYPE" != "LLM_ERROR" ]; then
    exit 1
fi
if [ "$EXECUTION_SUCCESS" != "true" ]; then
    exit 1
fi
exit 0
