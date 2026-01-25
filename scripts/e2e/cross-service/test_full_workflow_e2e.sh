#!/bin/bash
# ============================================
# Full Workflow E2E Test
# Cross-Service Integration Test
# ============================================
#
# テストシナリオ:
#   1. myAgentDesk経由でJob Generateを実行
#   2. 生成されたJobでRunを作成・実行
#   3. ワークフロー完了を確認
#   4. 結果検証
#
# 前提条件:
#   - ./scripts/dev-hybrid.sh start --local-only でサービス起動済み
#   - myVaultにdefault_projectのシークレット設定済み
#   - myAgentDeskでProject/Workbench作成済み
#
# 使用方法:
#   ./test_full_workflow_e2e.sh
#   ./test_full_workflow_e2e.sh --keyword "検索キーワード" --email "test@example.com"
#   ./test_full_workflow_e2e.sh --project-id "proj_xxx" --workbench-id "wb_xxx"
#

set -e

# ============================================
# 設定
# ============================================

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# サービスURL
MYAGENTDESK_URL="${MYAGENTDESK_URL:-http://localhost:8000}"
EXPERTAGENT_URL="${EXPERTAGENT_URL:-http://localhost:8004}"
MYSWIFTAGENTCORE_URL="${MYSWIFTAGENTCORE_URL:-http://localhost:8006}"
MYVAULT_URL="${MYVAULT_URL:-http://localhost:8003}"

# デフォルト値
DEFAULT_KEYWORD="AI技術の最新動向"
DEFAULT_EMAIL=""
DEFAULT_PROJECT_ID=""
DEFAULT_WORKBENCH_ID=""

# タイムアウト設定
HEALTH_CHECK_TIMEOUT=10
GENERATE_TIMEOUT=120
RUN_TIMEOUT=300
POLL_INTERVAL=5

# 結果ディレクトリ
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RESULTS_DIR="${SCRIPT_DIR}/results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${RESULTS_DIR}/test_full_workflow_${TIMESTAMP}.log"
RESULT_FILE="${RESULTS_DIR}/test_full_workflow_${TIMESTAMP}.json"

# ============================================
# ヘルプ
# ============================================

show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Full Workflow E2E Test - サービス間統合テスト"
    echo ""
    echo "OPTIONS:"
    echo "  --keyword <keyword>       検索キーワード (default: ${DEFAULT_KEYWORD})"
    echo "  --email <email>           メール送信先アドレス (必須)"
    echo "  --project-id <id>         Project ID (省略時は対話式で選択)"
    echo "  --workbench-id <id>       Workbench ID (省略時は対話式で選択)"
    echo "  --skip-generate           Job生成をスキップ（既存JobVersionを使用）"
    echo "  --job-version-id <id>     使用するJobVersion ID (--skip-generate時に必須)"
    echo "  --no-confirm              確認プロンプトをスキップ"
    echo "  --help                    このヘルプを表示"
    echo ""
    echo "EXAMPLES:"
    echo "  # インタラクティブモード"
    echo "  $0"
    echo ""
    echo "  # パラメータ指定"
    echo "  $0 --keyword \"大谷翔平\" --email \"test@example.com\""
    echo ""
    echo "  # 既存JobVersionを使用"
    echo "  $0 --skip-generate --job-version-id \"jv_xxx\" --email \"test@example.com\""
    echo ""
    echo "ENVIRONMENT VARIABLES:"
    echo "  MYAGENTDESK_URL      myAgentDesk URL (default: http://localhost:8000)"
    echo "  EXPERTAGENT_URL      expertAgent URL (default: http://localhost:8004)"
    echo "  MYSWIFTAGENTCORE_URL mySwiftAgentCore URL (default: http://localhost:8006)"
    echo "  MYVAULT_URL          myVault URL (default: http://localhost:8003)"
}

# ============================================
# ユーティリティ関数
# ============================================

log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$LOG_FILE"
}

log_info() {
    log "${BLUE}INFO${NC}" "$1"
}

log_success() {
    log "${GREEN}SUCCESS${NC}" "$1"
}

log_warn() {
    log "${YELLOW}WARN${NC}" "$1"
}

log_error() {
    log "${RED}ERROR${NC}" "$1"
}

log_step() {
    echo ""
    echo -e "${CYAN}========================================${NC}" | tee -a "$LOG_FILE"
    echo -e "${CYAN}$1${NC}" | tee -a "$LOG_FILE"
    echo -e "${CYAN}========================================${NC}" | tee -a "$LOG_FILE"
}

# JSON安全エスケープ
json_escape() {
    echo "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().strip()))'
}

# ============================================
# 引数解析
# ============================================

KEYWORD=""
EMAIL=""
PROJECT_ID=""
WORKBENCH_ID=""
SKIP_GENERATE=false
JOB_VERSION_ID=""
NO_CONFIRM=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --keyword)
            KEYWORD="$2"
            shift 2
            ;;
        --email)
            EMAIL="$2"
            shift 2
            ;;
        --project-id)
            PROJECT_ID="$2"
            shift 2
            ;;
        --workbench-id)
            WORKBENCH_ID="$2"
            shift 2
            ;;
        --skip-generate)
            SKIP_GENERATE=true
            shift
            ;;
        --job-version-id)
            JOB_VERSION_ID="$2"
            shift 2
            ;;
        --no-confirm)
            NO_CONFIRM=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# ============================================
# 初期化
# ============================================

mkdir -p "$RESULTS_DIR"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           Full Workflow E2E Test                           ║${NC}"
echo -e "${GREEN}║           Cross-Service Integration Test                   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Timestamp: ${TIMESTAMP}"
echo "Log file:  ${LOG_FILE}"
echo ""

# ============================================
# Step 1: ヘルスチェック
# ============================================

log_step "Step 1: Service Health Check"

check_health() {
    local name="$1"
    local url="$2"
    local endpoint="${3:-/health}"

    log_info "Checking ${name}..."

    local response
    response=$(curl -s -o /dev/null -w "%{http_code}" --max-time $HEALTH_CHECK_TIMEOUT "${url}${endpoint}" 2>/dev/null || echo "000")

    if [ "$response" = "200" ]; then
        log_success "${name}: OK (${url})"
        return 0
    else
        log_error "${name}: FAILED (HTTP ${response})"
        return 1
    fi
}

HEALTH_FAILED=false

check_health "myAgentDesk" "$MYAGENTDESK_URL" "/api/health" || HEALTH_FAILED=true
check_health "expertAgent" "$EXPERTAGENT_URL" "/health" || HEALTH_FAILED=true
check_health "mySwiftAgentCore" "$MYSWIFTAGENTCORE_URL" "/health" || HEALTH_FAILED=true
check_health "myVault" "$MYVAULT_URL" "/health" || HEALTH_FAILED=true

if [ "$HEALTH_FAILED" = true ]; then
    log_error "Some services are not healthy. Please start services with:"
    log_error "  ./scripts/dev-hybrid.sh start --local-only"
    exit 1
fi

log_success "All services are healthy!"

# ============================================
# Step 2: Project/Workbench取得
# ============================================

log_step "Step 2: Get Project and Workbench"

if [ -z "$PROJECT_ID" ]; then
    log_info "Fetching projects from myAgentDesk..."

    PROJECTS_RESPONSE=$(curl -s "${MYAGENTDESK_URL}/api/projects" 2>/dev/null)

    if [ -z "$PROJECTS_RESPONSE" ] || [ "$PROJECTS_RESPONSE" = "[]" ]; then
        log_error "No projects found. Please create a project in myAgentDesk first."
        exit 1
    fi

    echo ""
    echo "Available projects:"
    echo "$PROJECTS_RESPONSE" | jq -r '.[] | "  \(.id): \(.name)"'
    echo ""

    if [ "$NO_CONFIRM" = true ]; then
        PROJECT_ID=$(echo "$PROJECTS_RESPONSE" | jq -r '.[0].id')
        log_info "Auto-selected first project: ${PROJECT_ID}"
    else
        read -p "Enter Project ID: " PROJECT_ID
    fi
fi

if [ -z "$WORKBENCH_ID" ]; then
    log_info "Fetching workbenches for project ${PROJECT_ID}..."

    WORKBENCHES_RESPONSE=$(curl -s "${MYAGENTDESK_URL}/api/projects/${PROJECT_ID}/workbenches" 2>/dev/null)

    if [ -z "$WORKBENCHES_RESPONSE" ] || [ "$WORKBENCHES_RESPONSE" = "[]" ]; then
        log_error "No workbenches found. Please create a workbench in myAgentDesk first."
        exit 1
    fi

    echo ""
    echo "Available workbenches:"
    echo "$WORKBENCHES_RESPONSE" | jq -r '.[] | "  \(.id): \(.name)"'
    echo ""

    if [ "$NO_CONFIRM" = true ]; then
        WORKBENCH_ID=$(echo "$WORKBENCHES_RESPONSE" | jq -r '.[0].id')
        log_info "Auto-selected first workbench: ${WORKBENCH_ID}"
    else
        read -p "Enter Workbench ID: " WORKBENCH_ID
    fi
fi

log_success "Project: ${PROJECT_ID}"
log_success "Workbench: ${WORKBENCH_ID}"

# ============================================
# Step 3: パラメータ確認
# ============================================

log_step "Step 3: Confirm Parameters"

if [ -z "$KEYWORD" ]; then
    if [ "$NO_CONFIRM" = true ]; then
        KEYWORD="$DEFAULT_KEYWORD"
    else
        read -p "Enter search keyword [${DEFAULT_KEYWORD}]: " KEYWORD
        KEYWORD="${KEYWORD:-$DEFAULT_KEYWORD}"
    fi
fi

if [ -z "$EMAIL" ]; then
    if [ "$NO_CONFIRM" = true ]; then
        log_error "--email is required in non-interactive mode"
        exit 1
    else
        read -p "Enter email address: " EMAIL
        if [ -z "$EMAIL" ]; then
            log_error "Email address is required"
            exit 1
        fi
    fi
fi

echo ""
echo -e "${YELLOW}Test Parameters:${NC}"
echo "  Keyword: ${KEYWORD}"
echo "  Email:   ${EMAIL}"
echo "  Project: ${PROJECT_ID}"
echo "  Workbench: ${WORKBENCH_ID}"
echo ""

if [ "$NO_CONFIRM" = false ]; then
    read -p "Proceed with test? (y/N): " CONFIRM
    if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
        log_warn "Test cancelled by user"
        exit 0
    fi
fi

# ============================================
# Step 4: Job Generate
# ============================================

if [ "$SKIP_GENERATE" = false ]; then
    log_step "Step 4: Generate Job"

    log_info "Triggering job generation..."

    # Generate APIを呼び出し
    GENERATE_RESPONSE=$(curl -s -X POST "${MYAGENTDESK_URL}/api/projects/${PROJECT_ID}/workbenches/${WORKBENCH_ID}/generate" \
        -H "Content-Type: application/json" \
        --max-time $GENERATE_TIMEOUT 2>/dev/null)

    if [ -z "$GENERATE_RESPONSE" ]; then
        log_error "Generate API returned empty response"
        exit 1
    fi

    log_info "Generate response: $(echo "$GENERATE_RESPONSE" | jq -c '.')"

    # JobVersion IDを取得
    JOB_VERSION_ID=$(echo "$GENERATE_RESPONSE" | jq -r '.jobVersionId // .job_version_id // .id // empty')

    if [ -z "$JOB_VERSION_ID" ]; then
        log_error "Failed to get JobVersion ID from response"
        log_error "Response: $GENERATE_RESPONSE"
        exit 1
    fi

    log_success "JobVersion created: ${JOB_VERSION_ID}"

    # 生成完了を待機
    log_info "Waiting for job generation to complete..."

    GENERATE_STATUS="generating"
    GENERATE_WAIT=0

    while [ "$GENERATE_STATUS" = "generating" ] && [ $GENERATE_WAIT -lt $GENERATE_TIMEOUT ]; do
        sleep $POLL_INTERVAL
        GENERATE_WAIT=$((GENERATE_WAIT + POLL_INTERVAL))

        JOB_VERSION_RESPONSE=$(curl -s "${MYAGENTDESK_URL}/api/job-versions/${JOB_VERSION_ID}" 2>/dev/null)
        GENERATE_STATUS=$(echo "$JOB_VERSION_RESPONSE" | jq -r '.status // "unknown"')

        log_info "Generation status: ${GENERATE_STATUS} (${GENERATE_WAIT}s elapsed)"
    done

    if [ "$GENERATE_STATUS" != "active" ] && [ "$GENERATE_STATUS" != "ready" ] && [ "$GENERATE_STATUS" != "completed" ]; then
        log_error "Job generation failed or timed out. Status: ${GENERATE_STATUS}"
        exit 1
    fi

    log_success "Job generation completed!"
else
    log_step "Step 4: Skip Generate (Using existing JobVersion)"

    if [ -z "$JOB_VERSION_ID" ]; then
        log_error "--job-version-id is required when using --skip-generate"
        exit 1
    fi

    log_info "Using existing JobVersion: ${JOB_VERSION_ID}"
fi

# ============================================
# Step 5: Create and Execute Run
# ============================================

log_step "Step 5: Create and Execute Run"

log_info "Creating run with parameters..."

# Run作成リクエスト
RUN_REQUEST=$(cat <<EOF
{
    "jobVersionId": "${JOB_VERSION_ID}",
    "inputs": {
        "keyword": "${KEYWORD}",
        "email": "${EMAIL}"
    }
}
EOF
)

log_info "Run request: $(echo "$RUN_REQUEST" | jq -c '.')"

RUN_RESPONSE=$(curl -s -X POST "${MYAGENTDESK_URL}/api/runs" \
    -H "Content-Type: application/json" \
    -d "$RUN_REQUEST" \
    --max-time 30 2>/dev/null)

if [ -z "$RUN_RESPONSE" ]; then
    log_error "Run API returned empty response"
    exit 1
fi

log_info "Run response: $(echo "$RUN_RESPONSE" | jq -c '.')"

RUN_ID=$(echo "$RUN_RESPONSE" | jq -r '.id // .runId // .run_id // empty')

if [ -z "$RUN_ID" ]; then
    log_error "Failed to get Run ID from response"
    log_error "Response: $RUN_RESPONSE"
    exit 1
fi

log_success "Run created: ${RUN_ID}"

# ============================================
# Step 6: Wait for Run Completion
# ============================================

log_step "Step 6: Wait for Run Completion"

RUN_STATUS="queued"
RUN_WAIT=0

while [ "$RUN_STATUS" != "success" ] && [ "$RUN_STATUS" != "failed" ] && [ "$RUN_STATUS" != "canceled" ] && [ $RUN_WAIT -lt $RUN_TIMEOUT ]; do
    sleep $POLL_INTERVAL
    RUN_WAIT=$((RUN_WAIT + POLL_INTERVAL))

    RUN_STATUS_RESPONSE=$(curl -s "${MYAGENTDESK_URL}/api/runs/${RUN_ID}/status" 2>/dev/null)
    RUN_STATUS=$(echo "$RUN_STATUS_RESPONSE" | jq -r '.status // "unknown"')

    log_info "Run status: ${RUN_STATUS} (${RUN_WAIT}s elapsed)"
done

# ============================================
# Step 7: Verify Results
# ============================================

log_step "Step 7: Verify Results"

# 最終ステータス取得
FINAL_RUN_RESPONSE=$(curl -s "${MYAGENTDESK_URL}/api/runs/${RUN_ID}" 2>/dev/null)
FINAL_STATUS=$(echo "$FINAL_RUN_RESPONSE" | jq -r '.status // "unknown"')

# 結果をJSONファイルに保存
cat > "$RESULT_FILE" <<EOF
{
    "timestamp": "${TIMESTAMP}",
    "test": "full_workflow_e2e",
    "parameters": {
        "keyword": "${KEYWORD}",
        "email": "${EMAIL}",
        "project_id": "${PROJECT_ID}",
        "workbench_id": "${WORKBENCH_ID}",
        "job_version_id": "${JOB_VERSION_ID}",
        "run_id": "${RUN_ID}"
    },
    "result": {
        "status": "${FINAL_STATUS}",
        "duration_seconds": ${RUN_WAIT},
        "success": $([ "$FINAL_STATUS" = "success" ] && echo "true" || echo "false")
    },
    "run_details": $(echo "$FINAL_RUN_RESPONSE" | jq '.')
}
EOF

log_info "Result saved to: ${RESULT_FILE}"

# 結果表示
echo ""
echo -e "${CYAN}════════════════════════════════════════${NC}"
echo -e "${CYAN}           TEST RESULTS                  ${NC}"
echo -e "${CYAN}════════════════════════════════════════${NC}"
echo ""
echo "  Run ID:       ${RUN_ID}"
echo "  Status:       ${FINAL_STATUS}"
echo "  Duration:     ${RUN_WAIT} seconds"
echo ""

if [ "$FINAL_STATUS" = "success" ]; then
    echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║         ✅ TEST PASSED                 ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
    log_success "Full workflow E2E test completed successfully!"
    echo ""
    echo "Please check your email (${EMAIL}) for the result."
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════╗${NC}"
    echo -e "${RED}║         ❌ TEST FAILED                 ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════╝${NC}"
    log_error "Full workflow E2E test failed. Status: ${FINAL_STATUS}"

    # タスク詳細を取得して表示
    log_info "Fetching task details..."
    TASKS_RESPONSE=$(curl -s "${MYAGENTDESK_URL}/api/runs/${RUN_ID}/tasks" 2>/dev/null)
    echo ""
    echo "Task details:"
    echo "$TASKS_RESPONSE" | jq '.[] | {id, status, error}'

    exit 1
fi
