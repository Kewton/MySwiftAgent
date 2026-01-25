# Issue #244 設計方針書
## expertAgent main.py で JobCreationStateManager の Valkey 接続初期化

---

## 1. 設計概要

### 1.1 目的

FastAPI アプリケーションの lifespan イベントで `JobCreationStateManager` の Valkey（L2キャッシュ）接続を初期化し、ジョブ状態の永続化を有効化する。

### 1.2 設計原則

| 原則 | 適用方針 |
|------|---------|
| **KISS** | 既存の `JobCreationStateManager` と `ValkeyClient` をそのまま活用。新規クラス作成なし |
| **YAGNI** | 接続プール、再接続機能は将来課題。現時点では単純な接続/切断のみ |
| **DRY** | 設定値は `core/config.py` の `settings` を使用。重複定義なし |
| **単一責任** | main.py は「初期化の調整役」に徹し、接続ロジックは既存クラスに委譲 |

---

## 2. アーキテクチャ設計

### 2.1 コンポーネント構成

```
┌─────────────────────────────────────────────────────────────────┐
│                    expertAgent Application                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    lifespan     ┌─────────────────────────┐   │
│  │   main.py    │ ──────────────► │ JobCreationStateManager │   │
│  │  (lifespan)  │   connect/      │     (Singleton)         │   │
│  └──────────────┘   disconnect    └───────────┬─────────────┘   │
│         │                                     │                  │
│         │ settings                            │ _valkey_client   │
│         ▼                                     ▼                  │
│  ┌──────────────┐                 ┌─────────────────────────┐   │
│  │ core/config  │                 │     ValkeyClient        │   │
│  │  (Settings)  │                 │   (host, port, db)      │   │
│  └──────────────┘                 └───────────┬─────────────┘   │
│                                               │                  │
└───────────────────────────────────────────────│──────────────────┘
                                                │
                                                ▼
                                    ┌─────────────────────┐
                                    │   Valkey Server     │
                                    │   (Redis互換)       │
                                    └─────────────────────┘
```

### 2.2 シーケンス図

#### 起動時（Startup）

```
┌────────┐     ┌──────────┐     ┌────────────────────┐     ┌─────────────┐
│ FastAPI│     │ main.py  │     │JobCreationState    │     │ValkeyClient │
│        │     │ lifespan │     │Manager             │     │             │
└───┬────┘     └────┬─────┘     └─────────┬──────────┘     └──────┬──────┘
    │               │                     │                       │
    │ startup       │                     │                       │
    │──────────────►│                     │                       │
    │               │                     │                       │
    │               │ if VALKEY_ENABLED   │                       │
    │               │─────────────────────│                       │
    │               │                     │                       │
    │               │ create ValkeyClient │                       │
    │               │─────────────────────────────────────────────►
    │               │                     │                       │
    │               │ set _valkey_client  │                       │
    │               │────────────────────►│                       │
    │               │                     │                       │
    │               │ connect_valkey()    │                       │
    │               │────────────────────►│                       │
    │               │                     │ connect()             │
    │               │                     │──────────────────────►│
    │               │                     │                       │
    │               │                     │ ping() / test         │
    │               │                     │◄──────────────────────│
    │               │                     │                       │
    │               │ [success/failure]   │                       │
    │               │◄────────────────────│                       │
    │               │                     │                       │
    │ yield         │                     │                       │
    │◄──────────────│                     │                       │
```

#### 終了時（Shutdown）

```
┌────────┐     ┌──────────┐     ┌────────────────────┐     ┌─────────────┐
│ FastAPI│     │ main.py  │     │JobCreationState    │     │ValkeyClient │
│        │     │ lifespan │     │Manager             │     │             │
└───┬────┘     └────┬─────┘     └─────────┬──────────┘     └──────┬──────┘
    │               │                     │                       │
    │ shutdown      │                     │                       │
    │──────────────►│                     │                       │
    │               │                     │                       │
    │               │ disconnect_valkey() │                       │
    │               │────────────────────►│                       │
    │               │                     │ disconnect()          │
    │               │                     │──────────────────────►│
    │               │                     │                       │
    │               │ [completed]         │                       │
    │◄──────────────│                     │                       │
```

---

## 3. 設計判断

### 3.1 Decision Record

#### DR-1: シングルトンインスタンスへの直接設定

| 項目 | 内容 |
|------|------|
| **決定** | `job_state_manager` シングルトンの `_valkey_client` を直接設定する |
| **理由** | 既存コードの変更を最小限に抑え、シンプルに実装できる |
| **代替案** | ① ファクトリパターンで新規インスタンス生成 → 他モジュールへの影響大 |
| | ② 環境変数で自動初期化 → テストの制御が困難 |
| **トレードオフ** | プライベート属性 `_valkey_client` への直接アクセスは設計上望ましくないが、既存APIを変更せずに済む |

#### DR-2: Graceful Degradation の実装場所

| 項目 | 内容 |
|------|------|
| **決定** | Graceful Degradation は `JobCreationStateManager.connect_valkey()` 内で処理（既存実装を活用） |
| **理由** | 既に実装済み。main.py で追加のエラーハンドリング不要 |
| **代替案** | main.py でtry-except → 責務の重複、DRY違反 |

#### DR-3: 設定の取得元

| 項目 | 内容 |
|------|------|
| **決定** | `core/config.py` の `settings` インスタンスから全設定を取得 |
| **理由** | 既存の設定管理機構を使用。環境変数 → Settings → 利用の一貫性 |
| **設定項目** | `VALKEY_ENABLED`, `VALKEY_HOST`, `VALKEY_PORT`, `VALKEY_DB`, `VALKEY_TTL` |

---

## 4. 詳細設計

### 4.1 修正箇所

| ファイル | 変更内容 |
|---------|---------|
| `expertAgent/app/services/job_creation_state.py` | `configure_valkey()` メソッド、`is_valkey_connected` プロパティを追加 |
| `expertAgent/app/main.py` | lifespan 関数に Valkey 初期化/切断処理を追加、`/health` エンドポイント拡張 |

### 4.2 実装コード

#### 4.2.1 job_creation_state.py - 公開メソッド追加

```python
# expertAgent/app/services/job_creation_state.py

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

#### 4.2.2 main.py - lifespan 関数

```python
# expertAgent/app/main.py

from app.services.job_creation_state import job_state_manager
from app.services.valkey_client import ValkeyClient
from core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Initialize logging
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

    # Shutdown: cleanup
    if settings.VALKEY_ENABLED:
        await job_state_manager.disconnect_valkey()
```

#### 4.2.3 main.py - health エンドポイント拡張

```python
from typing import Any

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

### 4.3 追加インポート

```python
from typing import Any
from app.services.job_creation_state import job_state_manager
from app.services.valkey_client import ValkeyClient
from core.config import settings
```

---

## 5. エラーハンドリング

### 5.1 エラーケースと対応

| エラーケース | 対応 | 実装場所 |
|-------------|------|---------|
| Valkeyサーバー未起動 | WARNING ログ出力、L1キャッシュのみで継続 | `JobCreationStateManager.connect_valkey()` |
| 接続タイムアウト | 同上 | 同上 |
| 設定値不正 | アプリケーション起動時にValidationError | `core/config.py` (Pydantic) |

### 5.2 ログ出力

| 状況 | ログレベル | メッセージ例 |
|------|-----------|-------------|
| 接続成功 | INFO | `Valkey connection: success - L2 cache enabled for job state persistence` |
| 接続失敗 | WARNING | `Valkey connection: failed - degrading to L1 only. Error: {e}` |
| Valkey無効 | INFO | `Valkey disabled - JobCreationStateManager using L1 cache only` |
| 切断成功 | INFO | `Valkey connection: disconnected` |

---

## 6. テスト戦略

### 6.1 テスト方針

| テスト種別 | 対象 | 方針 |
|-----------|------|------|
| 単体テスト | main.py lifespan | モックを使用してValkey接続初期化の呼び出しを検証 |
| E2Eテスト | Valkey連携 | 実際のValkeyサーバーを使用して動作確認 |

### 6.2 テストケース

| ID | 条件 | 期待結果 |
|----|------|---------|
| T-1 | `VALKEY_ENABLED=true`, Valkey起動中 | 接続成功、L2キャッシュ有効 |
| T-2 | `VALKEY_ENABLED=true`, Valkey未起動 | 接続失敗、L1キャッシュのみ、アプリ起動成功 |
| T-3 | `VALKEY_ENABLED=false` | 接続試行なし、L1キャッシュのみ |
| T-4 | アプリ終了 | Valkey接続が正常に切断される |

---

## 7. 設定一覧

### 7.1 環境変数

| 環境変数 | 型 | デフォルト | 説明 |
|---------|-----|-----------|------|
| `VALKEY_ENABLED` | bool | `false` | Valkey有効化フラグ |
| `VALKEY_HOST` | str | `localhost` | Valkeyサーバーホスト |
| `VALKEY_PORT` | int | `6379` | Valkeyサーバーポート |
| `VALKEY_DB` | int | `0` | データベース番号 (0-15) |
| `VALKEY_TTL` | int | `86400` | キャッシュTTL（秒）= 24時間 |

### 7.2 設定例

```bash
# .env (Valkey有効化)
VALKEY_ENABLED=true
VALKEY_HOST=localhost
VALKEY_PORT=6379
VALKEY_DB=0
VALKEY_TTL=86400
```

---

## 8. 将来の拡張ポイント

| 項目 | 説明 | 優先度 |
|------|------|-------|
| 接続プール | 複数接続の管理（高負荷対応） | 低 |
| 自動再接続 | 接続断後の自動復旧 | 中 |
| ヘルスチェック | `/health` にValkey状態を追加 | 低 |
| 認証対応 | Valkey AUTH コマンド対応 | 低 |

---

## 9. チェックリスト

### 9.1 実装前確認

- [x] 既存の `JobCreationStateManager` API を理解
- [x] 既存の `ValkeyClient` API を理解
- [x] 設定値が `core/config.py` に定義済みか確認
- [x] Graceful Degradation の実装が既存コードにあるか確認

### 9.2 実装時確認

- [ ] インポート文の追加
- [ ] lifespan 関数の修正
- [ ] ログ出力の適切なレベル設定
- [ ] Ruff/MyPy エラーゼロ

### 9.3 実装後確認

- [ ] 既存テストがパス
- [ ] E2Eテストで L2 キャッシュ動作確認
- [ ] ログ出力の確認（接続成功/失敗）

---

## 10. 参考資料

- [Issue #239: Valkey統合実装](https://github.com/Kewton/MySwiftAgent/issues/239)
- [Issue #193: Marp Report永続化（親Issue）](https://github.com/Kewton/MySwiftAgent/issues/193)
- [requirements.md](./requirements.md) - 本Issueの要件定義書
