# 並列開発ワークフロー（git worktree）

**最終更新**: 2025-11-02
**対象読者**: MySwiftAgent 開発者
**前提知識**: Git基本操作、CLAUDE.md の理解

---

## 📚 目次

1. [概要](#概要)
2. [基本フロー（シングルIssue）](#基本フローシングルissue)
3. [並列開発フロー（複数Issue同時進行）](#並列開発フロー複数issue同時進行)
4. [実際のユースケース](#実際のユースケース)
5. [トラブルシューティング](#トラブルシューティング)
6. [ベストプラクティス](#ベストプラクティス)

---

## 概要

git worktree を使用することで、複数のブランチを同時に開発できます。

### メリット

- ✅ ブランチ切り替え不要（`git stash` / `git stash pop` 不要）
- ✅ 複数のIssueを同時並行で開発可能
- ✅ レビュー待ちの間に別作業が可能
- ✅ 実験的な機能を試しながら本作業が可能

### 前提条件

- CLAUDE.md の「🔄 並列開発環境（git worktree）」セクションを読んでいること
- `scripts/setup-worktree.sh` が実行可能であること
- メインworktree（`~/MySwiftAgent`）が `develop` ブランチであること

---

## 基本フロー（シングルIssue）

### Step 1: GitHub Issue作成

```bash
# ブラウザまたはCLI
gh issue create --title "Add user authentication API" --label feature

# 出力例: Created issue #126
```

**ポイント**:
- Issue番号（例: #126）をメモ
- ブランチ名は `feature/issue/126` とする規約

---

### Step 2: developブランチを最新化

```bash
# メインworktreeに移動
cd ~/MySwiftAgent

# developブランチを最新化
git checkout develop
git pull origin develop
```

**ポイント**: 常に最新のdevelopから分岐する

---

### Step 3: worktree作成

```bash
# worktreeを作成（ブランチも同時に作成）
git worktree add ../MySwiftAgent-worktrees/feature-issue-126 -b feature/issue/126

# 作成されたworktreeに移動
cd ../MySwiftAgent-worktrees/feature-issue-126
```

**ポイント**:
- ディレクトリ名はブランチ名と同じにすると管理しやすい
- `-b` オプションで新規ブランチを同時作成

---

### Step 4: 自動セットアップ実行

```bash
# セットアップスクリプトを実行
~/MySwiftAgent/scripts/setup-worktree.sh

# 出力例:
# ✅ Assigned index: 1
# ✅ Created .env.local with port assignments:
#    - expertAgent: 8114
#    - myVault: 8113
#    ...
```

**自動実行される処理**:
- ✅ 空きポート検出・割り当て
- ✅ `.env.local` 生成
- ✅ `.env` へのシンボリックリンク作成
- ✅ myVault DB のコピー

---

### Step 5: 開発作業

```bash
# 依存関係をインストール
cd expertAgent
uv sync

# 開発サーバー起動
uv run uvicorn app.main:app --reload
# → http://localhost:8114 で起動（ポート番号は自動割り当て）

# 別ターミナルで開発
# コード編集、テスト実行など
```

**ポイント**:
- ポート番号は `.env.local` から自動読み込み
- 他のworktreeと衝突しない

---

### Step 6: テスト・品質チェック

```bash
# 単体テスト
uv run pytest tests/unit/ -v

# カバレッジチェック
uv run pytest --cov=app --cov=core --cov-report=term-missing

# 静的解析
uv run ruff check .
uv run mypy .

# 全品質チェック
cd ~/MySwiftAgent-worktrees/feature-issue-126
~/MySwiftAgent/scripts/pre-push-check.sh
```

---

### Step 7: コミット・プッシュ

```bash
git add .
git commit -m "feat(auth): add user authentication API

Implement JWT-based authentication with the following features:
- Login endpoint (/api/v1/auth/login)
- Token validation middleware
- User session management

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push -u origin feature/issue/126
```

---

### Step 8: PR作成

```bash
# GitHub CLI でPR作成
gh pr create --base develop --label feature --title "feat(auth): add user authentication API"

# または、ブラウザでGitHub UIから作成
```

**自動実行されるCI/CD**:
- ✅ Ruff linting
- ✅ MyPy type checking
- ✅ Unit tests
- ✅ Integration tests
- ✅ Coverage check

---

### Step 9: レビュー・マージ

```bash
# レビュー待ち・修正対応
# マージ承認後、GitHub UIまたはCLIでマージ

gh pr merge --squash
```

---

### Step 10: worktree削除

```bash
# 開発サーバーを停止
pkill -f "uvicorn.*8114"

# worktreeを削除
cd ~/MySwiftAgent
git worktree remove ../MySwiftAgent-worktrees/feature-issue-126

# 不要なエントリをクリーンアップ
git worktree prune
```

**ポイント**:
- 必ず実行中のプロセスを停止してから削除
- 削除しても他のworktreeのポート番号は影響を受けない

---

### Step 11: developブランチを更新

```bash
# メインworktreeに戻る
cd ~/MySwiftAgent

# developブランチを更新
git checkout develop
git pull origin develop
```

---

## 並列開発フロー（複数Issue同時進行）

### シナリオ: Issue #126 と #127 を同時に開発

```bash
# ===== Issue #126 の開始 =====
cd ~/MySwiftAgent
git worktree add ../MySwiftAgent-worktrees/feature-issue-126 -b feature/issue/126
cd ../MySwiftAgent-worktrees/feature-issue-126
~/MySwiftAgent/scripts/setup-worktree.sh
# → ポート: expertAgent=8114, myVault=8113

# ===== Issue #127 の開始（並行して作業） =====
cd ~/MySwiftAgent
git worktree add ../MySwiftAgent-worktrees/feature-issue-127 -b feature/issue/127
cd ../MySwiftAgent-worktrees/feature-issue-127
~/MySwiftAgent/scripts/setup-worktree.sh
# → ポート: expertAgent=8124, myVault=8123

# ===== 並列開発 =====
# ターミナル1: Issue #126 の開発
cd ~/MySwiftAgent-worktrees/feature-issue-126/expertAgent
uv run uvicorn app.main:app --reload  # → http://localhost:8114

# ターミナル2: Issue #127 の開発
cd ~/MySwiftAgent-worktrees/feature-issue-127/expertAgent
uv run uvicorn app.main:app --reload  # → http://localhost:8124

# ===== Issue #126 が先に完了 =====
cd ~/MySwiftAgent-worktrees/feature-issue-126
git add . && git commit -m "feat: ..."
git push -u origin feature/issue/126
gh pr create --base develop --label feature

# Issue #126 のworktreeを削除
pkill -f "uvicorn.*8114"
cd ~/MySwiftAgent
git worktree remove ../MySwiftAgent-worktrees/feature-issue-126

# ===== Issue #127 は継続作業 =====
# → Issue #126 削除後も、Issue #127 のポート番号（8124）は不変
cd ~/MySwiftAgent-worktrees/feature-issue-127/expertAgent
# 引き続き http://localhost:8124 で開発可能

# ===== 新しいIssue #128 を開始 =====
cd ~/MySwiftAgent
git worktree add ../MySwiftAgent-worktrees/feature-issue-128 -b feature/issue/128
cd ../MySwiftAgent-worktrees/feature-issue-128
~/MySwiftAgent/scripts/setup-worktree.sh
# → 空きポート検出: index=1 を再利用 → ポート=8114
```

**ポイント**:
- worktreeを削除しても、既存worktreeのポート番号は変わらない
- 削除されたインデックスは次回の新規作成時に再利用される
- 最大3-4個のworktreeを推奨（ディスク容量とパフォーマンスのバランス）

---

## 実際のユースケース

### ケース1: バグ修正中に新機能の依頼が来た

```bash
# 現在: Issue #126 (バグ修正) を作業中
cd ~/MySwiftAgent-worktrees/feature-issue-126

# 緊急の新機能 Issue #130 が発生
# → ブランチ切り替え不要、新しいworktreeを作成

cd ~/MySwiftAgent
git worktree add ../MySwiftAgent-worktrees/feature-issue-130 -b feature/issue/130
cd ../MySwiftAgent-worktrees/feature-issue-130
~/MySwiftAgent/scripts/setup-worktree.sh

# Issue #130 を優先対応
cd expertAgent
uv sync
uv run uvicorn app.main:app --reload  # → 別ポート（8124）で起動

# Issue #130 完了後、Issue #126 に戻る
cd ~/MySwiftAgent-worktrees/feature-issue-126/expertAgent
# → そのまま作業継続（stash/unstash 不要）
```

---

### ケース2: レビュー待ちの間に別作業

```bash
# Issue #126 のPRを作成してレビュー待ち
cd ~/MySwiftAgent-worktrees/feature-issue-126
git push -u origin feature/issue/126
gh pr create --base develop --label feature

# レビュー待ちの間、Issue #127 を開始
cd ~/MySwiftAgent
git worktree add ../MySwiftAgent-worktrees/feature-issue-127 -b feature/issue/127
cd ../MySwiftAgent-worktrees/feature-issue-127
~/MySwiftAgent/scripts/setup-worktree.sh

# Issue #127 の開発中に、Issue #126 のレビューコメントが来た
# → 即座に Issue #126 のworktreeに切り替え

cd ~/MySwiftAgent-worktrees/feature-issue-126
# 修正対応
git add . && git commit -m "fix: address review comments"
git push

# Issue #127 に戻る
cd ~/MySwiftAgent-worktrees/feature-issue-127
# → そのまま作業継続
```

---

### ケース3: 実験的な機能を試しながら本作業

```bash
# メイン作業: Issue #126
cd ~/MySwiftAgent-worktrees/feature-issue-126

# 実験用worktree作成
cd ~/MySwiftAgent
git worktree add ../MySwiftAgent-worktrees/experiment-new-arch -b experiment/new-arch
cd ../MySwiftAgent-worktrees/experiment-new-arch
~/MySwiftAgent/scripts/setup-worktree.sh

# 実験してみる
cd expertAgent
uv run uvicorn app.main:app --reload  # → 別ポート（8124）

# 実験成功 → Issue #126 に反映
cd ~/MySwiftAgent-worktrees/feature-issue-126
# コードをコピー・適用

# 実験worktreeを削除
cd ~/MySwiftAgent
git worktree remove ../MySwiftAgent-worktrees/experiment-new-arch
git branch -D experiment/new-arch
```

---

## トラブルシューティング

### Q1: ポート番号が衝突する

```bash
# 原因: setup-worktree.sh を実行していない
# 解決策:
cd ~/MySwiftAgent-worktrees/feature-issue-XXX
~/MySwiftAgent/scripts/setup-worktree.sh
```

### Q2: myVault DBが古い

```bash
# メインworktreeのDBを全worktreeに同期
~/MySwiftAgent/scripts/sync-myvault-db.sh
```

### Q3: worktree削除できない

```bash
# 原因: プロセスが実行中
# 解決策: プロセスを停止
pkill -f "uvicorn.*8114"
pkill -f "vite.*5174"

# 再度削除
git worktree remove ../MySwiftAgent-worktrees/feature-issue-126
```

### Q4: .env.local が見つからない

```bash
# 原因: セットアップスクリプトを実行していない
# 解決策:
~/MySwiftAgent/scripts/setup-worktree.sh
```

### Q5: 依存関係がインストールされていない

```bash
# 各worktreeで個別にインストールが必要
cd expertAgent
uv sync

cd ../myAgentDesk
npm install
```

---

## ベストプラクティス

### 1. メインworktreeは保護

- ✅ developブランチ専用、作業しない
- ✅ `git pull` のみ実行
- ✅ PRマージ後に更新

### 2. worktree名 = ブランチ名

- ✅ 管理しやすい
- ✅ 一目でどのIssueか分かる

### 3. 作業完了後は即削除

- ✅ ディスク容量を節約
- ✅ インデックスを再利用可能

### 4. 最大3-4個まで

- ✅ パフォーマンスとディスク容量のバランス
- ✅ 管理しやすい数

### 5. 定期的に git worktree prune

- ✅ 不要なエントリを削除
- ✅ クリーンな状態を維持

```bash
# 週1回程度実行
cd ~/MySwiftAgent
git worktree prune
```

### 6. myVault DB同期を忘れずに

- ✅ 重要なシークレット追加後に同期
- ✅ 定期的に同期スクリプトを実行

```bash
~/MySwiftAgent/scripts/sync-myvault-db.sh
```

---

## 関連ドキュメント

- [CLAUDE.md - 並列開発環境（git worktree）](../../CLAUDE.md#-並列開発環境git-worktree)
- [Git - git-worktree Documentation](https://git-scm.com/docs/git-worktree)
- [Pydantic Settings - Multiple .env files](https://docs.pydantic.dev/latest/concepts/pydantic_settings/#dotenv-env-support)
