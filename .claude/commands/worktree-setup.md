# Worktree自動セットアップスキル

## 概要
GitHub Issue番号から自動的にgit worktree環境を構築するスキルです。Issue内容からブランチ種別を判定し、並行開発環境を即座に準備します。

## 使用方法
- `/worktree-setup [Issue番号]`
- 「Issue #126のworktreeを作成してください」

## 実行内容

あなたは開発環境セットアップの専門家です。以下の手順でworktree環境を自動構築してください：

### 1. Issue情報の取得と確認

GitHub Issue番号を受け取ったら、まず以下を実行：

```bash
gh issue view <Issue番号> --json labels,title,body
```

取得した情報をユーザーに確認表示：
- Issue番号
- タイトル
- ラベル一覧

### 2. ブランチ種別の判定

以下の優先順位で判定：

#### 優先度1: ラベルから判定
```
type: feature   → feature
type: fix       → fix
type: refactor  → refactor
type: test      → test
type: vibe      → vibe
type: hotfix    → hotfix
```

#### 優先度2: タイトル/本文のキーワード解析
ラベルがない場合、以下のキーワードで判定（大文字小文字区別なし）：

| ブランチ種別 | キーワード（優先度順） |
|-------------|---------------------|
| hotfix | hotfix, 緊急, critical, urgent |
| fix | bug, fix, 修正, バグ, 直す, エラー |
| test | test, テスト, testing |
| refactor | refactor, リファクタ, 整理, 改善 |
| vibe | vibe, 雰囲気, ui改善, デザイン調整 |
| feature | add, new, feature, implement, 追加, 新機能, 実装 |

#### 優先度3: ユーザーへの確認
判定できない場合はAskUserQuestionツールで選択肢を提示：
```
1) feature  - 新機能追加
2) fix      - バグ修正
3) refactor - リファクタリング
4) test     - テスト追加
5) vibe     - UI/UX改善
6) hotfix   - 緊急修正
```

### 3. worktree作成スクリプトの実行

判定したブランチ種別で以下を実行：

```bash
cd ~/MySwiftAgent
./scripts/worktree-create-from-issue.sh <Issue番号> <ブランチ種別>
```

**重要**: スクリプトは以下を自動実行します：
- `git worktree add ../MySwiftAgent-worktrees/{ブランチ種別}-issue-{Issue番号} -b {ブランチ種別}/issue/{Issue番号}`
- `setup-worktree.sh` （デフォルト設定: myVault/langfuse 共有モード）
- ポート番号の自動割り当て

### 4. 実行結果の確認と報告

スクリプト実行後、以下を確認してユーザーに報告：

✅ **成功時の報告内容**:
```
🎉 Worktree作成完了

📍 Worktree location: ~/MySwiftAgent-worktrees/{ブランチ種別}-issue-{Issue番号}
🌿 Branch: {ブランチ種別}/issue/{Issue番号}
📋 Issue: #{Issue番号} - {タイトル}

📝 次のステップ:
1. cd ~/MySwiftAgent-worktrees/{ブランチ種別}-issue-{Issue番号}
2. expertAgent: cd expertAgent && uv sync
3. myAgentDesk: cd myAgentDesk && npm install
4. 開発サーバー起動

🔗 ポート情報:
- expertAgent: http://localhost:{割り当てポート}
- myAgentDesk: http://localhost:{割り当てポート}
```

❌ **エラー時のハンドリング**:

| エラー種別 | 対処方法 |
|-----------|---------|
| Issue番号が存在しない | `gh issue view` エラーメッセージを表示し、Issue番号の確認を促す |
| 既存worktree/ブランチ | 既存worktreeの削除手順を提示：<br>`git worktree remove ...`<br>`git worktree prune` |
| gh CLI未インストール | GitHub CLIのインストール手順を案内 |

### 5. セッション切替の案内

worktree作成後、ユーザーに以下を案内：

```
📌 このIssueの開発を開始するには：

1. 新しいターミナル/セッションで以下を実行：
   cd ~/MySwiftAgent-worktrees/{ブランチ種別}-issue-{Issue番号}

2. または、Claude Codeの新しいセッションでworktreeディレクトリを開く

⚠️ 注意: メインセッション（developブランチ）と並行して作業できます
```

## エラーハンドリング詳細

### Issue情報取得エラー
```bash
# gh issue view が失敗した場合
if ! gh issue view <Issue番号> ... ; then
  echo "❌ Issue #{Issue番号} が見つかりません"
  echo "- Issue番号を確認してください"
  echo "- gh auth login で認証してください"
  exit 1
fi
```

### 既存worktree検出時
```bash
# 既存チェックで検出された場合
echo "⚠️ 既にworktreeが存在します"
echo ""
echo "削除手順:"
echo "  git worktree remove ~/MySwiftAgent-worktrees/..."
echo "  git worktree prune"
echo ""
echo "確認コマンド:"
echo "  git worktree list"
```

### ブランチ種別判定失敗時
AskUserQuestionツールで対話的に選択：
```
header: "Branch Type"
question: "ブランチ種別を選択してください（Issue内容から自動判定できませんでした）"
options:
  - label: "feature", description: "新機能追加"
  - label: "fix", description: "バグ修正"
  - label: "refactor", description: "リファクタリング"
  - label: "test", description: "テスト追加"
  - label: "vibe", description: "UI/UX改善"
  - label: "hotfix", description: "緊急修正"
multiSelect: false
```

## 出力フォーマット

実行完了後、以下の形式でサマリーを表示：

```markdown
## 🎉 Worktree作成完了

### 📋 Issue情報
- **Issue番号**: #126
- **タイトル**: ユーザープロフィール編集機能の追加
- **ブランチ種別**: feature（自動判定）

### 📍 Worktree情報
- **場所**: ~/MySwiftAgent-worktrees/feature-issue-126
- **ブランチ**: feature/issue/126
- **ベース**: develop

### 🔌 ポート割り当て
- expertAgent: http://localhost:8114
- myVault: http://localhost:8113（共有モード）
- myAgentDesk: http://localhost:5174

### 📝 次のステップ
1. 新しいセッションでworktreeディレクトリに移動
2. 依存関係のインストール（uv sync, npm install）
3. 開発開始

### 🔗 関連コマンド
- Issueを見る: `gh issue view 126`
- Worktree一覧: `git worktree list`
```

## 使用ツール

- **Bash**: `gh issue view`, `./scripts/worktree-create-from-issue.sh`
- **AskUserQuestion**: ブランチ種別が判定できない場合のみ

## モデル設定
- model: sonnet（環境構築タスクのため）
- temperature: 0.3（正確性重視）

## 関連ドキュメント
- [05-worktree-guide.md](../../docs/claude/05-worktree-guide.md)
- [01-development-workflow.md](../../docs/claude/01-development-workflow.md)（フェーズ7）

## 注意事項

1. **メインリポジトリで実行**: worktree作成は常に`~/MySwiftAgent`から実行
2. **developブランチがベース**: 全てのworktreeはdevelopブランチから作成
3. **デフォルト設定**: myVault/langfuseは共有モード（リソース効率重視）
4. **ポート衝突回避**: ポート番号は自動的に空きを検出して割り当て
5. **セッション分離推奨**: worktreeでの作業は別セッション/ターミナルで実施

## トラブルシューティング

### gh CLI が見つからない場合
```bash
# macOS
brew install gh

# 認証
gh auth login
```

### worktree削除後も残っている場合
```bash
git worktree prune
git worktree list  # 確認
```

### ポート番号が重複する場合
`.env.local` の `WORKTREE_INDEX` を手動調整（非推奨、通常は自動検出）
