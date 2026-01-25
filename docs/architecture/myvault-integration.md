# MyVault 統合規約

**バージョン:** 1.0.0
**最終更新日:** 2025-10-10
**ステータス:** 有効

---

## 📋 概要

本ドキュメントは、MySwiftAgentの全サービスにおけるMyVault統合の標準規約を定義します。MyVaultは以下の機能を提供する集中型シークレット管理サービスです:

- 🔒 **暗号化ストレージ**: 全シークレットをAES-256-GCMで暗号化
- 🛂 **ロールベースアクセス制御 (RBAC)**: サービスごとの細かい権限管理
- 📡 **HTTP API**: CRUD操作のためのRESTfulインターフェース
- 🧾 **監査証跡**: バージョン履歴と変更追跡
- 🔑 **トークンベース認証**: サービス識別の検証

---

## 🏗️ アーキテクチャ

### サービス間通信パターン

```
┌──────────────────┐
│  消費サービス     │
│  (ExpertAgent,   │
│   CommonUI等)    │
└─────────┬────────┘
          │ HTTPリクエスト
          │ ヘッダー:
          │ - X-Service: <service-name>
          │ - X-Token: <service-token>
          ▼
┌──────────────────┐
│   MyVault API    │
│   (ポート 8000)  │
└─────────┬────────┘
          │
          ▼
┌──────────────────┐
│暗号化SQLite      │
│ (data/myvault.db)│
└──────────────────┘
```

### 主要コンポーネント

| コンポーネント | 説明 | 場所 |
|-----------|-------------|----------|
| **MyVaultサービス** | FastAPIベースのシークレット管理API | `myVault/` |
| **設定ファイル** | 非機密設定 (ポリシー、サービス定義) | `myVault/config.yaml` |
| **環境変数ファイル** | 機密情報 (マスターキー、トークン) | `myVault/.env` |
| **データベース** | 暗号化SQLiteデータベース | `myVault/data/myvault.db` |
| **クライアントライブラリ** | サービス固有の統合コード | `<service>/core/myvault_client.py` |

---

## 🔑 必須パラメータ

### 環境変数 (全消費サービス)

MyVaultと連携する全サービスは以下の環境変数を定義する必要があります:

| 変数名 | 型 | 必須 | 説明 | 例 |
|---------------|------|----------|-------------|---------|
| `MYVAULT_BASE_URL` | String | ✅ はい | MyVault APIエンドポイントURL | `http://localhost:8000` (開発)<br>`http://myvault:8000` (docker) |
| `MYVAULT_SERVICE_NAME` | String | ✅ はい | 認証用のサービス識別子 | `expertagent`, `commonui`, `graphaiserver` |
| `MYVAULT_SERVICE_TOKEN` | String | ✅ はい | サービス用認証トークン | 安全に生成されたトークン (後述) |
| `MYVAULT_ENABLED` | Boolean | ⚠️ 任意 | MyVault統合の有効/無効 | `true` (デフォルト: `false`) |
| `MYVAULT_DEFAULT_PROJECT` | String | ⚠️ 任意 | シークレットのデフォルトプロジェクト名 | `myproject`, `default` |
| `SECRETS_CACHE_TTL` | Integer | ⚠️ 任意 | キャッシュTTL (秒) | `300` (5分) |

### MyVaultサーバー設定

MyVaultサーバーには以下の環境変数が必要です:

| 変数名 | 型 | 必須 | 説明 | 例 |
|---------------|------|----------|-------------|---------|
| `MSA_MASTER_KEY` | String | ✅ はい | Base64エンコードされた32バイト暗号化キー | `base64:jFi1bkzTyKQ5BLtw...` |
| `MYVAULT_TOKEN_<SERVICE>` | String | ✅ はい | 各サービスのトークン (例: `MYVAULT_TOKEN_EXPERTAGENT`) | 安全に生成されたトークン |

---

## 🛡️ 認証・認可

### 認証フロー

1. **消費サービス**がHTTPリクエストにヘッダーを付与:
   ```
   X-Service: expertagent
   X-Token: <service-token>
   ```

2. **MyVault**が検証:
   - サービス名が`config.yaml`のservicesセクションに存在するか
   - トークンが環境変数`MYVAULT_TOKEN_<SERVICE>`と一致するか
   - サービスが有効化されているか (`enabled: true`)

3. **認可チェック**:
   - `config.yaml`からサービスに割り当てられたロールを読み込み
   - 要求されたリソースに対して権限を評価
   - RBACポリシーに基づいて許可/拒否

### RBACアクション

| アクション | 説明 | ユースケース |
|--------|-------------|----------|
| `read` | シークレット値の取得 | アプリケーションによる認証情報の読み取り |
| `write` | シークレットの作成・更新 | 管理サービスによる設定管理 |
| `delete` | シークレットの削除 | シークレットローテーションとクリーンアップ |
| `list` | シークレット一覧 (値はマスク) | 探索とインベントリ操作 |

### RBACポリシー例

```yaml
# config.yaml
policies:
  - name: expertagent-reader
    description: "AIエージェント向け全シークレット読み取り専用アクセス"
    permissions:
      - effect: "allow"
        actions: ["read", "list"]
        resources: ["secret:*:*"]

  - name: expertagent-google-editor
    description: "Google OAuth シークレット書き込みアクセス"
    permissions:
      - effect: "allow"
        actions: ["read", "write", "list"]
        resources: ["secret:*:GOOGLE_*"]

services:
  - name: expertagent
    description: "ExpertAgent AIサービス"
    enabled: true
    roles:
      - expertagent-reader
      - expertagent-google-editor
```

---

## 🔧 統合実装手順

### ステップ1: サービストークンの生成

```bash
# 新サービス用の安全なトークンを生成
python -c "import secrets; print(secrets.token_urlsafe(32))"
# 出力: AbC123XyZ456...
```

### ステップ2: MyVaultサーバーの設定

`myVault/config.yaml`にサービス定義を追加:

```yaml
services:
  - name: mynewservice
    description: "MyVault統合を持つ新サービス"
    enabled: true
    roles:
      - common-reader  # 既存ポリシーを再利用または新規作成
```

`myVault/.env`にトークンを追加:

```env
MYVAULT_TOKEN_MYNEWSERVICE=AbC123XyZ456...
```

### ステップ3: 消費サービスの設定

サービス設定に環境変数を追加:

**Docker Compose (`docker-compose.yml`):**
```yaml
services:
  mynewservice:
    environment:
      - MYVAULT_BASE_URL=http://myvault:8000
      - MYVAULT_SERVICE_NAME=mynewservice
      - MYVAULT_SERVICE_TOKEN=${MYVAULT_TOKEN_MYNEWSERVICE}
```

**ローカル開発 (`.env` または `dev-start.sh`):**
```env
MYVAULT_BASE_URL=http://localhost:8003  # またはquick-start.shの場合は8103
MYVAULT_SERVICE_NAME=mynewservice
MYVAULT_SERVICE_TOKEN=AbC123XyZ456...
```

### ステップ4: クライアントコードの実装

#### Python実装例 (FastAPI/Pydantic)

```python
# core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # MyVault設定
    MYVAULT_ENABLED: bool = Field(default=False)
    MYVAULT_BASE_URL: str = Field(default="http://localhost:8000")
    MYVAULT_SERVICE_NAME: str = Field(default="mynewservice")
    MYVAULT_SERVICE_TOKEN: str = Field(default="")
    MYVAULT_DEFAULT_PROJECT: str = Field(default="")
    SECRETS_CACHE_TTL: int = Field(default=300)

settings = Settings()
```

```python
# core/myvault_client.py
import httpx
from typing import Optional

class MyVaultClient:
    def __init__(self, base_url: str, service_name: str, service_token: str):
        self.base_url = base_url.rstrip("/")
        self.service_name = service_name
        self.service_token = service_token
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={
                "X-Service": self.service_name,
                "X-Token": self.service_token,
            },
            timeout=30.0,
        )

    def get_secret(self, project: str, path: str) -> str:
        """シークレット値を取得"""
        response = self.client.get(f"/api/secrets/{project}/{path}")
        response.raise_for_status()
        return str(response.json()["value"])

    def set_secret(self, project: str, path: str, value: str) -> None:
        """シークレットを作成または更新"""
        response = self.client.post(
            "/api/secrets",
            json={"project": project, "path": path, "value": value},
        )
        response.raise_for_status()
```

```python
# core/secrets.py (統合シークレットマネージャー)
from typing import Optional
import os
import time
from core.config import settings
from core.myvault_client import MyVaultClient

class SecretsManager:
    def __init__(self):
        self.myvault_client: Optional[MyVaultClient] = None
        self._cache: dict[str, tuple[str, float]] = {}
        self.cache_ttl = settings.SECRETS_CACHE_TTL

        if settings.MYVAULT_ENABLED:
            self.myvault_client = MyVaultClient(
                base_url=settings.MYVAULT_BASE_URL,
                service_name=settings.MYVAULT_SERVICE_NAME,
                service_token=settings.MYVAULT_SERVICE_TOKEN,
            )

    def get_secret(self, key: str, project: Optional[str] = None) -> str:
        """
        MyVault優先でシークレットを取得し、環境変数にフォールバック

        Args:
            key: シークレットキー (例: "OPENAI_API_KEY")
            project: MyVaultプロジェクト名 (任意)

        Returns:
            シークレット値
        """
        # まずキャッシュをチェック
        cache_key = f"{project or 'default'}:{key}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key][0]

        # MyVaultを試行
        if self.myvault_client:
            try:
                proj = project or settings.MYVAULT_DEFAULT_PROJECT or "default"
                value = self.myvault_client.get_secret(proj, key)
                self._cache[cache_key] = (value, time.time())
                return value
            except Exception as e:
                # 警告をログに記録してフォールバック
                print(f"MyVault検索失敗 {key}: {e}、環境変数にフォールバック")

        # 環境変数にフォールバック
        value = os.getenv(key, "")
        if not value:
            raise ValueError(f"シークレット '{key}' がMyVaultまたは環境変数に見つかりません")

        self._cache[cache_key] = (value, time.time())
        return value

    def _is_cache_valid(self, key: str) -> bool:
        """キャッシュ値がTTL内かチェック"""
        if key not in self._cache:
            return False
        _, timestamp = self._cache[key]
        return (time.time() - timestamp) < self.cache_ttl

# グローバルインスタンス
secrets_manager = SecretsManager()
```

#### TypeScript実装例 (Express/Node.js)

```typescript
// src/config/settings.ts
export interface MyVaultConfig {
  MYVAULT_BASE_URL: string;
  MYVAULT_SERVICE_NAME: string;
  MYVAULT_SERVICE_TOKEN: string;
}

export const settings: MyVaultConfig = {
  MYVAULT_BASE_URL: process.env.MYVAULT_BASE_URL || 'http://localhost:8000',
  MYVAULT_SERVICE_NAME: process.env.MYVAULT_SERVICE_NAME || 'mynewservice',
  MYVAULT_SERVICE_TOKEN: process.env.MYVAULT_SERVICE_TOKEN || '',
};
```

```typescript
// src/services/myvaultClient.ts
import axios, { AxiosInstance } from 'axios';

export class MyVaultClient {
  private client: AxiosInstance;

  constructor(baseUrl: string, serviceName: string, serviceToken: string) {
    this.client = axios.create({
      baseURL: baseUrl,
      headers: {
        'X-Service': serviceName,
        'X-Token': serviceToken,
      },
      timeout: 30000,
    });
  }

  async getSecret(project: string, path: string): Promise<string> {
    const response = await this.client.get(`/api/secrets/${project}/${path}`);
    return response.data.value;
  }

  async setSecret(project: string, path: string, value: string): Promise<void> {
    await this.client.post('/api/secrets', { project, path, value });
  }
}
```

---

## 📡 APIエンドポイント

### 認証ヘッダー (全リクエスト共通)

```http
X-Service: <service-name>
X-Token: <service-token>
```

### 利用可能なエンドポイント

| メソッド | パス | 説明 | リクエストボディ | レスポンス |
|--------|------|-------------|--------------|----------|
| **GET** | `/health` | ヘルスチェック | - | `{"status":"healthy","service":"myVault"}` |
| **POST** | `/api/secrets/test` | 認証テスト | - | `{"status":"ok","message":"..."}` |
| **GET** | `/api/projects` | プロジェクト一覧 | - | `[{"id":1,"name":"myproject",...}]` |
| **POST** | `/api/projects` | プロジェクト作成 | `{"name":"myproject","description":"..."}` | `{"id":1,"name":"myproject",...}` |
| **GET** | `/api/secrets` | シークレット一覧 (値はマスク) | - | `[{"id":1,"project":"test","path":"api-key",...}]` |
| **GET** | `/api/secrets/{project}/{path}` | シークレット値取得 | - | `{"id":1,"project":"test","path":"api-key","value":"secret123",...}` |
| **POST** | `/api/secrets` | シークレット作成 | `{"project":"test","path":"api-key","value":"secret123"}` | `{"id":1,"project":"test",...}` |
| **PATCH** | `/api/secrets/{project}/{path}` | シークレット更新 (ローテーション) | `{"value":"new-secret456"}` | `{"id":1,"version":2,...}` |
| **DELETE** | `/api/secrets/{project}/{path}` | シークレット削除 | - | HTTP 204 No Content |

### API呼び出し例

**シークレット作成:**
```bash
curl -X POST http://localhost:8000/api/secrets \
  -H "Content-Type: application/json" \
  -H "X-Service: expertagent" \
  -H "X-Token: <service-token>" \
  -d '{
    "project": "myproject",
    "path": "OPENAI_API_KEY",
    "value": "sk-openai-secret-key-123"
  }'
```

**シークレット取得:**
```bash
curl http://localhost:8000/api/secrets/myproject/OPENAI_API_KEY \
  -H "X-Service: expertagent" \
  -H "X-Token: <service-token>"
```

**シークレット更新 (ローテーション):**
```bash
curl -X PATCH http://localhost:8000/api/secrets/myproject/OPENAI_API_KEY \
  -H "Content-Type: application/json" \
  -H "X-Service: expertagent" \
  -H "X-Token: <service-token>" \
  -d '{
    "value": "sk-openai-rotated-key-456"
  }'
```

---

## 🌐 ポート構成

### 標準ポート (Docker Compose / dev-start.sh)

| 環境 | MyVaultポート | 使用方法 |
|-------------|--------------|-------|
| **Docker Compose** | `8003` | 内部コンテナネットワーク: `http://myvault:8000`<br>外部ホスト: `http://localhost:8003` |
| **dev-start.sh** | `8003` | ローカル開発: `http://localhost:8003` |

### 代替ポート (quick-start.sh)

| 環境 | MyVaultポート | 使用方法 |
|-------------|--------------|-------|
| **quick-start.sh** | `8103` | ローカル開発 (並行実行): `http://localhost:8103` |

### サービス別設定

| サービス | Docker Compose | dev-start.sh | quick-start.sh |
|---------|----------------|--------------|----------------|
| **ExpertAgent** | `MYVAULT_BASE_URL=http://myvault:8000` | `MYVAULT_BASE_URL=http://localhost:8003` | `MYVAULT_BASE_URL=http://localhost:8103` |
| **CommonUI** | `MYVAULT_BASE_URL=http://myvault:8000` | `MYVAULT_BASE_URL=http://localhost:8003` | `MYVAULT_BASE_URL=http://localhost:8103` |
| **GraphAiServer** | `MYVAULT_BASE_URL=http://myvault:8000` | `MYVAULT_BASE_URL=http://localhost:8003` | `MYVAULT_BASE_URL=http://localhost:8103` |

---

## 🔒 セキュリティベストプラクティス

### 1. トークン管理

- ✅ **暗号学的に安全なトークンの生成**:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```

- ✅ **トークンを絶対にGitにコミットしない**:
  - `.env`ファイルに保存 (gitignore設定済み)
  - CI/CDで環境変数インジェクションを使用

- ✅ **トークンの定期的なローテーション**:
  - 推奨: 90日ごと
  - MyVaultの`.env`と消費サービスの`.env`の両方を更新

### 2. マスターキー管理

- ✅ **強力なマスターキーの生成**:
  ```bash
  python -c "import secrets, base64; print('base64:' + base64.b64encode(secrets.token_bytes(32)).decode())"
  ```

- ❌ **環境間でマスターキーを共有しない**:
  - 開発、ステージング、本番環境で異なるキーを使用

- ✅ **マスターキーの安全なバックアップ**:
  - パスワードマネージャーまたはハードウェアセキュリティモジュール (HSM) を使用
  - バックアップは別の暗号化キーで暗号化

### 3. アクセス制御

- ✅ **最小権限の原則**:
  - 必要最小限の権限のみを付与
  - 可能な限りワイルドカードではなく具体的なリソースパターンを使用

- ✅ **環境別のポリシー分離**:
  - 開発サービスは本番シークレットにアクセスすべきでない
  - プロジェクトネームスペースを使用 (例: `myproject:dev/*`, `myproject:prod/*`)

### 4. ネットワークセキュリティ

- ✅ **本番環境ではHTTPSを使用**:
  - リバースプロキシ (nginx, Traefik) でTLSを設定
  - `MYVAULT_BASE_URL`で`https://`スキームを強制

- ✅ **ネットワークアクセスの制限**:
  - Dockerネットワークでサービスを隔離
  - ファイアウォールルールでMyVaultポートへの外部アクセスをブロック

### 5. 監査・モニタリング

- ✅ **監査ログの有効化**:
  ```yaml
  # config.yaml
  audit:
    enabled: true
    log_access: true
    log_modifications: true
    retention_days: 90
  ```

- ✅ **異常の監視**:
  - 認証失敗の試行
  - 異常なアクセスパターン
  - 未承認サービスによるシークレットへのアクセス

---

## 🧪 テスト・検証

### ヘルスチェック

```bash
curl http://localhost:8000/health
# 期待値: {"status":"healthy","service":"myVault"}
```

### 認証テスト

```bash
curl -X POST http://localhost:8000/api/secrets/test \
  -H "X-Service: expertagent" \
  -H "X-Token: <service-token>"
# 期待値: {"status":"ok","message":"Authentication successful for service 'expertagent'"}
```

### 統合テスト (Python)

```python
import pytest
from core.secrets import secrets_manager

def test_myvault_integration():
    # シークレット取得のテスト
    api_key = secrets_manager.get_secret("OPENAI_API_KEY", project="test")
    assert api_key is not None
    assert len(api_key) > 0

    # キャッシングのテスト (2回目の呼び出しは高速であるべき)
    import time
    start = time.time()
    api_key_cached = secrets_manager.get_secret("OPENAI_API_KEY", project="test")
    elapsed = time.time() - start

    assert api_key == api_key_cached
    assert elapsed < 0.01  # キャッシュ取得は10ms未満であるべき
```

---

## 📚 一般的な統合パターン

### パターン1: 直接取得 (シンプル)

```python
# 用途: 初期化時の1回限りのシークレット検索
from core.myvault_client import MyVaultClient

client = MyVaultClient(
    base_url=settings.MYVAULT_BASE_URL,
    service_name=settings.MYVAULT_SERVICE_NAME,
    service_token=settings.MYVAULT_SERVICE_TOKEN,
)
api_key = client.get_secret("myproject", "OPENAI_API_KEY")
```

### パターン2: 統合シークレットマネージャー (推奨)

```python
# 用途: 環境変数へのフォールバック、キャッシュサポート
from core.secrets import secrets_manager

api_key = secrets_manager.get_secret("OPENAI_API_KEY", project="myproject")
# 自動的にまずMyVaultを試行し、次にos.getenv()にフォールバック
```

### パターン3: Settingsでの遅延ロード

```python
# 用途: MyVault統合を持つPydantic settings
from pydantic_settings import BaseSettings
from pydantic import Field
from core.secrets import secrets_manager

class Settings(BaseSettings):
    OPENAI_API_KEY: str = Field(default="")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # MyVaultが利用可能な場合はオーバーライド
        if not self.OPENAI_API_KEY:
            try:
                self.OPENAI_API_KEY = secrets_manager.get_secret("OPENAI_API_KEY")
            except ValueError:
                pass  # 環境変数のデフォルト値を使用

settings = Settings()
```

---

## 🔄 シークレットローテーションワークフロー

### 手動ローテーション

```bash
# 1. 新しいシークレットを生成 (例: 外部サービスからの新APIキー)
NEW_API_KEY="sk-new-openai-key-789"

# 2. MyVaultで更新
curl -X PATCH http://localhost:8000/api/secrets/myproject/OPENAI_API_KEY \
  -H "Content-Type: application/json" \
  -H "X-Service: commonui" \
  -H "X-Token: <admin-token>" \
  -d "{\"value\":\"$NEW_API_KEY\"}"

# 3. 依存サービスを再起動 (またはキャッシュTTL期限を待つ)
docker-compose restart expertagent
```

### 自動ローテーション (Python実装例)

```python
import schedule
import time
from core.myvault_client import MyVaultClient
from external_api import generate_new_api_key

def rotate_api_key():
    """90日ごとにAPIキーをローテーション"""
    client = MyVaultClient(...)

    # 1. 外部サービスから新キーを生成
    new_key = generate_new_api_key()

    # 2. MyVaultで更新
    client.update_secret("myproject", "OPENAI_API_KEY", new_key)

    # 3. モニタリングに通知
    print(f"✅ APIキーをローテーション: {time.ctime()}")

# 90日ごとにローテーションをスケジュール
schedule.every(90).days.do(rotate_api_key)

while True:
    schedule.run_pending()
    time.sleep(86400)  # 毎日チェック
```

---

## 🚨 トラブルシューティング

### エラー: "[Errno 61] Connection refused"

**原因**: MyVaultサービスが起動していないか、ポート設定が間違っている

**解決策**:
```bash
# 1. MyVaultが起動しているか確認
curl http://localhost:8003/health  # dev-start.sh
curl http://localhost:8103/health  # quick-start.sh

# 2. 環境変数を確認
echo $MYVAULT_BASE_URL

# 3. MyVaultを再起動
docker-compose restart myvault  # Docker
./scripts/restart-myvault.sh    # dev-start.sh
```

### エラー: "403 Forbidden - Service does not have access"

**原因**: サービスが要求されたリソースへのRBACアクセス権限を持っていない

**解決策**:
```bash
# 1. config.yamlでサービスのロールを確認
cat myVault/config.yaml | grep -A 5 "name: expertagent"

# 2. 必要なポリシーを追加
# myVault/config.yamlを編集してロールを追加/修正

# 3. 設定を再読み込みするためMyVaultを再起動
./scripts/restart-myvault.sh
```

### エラー: "401 Unauthorized - Invalid service token"

**原因**: 消費サービスとMyVault間でトークンが一致していない

**解決策**:
```bash
# 1. 消費サービスのトークンを確認
cat expertAgent/.env | grep MYVAULT_SERVICE_TOKEN

# 2. MyVaultサーバーのトークンを確認
cat myVault/.env | grep MYVAULT_TOKEN_EXPERTAGENT

# 3. トークンが一致することを確認 (必要に応じて更新)
# 4. 両サービスを再起動
```

---

## 📖 関連ドキュメント

- **MyVault README**: [`myVault/README.md`](../../myVault/README.md)
- **アーキテクチャ概要**: [`docs/design/architecture-overview.md`](./architecture-overview.md)
- **環境変数一覧**: [`docs/design/environment-variables.md`](./environment-variables.md)
- **Dockerガイド**: [`docs/guide/DOCKER_GUIDE.md`](../guide/DOCKER_GUIDE.md)
- **開発ガイド**: [`docs/guide/DEVELOPMENT_GUIDE.md`](../guide/DEVELOPMENT_GUIDE.md)

---

## ✅ コンプライアンスチェックリスト

新サービスをMyVault統合でデプロイする前に:

- [ ] `myVault/config.yaml`のservicesセクションにサービス名を追加
- [ ] 適切な権限を持つRBACポリシーを定義
- [ ] サービストークンを安全に生成し`myVault/.env`に追加
- [ ] 必須の環境変数で消費サービスを設定
- [ ] クライアントコード (MyVaultClientまたはSecretsManager) を実装
- [ ] MyVault統合の単体テストを作成
- [ ] ローカル開発環境で統合テストを検証
- [ ] ヘルスチェックエンドポイント (`/health`) をテスト
- [ ] 認証 (`/api/secrets/test`) をテスト
- [ ] 必要な全シークレットの取得をテスト
- [ ] MyVault利用不可時のエラーハンドリングを実装
- [ ] 環境変数へのフォールバックを検証
- [ ] キャッシュTTLを適切に設定
- [ ] ドキュメント (README, .env.example) を更新
- [ ] セキュリティレビューを完了 (トークン管理、権限)
- [ ] Docker Compose環境でデプロイをテスト

---

**管理者**: MySwiftAgentコアチーム
**質問**: メインリポジトリでissueを開く

---

最終更新: 2025-10-19
