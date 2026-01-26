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
#   ./test_full_workflow_e2e.sh --project-id "proj_xxx" --workbench-id "wb_xxx" --email "test@example.com"
#   ./test_full_workflow_e2e.sh --keyword "検索キーワード" --email "test@example.com" --project-id "proj_xxx" --workbench-id "wb_xxx"
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
# 固定のProject/Workbench ID（myAgentDeskで事前作成済み）
DEFAULT_PROJECT_ID="proj_mjbjua2z7y65wy"
DEFAULT_WORKBENCH_ID="wb_1766969315404_udrhx79"

# タイムアウト設定
HEALTH_CHECK_TIMEOUT=10
GENERATE_TIMEOUT=180
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
    echo "  --project-id <id>         Project ID (default: ${DEFAULT_PROJECT_ID})"
    echo "  --workbench-id <id>       Workbench ID (default: ${DEFAULT_WORKBENCH_ID})"
    echo "  --skip-generate           Job生成をスキップ（既存JobVersionを使用）"
    echo "  --job-version-id <id>     使用するJobVersion ID (--skip-generate時に必須)"
    echo "  --no-confirm              確認プロンプトをスキップ"
    echo "  --help                    このヘルプを表示"
    echo ""
    echo "EXAMPLES:"
    echo "  # 基本的な使用方法"
    echo "  $0 --keyword \"大谷翔平の妻\" --email \"test@example.com\""
    echo ""
    echo "  # Project/Workbench指定"
    echo "  $0 --project-id \"proj_xxx\" --workbench-id \"wb_xxx\" --email \"test@example.com\""
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
    local accept_codes="${4:-200}"

    log_info "Checking ${name}..."

    local response
    response=$(curl -s -o /dev/null -w "%{http_code}" --max-time $HEALTH_CHECK_TIMEOUT "${url}${endpoint}" 2>/dev/null || echo "000")

    # Check if response code is in acceptable codes
    if [[ "$accept_codes" == *"$response"* ]]; then
        log_success "${name}: OK (${url})"
        return 0
    else
        log_error "${name}: FAILED (HTTP ${response})"
        return 1
    fi
}

HEALTH_FAILED=false

# myAgentDeskはルートページの存在確認（200または304）
check_health "myAgentDesk" "$MYAGENTDESK_URL" "/" "200 304" || HEALTH_FAILED=true
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
# Step 2: Project/Workbench確認
# ============================================

log_step "Step 2: Validate Project and Workbench"

# デフォルト値を適用
if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID="$DEFAULT_PROJECT_ID"
    log_info "Using default project: ${PROJECT_ID}"
fi

if [ -z "$WORKBENCH_ID" ]; then
    WORKBENCH_ID="$DEFAULT_WORKBENCH_ID"
    log_info "Using default workbench: ${WORKBENCH_ID}"
fi

# Workbenchページの存在確認
log_info "Validating workbench exists..."
WORKBENCH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" --max-time $HEALTH_CHECK_TIMEOUT \
    "${MYAGENTDESK_URL}/projects/${PROJECT_ID}/workbenches/${WORKBENCH_ID}" 2>/dev/null || echo "000")

if [ "$WORKBENCH_CHECK" != "200" ]; then
    log_error "Workbench not found (HTTP ${WORKBENCH_CHECK})"
    log_error "Please create the workbench in myAgentDesk first:"
    log_error "  ${MYAGENTDESK_URL}/projects/${PROJECT_ID}/workbenches"
    exit 1
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

    log_info "Triggering job generation via SvelteKit Form Action..."

    # SvelteKit Form Actionsを呼び出す（?/generateJobアクション）
    GENERATE_RESPONSE=$(curl -s -X POST \
        "${MYAGENTDESK_URL}/projects/${PROJECT_ID}/workbenches/${WORKBENCH_ID}/generate?/generateJob" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        --max-time $GENERATE_TIMEOUT 2>/dev/null)

    if [ -z "$GENERATE_RESPONSE" ]; then
        log_error "Generate API returned empty response"
        exit 1
    fi

    log_info "Generate response: $(echo "$GENERATE_RESPONSE" | head -c 500)"

    # SvelteKit Form ActionsのレスポンスからjobVersionIdを抽出
    # SvelteKitはdevalシリアライズ形式で返す場合がある
    # 例: {"type":"success","data":"[{\"success\":1,\"jobVersionId\":2,...},true,\"jv_xxx\",...]}
    # 例: {"type":"failure","data":"[{\"error\":1},\"A job is already being generated...\"]"}

    # エラーチェック（既に生成中のJobがある場合）
    GENERATE_TYPE=$(echo "$GENERATE_RESPONSE" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("type",""))' 2>/dev/null || echo "")

    if [ "$GENERATE_TYPE" = "failure" ]; then
        ERROR_MSG=$(echo "$GENERATE_RESPONSE" | python3 -c 'import json,sys,re; d=json.load(sys.stdin); m=re.search(r"already being generated", d.get("data","")); print("generating" if m else "error")' 2>/dev/null || echo "error")

        if [ "$ERROR_MSG" = "generating" ]; then
            log_warn "A job is already being generated. Waiting for existing job..."

            # 生成中のJobを見つける（generateページをロードしてステータス確認）
            for i in {1..36}; do
                GENERATING_JOB=$(curl -s "${MYAGENTDESK_URL}/projects/${PROJECT_ID}/workbenches/${WORKBENCH_ID}/generate" 2>/dev/null | \
                    python3 -c 'import sys,re; c=sys.stdin.read(); m=re.search(r"jv_[a-zA-Z0-9_]+", c); print(m.group(0) if m else "")' 2>/dev/null || echo "")

                if [ -n "$GENERATING_JOB" ]; then
                    JOB_STATUS=$(curl -s "${MYAGENTDESK_URL}/api/jobs/${GENERATING_JOB}/status" 2>/dev/null | \
                        python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("status","unknown"))' 2>/dev/null || echo "unknown")

                    if [ "$JOB_STATUS" = "success" ] || [ "$JOB_STATUS" = "active" ]; then
                        log_success "Found completed job: ${GENERATING_JOB}"
                        JOB_VERSION_ID="$GENERATING_JOB"
                        break
                    elif [ "$JOB_STATUS" = "generating" ]; then
                        PROGRESS=$(curl -s "${MYAGENTDESK_URL}/api/jobs/${GENERATING_JOB}/status" 2>/dev/null | \
                            python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("progress",""))' 2>/dev/null || echo "")
                        log_info "Waiting for existing job ${GENERATING_JOB}... (${PROGRESS}%)"
                    fi
                fi
                sleep 5
            done
        else
            log_error "Job generation failed: $(echo "$GENERATE_RESPONSE" | head -c 500)"
            exit 1
        fi
    else
        JOB_VERSION_ID=$(echo "$GENERATE_RESPONSE" | python3 -c '
import json
import sys
import re

try:
    data = json.load(sys.stdin)

    # SvelteKit deval形式の場合
    if isinstance(data, dict) and "data" in data:
        data_str = data["data"]
        if isinstance(data_str, str):
            # "jv_" で始まるIDを抽出
            match = re.search(r"jv_[a-zA-Z0-9_]+", data_str)
            if match:
                print(match.group(0))
                sys.exit(0)

    # 通常のJSON形式の場合
    if isinstance(data, dict):
        job_version_id = data.get("jobVersionId") or data.get("id", "")
        print(job_version_id)
except Exception as e:
    print("", file=sys.stderr)
' 2>/dev/null || echo "")
    fi

    if [ -z "$JOB_VERSION_ID" ]; then
        log_error "Failed to get JobVersion ID from response"
        log_error "Response: $(echo "$GENERATE_RESPONSE" | head -c 1000)"
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

        # /api/jobs/{jobId}/status でステータス確認
        JOB_STATUS_RESPONSE=$(curl -s "${MYAGENTDESK_URL}/api/jobs/${JOB_VERSION_ID}/status" 2>/dev/null)
        GENERATE_STATUS=$(echo "$JOB_STATUS_RESPONSE" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("status","unknown"))' 2>/dev/null || echo "unknown")
        PHASE=$(echo "$JOB_STATUS_RESPONSE" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("phase",""))' 2>/dev/null || echo "")
        PROGRESS=$(echo "$JOB_STATUS_RESPONSE" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("progress",""))' 2>/dev/null || echo "")

        if [ -n "$PHASE" ] && [ -n "$PROGRESS" ]; then
            log_info "Generation status: ${GENERATE_STATUS} | Phase: ${PHASE} | Progress: ${PROGRESS}% (${GENERATE_WAIT}s elapsed)"
        else
            log_info "Generation status: ${GENERATE_STATUS} (${GENERATE_WAIT}s elapsed)"
        fi
    done

    if [ "$GENERATE_STATUS" != "active" ] && [ "$GENERATE_STATUS" != "success" ] && [ "$GENERATE_STATUS" != "completed" ]; then
        log_error "Job generation failed or timed out. Status: ${GENERATE_STATUS}"
        log_error "Last response: $(echo "$JOB_STATUS_RESPONSE" | head -c 500)"
        exit 1
    fi

    log_success "Job generation completed!"

    # externalJobMasterIdを取得
    EXTERNAL_JOB_MASTER_ID=$(echo "$JOB_STATUS_RESPONSE" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("externalJobMasterId",""))' 2>/dev/null || echo "")
    if [ -n "$EXTERNAL_JOB_MASTER_ID" ]; then
        log_info "External Job Master ID: ${EXTERNAL_JOB_MASTER_ID}"
    fi
else
    log_step "Step 4: Skip Generate (Using existing JobVersion)"

    if [ -z "$JOB_VERSION_ID" ]; then
        log_error "--job-version-id is required when using --skip-generate"
        exit 1
    fi

    log_info "Using existing JobVersion: ${JOB_VERSION_ID}"

    # 既存のJobVersionのステータス確認
    JOB_STATUS_RESPONSE=$(curl -s "${MYAGENTDESK_URL}/api/jobs/${JOB_VERSION_ID}/status" 2>/dev/null)
    GENERATE_STATUS=$(echo "$JOB_STATUS_RESPONSE" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("status","unknown"))' 2>/dev/null || echo "unknown")

    if [ "$GENERATE_STATUS" != "active" ] && [ "$GENERATE_STATUS" != "success" ]; then
        log_error "JobVersion is not active/success. Status: ${GENERATE_STATUS}"
        exit 1
    fi
fi

# ============================================
# Step 5: Create and Execute Run
# ============================================

log_step "Step 5: Create and Execute Run"

log_info "Creating run with parameters..."

# executionParamsをJSON形式で作成
EXECUTION_PARAMS=$(cat <<EOF
{"keyword": "${KEYWORD}", "email": "${EMAIL}"}
EOF
)

# Run作成リクエスト
RUN_REQUEST=$(cat <<EOF
{
    "workbenchId": "${WORKBENCH_ID}",
    "jobVersionId": "${JOB_VERSION_ID}",
    "executionParams": $(echo "$EXECUTION_PARAMS" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().strip()))')
}
EOF
)

log_info "Run request: $(echo "$RUN_REQUEST" | tr -d '\n' | head -c 200)"

RUN_RESPONSE=$(curl -s -X POST "${MYAGENTDESK_URL}/api/runs" \
    -H "Content-Type: application/json" \
    -d "$RUN_REQUEST" \
    --max-time 30 2>/dev/null)

if [ -z "$RUN_RESPONSE" ]; then
    log_error "Run API returned empty response"
    exit 1
fi

log_info "Run response: $(echo "$RUN_RESPONSE" | head -c 500)"

RUN_ID=$(echo "$RUN_RESPONSE" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("id",""))' 2>/dev/null || echo "")

if [ -z "$RUN_ID" ]; then
    log_error "Failed to get Run ID from response"
    log_error "Response: $RUN_RESPONSE"
    exit 1
fi

log_success "Run created: ${RUN_ID}"

# externalJobIdを取得
EXTERNAL_JOB_ID=$(echo "$RUN_RESPONSE" | python3 -c 'import json,sys; d=json.load(sys.stdin); v=d.get("externalJobId"); print(v if v else "")' 2>/dev/null || echo "")
if [ -n "$EXTERNAL_JOB_ID" ]; then
    log_info "External Job ID (JobQueue): ${EXTERNAL_JOB_ID}"
fi

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
    RUN_STATUS=$(echo "$RUN_STATUS_RESPONSE" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("status","unknown"))' 2>/dev/null || echo "unknown")

    # タスクステータスからも判断（Run statusが更新されない場合の対策）
    TASKS_RESPONSE=$(curl -s "${MYAGENTDESK_URL}/api/runs/${RUN_ID}/tasks" 2>/dev/null)
    TASK_STATUS_INFO=$(echo "$TASKS_RESPONSE" | python3 -c '
import json
import sys
try:
    data = json.load(sys.stdin)
    tasks = data.get("tasks", [])
    total = len(tasks)
    succeeded = sum(1 for t in tasks if t.get("status") == "SUCCEEDED")
    failed = sum(1 for t in tasks if t.get("status") == "FAILED")
    running = sum(1 for t in tasks if t.get("status") in ["RUNNING", "PENDING", "QUEUED"])
    print(f"{succeeded}/{total} succeeded, {failed} failed, {running} running")

    # 全タスク完了の場合はステータスを判断
    if total > 0 and running == 0:
        if failed > 0:
            print("COMPUTED_STATUS:failed")
        elif succeeded == total:
            print("COMPUTED_STATUS:success")
except Exception as e:
    print("unknown")
' 2>/dev/null || echo "unknown")

    # タスクベースでステータスを判断
    if echo "$TASK_STATUS_INFO" | grep -q "COMPUTED_STATUS:success"; then
        log_info "Run status: ${RUN_STATUS} | Tasks: ${TASK_STATUS_INFO} (${RUN_WAIT}s elapsed)"
        RUN_STATUS="success"
        break
    elif echo "$TASK_STATUS_INFO" | grep -q "COMPUTED_STATUS:failed"; then
        log_info "Run status: ${RUN_STATUS} | Tasks: ${TASK_STATUS_INFO} (${RUN_WAIT}s elapsed)"
        RUN_STATUS="failed"
        break
    fi

    log_info "Run status: ${RUN_STATUS} | Tasks: ${TASK_STATUS_INFO} (${RUN_WAIT}s elapsed)"
done

# ============================================
# Step 7: Verify Results
# ============================================

log_step "Step 7: Verify Results"

# 最終ステータス取得
# タスクベースで判定したRUN_STATUSを使用（APIのstatusフィールドは更新遅延があるため）
FINAL_RUN_RESPONSE=$(curl -s "${MYAGENTDESK_URL}/api/runs/${RUN_ID}/status" 2>/dev/null)
API_STATUS=$(echo "$FINAL_RUN_RESPONSE" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("status","unknown"))' 2>/dev/null || echo "unknown")
# タスクベースで判定済みのRUN_STATUSを優先使用
FINAL_STATUS="${RUN_STATUS:-$API_STATUS}"

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
        "run_id": "${RUN_ID}",
        "external_job_id": "${EXTERNAL_JOB_ID}"
    },
    "result": {
        "status": "${FINAL_STATUS}",
        "duration_seconds": ${RUN_WAIT},
        "success": $([ "$FINAL_STATUS" = "success" ] && echo "true" || echo "false")
    }
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
    echo "$TASKS_RESPONSE" | python3 -c 'import json,sys; data=json.load(sys.stdin); print(json.dumps(data, indent=2, ensure_ascii=False))' 2>/dev/null || echo "$TASKS_RESPONSE"

    exit 1
fi
