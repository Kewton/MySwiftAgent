# 設定ファイル

MySwiftAgentの設定ファイル構成と設定方法です。

## 設定ファイル一覧

| ファイル | 場所 | 用途 |
|---------|------|------|
| `.env` | プロジェクトルート | 環境変数（ローカル開発用） |
| `docker-compose.yml` | プロジェクトルート | Docker構成 |
| `pyproject.toml` | 各Pythonプロジェクト | Python依存関係・ツール設定 |
| `package.json` | 各TypeScriptプロジェクト | Node.js依存関係 |
| `tsconfig.json` | 各TypeScriptプロジェクト | TypeScript設定 |

## 環境変数ファイル (.env)

### 基本構成

```bash
# LLM API キー
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# サービスポート
JOBQUEUE_PORT=8001
MYSCHEDULER_PORT=8002
MYVAULT_PORT=8003
EXPERTAGENT_PORT=8004
GRAPHAISERVER_PORT=8005

# データベース
DATABASE_URL=sqlite:///./data/app.db

# Langfuse（Observability）
LANGFUSE_SECRET_KEY=your-langfuse-secret
LANGFUSE_PUBLIC_KEY=your-langfuse-public
LANGFUSE_HOST=http://localhost:3001
```

詳細は [環境変数一覧](./environment-variables.md) を参照。

## Docker Compose 設定

### サービス定義

```yaml
version: '3.8'
services:
  jobqueue:
    build: ./jobqueue
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=sqlite:///./data/app.db
    volumes:
      - ./jobqueue/data:/app/data
    depends_on:
      - valkey

  expertagent:
    build: ./expertAgent
    ports:
      - "8004:8004"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - MYVAULT_URL=http://myvault:8003
    depends_on:
      - myvault

  # ... 他のサービス
```

### ボリューム構成

| ボリューム | マウント先 | 用途 |
|-----------|----------|------|
| `./jobqueue/data` | `/app/data` | JobQueueデータベース |
| `./myVault/data` | `/app/data` | MyVaultデータベース |
| `./valkey/data` | `/data` | Valkeyデータ永続化 |

## Python プロジェクト設定 (pyproject.toml)

### 基本構成

```toml
[project]
name = "expertAgent"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.100.0",
    "uvicorn>=0.23.0",
    "langchain>=0.1.0",
    "langgraph>=0.0.20",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
]

[tool.ruff]
line-length = 120
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "W"]

[tool.mypy]
python_version = "3.11"
strict = true
```

## TypeScript プロジェクト設定

### tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "outDir": "./dist"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

### package.json (scripts)

```json
{
  "scripts": {
    "dev": "vite dev",
    "build": "vite build",
    "test": "vitest",
    "lint": "eslint .",
    "format": "prettier --write ."
  }
}
```

## ワークフロー設定

### TaskFlow 設定ディレクトリ

```
mySwiftAgentCore/
├── config/
│   └── taskflows/
│       └── {project_name}/
│           └── {workflow_name}.json
└── generated/
    └── workflows/
        └── {project_name}/
            └── {workflow_name}/
                └── {workflow_name}.json
```

### GraphAI 設定ディレクトリ

```
graphAiServer/
└── config/
    └── graphai/
        └── {project_name}/
            └── {workflow_name}.yml
```

## 設定の優先順位

1. **環境変数** - 最優先
2. **`.env` ファイル** - ローカル開発用
3. **Docker Compose環境変数** - コンテナ環境
4. **デフォルト値** - コード内定義

## 次のステップ

- [環境変数一覧](./environment-variables.md) - 全環境変数の詳細
- [TaskFlow形式仕様](./taskflow-format.md) - ワークフロー定義
- [デプロイガイド](../operations/deployment.md) - 本番環境設定

---

**関連ドキュメント**:
- [クイックスタート](../getting-started/quick-start.md)
- [ローカル開発環境](../operations/local-development.md)
