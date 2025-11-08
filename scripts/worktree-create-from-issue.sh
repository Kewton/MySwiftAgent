#!/bin/bash
# scripts/worktree-create-from-issue.sh
# GitHub IssueからWorktreeを自動作成するスクリプト
#
# Usage:
#   cd ~/MySwiftAgent
#   ./scripts/worktree-create-from-issue.sh <issue_number> [branch_type]
#
# Args:
#   issue_number: GitHub Issue番号（必須）
#   branch_type: ブランチ種別（任意） feature|fix|refactor|test|vibe|hotfix
#               指定がない場合はIssueラベル/内容から自動判定
#
# Features:
#   - GitHub Issue情報取得（gh CLI使用）
#   - ブランチ種別自動判定（ラベル優先、フォールバックでキーワード解析）
#   - worktree作成（../MySwiftAgent-worktrees/{branch_type}-issue-{number}）
#   - setup-worktree.sh 自動実行（デフォルト設定）
#
# Example:
#   ./scripts/worktree-create-from-issue.sh 126
#   ./scripts/worktree-create-from-issue.sh 127 feature

set -e

# ==================== 設定 ====================
MAIN_REPO=$(git rev-parse --show-toplevel 2>/dev/null || echo "$HOME/MySwiftAgent")
WORKTREES_BASE_DIR="$(dirname "$MAIN_REPO")/MySwiftAgent-worktrees"
SETUP_SCRIPT="$MAIN_REPO/scripts/setup-worktree.sh"

# ==================== 引数チェック ====================
if [ $# -lt 1 ]; then
    echo "❌ Error: Issue number is required"
    echo ""
    echo "Usage: $0 <issue_number> [branch_type]"
    echo ""
    echo "Arguments:"
    echo "  issue_number: GitHub Issue番号（必須）"
    echo "  branch_type:  ブランチ種別（任意） feature|fix|refactor|test|vibe|hotfix"
    echo ""
    echo "Example:"
    echo "  $0 126              # Issue #126から自動判定"
    echo "  $0 127 feature      # Issue #127をfeatureブランチとして作成"
    exit 1
fi

ISSUE_NUMBER=$1
BRANCH_TYPE_OVERRIDE=${2:-}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Worktree Creation from GitHub Issue #$ISSUE_NUMBER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ==================== GitHub CLI チェック ====================
if ! command -v gh &> /dev/null; then
    echo "❌ Error: gh CLI not found"
    echo "   Please install GitHub CLI: https://cli.github.com/"
    exit 1
fi

# ==================== Issue情報取得 ====================
echo "🔍 Fetching Issue #$ISSUE_NUMBER from GitHub..."

# gh issue view で情報取得（エラーハンドリング）
if ! ISSUE_JSON=$(gh issue view "$ISSUE_NUMBER" --json labels,title,body 2>&1); then
    echo "❌ Error: Failed to fetch Issue #$ISSUE_NUMBER"
    echo ""
    echo "Details:"
    echo "$ISSUE_JSON"
    echo ""
    echo "Possible reasons:"
    echo "  - Issue does not exist"
    echo "  - Not authenticated with gh (run: gh auth login)"
    echo "  - No internet connection"
    exit 1
fi

# JSONパース
ISSUE_TITLE=$(echo "$ISSUE_JSON" | jq -r '.title')
ISSUE_BODY=$(echo "$ISSUE_JSON" | jq -r '.body // ""')
ISSUE_LABELS=$(echo "$ISSUE_JSON" | jq -r '.labels[].name' 2>/dev/null || echo "")

echo "✅ Issue found:"
echo "   Title: $ISSUE_TITLE"
echo "   Labels: $(echo "$ISSUE_LABELS" | tr '\n' ',' | sed 's/,$//')"
echo ""

# ==================== ブランチ種別判定 ====================
if [ -n "$BRANCH_TYPE_OVERRIDE" ]; then
    # 引数でブランチ種別が指定されている場合
    BRANCH_TYPE="$BRANCH_TYPE_OVERRIDE"
    echo "✅ Branch type specified: $BRANCH_TYPE"
else
    echo "🔍 Auto-detecting branch type..."

    # 1. ラベルから判定（優先）
    BRANCH_TYPE=""

    # ラベルマッピング（"type: feature" または "feature" の両方に対応）
    if echo "$ISSUE_LABELS" | grep -qE "^(type: )?feature$"; then
        BRANCH_TYPE="feature"
    elif echo "$ISSUE_LABELS" | grep -qE "^(type: )?(fix|bug)$"; then
        BRANCH_TYPE="fix"
    elif echo "$ISSUE_LABELS" | grep -qE "^(type: )?refactor$"; then
        BRANCH_TYPE="refactor"
    elif echo "$ISSUE_LABELS" | grep -qE "^(type: )?test$"; then
        BRANCH_TYPE="test"
    elif echo "$ISSUE_LABELS" | grep -qE "^(type: )?vibe$"; then
        BRANCH_TYPE="vibe"
    elif echo "$ISSUE_LABELS" | grep -qE "^(type: )?hotfix$"; then
        BRANCH_TYPE="hotfix"
    fi

    # 2. ラベルで判定できなかった場合、タイトル/本文のキーワードから判定
    if [ -z "$BRANCH_TYPE" ]; then
        echo "   No type label found. Analyzing title and body..."

        # タイトル + 本文を結合して小文字変換
        CONTENT_LOWER=$(echo "$ISSUE_TITLE $ISSUE_BODY" | tr '[:upper:]' '[:lower:]')

        # キーワードマッチング（優先度順）
        if echo "$CONTENT_LOWER" | grep -qE "(hotfix|緊急|critical|urgent)"; then
            BRANCH_TYPE="hotfix"
        elif echo "$CONTENT_LOWER" | grep -qE "(bug|fix|修正|バグ|直す|エラー)"; then
            BRANCH_TYPE="fix"
        elif echo "$CONTENT_LOWER" | grep -qE "(test|テスト|testing)"; then
            BRANCH_TYPE="test"
        elif echo "$CONTENT_LOWER" | grep -qE "(refactor|リファクタ|整理|改善)"; then
            BRANCH_TYPE="refactor"
        elif echo "$CONTENT_LOWER" | grep -qE "(vibe|雰囲気|ui改善|デザイン調整)"; then
            BRANCH_TYPE="vibe"
        elif echo "$CONTENT_LOWER" | grep -qE "(add|new|feature|implement|追加|新機能|実装)"; then
            BRANCH_TYPE="feature"
        fi
    fi

    # 3. 判定できなかった場合はエラー（ユーザーに選択させる）
    if [ -z "$BRANCH_TYPE" ]; then
        echo ""
        echo "⚠️  Could not determine branch type from labels or content."
        echo ""
        echo "Please select branch type manually:"
        echo "  1) feature  - 新機能追加"
        echo "  2) fix      - バグ修正"
        echo "  3) refactor - リファクタリング"
        echo "  4) test     - テスト追加"
        echo "  5) vibe     - UI/UX改善"
        echo "  6) hotfix   - 緊急修正"
        echo ""
        read -p "Enter choice [1-6]: " choice

        case $choice in
            1) BRANCH_TYPE="feature" ;;
            2) BRANCH_TYPE="fix" ;;
            3) BRANCH_TYPE="refactor" ;;
            4) BRANCH_TYPE="test" ;;
            5) BRANCH_TYPE="vibe" ;;
            6) BRANCH_TYPE="hotfix" ;;
            *)
                echo "❌ Invalid choice. Aborting."
                exit 1
                ;;
        esac
    fi

    echo "✅ Auto-detected branch type: $BRANCH_TYPE"
fi

echo ""

# ==================== 既存worktree/ブランチチェック ====================
BRANCH_NAME="$BRANCH_TYPE/issue/$ISSUE_NUMBER"
WORKTREE_DIR="$WORKTREES_BASE_DIR/$BRANCH_TYPE-issue-$ISSUE_NUMBER"

echo "📝 Target configuration:"
echo "   Branch name: $BRANCH_NAME"
echo "   Worktree dir: $WORKTREE_DIR"
echo ""

# ブランチ存在チェック
if git show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
    echo "⚠️  Branch '$BRANCH_NAME' already exists!"
    echo ""
    echo "To delete and recreate:"
    echo "  git branch -D $BRANCH_NAME"
    echo "  git worktree remove $WORKTREE_DIR"
    echo "  git worktree prune"
    echo ""
    exit 1
fi

# worktree存在チェック
if [ -d "$WORKTREE_DIR" ]; then
    echo "⚠️  Worktree directory already exists: $WORKTREE_DIR"
    echo ""
    echo "To remove:"
    echo "  git worktree remove $WORKTREE_DIR"
    echo "  git worktree prune"
    echo ""
    exit 1
fi

# worktree登録チェック（git worktree list）
if git worktree list | grep -q "$WORKTREE_DIR"; then
    echo "⚠️  Worktree is registered in git but directory may be missing."
    echo ""
    echo "To cleanup:"
    echo "  git worktree prune"
    echo "  rm -rf $WORKTREE_DIR"
    echo ""
    exit 1
fi

# ==================== worktree作成 ====================
echo "🏗️  Creating worktree..."
echo "   Running: git worktree add $WORKTREE_DIR -b $BRANCH_NAME"
echo ""

# develop ブランチから作成
git worktree add "$WORKTREE_DIR" -b "$BRANCH_NAME"

echo "✅ Worktree created successfully"
echo ""

# ==================== setup-worktree.sh 自動実行 ====================
if [ -f "$SETUP_SCRIPT" ]; then
    echo "🔧 Running setup-worktree.sh (auto-mode)..."
    echo ""

    # setup-worktree.shをworktree内で実行（デフォルト設定で自動実行）
    cd "$WORKTREE_DIR"

    # デフォルト設定（共有モード）で自動実行
    # myVault: 1（共有）、langfuse: 1（共有）
    echo -e "1\n1" | "$SETUP_SCRIPT"

    echo ""
    echo "✅ Setup completed"
else
    echo "⚠️  setup-worktree.sh not found. Skipping setup."
    echo "   Run manually: cd $WORKTREE_DIR && $SETUP_SCRIPT"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Worktree creation complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 Worktree location: $WORKTREE_DIR"
echo "🌿 Branch: $BRANCH_NAME"
echo "📋 Issue: #$ISSUE_NUMBER - $ISSUE_TITLE"
echo ""
echo "📝 Next steps:"
echo "   1. Move to worktree:"
echo "      cd $WORKTREE_DIR"
echo ""
echo "   2. Install dependencies:"
echo "      cd expertAgent && uv sync"
echo "      cd myAgentDesk && npm install"
echo ""
echo "   3. Start development"
echo ""
echo "🔗 Quick links:"
echo "   - View Issue: gh issue view $ISSUE_NUMBER"
echo "   - Worktree list: git worktree list"
echo ""
