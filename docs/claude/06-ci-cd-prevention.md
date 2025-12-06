# 🛡️ GitHub Actions エラー再発防止策

このセクションでは、CI/CDパイプラインでのエラーを未然に防ぐための包括的な対策をまとめています。

## 📊 エラーパターン分析

過去に発生したGitHub Actionsエラーとその根本原因:

| エラー種類 | 発生回数 | 影響度 | 根本原因 |
|-----------|---------|-------|---------|
| **Linting errors (Ruff)** | 高頻度 | 🔴 Critical | コミット前の品質チェック不足 |
| **Import順序 (I001)** | 中頻度 | 🟡 Medium | Import自動整理の未設定 |
| **未使用import (F401)** | 中頻度 | 🟡 Medium | 保存時の自動クリーンアップ不足 |
| **Pytest設定エラー** | 低頻度 | 🟢 Low | 新規marker追加時の設定漏れ |

## 🎯 再発防止策（優先度順）

### **優先度1: Pre-commit Hooks 導入** (必須)

コミット前に自動チェックを実行し、不合格なコードのコミットを防止します。

#### インストール手順

```bash
# 1. Pre-commitのインストール
pip install pre-commit

# 2. Hooksの有効化
pre-commit install

# 3. 既存コード全体のチェック（初回のみ）
pre-commit run --all-files
```

#### 設定ファイル

`.pre-commit-config.yaml` に以下の内容を設定済み:

- **Ruff linting** (自動修正付き)
- **Ruff formatting** (自動適用)
- **MyPy type checking**
- **Fast unit tests** (高速テストのみ)
- **一般的なファイルチェック** (trailing spaces, merge conflicts等)

#### コミット時の動作

```bash
git commit -m "your message"
# ↓ Pre-commit hooks が自動実行
# ✓ Ruff linting... (自動修正)
# ✓ Ruff formatting...
# ✓ MyPy type checking...
# ✓ Pytest (unit tests)...
# ✓ All checks passed!
```

### **優先度2: VS Code 設定の最適化**

保存時に自動フォーマット・自動import整理を実行します。

#### 推奨拡張機能（必須）

以下の拡張機能をインストールしてください（`.vscode/extensions.json` に記載）:

1. **Ruff** (`charliermarsh.ruff`) - 必須
2. **Python** (`ms-python.python`) - 必須
3. **Pylance** (`ms-python.vscode-pylance`) - 推奨

#### 自動設定内容

`.vscode/settings.json` で以下が自動化済み:

- **保存時にフォーマット** (`editor.formatOnSave: true`)
- **保存時にimport整理** (`source.organizeImports: "explicit"`)
- **保存時にlint自動修正** (`source.fixAll: "explicit"`)
- **Ruff自動実行** (`ruff.lint.run: "onSave"`)

### **優先度3: プッシュ前チェックスクリプト**

プッシュ前に全品質チェックを一括実行します。

#### 使用方法

```bash
# 全プロジェクトをチェック（推奨）
./scripts/pre-push-check-all.sh

# expertAgentプロジェクトのみチェック（高速）
./scripts/pre-push-check.sh
```

#### チェック内容

**pre-push-check-all.sh** （マルチプロジェクト対応版）:
- 対象プロジェクト: expertAgent, jobqueue, myscheduler, myVault, graphAiServer
- Python プロジェクト: Ruff linting, Ruff formatting, MyPy type checking, Unit tests, Coverage check (90%以上)
- TypeScript プロジェクト: ESLint, TypeScript compilation, Build

**pre-push-check.sh** （expertAgent専用）:
1. ✅ Ruff linting
2. ✅ Ruff formatting
3. ✅ MyPy type checking
4. ✅ Unit tests (高速)
5. ✅ Coverage check (90%以上)

すべて合格したらプッシュ可能です。

### **優先度4: 開発ガイドライン遵守**

`DEVELOPMENT_GUIDE.md` に詳細な開発ルールとチェックリストを記載しています。

#### よくあるエラーと対策

| エラー | 対策 |
|-------|------|
| **Import順序 (I001)** | VS Code設定で保存時に自動整理 |
| **未使用import (F401)** | Pre-commit hooksが自動削除 |
| **重複import (F811)** | トップレベルでのみimport |
| **Pytest marker未定義** | `pyproject.toml`に必ず登録 |
| **カバレッジ不足** | HTMLレポートで未カバー箇所を確認 |

## 📋 コミット前チェックリスト

### 自動チェック（Pre-commit Hooks）

- [ ] Ruff linting (自動修正)
- [ ] Ruff formatting (自動適用)
- [ ] Type checking (MyPy)
- [ ] Unit tests (高速)

### 手動チェック

- [ ] 新しいテストを追加したか？
- [ ] カバレッジは維持されているか？ (90%以上)
- [ ] コミットメッセージは規約に従っているか？
- [ ] プッシュ前に `./scripts/pre-push-check-all.sh` を実行したか？

## 🔄 CI/CDエラー発生時の対応手順

### 1. エラーログの確認

```bash
# 最新のワークフロー実行を確認
gh run list --branch feature/your-branch --limit 1

# 失敗ログを表示
gh run view <run-id> --log-failed
```

### 2. ローカルで再現

```bash
cd expertAgent

# Lintingエラーの場合
uv run ruff check .

# Test失敗の場合
uv run pytest tests/ -v

# Coverage不足の場合
uv run pytest tests/ --cov=app --cov=core --cov-report=html
open htmlcov/index.html
```

### 3. 修正して再プッシュ

```bash
# 自動修正
uv run ruff check . --fix

# テスト追加後、全チェック実行
./scripts/pre-push-check-all.sh

# コミット・プッシュ
git add -u
git commit -m "fix: resolve CI errors"
git push
```

## 🚀 効果測定

### 導入前（2025年10月9日以前）

- ❌ CI失敗率: **83%** (6回中5回失敗)
- ⏱️ 平均修正時間: 15-30分/回
- 🔄 平均リトライ回数: 2-3回

### 導入後（期待値）

- ✅ CI成功率: **95%以上** (Pre-commit hooksで事前防止)
- ⏱️ 平均修正時間: 5分以内 (ローカルで即座に検出)
- 🔄 リトライ回数: 0-1回

## 📚 参考ドキュメント

- 📖 **詳細ガイド**: `DEVELOPMENT_GUIDE.md`
- 🔧 **Pre-commitチェックスクリプト（全プロジェクト）**: `scripts/pre-push-check-all.sh`
- 🔧 **Pre-commitチェックスクリプト（expertAgent専用）**: `scripts/pre-push-check.sh`
- ⚙️ **VS Code設定**: `.vscode/settings.json`
- 🪝 **Pre-commit Hooks設定**: `.pre-commit-config.yaml`

---

## 🐳 Docker操作のベストプラクティス

### ⚠️ 禁止事項

| 操作 | リスク | 代替手段 |
|------|--------|---------|
| `docker rm -f <container>` | データ消失、設定喪失 | `make down` または `make stop` |
| `docker volume rm` | 永続データ完全消失 | `make clean`（確認プロンプト付き） |
| `docker system prune -a` | 全イメージ・ボリューム削除 | 個別に `docker image prune` |

### ✅ 推奨手順

#### コンテナ名競合が発生した場合

```bash
# ❌ 禁止: 強制削除（データ消失リスク）
docker rm -f myswiftagent-myvault

# ✅ 推奨: docker compose で安全に停止
make down
# または
make stop  # コンテナを停止（削除せず保持）
```

#### コンテナの状態確認

```bash
# 起動中のコンテナ確認
make status

# 停止中のコンテナも含めて確認
docker ps -a | grep myswiftagent
```

#### 既存コンテナの再利用

```bash
# 停止中のコンテナがある場合は再起動
docker start myswiftagent-myvault

# または make で全体を起動
make dev-all
```

### 📋 Docker操作チェックリスト

コンテナを削除する前に必ず確認：

- [ ] `docker ps -a` で停止状態のコンテナを確認
- [ ] 重要なデータがボリュームマウントされているか確認
- [ ] `make stop` で停止のみ可能か検討
- [ ] 削除が必要な場合は `make down` を使用

### 🔄 データ永続化の確認

```bash
# ボリュームマウント先の確認
ls -la docker-compose-data/

# 各サービスのデータ
docker-compose-data/
├── myvault/       # APIキー、シークレット
├── jobqueue/      # ジョブキューデータ
├── expertagent/   # トークン、ログ
└── valkey/        # キャッシュデータ（./valkey/data/）
```

---

[← 並列開発環境](./05-worktree-guide.md) | [CLAUDE.md](../../CLAUDE.md) | [次: ドキュメント管理 →](./07-documentation-rules.md)