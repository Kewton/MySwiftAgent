# MySwiftAgent アーキテクチャ概要

## 📋 目次

- [システム構成図](#システム構成図)
- [サービス一覧](#サービス一覧)
- [ネットワーク構成](#ネットワーク構成)
- [ポート設定](#ポート設定)
- [環境変数](#環境変数)
- [サービス依存関係](#サービス依存関係)
- [データ永続化](#データ永続化)
- [起動モード](#起動モード)

---

## システム構成図

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          MySwiftAgent System                            │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    CommonUI (Streamlit)                         │   │
│  │                   http://localhost:8501                         │   │
│  └────────┬───────────────┬─────────────┬─────────────┬────────────┘   │
│           │               │             │             │                │
│  ┌────────▼────────┐  ┌──▼──────────┐ ┌▼────────────┐ ┌▼────────────┐ │
│  │   JobQueue      │  │ MyScheduler │ │  MyVault    │ │ ExpertAgent │ │
│  │  :8001 → :8000  │  │ :8002→:8000 │ │ :8003→:8000 │ │ :8004→:8000 │ │
│  └────────┬────────┘  └──┬──────────┘ └┬────────────┘ └┬────────────┘ │
│           │              │              │               │              │
│  ┌────────▼──────────────▼──────────────▼───────────────▼───────────┐  │
│  │                    Internal Network                              │  │
│  │              myswiftagent-network (bridge)                       │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌──────────────────────┐                                              │
│  │   GraphAiServer      │                                              │
│  │   :8005 → :8000      │                                              │
│  └──────────────────────┘                                              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## サービス一覧

### 1. JobQueue (ジョブキュー管理)

- **説明**: ジョブキューの管理と実行を担当するバックエンドAPI
- **技術スタック**: FastAPI + Python + SQLAlchemy
- **リポジトリ**: `jobqueue/`
- **主要機能**:
  - ジョブの登録・取得・更新・削除
  - ジョブステータス管理
  - 非同期ジョブ実行

### 2. MyScheduler (ジョブスケジューリング)

- **説明**: スケジュール実行機能を提供するサービス
- **技術スタック**: FastAPI + Python + APScheduler
- **リポジトリ**: `myscheduler/`
- **主要機能**:
  - Cron形式スケジュール管理
  - ジョブの定期実行
  - JobQueue連携

### 3. MyVault (シークレット管理)

- **説明**: API キーやトークンなどのシークレットを安全に管理
- **技術スタック**: FastAPI + Python + SQLite + AES暗号化
- **リポジトリ**: `myVault/`
- **主要機能**:
  - シークレットの暗号化保存
  - サービス認証トークン管理
  - プロジェクト別シークレット管理
- **セキュリティ**:
  - マスターキー（`MSA_MASTER_KEY`）による暗号化
  - サービス別認証トークン

### 4. ExpertAgent (AI エージェント)

- **説明**: LLMを活用したAIエージェント機能
- **技術スタック**: FastAPI + Python + OpenAI/Anthropic/Google APIs
- **リポジトリ**: `expertAgent/`
- **主要機能**:
  - 複数LLMプロバイダー対応（OpenAI, Anthropic, Google, Ollama）
  - Playwright ブラウザ自動化
  - Google APIs 連携
  - MyVault連携によるシークレット管理

### 5. GraphAiServer (Graph AI ワークフロー)

- **説明**: GraphAIを使用したワークフロー実行エンジン
- **技術スタック**: Node.js/TypeScript + Express
- **リポジトリ**: `graphAiServer/`
- **主要機能**:
  - GraphAIワークフロー実行
  - カスタムノード管理

### 6. CommonUI (Web インターフェース)

- **説明**: 統合Webダッシュボード
- **技術スタック**: Streamlit + Python
- **リポジトリ**: `commonUI/`
- **主要機能**:
  - 各サービスの統合ダッシュボード
  - ジョブ管理UI
  - スケジュール管理UI
  - シークレット管理UI

---

## ネットワーク構成

### Docker Compose ネットワーク

- **ネットワーク名**: `myswiftagent-network`
- **ドライバー**: `bridge`
- **タイプ**: 内部ネットワーク（サービス間通信専用）

### サービス間通信

Docker Compose環境では、サービス名で内部DNS解決が行われます：

| 発信元 | 宛先サービス | アクセス先URL | 実際の接続先 |
|--------|------------|-------------|-------------|
| CommonUI | JobQueue | `http://jobqueue:8000` | コンテナ内ポート8000 |
| CommonUI | MyScheduler | `http://myscheduler:8000` | コンテナ内ポート8000 |
| CommonUI | MyVault | `http://myvault:8000` | コンテナ内ポート8000 |
| CommonUI | ExpertAgent | `http://expertagent:8000` | コンテナ内ポート8000 |
| CommonUI | GraphAiServer | `http://graphaiserver:8000` | コンテナ内ポート8000 |
| MyScheduler | JobQueue | `http://jobqueue:8000` | コンテナ内ポート8000 |
| ExpertAgent | MyVault | `http://myvault:8000` | コンテナ内ポート8000 |

### ホストからのアクセス

| サービス | ホストからのURL | コンテナ内ポート | ホスト公開ポート |
|---------|----------------|----------------|----------------|
| JobQueue | `http://localhost:8001` | 8000 | 8001 |
| MyScheduler | `http://localhost:8002` | 8000 | 8002 |
| MyVault | `http://localhost:8003` | 8000 | 8003 |
| ExpertAgent | `http://localhost:8004` | 8000 | 8004 |
| GraphAiServer | `http://localhost:8005` | 8000 | 8005 |
| CommonUI | `http://localhost:8501` | 8501 | 8501 |

---

## ポート設定

### Docker Compose モード

docker-compose.yml で定義されたポートマッピング：

```yaml
services:
  jobqueue:
    ports:
      - "8001:8000"    # ホスト:8001 → コンテナ:8000

  myscheduler:
    ports:
      - "8002:8000"    # ホスト:8002 → コンテナ:8000

  myvault:
    ports:
      - "8003:8000"    # ホスト:8003 → コンテナ:8000

  expertagent:
    ports:
      - "8004:8000"    # ホスト:8004 → コンテナ:8000

  graphaiserver:
    ports:
      - "8005:8000"    # ホスト:8005 → コンテナ:8000

  commonui:
    ports:
      - "8501:8501"    # ホスト:8501 → コンテナ:8501
```

### ローカル開発モード (dev-start.sh / quick-start.sh)

環境変数でポートをカスタマイズ可能（デフォルト値）：

| 環境変数 | デフォルト | quick-start.sh | 説明 |
|---------|-----------|---------------|-----|
| `JOBQUEUE_PORT` | 8001 | 8101 | JobQueue APIポート |
| `MYSCHEDULER_PORT` | 8002 | 8102 | MyScheduler APIポート |
| `MYVAULT_PORT` | 8003 | 8103 | MyVault APIポート |
| `EXPERTAGENT_PORT` | 8004 | 8104 | ExpertAgent APIポート |
| `GRAPHAISERVER_PORT` | 8005 | 8105 | GraphAiServer APIポート |
| `COMMONUI_PORT` | 8501 | 8601 | CommonUI Webポート |

**ポート衝突回避の仕組み**:

- **dev-start.sh**: Docker Composeと同じポート範囲（8001-8005, 8501）を使用
- **quick-start.sh**: ポート衝突を避けるため、8100番台・8600番台に自動割り当て

---

## 環境変数

### 共通環境変数

すべてのサービスで使用される環境変数：

```bash
# タイムゾーン
TZ=Asia/Tokyo

# Pythonパス（Pythonサービス）
PYTHONPATH=/app

# Node.js環境（TypeScriptサービス）
NODE_ENV=production
```

### サービス別環境変数

#### JobQueue

```bash
JOBQUEUE_DB_URL=sqlite+aiosqlite:///./data/jobqueue.db
```

#### MyScheduler

```bash
DATABASE_URL=sqlite:///./data/jobs.db
JOBQUEUE_API_URL=http://jobqueue:8000  # Docker内部
```

#### MyVault

```bash
DATABASE_URL=sqlite:///./data/myvault.db
MSA_MASTER_KEY=<必須：暗号化マスターキー>
TOKEN_expertagent=<ExpertAgent認証トークン>
TOKEN_myscheduler=<MyScheduler認証トークン>
TOKEN_jobqueue=<JobQueue認証トークン>
TOKEN_commonui=<CommonUI認証トークン>
```

**セキュリティ注意事項**:

- `MSA_MASTER_KEY` は `.env` ファイルで管理し、Git管理外に配置すること
- 本番環境では必ず強力なランダム文字列を使用すること

#### ExpertAgent

```bash
# MyVault連携（優先）
MYVAULT_ENABLED=true
MYVAULT_BASE_URL=http://myvault:8000
MYVAULT_SERVICE_NAME=expertagent
MYVAULT_SERVICE_TOKEN=<認証トークン>
MYVAULT_DEFAULT_PROJECT=expertagent

# API Keys（MyVault無効時のフォールバック）
OPENAI_API_KEY=<OpenAI APIキー>
ANTHROPIC_API_KEY=<Anthropic APIキー>
GOOGLE_API_KEY=<Google APIキー>
SERPER_API_KEY=<Serper APIキー>

# Ollama設定（ローカルLLM）
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_DEF_SMALL_MODEL=gemma3:27b-it-q8_0

# モデル設定
GRAPH_AGENT_MODEL=gemini-2.5-flash
PODCAST_SCRIPT_DEFAULT_MODEL=gpt-4o-mini
EXTRACT_KNOWLEDGE_MODEL=gemma3:27b-it-q8_0

# MLX LLM Server（Macのみ）
MLX_LLM_SERVER_URL=http://host.docker.internal:8080

# Google APIs
GOOGLE_APIS_TOKEN_PATH=/app/token/token.json
GOOGLE_APIS_CREDENTIALS_PATH=/app/token/credentials.json

# その他
SPREADSHEET_ID=<Google SpreadsheetのID>
MAIL_TO=<通知先メールアドレス>
LOG_DIR=/app/logs
LOG_LEVEL=INFO

# Playwright用
NODE_PATH=/usr/lib/node_modules
```

#### GraphAiServer

```bash
PORT=8000
MODEL_BASE_PATH=/app/config/graphai/
OPENAI_API_KEY=<OpenAI APIキー>
ANTHROPIC_API_KEY=<Anthropic APIキー>
```

#### CommonUI

```bash
# サービスURL（Docker内部DNS）
JOBQUEUE_BASE_URL=http://jobqueue:8000
MYSCHEDULER_BASE_URL=http://myscheduler:8000
MYVAULT_BASE_URL=http://myvault:8000
EXPERTAGENT_BASE_URL=http://expertagent:8000
GRAPHAISERVER_BASE_URL=http://graphaiserver:8000

# 認証トークン
JOBQUEUE_API_TOKEN=<オプション>
MYSCHEDULER_API_TOKEN=<オプション>
MYVAULT_SERVICE_NAME=commonui
MYVAULT_SERVICE_TOKEN=<MyVault認証トークン>
EXPERTAGENT_ADMIN_TOKEN=<オプション>
GRAPHAISERVER_ADMIN_TOKEN=<オプション>

# CommonUI設定（ローカル開発時）
POLLING_INTERVAL=5
DEFAULT_SERVICE=JobQueue
OPERATION_MODE=full
```

---

## サービス依存関係

### 起動順序

Docker Composeの `depends_on` と `healthcheck` により、以下の順序で起動：

```
1. JobQueue    (依存なし)
   ↓
2. MyScheduler (JobQueue完了後)
   MyVault     (並列起動可能)
   ↓
3. ExpertAgent (MyVault完了後)
   ↓
4. GraphAiServer (並列起動可能)
   ↓
5. CommonUI    (全サービス完了後)
```

### 依存関係の詳細

| サービス | 依存先 | 条件 |
|---------|-------|------|
| MyScheduler | JobQueue | `service_healthy` |
| ExpertAgent | MyVault | `service_healthy` |
| CommonUI | JobQueue, MyScheduler, MyVault, ExpertAgent, GraphAiServer | すべて `service_healthy` |

### ヘルスチェック設定

すべてのサービスは `/health` エンドポイントでヘルスチェック実行：

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s      # 30秒ごとにチェック
  timeout: 10s       # 10秒でタイムアウト
  retries: 3         # 3回失敗で unhealthy
  start_period: 5-15s # 起動猶予時間
```

---

## データ永続化

### Docker Compose ボリュームマッピング

| サービス | ホストパス | コンテナパス | 用途 |
|---------|----------|------------|------|
| JobQueue | `./docker-compose-data/jobqueue/` | `/app/data/` | SQLiteデータベース |
| MyScheduler | `./docker-compose-data/myscheduler/` | `/app/data/` | SQLiteデータベース |
| MyVault | `./docker-compose-data/myvault/` | `/app/data/` | 暗号化シークレットDB |
| MyVault | `./myVault/config.yaml` | `/app/config.yaml` | 設定ファイル（読み取り専用） |
| ExpertAgent | `./docker-compose-data/expertagent/token/` | `/app/token/` | Google API認証情報 |
| ExpertAgent | `./docker-compose-data/expertagent/logs/` | `/app/logs/` | ログファイル |
| GraphAiServer | `./docker-compose-data/graphaiserver/config/` | `/app/config/` | GraphAI設定 |
| CommonUI | `./docker-compose-data/commonUI/` | `/app/data/` | Streamlit設定 |

### ローカル開発モード

dev-start.sh では各サービスの `data/` ディレクトリに直接保存：

```
jobqueue/data/jobqueue.db
myscheduler/data/jobs.db
myVault/data/myvault.db
expertAgent/logs/
graphAiServer/config/
```

---

## 起動モード

### 1. Docker Compose モード（本番・ステージング）

**特徴**:
- 完全にコンテナ化された環境
- サービス間通信は内部ネットワーク
- ポート固定（8001-8005, 8501）
- 自動再起動・ヘルスチェック対応

**起動コマンド**:
```bash
docker-compose up -d
```

**確認コマンド**:
```bash
docker-compose ps
docker-compose logs -f <service-name>
```

**停止コマンド**:
```bash
docker-compose down
```

### 2. ローカル開発モード (dev-start.sh)

**特徴**:
- ホストマシン上でプロセス実行
- ポート範囲: 8001-8005, 8501
- `uv` および `npm` で依存関係管理
- デバッグしやすい

**起動コマンド**:
```bash
./scripts/dev-start.sh start
```

**便利なコマンド**:
```bash
# ステータス確認
./scripts/dev-start.sh status

# ログ確認
./scripts/dev-start.sh logs
./scripts/dev-start.sh logs jobqueue

# 停止
./scripts/dev-start.sh stop

# 再起動
./scripts/dev-start.sh restart

# テスト実行
./scripts/dev-start.sh test
```

### 3. クイックスタートモード (quick-start.sh)

**特徴**:
- Docker Composeポートとの衝突回避
- ポート範囲: 8101-8105, 8601
- 最小設定で即座に起動

**起動コマンド**:
```bash
./scripts/quick-start.sh
```

**ポート設定のカスタマイズ**:
```bash
# 環境変数で上書き
COMMONUI_PORT=9000 ./scripts/quick-start.sh
```

---

## 設定ファイル一覧

### プロジェクトルート

```
.env                          # 環境変数（Git管理外）
docker-compose.yml            # Docker Compose設定
```

### サービス設定

```
jobqueue/pyproject.toml       # JobQueue依存関係
myscheduler/pyproject.toml    # MyScheduler依存関係
myVault/config.yaml           # MyVault設定
myVault/pyproject.toml        # MyVault依存関係
expertAgent/pyproject.toml    # ExpertAgent依存関係
graphAiServer/package.json    # GraphAiServer依存関係
commonUI/pyproject.toml       # CommonUI依存関係
```

---

## セキュリティ考慮事項

### 1. シークレット管理

- **MyVault**: 暗号化シークレット管理サービスを使用
- **マスターキー**: `MSA_MASTER_KEY` は絶対にGit管理に含めない
- **.env ファイル**: `.gitignore` に追加し、チーム内で安全に共有

### 2. 認証トークン

- サービス間通信は認証トークンで保護
- 開発環境用トークンと本番環境用トークンを分離

### 3. Docker セキュリティ

- **ExpertAgent**: Playwright実行のため `SYS_ADMIN` capability必要
- **ネットワーク分離**: 内部ネットワークで通信を隔離

---

## トラブルシューティング

### ポート衝突が発生した場合

**Docker Composeモード**:
```bash
# 使用中のポートを確認
lsof -i :8001
lsof -i :8501

# プロセスを終了
kill -9 <PID>
```

**ローカル開発モード**:
```bash
# dev-start.sh が自動的にポートをクリーンアップ
./scripts/dev-start.sh stop
./scripts/dev-start.sh clean
```

### ヘルスチェック失敗

```bash
# ログを確認
docker-compose logs <service-name>

# または
./scripts/dev-start.sh logs <service-name>
```

### データベースエラー

```bash
# データをリセット
docker-compose down -v
rm -rf docker-compose-data/

# 再起動
docker-compose up -d
```

---

## パフォーマンス考慮事項

### リソース要件

| サービス | CPU | Memory | Disk |
|---------|-----|--------|------|
| JobQueue | 0.5 core | 256MB | 100MB |
| MyScheduler | 0.5 core | 256MB | 100MB |
| MyVault | 0.5 core | 256MB | 50MB |
| ExpertAgent | 1 core | 1GB | 500MB |
| GraphAiServer | 0.5 core | 512MB | 200MB |
| CommonUI | 0.5 core | 512MB | 100MB |

### ExpertAgent 特記事項

- **Playwright**: 2GB shm_size必要（Chromiumブラウザ実行用）
- **Docker設定**: `shm_size: 2gb` を設定済み

---

## 関連ドキュメント

- [環境変数詳細](./environment-variables.md)
- [開発ガイド](../CLAUDE.md)
- [デプロイメント手順](../.github/DEPLOYMENT.md)

---

最終更新: 2025-10-19
