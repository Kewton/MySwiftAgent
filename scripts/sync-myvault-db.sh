#!/bin/bash
# scripts/sync-myvault-db.sh
# メインworktreeのmyVault DBを全worktreeに同期するスクリプト
#
# Usage:
#   ~/MySwiftAgent/scripts/sync-myvault-db.sh

set -e

MAIN_REPO=$(git rev-parse --show-toplevel 2>/dev/null || echo "$HOME/MySwiftAgent")
MAIN_DB="$MAIN_REPO/myVault/data/myvault.db"

echo "🔄 Syncing myVault DB from main worktree..."
echo "   Source: $MAIN_DB"

# メインDBの存在確認
if [ ! -f "$MAIN_DB" ]; then
    echo "❌ Error: Main myVault DB not found"
    echo "   Expected: $MAIN_DB"
    echo "   Please run myVault setup in main worktree first."
    exit 1
fi

# MySwiftAgent-worktrees ディレクトリのパスを取得
WORKTREES_DIR="$(dirname "$MAIN_REPO")/MySwiftAgent-worktrees"

if [ ! -d "$WORKTREES_DIR" ]; then
    echo "ℹ️  No worktrees directory found: $WORKTREES_DIR"
    echo "   Nothing to sync."
    exit 0
fi

# 全worktreeに同期
SYNC_COUNT=0
for worktree in "$WORKTREES_DIR"/*/; do
    if [ -d "$worktree" ]; then
        WORKTREE_NAME=$(basename "$worktree")
        TARGET_DB="${worktree}myVault/data/myvault.db"
        TARGET_DIR="${worktree}myVault/data"

        # myVault/data ディレクトリが存在するか確認
        if [ -d "$TARGET_DIR" ]; then
            # DBをコピー
            cp -v "$MAIN_DB" "$TARGET_DB"
            echo "✅ Synced DB to $WORKTREE_NAME"
            SYNC_COUNT=$((SYNC_COUNT + 1))
        else
            echo "⚠️  Skipped $WORKTREE_NAME (myVault/data directory not found)"
        fi
    fi
done

echo ""
if [ $SYNC_COUNT -eq 0 ]; then
    echo "ℹ️  No worktrees with myVault found. Nothing synced."
else
    echo "🎉 Successfully synced myVault DB to $SYNC_COUNT worktree(s)!"
    echo ""
    echo "📝 Note:"
    echo "   - All worktrees now have the same myVault secrets"
    echo "   - Restart myVault services if they are running"
fi
