# Issue #244 要件定義書
## expertAgent main.py で JobCreationStateManager の Valkey 接続初期化

---

## 1. ユーザーストーリー

```
As a システム管理者
I want to アプリケーション起動時に自動的にValkey接続が初期化される
So that L2キャッシュによるジョブ状態の永続化が有効化され、サーバー再起動後もジョブ結果を取得できる
```

---

## 2. 受入条件（Acceptance Criteria）

### AC-1: 正常系 - Valkey接続初期化
```gherkin
Given VALKEY_ENABLED=true が設定されている
When expertAgentアプリケーションが起動する
Then JobCreationStateManagerのValkey接続が初期化される
And ログに "Valkey connection: success - L2 cache enabled" が出力される
```

### AC-2: 正常系 - Valkeyを使用したジョブ取得
```gherkin
Given アプリケーションがValkey接続済みで起動している
And ジョブがValkey（L2キャッシュ）に保存されている
When GET /v1/marp-report/{job_id} を呼び出す
Then Valkeyからジョブ結果を取得できる
And ログに "L2 read: hit for job {job_id}" が出力される
```

### AC-3: 異常系 - Graceful Degradation
```gherkin
Given VALKEY_ENABLED=true だがValkeyサーバーが起動していない
When expertAgentアプリケーションが起動する
Then アプリケーションは正常に起動する（L1キャッシュのみ）
And ログに "Valkey connection: failed - degrading to L1 only" が出力される
```

### AC-4: 正常系 - Valkey無効時
```gherkin
Given VALKEY_ENABLED=false が設定されている
When expertAgentアプリケーションが起動する
Then Valkey接続は試行されない
And L1キャッシュ（メモリ）のみが使用される
```

### AC-5: シャットダウン時のクリーンアップ
```gherkin
Given アプリケーションがValkey接続済みで起動している
When アプリケーションがシャットダウンする
Then Valkey接続が正常に切断される
And ログに "Valkey connection: disconnected" が出力される
```

---

## 3. 機能要件

### 3.1 必須機能（Must Have）

| ID | 機能 | 詳細 |
|----|------|------|
| F-1 | Valkey接続初期化 | lifespan startup で `settings.VALKEY_ENABLED=true` 時に ValkeyClient を生成し、`job_state_manager.connect_valkey()` を呼び出す |
| F-2 | 接続情報の設定取得 | `settings.VALKEY_HOST`, `settings.VALKEY_PORT`, `settings.VALKEY_DB` から接続情報を取得 |
| F-3 | シャットダウン処理 | lifespan shutdown で `job_state_manager.disconnect_valkey()` を呼び出す |
| F-4 | Graceful Degradation | Valkey接続失敗時もアプリケーション起動を継続（L1キャッシュのみ） |
| F-5 | 公開メソッド追加 | `JobCreationStateManager.configure_valkey()` メソッドを追加し、プライベート属性への直接アクセスを排除 |
| F-6 | ヘルスチェック拡張 | `/health` エンドポイントにValkey接続状態（enabled, connected）を含める |

### 3.2 あると良い機能（Nice to Have）

なし（全て必須機能に移動）

### 3.3 将来的な拡張（Future Enhancement）

| ID | 機能 | 詳細 |
|----|------|------|
| E-1 | 接続プール | 複数のValkey接続をプール管理 |
| E-2 | 再接続機能 | 実行中に接続が切れた場合の自動再接続 |

---

## 4. 非機能要件

### 4.1 パフォーマンス要件

| 項目 | 要件 |
|------|------|
| 起動時間への影響 | Valkey接続は500ms以内に完了（タイムアウト） |
| 接続失敗時の起動 | 接続失敗でも起動時間に影響なし（非同期処理） |

### 4.2 セキュリティ要件

| 項目 | 要件 |
|------|------|
| 認証情報 | Valkey認証が必要な場合は将来的に対応（現状は認証なし） |
| ネットワーク | ローカルネットワーク内でのみ接続 |

### 4.3 可用性要件

| 項目 | 要件 |
|------|------|
| Graceful Degradation | Valkey障害時もサービス継続（L1キャッシュで動作） |
| ログ出力 | 接続状態の変化を全てログ出力 |

---

## 5. 技術的制約

### 5.1 使用する技術スタック

| 技術 | バージョン | 用途 |
|------|-----------|------|
| Python | 3.11+ | 実行環境 |
| FastAPI | 0.100+ | Webフレームワーク |
| valkey-py | latest | Valkeyクライアント |

### 5.2 既存システムとの連携

| システム | 連携方法 |
|---------|---------|
| JobCreationStateManager | シングルトンインスタンス `job_state_manager` を使用 |
| ValkeyClient | `app.services.valkey_client.ValkeyClient` を使用 |
| Settings | `expertAgent/core/config.py` の `settings` インスタンスを使用 |

### 5.3 設定値

| 設定名 | デフォルト値 | 説明 |
|--------|-------------|------|
| `VALKEY_ENABLED` | `false` | Valkey有効化フラグ |
| `VALKEY_HOST` | `localhost` | Valkeyサーバーホスト |
| `VALKEY_PORT` | `6379` | Valkeyサーバーポート |
| `VALKEY_DB` | `0` | データベース番号 |
| `VALKEY_TTL` | `86400` | キャッシュTTL（24時間） |

---

## 6. リスクと対策

| リスク | 影響度 | 発生確率 | 対策 |
|--------|-------|---------|------|
| Valkeyサーバー未起動 | 中 | 高 | Graceful Degradationで対応（L1キャッシュのみ） |
| 接続タイムアウト | 低 | 中 | タイムアウト設定と適切なエラーハンドリング |
| 既存テストへの影響 | 中 | 低 | モック使用の既存テストは影響なし |

---

## 7. 実装方針

### 7.1 修正対象ファイル

| ファイル | 変更内容 |
|---------|---------|
| `expertAgent/app/main.py` | lifespan関数にValkey初期化/切断処理を追加、healthエンドポイント拡張 |
| `expertAgent/app/services/job_creation_state.py` | `configure_valkey()` 公開メソッドを追加 |

### 7.2 実装コード案

#### job_creation_state.py - 公開メソッド追加

```python
def configure_valkey(
    self,
    client: "ValkeyClient",
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> None:
    """Configure Valkey client for L2 cache.

    Args:
        client: ValkeyClient instance for L2 cache operations
        ttl_seconds: TTL for Valkey cache in seconds (default: 24 hours)
    """
    self._valkey_client = client
    self._ttl_seconds = ttl_seconds
    logger.info(f"Valkey client configured (TTL: {ttl_seconds}s)")

@property
def is_valkey_connected(self) -> bool:
    """Check if Valkey is currently connected.

    Returns:
        True if Valkey client is configured and connected
    """
    return self._valkey_connected
```

#### main.py - lifespan 関数

```python
from app.services.job_creation_state import job_state_manager
from app.services.valkey_client import ValkeyClient
from core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    setup_logging()

    # Initialize Valkey connection for JobCreationStateManager (Issue #244)
    if settings.VALKEY_ENABLED:
        logger.info(
            f"Initializing Valkey connection: {settings.VALKEY_HOST}:{settings.VALKEY_PORT}"
        )
        valkey_client = ValkeyClient(
            host=settings.VALKEY_HOST,
            port=settings.VALKEY_PORT,
            db=settings.VALKEY_DB,
        )
        job_state_manager.configure_valkey(valkey_client, settings.VALKEY_TTL)
        await job_state_manager.connect_valkey()
    else:
        logger.info("Valkey disabled - JobCreationStateManager using L1 cache only")

    yield

    # Shutdown
    if settings.VALKEY_ENABLED:
        await job_state_manager.disconnect_valkey()
```

#### main.py - healthエンドポイント拡張

```python
@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint (used by CI/CD)."""
    return {
        "status": "healthy",
        "service": "expertAgent",
        "valkey": {
            "enabled": settings.VALKEY_ENABLED,
            "connected": job_state_manager.is_valkey_connected,
        },
    }
```

---

## 8. テストケース

| ID | テスト種別 | テストケース | 期待結果 |
|----|----------|-------------|---------|
| T-1 | E2E | Valkey有効 + 接続成功 → GET /v1/marp-report/{job_id} | L2キャッシュからジョブ取得成功 |
| T-2 | E2E | Valkey有効 + 接続失敗 → アプリ起動 | 起動成功（L1のみ） |
| T-3 | E2E | Valkey無効 → アプリ起動 | 起動成功（L1のみ） |
| T-4 | 単体 | Valkey接続初期化の呼び出し確認 | connect_valkey() が呼ばれる |

---

## 9. 依存関係

```
#239 (Valkey統合実装) ← #244 (本Issue) → #240 (非同期対応)
        ↓
      #193 (親Issue: Marp Report永続化)
```

---

## 10. 完了定義（Definition of Done）

- [ ] `JobCreationStateManager.configure_valkey()` メソッドが実装されている
- [ ] `JobCreationStateManager.is_valkey_connected` プロパティが実装されている
- [ ] `main.py` lifespan で Valkey 接続初期化が実装されている
- [ ] `VALKEY_ENABLED=true` 時に L2 キャッシュが有効化される
- [ ] Valkey 接続失敗時もアプリケーションが起動する
- [ ] `/health` エンドポイントが Valkey 状態を返す
- [ ] Ruff/MyPy エラーゼロ
- [ ] 既存テストがパス
- [ ] 新規メソッドの単体テストがパス
- [ ] E2Eテストで L2 キャッシュ動作を確認
