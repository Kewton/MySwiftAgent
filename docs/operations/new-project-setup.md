# 新プロジェクトセットアップ手順書

**最終更新**: 2025-10-19
**対象**: Python、TypeScript/Node.js プロジェクト

---

## 📌 この手順書について

このドキュメントは、MySwiftAgentモノレポに新しいマイクロサービス・プロジェクトを追加する際の完全な手順書です。

### **必須確認事項**

- [ ] この手順書を**最初から最後まで**読んでから作業開始
- [ ] 作業計画書 (`work-plan.md`) にこの手順書への参照を明記
- [ ] 各Phase完了時に手順書の項目を確認

### **サポート対象言語**

- ✅ **Python** (FastAPI + uv)
- ✅ **TypeScript** (Express/Fastify + npm)

---

# 📦 新プロジェクト追加時の手順

MySwiftAgentはマルチプロジェクト対応のモノレポ構成を採用しており、新しいマイクロサービス・プロジェクトの追加は以下の手順で行います。

**対応言語**: Python、TypeScript/Node.js

## 📋 追加手順チェックリスト

### 1. **プロジェクト基盤の作成**

#### Python プロジェクトの場合

```bash
# 新プロジェクトディレクトリ作成
mkdir {project_name}
cd {project_name}

# 必須ファイルの作成
touch pyproject.toml
touch Dockerfile
mkdir -p app tests/unit tests/integration
```

**必須ファイル構成:**
```
{project_name}/
├── pyproject.toml          # プロジェクト設定・依存関係・バージョン
├── Dockerfile              # コンテナイメージ定義
├── app/                    # アプリケーションコード
│   ├── main.py            # FastAPIエントリーポイント
│   └── core/              # コア機能
├── tests/                  # テストコード
│   ├── unit/              # 単体テスト
│   ├── integration/       # 結合テスト
│   └── conftest.py        # テスト設定
└── README.md              # プロジェクト固有ドキュメント
```

#### TypeScript プロジェクトの場合

```bash
# 新プロジェクトディレクトリ作成
mkdir {project_name}
cd {project_name}

# 必須ファイルの作成
npm init -y
touch tsconfig.json
touch Dockerfile
mkdir -p src tests
```

**必須ファイル構成:**
```
{project_name}/
├── package.json           # プロジェクト設定・依存関係・バージョン
├── package-lock.json      # 依存関係ロックファイル
├── tsconfig.json          # TypeScript設定
├── Dockerfile             # コンテナイメージ定義
├── src/                   # ソースコード
│   ├── index.ts          # アプリケーションエントリーポイント
│   └── app.ts            # Express/Fastifyアプリケーション
├── tests/                 # テストコード
│   ├── unit/             # 単体テスト
│   └── integration/      # 結合テスト
├── dist/                  # ビルド出力（.gitignore対象）
└── README.md             # プロジェクト固有ドキュメント
```

### 2. **バージョン管理ファイルの設定**

#### Python: pyproject.toml の設定

```toml
[project]
name = "{project_name}"
version = "0.1.0"  # 初回リリース用バージョン
description = "プロジェクトの説明"
authors = [
    {name = "Your Name", email = "your.email@example.com"},
]
dependencies = [
    "fastapi>=0.100.0",
    "uvicorn>=0.23.0",
    # その他の依存関係
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
]

[tool.ruff]
target-version = "py312"
line-length = 88

[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
```

#### TypeScript: package.json の設定

```json
{
  "name": "{project_name}",
  "version": "0.1.0",
  "description": "プロジェクトの説明",
  "main": "dist/index.js",
  "scripts": {
    "build": "tsc",
    "start": "node dist/index.js",
    "dev": "ts-node src/index.ts",
    "test": "jest",
    "lint": "eslint src/**/*.ts",
    "type-check": "tsc --noEmit"
  },
  "keywords": [],
  "author": "Your Name <your.email@example.com>",
  "license": "MIT",
  "dependencies": {
    "express": "^4.18.0"
  },
  "devDependencies": {
    "@types/express": "^4.17.0",
    "@types/node": "^20.0.0",
    "@typescript-eslint/eslint-plugin": "^6.0.0",
    "@typescript-eslint/parser": "^6.0.0",
    "eslint": "^8.0.0",
    "jest": "^29.0.0",
    "ts-jest": "^29.0.0",
    "ts-node": "^10.0.0",
    "typescript": "^5.0.0"
  }
}
```

**tsconfig.json の設定:**
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "tests"]
}
```

### 3. **CI/CD設定への追加**

#### 3.1 multi-release.yml ワークフローの更新

**🎉 自動言語検出対応**

`multi-release.yml` は **Python と TypeScript の両方に自動対応** しています。以下の検出ロジックで動作します：

- **Python プロジェクト**: `pyproject.toml` の存在で検出
- **TypeScript プロジェクト**: `package.json` の存在で検出

**変更が必要な箇所:**

プロジェクト検出リストに新プロジェクトを追加（行395付近）:

```yaml
# Multi-project format: release/multi/vYYYY.MM.DD or vX.Y.Z
if [[ $BRANCH_NAME =~ ^release/multi/v(.+)$ ]]; then
  # Detect changed projects from git diff
  CHANGED_PROJECTS=""
  for project in myscheduler jobqueue docs commonUI {project_name}; do  # ← 新プロジェクト追加
    # Check if project has version file (pyproject.toml or package.json)
    if ([[ -f "$project/pyproject.toml" ]] || [[ -f "$project/package.json" ]]) && git diff HEAD~1 HEAD --name-only | grep -q "^$project/"; then
```

**バージョン管理ファイル対応:**
- **Python**: `pyproject.toml` の `version = "X.Y.Z"` 行を自動更新
- **TypeScript**: `package.json` の `"version": "X.Y.Z"` フィールドを jq で自動更新

**テスト・ビルドコマンド自動切替:**
| 言語 | Linting | Type Check | Tests | Build |
|------|---------|-----------|-------|-------|
| **Python** | `uv run ruff check .` | `uv run mypy app/` | `uv run pytest` | `uv build` |
| **TypeScript** | `npm run lint` | `npm run type-check` または `npx tsc --noEmit` | `npm test` | `npm run build` |

#### 3.2 他のワークフローファイルの更新確認

以下のワークフローが新プロジェクトに対応するか確認・更新：
- `ci-feature.yml`
- `cd-develop.yml`
- `ci-main.yml`

### 4. **Dockerfileの作成**

#### Python プロジェクト用 Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --no-dev

# Copy application code
COPY app/ ./app/

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### TypeScript プロジェクト用 Dockerfile（Multi-stage build）

```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency files
COPY package*.json ./
COPY tsconfig.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY src/ ./src/

# Build TypeScript
RUN npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

# Copy only production dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy built application
COPY --from=builder /app/dist ./dist

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["node", "dist/index.js"]
```

### 5. **基本APIエンドポイントの実装**

#### Python (FastAPI) 実装例

**`app/main.py`**:
```python
from fastapi import FastAPI

app = FastAPI(
    title="{project_name}",
    version="0.1.0",
    description="プロジェクトの説明"
)

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント（CI/CDで使用）"""
    return {"status": "healthy", "service": "{project_name}"}

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {"message": "Welcome to {project_name}"}

@app.get("/api/v1/")
async def api_root():
    """API v1 ルート"""
    return {"version": "1.0", "service": "{project_name}"}
```

#### TypeScript (Express) 実装例

**`src/app.ts`**:
```typescript
import express, { Request, Response } from 'express';

const app = express();

app.use(express.json());

// Health check endpoint (required for CI/CD)
app.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'healthy', service: '{project_name}' });
});

// Root endpoint
app.get('/', (req: Request, res: Response) => {
  res.json({ message: 'Welcome to {project_name}' });
});

// API v1 root
app.get('/api/v1/', (req: Request, res: Response) => {
  res.json({ version: '1.0', service: '{project_name}' });
});

export default app;
```

**`src/index.ts`**:
```typescript
import app from './app';

const PORT = process.env.PORT || 8000;

app.listen(PORT, () => {
  console.log(`🚀 Server is running on port ${PORT}`);
});
```

### 6. **テスト環境の設定**

#### Python テストの設定

**`tests/conftest.py`**:
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)
```

**`tests/integration/test_api.py`**:
```python
def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "{project_name}"}

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
```

#### TypeScript テストの設定

**`tests/integration/app.test.ts`**:
```typescript
import request from 'supertest';
import app from '../../src/app';

describe('API Endpoints', () => {
  describe('GET /health', () => {
    it('should return health status', async () => {
      const response = await request(app).get('/health');
      expect(response.status).toBe(200);
      expect(response.body).toEqual({
        status: 'healthy',
        service: '{project_name}'
      });
    });
  });

  describe('GET /', () => {
    it('should return welcome message', async () => {
      const response = await request(app).get('/');
      expect(response.status).toBe(200);
      expect(response.body.message).toBeDefined();
    });
  });
});
```

**jest.config.js**:
```javascript
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/tests'],
  testMatch: ['**/*.test.ts'],
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.d.ts'
  ]
};
```

**必須追加パッケージ:**
```bash
npm install --save-dev supertest @types/supertest jest ts-jest
```

### 7. **初回リリースの実行**

#### Python プロジェクトの場合

```bash
# 1. 開発ブランチから作業開始
git checkout develop
git pull origin develop

# 2. 新プロジェクト用feature/vibe ブランチ作成
git checkout -b feature/{project_name}-initial-setup

# 3. ファイル追加・コミット
git add {project_name}/
git commit -m "feat({project_name}): add initial Python project structure

- Add pyproject.toml with basic dependencies
- Add FastAPI application with health check
- Add Docker configuration
- Add test structure and basic tests
- Add CI/CD integration

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 4. プッシュしてPR作成
git push origin feature/{project_name}-initial-setup

# 5. developブランチへのPR作成（featureラベル付与）
gh pr create \
  --title "🎉 Add new Python project: {project_name}" \
  --body "初回Pythonプロジェクト追加..." \
  --base develop \
  --label feature
```

#### TypeScript プロジェクトの場合

```bash
# 1. 開発ブランチから作業開始
git checkout develop
git pull origin develop

# 2. 新プロジェクト用feature/vibe ブランチ作成
git checkout -b feature/{project_name}-initial-setup

# 3. ファイル追加・コミット
git add {project_name}/
git commit -m "feat({project_name}): add initial TypeScript project structure

- Add package.json with basic dependencies
- Add Express application with health check
- Add TypeScript configuration
- Add Docker configuration (multi-stage build)
- Add test structure with Jest and Supertest
- Add CI/CD integration

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 4. プッシュしてPR作成
git push origin feature/{project_name}-initial-setup

# 5. developブランチへのPR作成（featureラベル付与）
gh pr create \
  --title "🎉 Add new TypeScript project: {project_name}" \
  --body "初回TypeScriptプロジェクト追加..." \
  --base develop \
  --label feature
```

### 8. **リリースワークフローの実行**

```bash
# developマージ後、リリースワークフロー実行
gh workflow run multi-release.yml \
  -f projects={project_name} \
  -f release_type=minor \
  -f custom_version="0.1.0"

# または手動でリリースブランチ作成
git checkout develop
git pull origin develop
git checkout -b release/{project_name}/v0.1.0
git push origin release/{project_name}/v0.1.0
```

## 📊 マルチプロジェクト対応状況

### 現在のプロジェクト一覧

| プロジェクト | 目的 | 技術スタック | リリース状況 |
|-------------|------|-------------|-------------|
| `myscheduler` | ジョブスケジューリング | FastAPI + APScheduler + SQLAlchemy | ✅ 本番運用中 |
| `jobqueue` | ジョブキュー管理 | FastAPI + Redis/PostgreSQL | 🚀 初回リリース準備中 |
| `docs` | プロジェクトドキュメント | Markdown + 静的サイトジェネレータ | 📝 軽量ワークフロー対応 |

### プロジェクト追加時のCI/CD更新箇所

- **`.github/workflows/multi-release.yml`**: workflow_dispatch inputsとジョブ条件
- **`.github/workflows/ci-feature.yml`**: フィーチャーブランチ用品質チェック（docs/** パス除外設定済み）
- **`.github/workflows/cd-develop.yml`**: 開発統合用テスト（docs/** パス除外設定済み）
- **`.github/workflows/ci-main.yml`**: 本番品質チェック（docs/** パス除外設定済み）
- **`.github/workflows/hotfix.yml`**: 緊急修正ワークフロー（docs変更時は軽量実行）
- **`.github/workflows/docs.yml`**: **🆕 ドキュメント専用軽量ワークフロー**
- **`.github/DEPLOYMENT.md`**: プロジェクト一覧表とリリース手順

### 📝 ドキュメントプロジェクト専用の最適化

**docs プロジェクト** は他のアプリケーションプロジェクトと異なり、以下の最適化が実装されています：

#### **軽量ワークフロー分離**
- **専用ワークフロー**: `.github/workflows/docs.yml`
- **処理内容**: Markdownlinting、構造検証、静的サイト生成のみ
- **除外処理**: Docker、Python依存関係、セキュリティスキャンは実行しない

#### **パス除外設定**
他の重いワークフローから `docs/**` パスを除外：
```yaml
paths:
  - 'myscheduler/**'
  - 'jobqueue/**'
  - '.github/workflows/**'
  # docs changes are handled by separate docs workflow
  - '!docs/**'
```

#### **バージョン管理対応**
- **リリースブランチ**: `release/docs/vX.Y.Z` 形式をサポート
- **pyproject.toml**: 存在しない場合は軽量版を自動生成
- **専用バリデーション**: multi-release.ymlでdocs専用の軽量チェックを実行

## 🔧 新プロジェクト追加後の品質チェック

### Python プロジェクトの品質チェック

```bash
# 新プロジェクトのローカル検証
cd {project_name}

# 1. 依存関係インストール
uv sync --extra dev

# 2. 品質チェック実行
uv run ruff check .
uv run ruff format . --check
uv run mypy app/

# 3. テスト実行
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -v

# 4. アプリケーション起動テスト
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# 5. ヘルスチェック
curl -f http://localhost:8000/health
```

### TypeScript プロジェクトの品質チェック

```bash
# 新プロジェクトのローカル検証
cd {project_name}

# 1. 依存関係インストール
npm ci

# 2. 品質チェック実行
npm run lint
npm run type-check

# 3. テスト実行
npm test

# 4. ビルド検証
npm run build

# 5. アプリケーション起動テスト
npm start &
sleep 5

# 6. ヘルスチェック
curl -f http://localhost:8000/health

# 7. プロセス停止
pkill -f "node dist/index.js"
```

## ⚠️ 注意事項

1. **リリースブランチ命名**: 必ず `release/{project_name}/vX.Y.Z` 形式を使用
2. **初回バージョン**: 新プロジェクトは `0.1.0` から開始することを推奨
3. **CI/CD設定**: validate-releaseジョブのプロジェクトリスト（行395付近）への新プロジェクト追加が必須
4. **依存関係管理**:
   - **Python**: `uv`を使用し、`pyproject.toml`で一元管理
   - **TypeScript**: `npm`を使用し、`package.json`で一元管理
5. **Docker対応**: リリースフローではDockerイメージビルド・テストが必須
6. **API規約**: ヘルスチェック（`/health`）とルートエンドポイント（`/`、`/api/v1/`）は実装必須（両言語共通）
7. **必須npmスクリプト（TypeScript）**: `build`, `test`, `lint`, `type-check` は package.json に定義必須
8. **バージョンファイル**: Python は `pyproject.toml`、TypeScript は `package.json` にバージョン記載必須
