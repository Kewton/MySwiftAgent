# MySwiftAgent 環境変数一覧

## 起動方法の比較

| 起動方法 | ポート範囲 | 環境変数ソース | 用途 |
|---------|----------|---------------|------|
| **docker-compose up** | 8001-8005, 8501 | .env → docker-compose.yml | 本番相当環境 |
| **scripts/quick-start.sh** | 8101-8105, 8601 | .env → dev-start.sh → 各サービス | ローカル開発 |

---

## 📋 JobQueue サービス

### Docker Compose モード

| 環境変数 | 値 | ソース | 必須/任意 | 説明 |
|---------|-----|--------|----------|------|
| `PYTHONPATH` | `/app` | docker-compose.yml (固定) | 必須 | Pythonモジュールパス |
| `JOBQUEUE_DB_URL` | `sqlite+aiosqlite:///./data/jobqueue.db` | docker-compose.yml (固定) | 必須 | データベース接続URL |
| `TZ` | `Asia/Tokyo` | docker-compose.yml (固定) | 任意 | タイムゾーン |

### dev-start.sh モード

| 環境変数 | 値 | ソース | 必須/任意 | 説明 |
|---------|-----|--------|----------|------|
| `JOBQUEUE_PORT` | `8001` (docker) / `8101` (quick-start) | 環境変数 / スクリプト | 任意 | サービスポート番号 |

**取得方法**:
- Docker: `.env`ファイルは不要（docker-compose.ymlで完結）
- dev-start.sh: ポート番号のみ環境変数で上書き可能

---

## ⏰ MyScheduler サービス

### Docker Compose モード

| 環境変数 | 値 | ソース | 必須/任意 | 説明 |
|---------|-----|--------|----------|------|
| `PYTHONPATH` | `/app` | docker-compose.yml (固定) | 必須 | Pythonモジュールパス |
| `TZ` | `Asia/Tokyo` | docker-compose.yml (固定) | 任意 | タイムゾーン |
| `JOBQUEUE_API_URL` | `http://jobqueue:8000` | docker-compose.yml (固定) | 必須 | JobQueue API URL (内部通信) |
| `DATABASE_URL` | `sqlite:///./data/jobs.db` | docker-compose.yml (固定) | 必須 | データベース接続URL |

### dev-start.sh モード

| 環境変数 | 値 | ソース | 必須/任意 | 説明 |
|---------|-----|--------|----------|------|
| `MYSCHEDULER_PORT` | `8002` (docker) / `8102` (quick-start) | 環境変数 / スクリプト | 任意 | サービスポート番号 |

**取得方法**:
- Docker: `.env`ファイルは不要
- dev-start.sh: ポート番号のみ環境変数で上書き可能

---

## 🔐 MyVault サービス (Secrets管理)

### Docker Compose モード

| 環境変数 | 値 | ソース | 必須/任意 | 説明 |
|---------|-----|--------|----------|------|
| `PYTHONPATH` | `/app` | docker-compose.yml (固定) | 必須 | Pythonモジュールパス |
| `TZ` | `Asia/Tokyo` | docker-compose.yml (固定) | 任意 | タイムゾーン |
| `DATABASE_URL` | `sqlite:///./data/myvault.db` | docker-compose.yml (固定) | 必須 | データベース接続URL |
| **`MSA_MASTER_KEY`** | `${MSA_MASTER_KEY}` | **.env** | **必須** | マスター暗号化キー |
| **`TOKEN_expertagent`** | `${MYVAULT_TOKEN_EXPERTAGENT}` | **.env** | **必須** | ExpertAgent認証トークン |
| **`TOKEN_myscheduler`** | `${MYVAULT_TOKEN_MYSCHEDULER}` | **.env** | **必須** | MyScheduler認証トークン |
| **`TOKEN_jobqueue`** | `${MYVAULT_TOKEN_JOBQUEUE}` | **.env** | **必須** | JobQueue認証トークン |
| **`TOKEN_commonui`** | `${MYVAULT_TOKEN_COMMONUI}` | **.env** | **必須** | CommonUI認証トークン |

### dev-start.sh モード

| 環境変数 | 値 | ソース | 必須/任意 | 説明 |
|---------|-----|--------|----------|------|
| `MYVAULT_PORT` | `8003` (docker) / `8103` (quick-start) | 環境変数 / スクリプト | 任意 | サービスポート番号 |
| **`MSA_MASTER_KEY`** | `base64:...` | **.env** | **必須** | マスター暗号化キー |
| `MYVAULT_TOKEN_EXPERTAGENT` | `.env` or `dev-expertagent-token` | .env (fallback: デフォルト値) | 任意 | ExpertAgent認証トークン |
| `MYVAULT_TOKEN_MYSCHEDULER` | `.env` or `dev-myscheduler-token` | .env (fallback: デフォルト値) | 任意 | MyScheduler認証トークン |
| `MYVAULT_TOKEN_JOBQUEUE` | `.env` or `dev-jobqueue-token` | .env (fallback: デフォルト値) | 任意 | JobQueue認証トークン |
| `MYVAULT_TOKEN_COMMONUI` | `.env` or `dev-myvault-token` | .env (fallback: デフォルト値) | 任意 | CommonUI認証トークン |

**取得方法**:
- **MSA_MASTER_KEY**: `.env`ファイルに設定必須（例: `base64:Rup6PTJHFJybCSG0sY9a/wtT/wNoEWlu1MfV6nCdhr8=`）
- **サービストークン**:
  - Docker: `.env`に設定必須（空だと認証エラー）
  - dev-start.sh: `.env`に未設定でもデフォルト値で起動可能

**⚠️ 現在の問題**: `.env`ファイルの`MYVAULT_TOKEN_*`が空文字列のため、Docker起動時に認証失敗

---

## 🤖 ExpertAgent サービス

### Docker Compose モード

| 環境変数 | 値 | ソース | 必須/任意 | 説明 |
|---------|-----|--------|----------|------|
| `PYTHONPATH` | `/app` | docker-compose.yml (固定) | 必須 | Pythonモジュールパス |
| `TZ` | `Asia/Tokyo` | docker-compose.yml (固定) | 任意 | タイムゾーン |
| **MyVault Configuration (優先)** | | | | |
| `MYVAULT_ENABLED` | `${MYVAULT_ENABLED:-true}` | .env (デフォルト: true) | 任意 | MyVault有効化フラグ |
| `MYVAULT_BASE_URL` | `http://myvault:8000` | docker-compose.yml (固定) | 必須 | MyVault URL (内部通信) |
| `MYVAULT_SERVICE_NAME` | `expertagent` | docker-compose.yml (固定) | 必須 | サービス名 |
| **`MYVAULT_SERVICE_TOKEN`** | `${MYVAULT_TOKEN_EXPERTAGENT}` | **.env** | **必須** | MyVault認証トークン |
| `MYVAULT_DEFAULT_PROJECT` | `${MYVAULT_DEFAULT_PROJECT:-expertagent}` | .env (デフォルト: expertagent) | 任意 | デフォルトプロジェクト名 |
| **API Keys (MyVault無効時のフォールバック)** | | | | |
| `OPENAI_API_KEY` | `${OPENAI_API_KEY}` | **.env** | 任意 (MyVault優先) | OpenAI APIキー |
| `ANTHROPIC_API_KEY` | `${ANTHROPIC_API_KEY}` | **.env** | 任意 (MyVault優先) | Anthropic APIキー |
| `GOOGLE_API_KEY` | `${GOOGLE_API_KEY}` | **.env** | 任意 (MyVault優先) | Google APIキー |
| `SERPER_API_KEY` | `${SERPER_API_KEY}` | **.env** | 任意 (MyVault優先) | Serper APIキー |
| **Google APIs** | | | | |
| `GOOGLE_APIS_TOKEN_PATH` | `/app/token/token.json` | docker-compose.yml (固定) | 任意 | Google OAuth2トークンパス |
| `GOOGLE_APIS_CREDENTIALS_PATH` | `/app/token/credentials.json` | docker-compose.yml (固定) | 任意 | Google OAuth2クレデンシャル |
| **Mail Configuration** | | | | |
| `MAIL_TO` | `${MAIL_TO}` | **.env** | 任意 | メール送信先アドレス |
| **Model Configuration** | | | | |
| `GRAPH_AGENT_MODEL` | `${GRAPH_AGENT_MODEL:-gemini-2.5-flash}` | .env (デフォルト: gemini-2.5-flash) | 任意 | Graph Agent モデル名 |
| `PODCAST_SCRIPT_DEFAULT_MODEL` | `${PODCAST_SCRIPT_DEFAULT_MODEL:-gpt-4o-mini}` | .env (デフォルト: gpt-4o-mini) | 任意 | Podcast スクリプトモデル |
| `EXTRACT_KNOWLEDGE_MODEL` | `${EXTRACT_KNOWLEDGE_MODEL:-gemma3:27b-it-q8_0}` | .env (デフォルト: gemma3:27b-it-q8_0) | 任意 | 知識抽出モデル |
| **Ollama Configuration** | | | | |
| `OLLAMA_URL` | `http://host.docker.internal:11434` | docker-compose.yml (固定) | 任意 | Ollama サーバーURL |
| `OLLAMA_DEF_SMALL_MODEL` | `${OLLAMA_DEF_SMALL_MODEL:-gemma3:27b-it-q8_0}` | .env (デフォルト: gemma3:27b-it-q8_0) | 任意 | Ollama デフォルトモデル |
| **Other Services** | | | | |
| `SPREADSHEET_ID` | `${SPREADSHEET_ID}` | **.env** | 任意 | Google スプレッドシートID |
| `MLX_LLM_SERVER_URL` | `http://host.docker.internal:8080` | docker-compose.yml (固定) | 任意 | MLX LLMサーバーURL |
| **Logging** | | | | |
| `LOG_DIR` | `/app/logs` | docker-compose.yml (固定) | 任意 | ログ出力ディレクトリ |
| `LOG_LEVEL` | `${LOG_LEVEL:-INFO}` | .env (デフォルト: INFO) | 任意 | ログレベル |
| `NODE_PATH` | `/usr/lib/node_modules` | docker-compose.yml (固定) | 任意 | Node.js モジュールパス |

### dev-start.sh モード

| 環境変数 | 値 | ソース | 必須/任意 | 説明 |
|---------|-----|--------|----------|------|
| `EXPERTAGENT_PORT` | `8004` (docker) / `8104` (quick-start) | 環境変数 / スクリプト | 任意 | サービスポート番号 |
| その他すべて | Docker Composeと同じ | .env | 同上 | 同上 |

**取得方法**:
- **API Keys**: `.env`に設定（MyVault有効時はMyVaultから取得）
- **MyVault認証**: `.env`の`MYVAULT_TOKEN_EXPERTAGENT`に設定必須
- **Model設定**: `.env`でカスタマイズ可能（デフォルト値あり）

---

## 🔄 GraphAiServer サービス

### Docker Compose モード

| 環境変数 | 値 | ソース | 必須/任意 | 説明 |
|---------|-----|--------|----------|------|
| `NODE_ENV` | `production` | docker-compose.yml (固定) | 任意 | Node.js 環境 |
| `PORT` | `8000` | docker-compose.yml (固定) | 必須 | サーバーポート (内部) |
| `TZ` | `Asia/Tokyo` | docker-compose.yml (固定) | 任意 | タイムゾーン |
| `MODEL_BASE_PATH` | `/app/config/graphai/` | docker-compose.yml (固定) | 必須 | モデル設定パス |
| `OPENAI_API_KEY` | `${OPENAI_API_KEY}` | **.env** | 任意 | OpenAI APIキー |
| `ANTHROPIC_API_KEY` | `${ANTHROPIC_API_KEY}` | **.env** | 任意 | Anthropic APIキー |

### dev-start.sh モード

| 環境変数 | 値 | ソース | 必須/任意 | 説明 |
|---------|-----|--------|----------|------|
| `GRAPHAISERVER_PORT` | `8005` (docker) / `8105` (quick-start) | 環境変数 / スクリプト | 任意 | サービスポート番号 |
| `PORT` | `$GRAPHAISERVER_PORT` | スクリプト経由 | 必須 | npm start に渡される |

**取得方法**:
- **API Keys**: `.env`に設定

---

## 🎨 CommonUI サービス

### Docker Compose モード

| 環境変数 | 値 | ソース | 必須/任意 | 説明 |
|---------|-----|--------|----------|------|
| `PYTHONPATH` | `/app` | docker-compose.yml (固定) | 必須 | Pythonモジュールパス |
| `TZ` | `Asia/Tokyo` | docker-compose.yml (固定) | 任意 | タイムゾーン |
| **Service API URLs** | | | | |
| `JOBQUEUE_BASE_URL` | `http://jobqueue:8000` | docker-compose.yml (固定) | 必須 | JobQueue API URL (内部通信) |
| `MYSCHEDULER_BASE_URL` | `http://myscheduler:8000` | docker-compose.yml (固定) | 必須 | MyScheduler API URL (内部通信) |
| `MYVAULT_BASE_URL` | `http://myvault:8000` | docker-compose.yml (固定) | 必須 | MyVault API URL (内部通信) |
| `EXPERTAGENT_BASE_URL` | `http://expertagent:8000` | docker-compose.yml (固定) | 必須 | ExpertAgent API URL (内部通信) |
| `GRAPHAISERVER_BASE_URL` | `http://graphaiserver:8000` | docker-compose.yml (固定) | 必須 | GraphAiServer API URL (内部通信) |
| **Service Authentication Tokens** | | | | |
| `JOBQUEUE_API_TOKEN` | `${JOBQUEUE_API_TOKEN:-}` | .env (空でも可) | 任意 | JobQueue 認証トークン |
| `MYSCHEDULER_API_TOKEN` | `${MYSCHEDULER_API_TOKEN:-}` | .env (空でも可) | 任意 | MyScheduler 認証トークン |
| `MYVAULT_SERVICE_NAME` | `commonui` | docker-compose.yml (固定) | 必須 | MyVault サービス名 |
| **`MYVAULT_SERVICE_TOKEN`** | `${MYVAULT_TOKEN_COMMONUI}` | **.env** | **必須** | MyVault 認証トークン |
| `EXPERTAGENT_ADMIN_TOKEN` | `${EXPERTAGENT_ADMIN_TOKEN:-}` | .env (空でも可) | 任意 | ExpertAgent 管理者トークン |
| `GRAPHAISERVER_ADMIN_TOKEN` | `${GRAPHAISERVER_ADMIN_TOKEN:-}` | .env (空でも可) | 任意 | GraphAiServer 管理者トークン |

### dev-start.sh モード

**dev-start.sh は `commonUI/.env` ファイルを自動生成します**:

| 環境変数 | 値 | ソース | 必須/任意 | 説明 |
|---------|-----|--------|----------|------|
| `COMMONUI_PORT` | `8501` (docker) / `8601` (quick-start) | 環境変数 / スクリプト | 任意 | サービスポート番号 |
| `JOBQUEUE_BASE_URL` | `http://localhost:$JOBQUEUE_PORT` | スクリプト生成 (.env) | 必須 | JobQueue API URL |
| `JOBQUEUE_API_TOKEN` | `dev-jobqueue-token-{timestamp}` | スクリプト生成 (自動) | 必須 | JobQueue 認証トークン |
| `MYSCHEDULER_BASE_URL` | `http://localhost:$MYSCHEDULER_PORT` | スクリプト生成 (.env) | 必須 | MyScheduler API URL |
| `MYSCHEDULER_API_TOKEN` | `dev-myscheduler-token-{timestamp}` | スクリプト生成 (自動) | 必須 | MyScheduler 認証トークン |
| `MYVAULT_BASE_URL` | `http://localhost:$MYVAULT_PORT` | スクリプト生成 (.env) | 必須 | MyVault API URL |
| `MYVAULT_SERVICE_NAME` | `commonui` | スクリプト生成 (.env) | 必須 | MyVault サービス名 |
| `MYVAULT_SERVICE_TOKEN` | `${MYVAULT_TOKEN_COMMONUI:-dev-myvault-token}` | .env (fallback: デフォルト値) | 任意 | MyVault 認証トークン |
| `EXPERTAGENT_BASE_URL` | `http://localhost:$EXPERTAGENT_PORT/aiagent-api` | スクリプト生成 (.env) | 必須 | ExpertAgent API URL |
| `GRAPHAISERVER_BASE_URL` | `http://localhost:$GRAPHAISERVER_PORT/api` | スクリプト生成 (.env) | 必須 | GraphAiServer API URL |
| `POLLING_INTERVAL` | `5` | スクリプト生成 (.env) | 任意 | ポーリング間隔 (秒) |
| `DEFAULT_SERVICE` | `JobQueue` | スクリプト生成 (.env) | 任意 | デフォルトサービス |
| `OPERATION_MODE` | `full` | スクリプト生成 (.env) | 任意 | 動作モード |

**取得方法**:
- Docker: すべて docker-compose.yml で設定（MyVault トークンのみ .env 必須）
- dev-start.sh: `commonUI/.env` ファイルを自動生成（毎回上書き）

---

## 🔑 環境変数の設定方法

### 1. プロジェクトルートの .env ファイル設定

```bash
# プロジェクトルートで実行
cp .env.example .env
```

**必須の設定項目**:

#### MyVault 認証トークン（Docker起動時に必須）

```bash
# 各サービス用のトークンを生成・設定
MYVAULT_TOKEN_EXPERTAGENT=wBZrUftRV6_MsCj8iVXb-uc60-A95HqyuESL2tVFGQ4
MYVAULT_TOKEN_MYSCHEDULER=7aYvsd5dqgMn3C3wHd4l8mODfOxLMlRRKY10bVZkOqg
MYVAULT_TOKEN_JOBQUEUE=4sxKa7mXfXAosr7ZJcryeOwnjUEbHzLRqvtZF3qFEn0
MYVAULT_TOKEN_COMMONUI=L8Z7mbEqJLHITqXn6SnOBOYZnmnfnSpC8Lebetpvmu8
```

**トークン生成方法**:
```bash
# ランダムな安全なトークンを生成
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### マスター暗号化キー（必須）

```bash
# すでに設定済み
MSA_MASTER_KEY=base64:Rup6PTJHFJybCSG0sY9a/wtT/wNoEWlu1MfV6nCdhr8=
```

#### API Keys（任意、MyVault経由でも設定可能）

```bash
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-api03-...
GOOGLE_API_KEY=AIzaSy...
SERPER_API_KEY=aff8257f...
```

### 2. dev-start.sh 使用時の注意点

- `.env`の`MYVAULT_TOKEN_*`が空でも、デフォルト値で起動可能
- `commonUI/.env`は自動生成されるため、手動編集不要
- ポート番号は環境変数で上書き可能:
  ```bash
  JOBQUEUE_PORT=9001 MYSCHEDULER_PORT=9002 ./scripts/quick-start.sh
  ```

### 3. Docker Compose 使用時の注意点

- **`.env`の`MYVAULT_TOKEN_*`が空だと MyVault 認証エラーが発生**
- すべてのサービス間通信は Docker ネットワーク内部（`http://{service_name}:8000`）
- 外部からのアクセスはポートマッピングで制御（8001-8005, 8501）

---

## ⚙️ 環境変数ポリシー

### 優先順位

1. **docker-compose.yml の固定値**（最優先）
   - 内部通信URL、PYTHONPATH、TZ など

2. **プロジェクトルート .env**（次点）
   - MyVault トークン、API Keys、マスター暗号化キー

3. **デフォルト値**（最終フォールバック）
   - dev-start.sh のデフォルト値、docker-compose.yml の `${VAR:-default}`

### セキュリティ方針

- **トークン類は .env で管理し、Git に含めない** (`.gitignore`で除外済み)
- **MyVault マスター暗号化キーは必ず base64 エンコードされた形式**
- **本番環境では環境変数を直接設定し、.env ファイルを使用しない**

### 開発環境の使い分け

| 用途 | 使用方法 | 特徴 |
|------|---------|------|
| **フルスタック検証** | `docker-compose up` | 本番相当、全サービス連携、MyVault認証必須 |
| **高速開発** | `./scripts/quick-start.sh` | ローカル実行、ポート競合回避、デフォルト認証 |
| **個別サービス開発** | `./scripts/dev-start.sh --{service}-only` | 特定サービスのみ起動、ログ確認容易 |

---

## 🛠️ トラブルシューティング

### エラー: "Authentication failed for 'MyVault'"

**原因**: `.env`の`MYVAULT_TOKEN_COMMONUI`が空

**解決策**:
```bash
# トークンを生成して .env に追加
echo "MYVAULT_TOKEN_COMMONUI=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')" >> .env

# 他のサービス用トークンも同様に設定
echo "MYVAULT_TOKEN_EXPERTAGENT=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')" >> .env
echo "MYVAULT_TOKEN_MYSCHEDULER=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')" >> .env
echo "MYVAULT_TOKEN_JOBQUEUE=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')" >> .env
```

### エラー: "Connection refused" (dev-start.sh使用時)

**原因**: ポート競合（docker-compose が 8001-8005 を使用中）

**解決策**:
```bash
# quick-start.sh を使用（自動的に 8101-8105 に変更）
./scripts/quick-start.sh

# または手動でポート指定
MYVAULT_PORT=8103 ./scripts/dev-start.sh
```

### エラー: "MSA_MASTER_KEY not set"

**原因**: `.env`に`MSA_MASTER_KEY`が未設定

**解決策**:
```bash
# キーを生成して .env に追加
python3 -c "import base64, os; print('MSA_MASTER_KEY=base64:' + base64.urlsafe_b64encode(os.urandom(32)).decode())" >> .env
```

---

## 📊 環境変数一覧（簡易版）

### .env ファイルに設定が必須の変数

| 変数名 | 必須レベル | 説明 |
|-------|----------|------|
| `MSA_MASTER_KEY` | ⭐⭐⭐ 必須 | MyVault マスター暗号化キー |
| `MYVAULT_TOKEN_EXPERTAGENT` | ⭐⭐ Docker必須 | ExpertAgent → MyVault 認証 |
| `MYVAULT_TOKEN_MYSCHEDULER` | ⭐⭐ Docker必須 | MyScheduler → MyVault 認証 |
| `MYVAULT_TOKEN_JOBQUEUE` | ⭐⭐ Docker必須 | JobQueue → MyVault 認証 |
| `MYVAULT_TOKEN_COMMONUI` | ⭐⭐ Docker必須 | CommonUI → MyVault 認証 |
| `OPENAI_API_KEY` | ⭐ 任意 | OpenAI APIキー（MyVault経由も可） |
| `ANTHROPIC_API_KEY` | ⭐ 任意 | Anthropic APIキー（MyVault経由も可） |
| `GOOGLE_API_KEY` | ⭐ 任意 | Google APIキー（MyVault経由も可） |

### 環境変数で上書き可能なポート番号

| 変数名 | デフォルト値 (docker-compose) | デフォルト値 (quick-start.sh) |
|-------|------------------------------|------------------------------|
| `JOBQUEUE_PORT` | 8001 | 8101 |
| `MYSCHEDULER_PORT` | 8002 | 8102 |
| `MYVAULT_PORT` | 8003 | 8103 |
| `EXPERTAGENT_PORT` | 8004 | 8104 |
| `GRAPHAISERVER_PORT` | 8005 | 8105 |
| `COMMONUI_PORT` | 8501 | 8601 |
