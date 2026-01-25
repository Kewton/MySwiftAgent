#!/bin/bash
# E2E Test Runner: 全capabilityテストを実行
#
# Usage:
#   ./run_all_tests.sh              # 基本テストのみ（メール送信なし）
#   ./run_all_tests.sh --with-email <address>  # メール送信テストを含む
#   ./run_all_tests.sh --skip-google           # google_searchをスキップ

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PASSED=0
FAILED=0
SKIPPED=0

# オプション解析
WITH_EMAIL=""
SKIP_GOOGLE=false
EMAIL_ADDRESS=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --with-email)
      WITH_EMAIL=true
      EMAIL_ADDRESS="$2"
      shift 2
      ;;
    --skip-google)
      SKIP_GOOGLE=true
      shift
      ;;
    *)
      shift
      ;;
  esac
done

echo "========================================"
echo "  TaskFlowEngine E2E Test Runner"
echo "========================================"
echo ""
echo "Options:"
echo "  Email Test: ${WITH_EMAIL:-disabled}"
echo "  Skip Google: ${SKIP_GOOGLE}"
echo ""

run_test() {
  local name="$1"
  local script="$2"
  shift 2

  echo "----------------------------------------"
  echo "Running: ${name}"
  echo "----------------------------------------"

  if bash "${SCRIPT_DIR}/${script}" "$@"; then
    PASSED=$((PASSED + 1))
  else
    FAILED=$((FAILED + 1))
  fi
  echo ""
}

skip_test() {
  local name="$1"
  echo "----------------------------------------"
  echo "Skipping: ${name}"
  echo "----------------------------------------"
  SKIPPED=$((SKIPPED + 1))
  echo ""
}

# テスト実行
echo ""
echo "========== Starting Tests =========="
echo ""

# 1. direct_llm テスト
run_test "direct_llm" "test_direct_llm.sh"

# 2. json_output_agent テスト
run_test "json_output_agent" "test_json_output_agent.sh"

# 3. google_search テスト（オプション）
if [ "$SKIP_GOOGLE" = true ]; then
  skip_test "google_search (skipped by --skip-google)"
else
  echo "[NOTE] google_search テストは1-3分かかります"
  run_test "google_search" "test_google_search.sh"
fi

# 4. gmail_send テスト（オプション）
if [ -n "$WITH_EMAIL" ] && [ -n "$EMAIL_ADDRESS" ]; then
  echo "[NOTE] gmail_send テストはメールを実際に送信します"
  # 自動実行用に確認をスキップ
  echo "y" | bash "${SCRIPT_DIR}/test_gmail_send.sh" "$EMAIL_ADDRESS" "E2E Test $(date +%Y%m%d_%H%M%S)" "This is an automated E2E test email."
  if [ $? -eq 0 ]; then
    PASSED=$((PASSED + 1))
  else
    FAILED=$((FAILED + 1))
  fi
else
  skip_test "gmail_send (use --with-email <address> to enable)"
fi

# 結果サマリー
echo ""
echo "========================================"
echo "  Test Results Summary"
echo "========================================"
echo "  Passed:  ${PASSED}"
echo "  Failed:  ${FAILED}"
echo "  Skipped: ${SKIPPED}"
echo "========================================"
echo ""

if [ $FAILED -gt 0 ]; then
  echo "❌ Some tests failed"
  exit 1
else
  echo "✅ All tests passed"
  exit 0
fi
