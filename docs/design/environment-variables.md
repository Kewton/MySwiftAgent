# MySwiftAgent 環境変数管理ポリシー

## 🎯 新ポリシー概要

MySwiftAgentは、環境変数管理を**シンプル化**し、**MyVault中心**の設計に移行しました。

### 基本方針

```
✅ ローカル開発: 各プロジェクトディレクトリ直下の .env を使用
✅ Docker Compose: プロジェクトルートの .env.docker を使用
✅ .env で管理する項目は最小限（ポート番号、MyVault接続情報のみ）
✅ API Keys などのシークレットは MyVault で一元管理
✅ サービス間URLは起動スクリプト/docker-composeが自動設定（手動設定不要）
```

### 旧ポリシーとの違い

| 項目 | 旧ポリシー | 新ポリシー |
|------|----------|----------|
| **環境変数ファイル配置** | プロジェクトルート（`.env`, `.env.docker`, `.env.local`） | **ローカル開発**: 各プロジェクトディレクトリ（`{project}/.env`）<br>**Docker Compose**: プロジェクトルート（`.env.docker`） |
| **ファイル数** | 3つ（用途別） | 2種類（ローカル用+Docker用） |
| **API Keys管理** | .envファイル | MyVault（暗号化保存） |
| **サービス間URL設定** | 手動設定必須 | 起動スクリプト/docker-composeが自動設定 |
| **ポート競合対策** | .env.local作成 | 起動スクリプトが自動切替 |

---

## 📁 ファイル配置

### 新しい構成

```
MySwiftAgent/
├── .env.docker           # Docker Compose用環境変数（必須）
├── expertAgent/
│   ├── .env              # ローカル開発用（ExpertAgent固有設定）
│   └── .env.example      # テンプレート
├── myscheduler/
│   ├── .env              # ローカル開発用（MyScheduler固有設定）
│   └── .env.example
├── jobqueue/
│   ├── .env              # ローカル開発用（JobQueue固有設定）
│   └── .env.example
├── myVault/
│   ├── .env              # ローカル開発用（MyVault固有設定）
│   └── .env.example
├── graphAiServer/
│   ├── .env              # ローカル開発用（GraphAiServer固有設定）
│   └── .env.example
└── commonUI/
    ├── .env              # ローカル開発用（CommonUI固有設定）
    └── .env.example
```

### ⚠️ 削除されたファイル

以下のファイルは**不要**になりました：

- ❌ `MySwiftAgent/.env` (プロジェクトルート)
- ❌ `MySwiftAgent/.env.local`

---

## 🔧 各プロジェクトの .env 設定

### 共通設定項目（全プロジェクト）

```bash
# ===== ポート設定 =====
# Docker Compose: コンテナ内は常に8000（8501 for CommonUI）
# ローカル開発: quick-start.shが自動設定（8101-8105, 8601）
PORT=8000

# ===== ログ設定 =====
LOG_LEVEL=INFO

# ===== MyVault統合（シークレット管理） =====
MYVAULT_ENABLED=true
# MYVAULT_BASE_URL は起動スクリプトが自動設定するため記載不要
MYVAULT_SERVICE_NAME={service_name}
MYVAULT_SERVICE_TOKEN={unique_token}
MYVAULT_DEFAULT_PROJECT={service_name}
```

---

## 📋 プロジェクト別 .env 設定例

### 1. JobQueue (`jobqueue/.env`)

```bash
# ポート設定
PORT=8000

# ログ設定
LOG_LEVEL=INFO

# MyVault統合（将来対応）
MYVAULT_ENABLED=false
```

**説明**:
- JobQueueは現在MyVault統合なし（将来対応予定）
- データベースURL (`JOBQUEUE_DB_URL`) はdocker-compose.ymlで設定

---

### 2. MyScheduler (`myscheduler/.env`)

```bash
# ポート設定
PORT=8000

# ログ設定
LOG_LEVEL=INFO

# データベース設定
DATABASE_URL=sqlite:///./data/jobs.db

# MyVault統合（将来対応）
MYVAULT_ENABLED=false
```

**説明**:
- JobQueue URLは起動スクリプトが自動設定（`JOBQUEUE_API_URL`）
- ローカル開発: `http://localhost:8101`
- Docker: `http://jobqueue:8000`

---

### 3. MyVault (`myVault/.env`)

```bash
# ポート設定
PORT=8000

# ログ設定
LOG_LEVEL=INFO

# データベース設定
DATABASE_URL=sqlite:///./data/myvault.db

# ===== マスター暗号化キー（必須） =====
MSA_MASTER_KEY=base64:Rup6PTJHFJybCSG0sY9a/wtT/wNoEWlu1MfV6nCdhr8=

# ===== サービス認証トークン（必須） =====
# 各サービスからのアクセスを認証するためのトークン
TOKEN_expertagent=wBZrUftRV6_MsCj8iVXb-uc60-A95HqyuESL2tVFGQ4
TOKEN_myscheduler=7aYvsd5dqgMn3C3wHd4l8mODfOxLMlRRKY10bVZkOqg
TOKEN_jobqueue=4sxKa7mXfXAosr7ZJcryeOwnjUEbHzLRqvtZF3qFEn0
TOKEN_commonui=L8Z7mbEqJLHITqXn6SnOBOYZnmnfnSpC8Lebetpvmu8
```

**トークン生成方法**:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**マスターキー生成方法**:
```bash
python3 -c "import base64, os; print('base64:' + base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

---

### 4. ExpertAgent (`expertAgent/.env`)

```bash
# ポート設定
PORT=8000

# ログ設定
LOG_LEVEL=INFO
LOG_DIR=/app/logs

# ===== MyVault統合（優先） =====
MYVAULT_ENABLED=true
# MYVAULT_BASE_URL は起動スクリプトが自動設定
MYVAULT_SERVICE_NAME=expertagent
MYVAULT_SERVICE_TOKEN=wBZrUftRV6_MsCj8iVXb-uc60-A95HqyuESL2tVFGQ4
MYVAULT_DEFAULT_PROJECT=expertagent

# ===== Ollama設定（ローカルLLM） =====
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_DEF_SMALL_MODEL=gemma3:27b-it-q8_0

# ===== モデル設定 =====
GRAPH_AGENT_MODEL=gemini-2.5-flash
PODCAST_SCRIPT_DEFAULT_MODEL=gpt-4o-mini
EXTRACT_KNOWLEDGE_MODEL=gemma3:27b-it-q8_0

# ===== MLX LLM Server（Macのみ） =====
MLX_LLM_SERVER_URL=http://host.docker.internal:8080

# ===== その他 =====
SPREADSHEET_ID=
MAIL_TO=
```

**重要**:
- API Keys（OpenAI, Anthropic, Google等）は**MyVaultで管理**するため、.envには記載しません。
- Google APIs認証情報（`GOOGLE_CREDENTIALS_JSON`, `GOOGLE_TOKEN_JSON`）も**MyVaultで管理**します（JSONファイルの中身を文字列として保存）

---

### 5. GraphAiServer (`graphAiServer/.env`)

```bash
# ポート設定
PORT=8000

# Node.js環境
NODE_ENV=production

# GraphAI設定
MODEL_BASE_PATH=/app/config/graphai/

# ===== MyVault統合（将来対応） =====
# 現在はAPI KeysをMyVaultで管理する予定
MYVAULT_ENABLED=false
```

**注意**: 現在はAPI KeysをプロジェクトルートのMyVaultで管理しています。

---

### 6. CommonUI (`commonUI/.env`)

```bash
# ポート設定
PORT=8501

# ログ設定
LOG_LEVEL=INFO

# ===== MyVault統合 =====
MYVAULT_ENABLED=true
# MYVAULT_BASE_URL は起動スクリプトが自動設定
MYVAULT_SERVICE_NAME=commonui
MYVAULT_SERVICE_TOKEN=L8Z7mbEqJLHITqXn6SnOBOYZnmnfnSpC8Lebetpvmu8

# ===== CommonUI設定 =====
POLLING_INTERVAL=5
DEFAULT_SERVICE=JobQueue
OPERATION_MODE=full
```

**説明**:
- サービスURL（`JOBQUEUE_BASE_URL`等）は起動スクリプトが自動設定
- 認証トークン（`JOBQUEUE_API_TOKEN`等）も自動生成

---

## 🚀 起動モード別の動作

### 1. Docker Compose モード

**ポート設定**:

| サービス | ホストポート | コンテナポート | アクセスURL |
|---------|------------|--------------|------------|
| JobQueue | 8001 | 8000 | `http://localhost:8001` |
| MyScheduler | 8002 | 8000 | `http://localhost:8002` |
| MyVault | 8003 | 8000 | `http://localhost:8003` |
| ExpertAgent | 8004 | 8000 | `http://localhost:8004` |
| GraphAiServer | 8005 | 8000 | `http://localhost:8005` |
| CommonUI | 8501 | 8501 | `http://localhost:8501` |

**環境変数の読み込み**:
```yaml
# docker-compose.yml
services:
  jobqueue:
    env_file:
      - .env.docker        # プロジェクトルートの .env.docker を読み込み
    environment:
      - PORT=8000          # コンテナ内ポート（固定）
      - LOG_LEVEL=${LOG_LEVEL:-INFO}  # .env.dockerから変数参照
```

**.env.docker の内容例**:
```bash
# MyVault設定
MSA_MASTER_KEY=base64:your_master_key
MYVAULT_TOKEN_EXPERTAGENT=your_token
MYVAULT_TOKEN_MYSCHEDULER=your_token
MYVAULT_TOKEN_JOBQUEUE=your_token
MYVAULT_TOKEN_COMMONUI=your_token

# Admin認証
EXPERTAGENT_ADMIN_TOKEN=your_admin_token
GRAPHAISERVER_ADMIN_TOKEN=your_admin_token

# ログ設定
LOG_LEVEL=INFO
```

**サービス間通信**:
- 内部DNS名を使用（例: `http://jobqueue:8000`）
- `MYVAULT_BASE_URL=http://myvault:8000` をdocker-compose.ymlで設定

---

### 2. ローカル開発モード (quick-start.sh)

**ポート設定** (ポート競合回避):

| サービス | ポート番号 | アクセスURL |
|---------|----------|------------|
| JobQueue | 8101 | `http://localhost:8101` |
| MyScheduler | 8102 | `http://localhost:8102` |
| MyVault | 8103 | `http://localhost:8103` |
| ExpertAgent | 8104 | `http://localhost:8104` |
| GraphAiServer | 8105 | `http://localhost:8105` |
| CommonUI | 8601 | `http://localhost:8601` |

**環境変数の読み込み**:
```bash
# quick-start.sh が各プロジェクトの .env を読み込み
source expertAgent/.env
source myscheduler/.env
# ...

# ポート番号を自動上書き
export JOBQUEUE_PORT=8101
export MYSCHEDULER_PORT=8102
# ...

# サービスURLを自動設定
export MYVAULT_BASE_URL=http://localhost:8103
export JOBQUEUE_API_URL=http://localhost:8101
# ...
```

---

## 🔐 MyVault統合によるシークレット管理

### MyVaultで管理するシークレット

以下のシークレットは**MyVaultで暗号化保存**し、.envファイルには記載しません：

| シークレット名 | 用途 | 設定場所 |
|-------------|------|---------|
| `OPENAI_API_KEY` | OpenAI API | MyVault (expertagent プロジェクト) |
| `ANTHROPIC_API_KEY` | Anthropic API | MyVault (expertagent プロジェクト) |
| `GOOGLE_API_KEY` | Google API | MyVault (expertagent プロジェクト) |
| `SERPER_API_KEY` | Serper検索API | MyVault (expertagent プロジェクト) |
| `GOOGLE_CREDENTIALS_JSON` | Google APIs認証情報（credentials.json） | MyVault (各プロジェクト) |
| `GOOGLE_TOKEN_JSON` | Google APIs トークン（token.json） | MyVault (各プロジェクト) |

### MyVault認証フロー

```
1. ExpertAgent起動
   ↓
2. expertAgent/.env から MYVAULT_SERVICE_TOKEN を読み込み
   ↓
3. MYVAULT_BASE_URL (起動スクリプトが設定) にアクセス
   ↓
4. TOKEN認証成功
   ↓
5. MyVaultからAPI Keysを取得（暗号化解除）
   ↓
6. メモリ上で使用（ディスクに保存しない）
```

---

## 🛠️ 初回セットアップ手順

### 1. 各プロジェクトの .env 作成

```bash
# プロジェクトルートで実行
for project in jobqueue myscheduler myVault expertAgent graphAiServer commonUI; do
    if [ -f "$project/.env.example" ]; then
        cp "$project/.env.example" "$project/.env"
        echo "✅ Created $project/.env"
    fi
done
```

### 2. MyVault認証トークンの生成・設定

```bash
# トークン生成スクリプト
cat > generate_tokens.sh << 'EOF'
#!/bin/bash
echo "# MyVault Service Tokens"
for service in expertagent myscheduler jobqueue commonui; do
    token=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    echo "TOKEN_$service=$token"
done
EOF

chmod +x generate_tokens.sh
./generate_tokens.sh

# 出力結果を myVault/.env に追記
./generate_tokens.sh >> myVault/.env
```

### 3. マスター暗号化キーの生成

```bash
# myVault/.env に追加
python3 -c "import base64, os; print('MSA_MASTER_KEY=base64:' + base64.urlsafe_b64encode(os.urandom(32)).decode())" >> myVault/.env
```

### 4. ExpertAgentにMyVault認証トークンを設定

```bash
# expertAgent/.env にトークンをコピー
EXPERTAGENT_TOKEN=$(grep "TOKEN_expertagent" myVault/.env | cut -d'=' -f2)
echo "MYVAULT_SERVICE_TOKEN=$EXPERTAGENT_TOKEN" >> expertAgent/.env

# 同様に他のサービスにも設定
# （現在はExpertAgentのみMyVault統合済み）
```

---

## 🎯 環境変数の優先順位

起動スクリプトによる環境変数設定の優先順位：

```
1. 起動スクリプトが設定する環境変数（最優先）
   - ポート番号（JOBQUEUE_PORT=8101 等）
   - サービス間URL（MYVAULT_BASE_URL 等）

2. 各プロジェクトの .env ファイル
   - MyVault認証トークン
   - モデル設定
   - その他カスタム設定

3. コード内のデフォルト値（最終フォールバック）
   - PORT=8000
   - LOG_LEVEL=INFO
```

---

## 📊 設定項目の一覧表

### 最小限の設定項目

| 項目 | 設定場所 | 必須/任意 | 説明 |
|------|---------|----------|------|
| **PORT** | 各プロジェクト/.env | 任意 | サービスポート（起動スクリプトが上書き） |
| **LOG_LEVEL** | 各プロジェクト/.env | 任意 | ログレベル（デフォルト: INFO） |
| **MSA_MASTER_KEY** | myVault/.env | **必須** | マスター暗号化キー |
| **TOKEN_{service}** | myVault/.env | **必須** | サービス認証トークン |
| **MYVAULT_SERVICE_TOKEN** | expertAgent/.env | **必須** | ExpertAgent→MyVault認証 |

### 削除された設定項目

以下の項目は**起動スクリプトが自動設定**するため、.envには記載不要：

- ❌ `JOBQUEUE_BASE_URL`
- ❌ `MYSCHEDULER_BASE_URL`
- ❌ `MYVAULT_BASE_URL`
- ❌ `EXPERTAGENT_BASE_URL`
- ❌ `GRAPHAISERVER_BASE_URL`
- ❌ `JOBQUEUE_API_URL`
- ❌ `JOBQUEUE_API_TOKEN` (dev環境では自動生成)
- ❌ `MYSCHEDULER_API_TOKEN` (dev環境では自動生成)

### MyVault管理に移行した項目

以下のシークレットは**.envから削除**し、MyVaultで管理：

**API Keys:**
- ❌ `OPENAI_API_KEY`
- ❌ `ANTHROPIC_API_KEY`
- ❌ `GOOGLE_API_KEY`
- ❌ `SERPER_API_KEY`

**Google APIs認証情報（JSON文字列として保存）:**
- ❌ `GOOGLE_CREDENTIALS_JSON` - credentials.jsonファイルの中身
- ❌ `GOOGLE_TOKEN_JSON` - token.jsonファイルの中身

**注意**:
- 従来は`GOOGLE_APIS_TOKEN_PATH`と`GOOGLE_APIS_CREDENTIALS_PATH`でファイルパスを管理していましたが、現在はJSONの中身を直接MyVaultで管理します。
- これにより、ファイルシステムへの依存がなくなり、よりセキュアな管理が可能になります。

---

## 🛠️ トラブルシューティング

### エラー: "MYVAULT_SERVICE_TOKEN not set"

**原因**: expertAgent/.env にMyVault認証トークンが未設定

**解決策**:
```bash
# myVault/.env からトークンを取得
EXPERTAGENT_TOKEN=$(grep "TOKEN_expertagent" myVault/.env | cut -d'=' -f2)

# expertAgent/.env に設定
echo "MYVAULT_SERVICE_TOKEN=$EXPERTAGENT_TOKEN" >> expertAgent/.env
```

---

### エラー: "MSA_MASTER_KEY not set"

**原因**: myVault/.env にマスターキーが未設定

**解決策**:
```bash
python3 -c "import base64, os; print('MSA_MASTER_KEY=base64:' + base64.urlsafe_b64encode(os.urandom(32)).decode())" >> myVault/.env
```

---

### エラー: "Connection refused" (ポート競合)

**原因**: Docker Composeとローカル開発が同じポートを使用

**解決策**:
```bash
# Docker Compose停止
docker-compose down

# quick-start.shを使用（自動的に8101-8105に切替）
./scripts/quick-start.sh
```

---

### エラー: "API Key not found in MyVault"

**原因**: MyVaultにAPI Keysが登録されていない

**解決策**:
1. CommonUIのSecretsタブを開く
2. プロジェクト選択: `expertagent` (または使用するプロジェクト)
3. 以下のシークレットを登録:
   - `OPENAI_API_KEY`: `sk-proj-...`
   - `ANTHROPIC_API_KEY`: `sk-ant-api03-...`
   - `GOOGLE_API_KEY`: `AIzaSy...`
   - `SERPER_API_KEY`: `aff8257f...`

---

### Google APIs認証情報の設定

**Google APIsを使用するための認証情報設定**:

1. **credentials.jsonの登録**:
   - CommonUIのSecretsタブを開く
   - プロジェクト選択（例: `default_project`）
   - シークレット名: `GOOGLE_CREDENTIALS_JSON`
   - 値: credentials.jsonファイルの中身（JSON文字列）を貼り付け

2. **token.jsonの登録（初回認証後）**:
   - 初回のOAuth認証後、token.jsonが生成されます
   - シークレット名: `GOOGLE_TOKEN_JSON`
   - 値: token.jsonファイルの中身（JSON文字列）を貼り付け
   - これにより、次回起動時から自動的に認証が行われます

**注意**:
- 従来のファイルベース管理（`GOOGLE_APIS_TOKEN_PATH`, `GOOGLE_APIS_CREDENTIALS_PATH`）は非推奨です
- JSONの中身を直接MyVaultで管理することで、ファイルシステムへの依存を排除できます

---

## 📚 関連ドキュメント

- [アーキテクチャ概要](./architecture-overview.md)
- [MyVault統合ポリシー](./myvault-integration.md)
- [開発ガイド](../../CLAUDE.md)
- [デプロイメント手順](../../.github/DEPLOYMENT.md)

---

最終更新: 2025-10-10
