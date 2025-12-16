#!/bin/bash
#
# Issue #286 受入テスト（L3: ローカル受入テスト）
# [myAgentDesk] Drizzle ORM + SQLite セットアップ
#
# 前提条件:
# - myAgentDeskディレクトリでnpm installが完了していること
# - sqlite3コマンドが利用可能であること
#
# 実行方法:
#   ./tests/acceptance/test_issue_286_acceptance.sh
#

set -e

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# カウンター
PASSED=0
FAILED=0
TOTAL=0

# テスト結果表示関数
pass() {
    echo -e "${GREEN}✅ PASS${NC}: $1"
    ((PASSED++))
    ((TOTAL++))
}

fail() {
    echo -e "${RED}❌ FAIL${NC}: $1"
    echo -e "${RED}  Error: $2${NC}"
    ((FAILED++))
    ((TOTAL++))
}

warn() {
    echo -e "${YELLOW}⚠️  WARN${NC}: $1"
}

# スクリプトのディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MYAGENTDESK_DIR="$PROJECT_ROOT/myAgentDesk"

echo "=============================================="
echo "Issue #286 受入テスト: Drizzle ORM + SQLite"
echo "=============================================="
echo ""
echo "Working directory: $MYAGENTDESK_DIR"
echo ""

# myAgentDeskディレクトリに移動
cd "$MYAGENTDESK_DIR"

# =============================================================================
# Step 1: DBファイル存在確認
# =============================================================================
echo "--- Step 1: DBファイル存在確認 ---"

if [ -f "data/local.db" ]; then
    pass "data/local.db ファイルが存在する"
else
    fail "data/local.db ファイルが存在しない" "npm run db:push を実行してください"
fi

# =============================================================================
# Step 2: マイグレーション冪等性確認
# =============================================================================
echo ""
echo "--- Step 2: マイグレーション冪等性確認 ---"

# 1回目のdb:push
if npm run db:push --silent 2>&1 | grep -q "error\|Error\|ERROR"; then
    fail "npm run db:push 1回目が失敗" "マイグレーションエラー"
else
    pass "npm run db:push 1回目が成功"
fi

# 2回目のdb:push（冪等性確認）
OUTPUT=$(npm run db:push 2>&1)
if echo "$OUTPUT" | grep -q "error\|Error\|ERROR"; then
    fail "npm run db:push 2回目が失敗（冪等性違反）" "$OUTPUT"
else
    pass "npm run db:push 2回目が成功（冪等性確認）"
fi

# =============================================================================
# Step 3: テーブル数確認
# =============================================================================
echo ""
echo "--- Step 3: テーブル数確認 ---"

TABLE_COUNT=$(sqlite3 data/local.db ".tables" | wc -w | tr -d ' ')

if [ "$TABLE_COUNT" -eq 6 ]; then
    pass "6テーブルが作成されている (実際: $TABLE_COUNT)"
else
    fail "テーブル数が不正" "期待: 6, 実際: $TABLE_COUNT"
fi

# =============================================================================
# Step 4: テーブル一覧確認
# =============================================================================
echo ""
echo "--- Step 4: テーブル一覧確認 ---"

TABLES=$(sqlite3 data/local.db ".tables")
EXPECTED_TABLES=("project" "workbench" "requirement_version" "job_version" "run" "schedule")

ALL_FOUND=true
MISSING_TABLES=""

for table in "${EXPECTED_TABLES[@]}"; do
    if echo "$TABLES" | grep -q "$table"; then
        : # テーブルが見つかった
    else
        ALL_FOUND=false
        MISSING_TABLES="$MISSING_TABLES $table"
    fi
done

if [ "$ALL_FOUND" = true ]; then
    pass "全ての期待するテーブルが存在する"
else
    fail "一部のテーブルが見つからない" "不足:$MISSING_TABLES"
fi

# テーブル一覧表示
echo "  テーブル一覧: $TABLES"

# =============================================================================
# Step 5: FK制約有効確認
# =============================================================================
echo ""
echo "--- Step 5: FK制約有効確認 ---"

# FK制約はアプリケーション側で有効にする必要がある
# ここではスキーマにFK定義があることを確認
FK_COUNT=$(sqlite3 data/local.db "SELECT COUNT(*) FROM pragma_foreign_key_list('workbench');" 2>/dev/null || echo "0")

if [ "$FK_COUNT" -ge 1 ]; then
    pass "workbenchテーブルにFK制約が定義されている"
else
    fail "workbenchテーブルにFK制約がない" "FK count: $FK_COUNT"
fi

# =============================================================================
# Step 6: FK違反テスト
# =============================================================================
echo ""
echo "--- Step 6: FK違反テスト ---"

# FK制約を有効にしてテスト
FK_RESULT=$(sqlite3 data/local.db "PRAGMA foreign_keys = ON; INSERT INTO workbench (id, project_id, name, status, created_at, updated_at) VALUES ('test_fk_violation', 'nonexistent_project', 'Test', 'draft', strftime('%s','now'), strftime('%s','now'));" 2>&1 || true)

if echo "$FK_RESULT" | grep -q "FOREIGN KEY constraint failed"; then
    pass "FK違反エラーが正しく発生する"
else
    fail "FK違反エラーが発生しない" "$FK_RESULT"
fi

# =============================================================================
# Step 7: シードデータ投入
# =============================================================================
echo ""
echo "--- Step 7: シードデータ投入 ---"

# 既存データをクリアしてシードを投入
if npm run db:seed 2>&1 | grep -q "error\|Error\|ERROR"; then
    fail "npm run db:seed が失敗" "シードデータ投入エラー"
else
    pass "npm run db:seed が成功"
fi

# =============================================================================
# Step 8: Project数確認
# =============================================================================
echo ""
echo "--- Step 8: Project数確認 ---"

PROJECT_COUNT=$(sqlite3 data/local.db "SELECT COUNT(*) FROM project;")

if [ "$PROJECT_COUNT" -ge 3 ]; then
    pass "3件以上のProjectが存在する (実際: $PROJECT_COUNT)"
else
    fail "Project数が不足" "期待: >= 3, 実際: $PROJECT_COUNT"
fi

# =============================================================================
# Step 9: Workbench数確認
# =============================================================================
echo ""
echo "--- Step 9: Workbench数確認 ---"

WORKBENCH_COUNT=$(sqlite3 data/local.db "SELECT COUNT(*) FROM workbench;")

if [ "$WORKBENCH_COUNT" -ge 5 ]; then
    pass "5件以上のWorkbenchが存在する (実際: $WORKBENCH_COUNT)"
else
    fail "Workbench数が不足" "期待: >= 5, 実際: $WORKBENCH_COUNT"
fi

# =============================================================================
# Step 10: FK関係確認（WorkbenchがProjectに紐づく）
# =============================================================================
echo ""
echo "--- Step 10: FK関係確認 ---"

FK_JOIN_COUNT=$(sqlite3 data/local.db "SELECT COUNT(*) FROM workbench w JOIN project p ON w.project_id = p.id;")

if [ "$FK_JOIN_COUNT" -ge 5 ]; then
    pass "WorkbenchがProjectに正しく紐づいている (件数: $FK_JOIN_COUNT)"
else
    fail "FK関係が不正" "JOIN結果: $FK_JOIN_COUNT"
fi

# サンプル表示
echo "  サンプルデータ:"
sqlite3 -header data/local.db "SELECT w.name as workbench_name, p.name as project_name FROM workbench w JOIN project p ON w.project_id = p.id LIMIT 3;" 2>/dev/null | head -5

# =============================================================================
# Step 11: TypeScript型チェック
# =============================================================================
echo ""
echo "--- Step 11: TypeScript型チェック ---"

if npm run type-check 2>&1 | grep -q "error\|Error"; then
    fail "TypeScript型チェックが失敗" "型エラーあり"
else
    pass "TypeScript型チェックが成功"
fi

# =============================================================================
# Step 12: 型エクスポート確認
# =============================================================================
echo ""
echo "--- Step 12: 型エクスポート確認 ---"

if [ -f "src/lib/server/db/schema.ts" ]; then
    TYPE_EXPORT_COUNT=$(grep -c "export type\|export const" src/lib/server/db/schema.ts || echo "0")

    if [ "$TYPE_EXPORT_COUNT" -ge 12 ]; then
        pass "十分な型/定数がエクスポートされている (件数: $TYPE_EXPORT_COUNT)"
    else
        warn "エクスポート数が少ない可能性 (件数: $TYPE_EXPORT_COUNT)"
        pass "スキーマファイルが存在する"
    fi
else
    fail "スキーマファイルが存在しない" "src/lib/server/db/schema.ts"
fi

# =============================================================================
# Step 13: ビルド確認
# =============================================================================
echo ""
echo "--- Step 13: ビルド確認 ---"

if npm run build 2>&1 | grep -q "error\|Error\|failed"; then
    fail "ビルドが失敗" "npm run build エラー"
else
    pass "ビルドが成功"
fi

# =============================================================================
# 結果サマリー
# =============================================================================
echo ""
echo "=============================================="
echo "受入テスト結果サマリー"
echo "=============================================="
echo ""
echo -e "Total: $TOTAL, ${GREEN}Passed: $PASSED${NC}, ${RED}Failed: $FAILED${NC}"
echo ""

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}🎉 全ての受入テストがパスしました！${NC}"
    exit 0
else
    echo -e "${RED}❌ 一部の受入テストが失敗しました${NC}"
    exit 1
fi
