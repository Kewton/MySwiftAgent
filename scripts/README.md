# MySwiftAgent Scripts

🚀 **統合開発環境管理スクリプト集**

JobQueue、MyScheduler、MyVault、ExpertAgent、GraphAiServer、CommonUIの全サービスを統合的に管理するためのシェルスクリプトです。

## 📁 スクリプト一覧

| スクリプト | 用途 | 概要 |
|-----------|------|------|
| `unified-start.sh` | **統一起動** | 全サービスの一括起動・停止（Phase 1 MVP） |
| `quick-start.sh` | **クイック起動** | 一発で全サービス起動（代替ポート使用） |
| `dev-start.sh` | **開発環境管理** | 包括的なサービス管理（標準ポート使用） |
| `health-check.sh` | **ヘルスチェック** | サービス監視・診断 |
| `pre-push-check.sh` | **品質チェック** | コミット前の品質検証 |
| `restart-myvault.sh` | **MyVault再起動** | MyVault設定リロード |
| `restart-graphaiserver.sh` | **GraphAiServer再起動** | GraphAiServer設定リロード |
| `reload-secrets.sh` | **Secrets更新** | MyVaultシークレット再読み込み |
| `build-images.sh` | **Docker Build** | バージョンタグ付きイメージビルド |
| `install-playwright.sh` | **Playwright導入** | TypeScript受入テスト用Playwright環境構築 |

## 🚀 クイックスタート

### 統一起動スクリプト（推奨・NEW）

```bash
# 全サービスを依存関係順に起動
./scripts/unified-start.sh start

# サービス状態確認
./scripts/unified-start.sh status

# 全サービス停止
./scripts/unified-start.sh stop

# 全サービス再起動
./scripts/unified-start.sh restart

# ヘルプ表示
./scripts/unified-start.sh --help
```

**unified-start.sh の特徴:**
- ✅ **依存関係順に自動起動**: Infrastructure → Middleware → Application
- ✅ **モジュール化設計**: ライブラリ構造（`unified-lib/`）でメンテナンス性向上
- ✅ **Bash 3.2対応**: macOSデフォルトBashで動作
- ✅ **標準ポート使用**: `8001-8005` (API), `5173, 8501` (UI)
- ✅ **Phase 1 MVP**: シンプルで確実な動作

**起動順序:**
1. Layer 1 (Infrastructure): myVault, jobqueue
2. Layer 2 (Middleware): myscheduler, graphAiServer
3. Layer 3 (Application): expertAgent, myAgentDesk, commonUI

**詳細ドキュメント:**
- [unified-start-usage.md](../docs/unified-start-usage.md)

**アクセスURL (unified-start.sh):**
- myAgentDesk: http://localhost:5173
- commonUI: http://localhost:8501
- jobqueue API: http://localhost:8001
- myscheduler API: http://localhost:8002
- myVault API: http://localhost:8003
- expertAgent API: http://localhost:8004
- graphAiServer API: http://localhost:8005

---

### 即座に起動（代替ポート）

```bash
# すべてのサービスを一発起動
./scripts/quick-start.sh
```

**quick-start.sh の特徴:**
- ✅ Docker Composeと**同時稼働可能**（代替ポート使用）
- ✅ デフォルトポート: `8101-8105` (API), `8601` (UI)
- ✅ 環境変数で上書き可能: `JOBQUEUE_PORT=8111 ./scripts/quick-start.sh`

**アクセスURL (quick-start.sh):**
- CommonUI: http://localhost:8601
- JobQueue API: http://localhost:8101
- MyScheduler API: http://localhost:8102
- MyVault API: http://localhost:8103
- ExpertAgent API: http://localhost:8104/aiagent-api
- GraphAiServer API: http://localhost:8105/api

### 開発用包括管理（標準ポート）

```bash
# 全サービス起動（依存関係自動解決）
./scripts/dev-start.sh

# 個別サービス起動
./scripts/dev-start.sh start --jobqueue-only
./scripts/dev-start.sh start --commonui-only

# サービス停止
./scripts/dev-start.sh stop

# ステータス確認
./scripts/dev-start.sh status

# ログ確認
./scripts/dev-start.sh logs
./scripts/dev-start.sh logs jobqueue
```

**dev-start.sh の特徴:**
- ✅ 標準ポート使用: `8001-8005` (API), `8501` (UI)
- ✅ Docker Composeと**同じポート**
- ✅ 包括的なサービス管理機能

**アクセスURL (dev-start.sh):**
- CommonUI: http://localhost:8501
- JobQueue API: http://localhost:8001
- MyScheduler API: http://localhost:8002
- MyVault API: http://localhost:8003
- ExpertAgent API: http://localhost:8004/aiagent-api
- GraphAiServer API: http://localhost:8005/api

## 🔍 ヘルスチェック・監視

### 基本ヘルスチェック

```bash
# 全サービスの健康状態確認
./scripts/health-check.sh

# 継続監視（10秒間隔）
./scripts/health-check.sh monitor

# 高頻度監視（3秒間隔）
./scripts/health-check.sh monitor --interval 3
```

### 統合テスト

```bash
# API連携テスト実行
./scripts/health-check.sh test

# システム情報表示
./scripts/health-check.sh info
```

## ✅ 品質チェック（プッシュ前）

### Pre-push Quality Checks

```bash
# プッシュ前の必須チェック（expertAgentプロジェクト）
./scripts/pre-push-check.sh
```

**チェック内容:**
- ✅ Ruff linting (自動修正あり)
- ✅ Ruff formatting
- ✅ MyPy type checking
- ✅ Unit tests (高速)
- ✅ Test coverage (90%以上)

**推奨ワークフロー:**
```bash
# 1. コード変更
vim expertAgent/app/main.py

# 2. 品質チェック
./scripts/pre-push-check.sh

# 3. 合格したらコミット・プッシュ
git add -u
git commit -m "feat: add new feature"
git push
```

## 📊 サービス構成

### ポート構成比較

| サービス | dev-start.sh<br/>(標準) | quick-start.sh<br/>(代替) | Docker Compose<br/>(標準) |
|---------|-------------|---------------|------------------|
| **CommonUI** | 8501 | 8601 | 8501 |
| **JobQueue** | 8001 | 8101 | 8001 |
| **MyScheduler** | 8002 | 8102 | 8002 |
| **MyVault** | 8003 | 8103 | 8003 |
| **ExpertAgent** | 8004 | 8104 | 8004 |
| **GraphAiServer** | 8005 | 8105 | 8005 |

### サービス依存関係

```
CommonUI (Frontend)
    ├── JobQueue API (Backend)
    ├── MyScheduler API (Backend)
    ├── MyVault API (Secret Management)
    ├── ExpertAgent API (AI Agent)
    └── GraphAiServer API (Workflow Engine)

MyScheduler
    └── JobQueue API (Job submission)

ExpertAgent
    └── MyVault API (Secret retrieval)

MyVault (Secret Management)
    └── 独立サービス（他サービスから呼び出される）
```

## ⚙️ 高度な機能

### 環境自動設定

```bash
# 開発環境セットアップのみ実行
./scripts/dev-start.sh setup

# 依存関係一括インストール
./scripts/dev-start.sh setup --jobqueue-only
```

### ログ管理

```bash
# 全ログ確認
./scripts/dev-start.sh logs

# サービス別ログ監視
./scripts/dev-start.sh logs myscheduler

# セットアップログ確認
./scripts/dev-start.sh logs setup

# ログファイルの直接参照
tail -f logs/commonui.log
tail -f logs/jobqueue.log
tail -f logs/myscheduler.log
tail -f logs/myvault.log
tail -f logs/expertagent.log
tail -f logs/graphaiserver.log
```

### MyVault管理

```bash
# MyVault再起動（設定変更時など）
./scripts/restart-myvault.sh

# MyVault起動
./scripts/restart-myvault.sh start

# MyVault停止
./scripts/restart-myvault.sh stop

# MyVaultステータス確認
./scripts/restart-myvault.sh status

# MyVaultログ確認
./scripts/restart-myvault.sh logs

# MyVaultログ監視
./scripts/restart-myvault.sh logs -f
```

> 💡 `restart-myvault.sh` は、config.yaml や .env の変更後に MyVault サービスを再起動して設定をリロードする際に使用します。

### GraphAiServer管理

```bash
# GraphAiServer再起動
./scripts/restart-graphaiserver.sh

# GraphAiServer起動
./scripts/restart-graphaiserver.sh start

# GraphAiServer停止
./scripts/restart-graphaiserver.sh stop

# GraphAiServerステータス確認
./scripts/restart-graphaiserver.sh status

# GraphAiServerログ確認
./scripts/restart-graphaiserver.sh logs
```

### Secrets更新

```bash
# MyVaultのシークレットを全サービスに再読み込み
./scripts/reload-secrets.sh

# 特定サービスのみ再読み込み
./scripts/reload-secrets.sh --service expertagent
```

### Docker イメージビルド

```bash
# 全サービスのイメージをビルド
./scripts/build-images.sh

# 特定サービスのみビルド
./scripts/build-images.sh --service jobqueue

# バージョンタグを指定してビルド
./scripts/build-images.sh --version 1.0.0

# レジストリにプッシュ
./scripts/build-images.sh --push --registry ghcr.io/kewton

# ヘルプ表示
./scripts/build-images.sh --help
```

### 開発用トークン

開発環境では自動生成されるAPIトークンを使用：

```bash
# トークン確認
cat logs/dev_tokens.txt

# 環境変数として読み込み
source logs/dev_tokens.txt
```

### クリーンアップ

```bash
# 一時ファイル・ログ・PIDファイル削除
./scripts/dev-start.sh clean
```

## 🔧 トラブルシューティング

### よくある問題

**1. ポートが既に使用中**

```bash
# ポート使用状況確認（標準・代替ポート両方をチェック）
lsof -i :8501 -i :8601 -i :8001-8005 -i :8101-8105

# 強制終了後に再起動
./scripts/dev-start.sh stop
./scripts/quick-start.sh stop
./scripts/dev-start.sh start
```

**2. 依存関係エラー**

```bash
# 依存関係を再インストール
./scripts/dev-start.sh setup
```

**3. サービス起動失敗**

```bash
# 詳細エラー確認
./scripts/dev-start.sh logs
./scripts/health-check.sh

# 個別起動でデバッグ
./scripts/dev-start.sh start --jobqueue-only
```

**4. MyVault 接続エラー**

CommonUIで "[Errno 61] Connection refused" エラーが出る場合：

```bash
# 1. MyVaultが起動しているか確認
./scripts/health-check.sh

# 2. ポート確認
lsof -i :8003  # dev-start.sh
lsof -i :8103  # quick-start.sh

# 3. 環境変数確認
cat commonUI/.env | grep MYVAULT_BASE_URL

# 4. CommonUI再起動
./scripts/dev-start.sh restart commonui
```

**5. 型チェックエラー**

```bash
# MyPy型エラーの自動修正
cd expertAgent
uv run ruff check . --fix
uv run mypy app/ core/

# 詳細は開発ガイド参照
cat docs/dev/DEVELOPMENT_GUIDE.md
```

### ログファイル場所

```
logs/  (quick-start.sh / dev-start.sh)
├── jobqueue.log      # JobQueue API ログ
├── myscheduler.log   # MyScheduler API ログ
├── myvault.log       # MyVault API ログ
├── expertagent.log   # ExpertAgent API ログ
├── graphaiserver.log # GraphAiServer API ログ
├── commonui.log      # CommonUI ログ
└── setup.log         # セットアップログ

docker-compose-data/  (docker-compose)
├── jobqueue/         # JobQueue データ・ログ
├── myscheduler/      # MyScheduler データ・ログ
├── myvault/          # MyVault データ・ログ
├── expertagent/logs/ # ExpertAgent ログ
├── graphaiserver/    # GraphAiServer データ・ログ
└── commonUI/         # CommonUI データ
```

### PIDファイル場所

```
.pids/  (quick-start.sh / dev-start.sh)
├── jobqueue.pid      # JobQueue プロセスID
├── myscheduler.pid   # MyScheduler プロセスID
├── myvault.pid       # MyVault プロセスID
├── expertagent.pid   # ExpertAgent プロセスID
├── graphaiserver.pid # GraphAiServer プロセスID
└── commonui.pid      # CommonUI プロセスID
```

## 🎯 使用例

### 通常の開発フロー

```bash
# 1. プロジェクト起動（代替ポート使用）
./scripts/quick-start.sh

# 2. ブラウザで CommonUI にアクセス
open http://localhost:8601

# 3. 開発作業...

# 4. ヘルスチェック
./scripts/health-check.sh

# 5. ログ確認
./scripts/dev-start.sh logs commonui

# 6. 終了
./scripts/quick-start.sh stop
```

### デバッグフロー

```bash
# 1. 個別サービス起動でデバッグ
./scripts/dev-start.sh start --jobqueue-only

# 2. ログ監視
./scripts/dev-start.sh logs jobqueue

# 3. 問題解決後、全サービス起動
./scripts/dev-start.sh start
```

### 継続監視

```bash
# バックグラウンドでヘルス監視
./scripts/health-check.sh monitor --interval 30 > monitoring.log 2>&1 &
```

### コミット前チェックフロー

```bash
# 1. コード変更
vim expertAgent/core/config.py

# 2. 品質チェック実行
./scripts/pre-push-check.sh

# 3. エラーがあれば修正
uv run ruff check . --fix
uv run ruff format .

# 4. 再チェック
./scripts/pre-push-check.sh

# 5. 合格したらコミット
git add -u
git commit -m "fix(type): resolve MyPy errors"
git push
```

### Docker環境との並行稼働

```bash
# 1. Docker Composeを起動（標準ポート: 8001-8005, 8501）
docker compose up -d

# 2. quick-start.shも起動（代替ポート: 8101-8105, 8601）
./scripts/quick-start.sh

# 3. 両方のUIにアクセス可能
open http://localhost:8501  # Docker Compose
open http://localhost:8601  # quick-start.sh

# 4. 両方を停止
docker compose down
./scripts/quick-start.sh stop
```

## 🔗 関連リンク

### プロジェクトドキュメント
- [JobQueue プロジェクト](../jobqueue/README.md)
- [MyScheduler プロジェクト](../myscheduler/README.md)
- [MyVault プロジェクト](../myVault/README.md)
- [ExpertAgent プロジェクト](../expertAgent/README.md)
- [GraphAiServer プロジェクト](../graphAiServer/README.md)
- [CommonUI プロジェクト](../commonUI/README.md)
- [プロジェクト全体ドキュメント](../README.md)

### 開発ガイド
- [開発ガイドライン](../docs/dev/DEVELOPMENT_GUIDE.md) - 品質チェック、型エラー対策
- [Docker ガイド](../docs/dev/DOCKER_GUIDE.md) - Docker Compose使用方法
- [デプロイメントガイド](./.github/DEPLOYMENT.md) - CI/CD、リリース手順

---

**💡 Tips**:
- `quick-start.sh` は Docker Compose と併用可能（代替ポート使用）
- `dev-start.sh` は最も包括的な管理スクリプト（標準ポート使用）
- `pre-push-check.sh` は**コミット前に必ず実行**してください
- `health-check.sh` は本番運用でのモニタリングにも使用できます
- MyVault接続エラーは環境変数（MYVAULT_BASE_URL）を確認してください
