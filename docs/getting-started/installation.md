# インストールガイド

MySwiftAgentの詳細なインストール手順です。

## 必要な環境

### 必須ソフトウェア

| ソフトウェア | バージョン | 用途 |
|-------------|----------|------|
| Docker Desktop | 4.0+ | コンテナ実行環境 |
| Git | 2.30+ | ソースコード管理 |

### 推奨ソフトウェア（ローカル開発時）

| ソフトウェア | バージョン | 用途 |
|-------------|----------|------|
| Python | 3.11+ | バックエンドサービス |
| Node.js | 20+ | フロントエンド・TypeScriptサービス |
| uv | 最新 | Python パッケージ管理 |

## インストール手順

### 1. リポジトリのクローン

```bash
git clone https://github.com/your-org/MySwiftAgent.git
cd MySwiftAgent
```

### 2. 環境変数の設定

```bash
cp .env.example .env
```

必須の環境変数を設定：

```bash
# LLM API キー（いずれか1つ）
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# Langfuse（オプション、Observability用）
LANGFUSE_SECRET_KEY=your-langfuse-secret
LANGFUSE_PUBLIC_KEY=your-langfuse-public
LANGFUSE_HOST=http://localhost:3001
```

詳細は [環境変数一覧](../reference/environment-variables.md) を参照。

### 3. 依存関係のインストール

#### Python プロジェクト

```bash
# expertAgent
cd expertAgent && uv sync && cd ..

# jobqueue
cd jobqueue && uv sync && cd ..

# myVault
cd myVault && uv sync && cd ..

# myscheduler
cd myscheduler && uv sync && cd ..
```

#### TypeScript プロジェクト

```bash
# mySwiftAgentCore
cd mySwiftAgentCore && npm install && cd ..

# graphAiServer
cd graphAiServer && npm install && cd ..

# myAgentDesk
cd myAgentDesk && npm install && cd ..
```

### 4. データベースの初期化

```bash
# myVault のデータベース作成
cd myVault && uv run alembic upgrade head && cd ..

# jobqueue のデータベース作成
cd jobqueue && uv run alembic upgrade head && cd ..
```

## 起動方法

### Docker（推奨）

```bash
make dev-all
```

### ハイブリッド（Agent層をローカルで開発）

```bash
./scripts/dev-hybrid.sh
```

### 全ローカル

```bash
./scripts/dev-start.sh
```

詳細は [ローカル開発環境](../operations/local-development.md) を参照。

## 動作確認

```bash
# 全サービスのヘルスチェック
./scripts/health-check.sh

# 個別サービスの確認
curl http://localhost:8001/health  # JobQueue
curl http://localhost:8003/health  # MyVault
curl http://localhost:8004/health  # ExpertAgent
```

## トラブルシューティング

### ポートが使用中

```bash
# 使用中のポートを確認
lsof -i :8001

# Docker コンテナを停止
make down
```

### 依存関係エラー

```bash
# Python 依存関係の再インストール
uv sync --reinstall

# Node.js 依存関係の再インストール
rm -rf node_modules && npm install
```

詳細は [トラブルシューティング](../operations/troubleshooting.md) を参照。

---

**次のステップ**: [初めてのワークフロー](./first-workflow.md)
