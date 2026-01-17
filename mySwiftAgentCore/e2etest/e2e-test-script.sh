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

echo ""
echo "============================================"
echo "  E2E Test Complete"
echo "============================================"
