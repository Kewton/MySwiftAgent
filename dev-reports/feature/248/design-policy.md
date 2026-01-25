# Issue #248 設計方針書

## 他サービスの接続情報の管理の myVault への集約

**作成日**: 2025-12-06
**Issue**: [#248](https://github.com/Kewton/MySwiftAgent/issues/248)
**要件定義書**: [requirements.md](./requirements.md)
**ステータス**: Draft

---

## 1. アーキテクチャ設計

### 1.1 システム構成図

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              expertAgent                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         SecretsManager                                   ││
│  │  ┌─────────────────────────────────────────────────────────────────────┐││
│  │  │                    get_connection_config()                          │││
│  │  │                                                                     │││
│  │  │  ┌─────────────┐     ┌─────────────┐     ┌─────────────────────┐   │││
│  │  │  │ Type        │────▶│ Cache       │────▶│ Value Resolver      │   │││
│  │  │  │ Converter   │     │ (TTL: 300s) │     │ (myVault → env)     │   │││
│  │  │  └─────────────┘     └─────────────┘     └─────────────────────┘   │││
│  │  │                                                                     │││
│  │  └─────────────────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                     │                                        │
│            ┌────────────────────────┼────────────────────────┐              │
│            ▼                        ▼                        ▼              │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐      │
│  │ LangfuseService  │    │   ValkeyClient   │    │  Other Services  │      │
│  │                  │    │                  │    │                  │      │
│  │ - host           │    │ - host           │    │                  │      │
│  │ - public_key     │    │ - port           │    │                  │      │
│  │ - secret_key     │    │ - db             │    │                  │      │
│  └──────────────────┘    │ - ttl            │    └──────────────────┘      │
│                          └──────────────────┘                               │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP API
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                myVault                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                          Secrets Storage                                 ││
│  │  ┌─────────────────────────────────────────────────────────────────────┐││
│  │  │  Project: default_project                                           │││
│  │  │  ┌─────────────────────────────────────────────────────────────────┐│││
│  │  │  │ Langfuse Config                    │ Valkey Config              ││││
│  │  │  │ ─────────────────────────────────  │ ────────────────────────── ││││
│  │  │  │ LANGFUSE_PUBLIC_KEY (既存)         │ VALKEY_HOST (新規)         ││││
│  │  │  │ LANGFUSE_SECRET_KEY (既存)         │ VALKEY_PORT (新規)         ││││
│  │  │  │ LANGFUSE_HOST (新規)               │ VALKEY_DB (新規)           ││││
│  │  │  │                                    │ VALKEY_TTL (新規)          ││││
│  │  │  └─────────────────────────────────────────────────────────────────┘│││
│  │  └─────────────────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Environment Variables                              │
│                              (.env / .env.local)                             │
│                                                                              │
│  LANGFUSE_HOST=http://localhost:3001        ← Fallback                       │
│  VALKEY_HOST=localhost                      ← Fallback                       │
│  VALKEY_PORT=6379                           ← Fallback                       │
│  ...                                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 レイヤー構成

| レイヤー | コンポーネント | 責務 |
|---------|--------------|------|
| **アプリケーション層** | `main.py`, サービス初期化 | 接続情報取得・サービス初期化 |
| **ビジネスロジック層** | `LangfuseService`, `ValkeyClient` | 外部サービスとの通信 |
| **インフラストラクチャ層** | `SecretsManager` | 設定値の解決（myVault → env） |
| **外部サービス層** | `MyVaultClient` | myVault API 通信 |

### 1.3 データフロー

#### 設定値取得フロー

```
1. Application Layer: サービス初期化
   │
   ▼
2. SecretsManager.get_connection_config("VALKEY_HOST", value_type=str)
   │
   ├─▶ 3a. Check Cache (TTL: 300s)
   │      └─ HIT → Return cached value
   │
   └─▶ 3b. MISS → MyVaultClient.get_secret()
           │
           ├─▶ 4a. myVault SUCCESS → Cache & Return
           │
           └─▶ 4b. myVault FAIL → Fallback to settings (env var)
                   │
                   ├─▶ 5a. env var EXISTS → Return
                   │
                   └─▶ 5b. env var NOT FOUND
                           │
                           ├─▶ 6a. default PROVIDED → Return default
                           │
                           └─▶ 6b. default NOT PROVIDED → Raise ValueError
```

---

## 2. 技術選定

### 2.1 技術スタック

| カテゴリ | 選定技術 | 選定理由 |
|---------|---------|---------|
| **設定管理** | myVault (既存) | プロジェクト別管理、暗号化、API 提供済み |
| **キャッシュ** | Python dict (インメモリ) | 既存 `secrets_manager` のキャッシュ機構を再利用 |
| **型変換** | Python 標準ライブラリ | `int()`, `bool()` による単純変換 |
| **API クライアント** | `MyVaultClient` (既存) | httpx ベース、async 対応 |

### 2.2 既存コンポーネントの活用

| コンポーネント | ファイル | 活用方法 |
|--------------|---------|---------|
| `SecretsManager` | `expertAgent/core/secrets.py` | `get_connection_config()` メソッド追加 |
| `MyVaultClient` | `expertAgent/core/myvault_client.py` | そのまま利用 |
| `settings` | `expertAgent/core/config.py` | フォールバック値として利用 |

---

## 3. 設計パターン

### 3.1 適用パターン

| パターン | 適用箇所 | 理由 |
|---------|---------|------|
| **Chain of Responsibility** | 設定値解決 | myVault → env → default の優先順位制御 |
| **Cache-Aside** | `get_connection_config()` | キャッシュヒット時の高速化 |
| **Adapter** | `get_connection_config()` | 既存 `get_secret()` を型変換対応に拡張 |
| **Singleton** | `secrets_manager` | アプリケーション全体で1インスタンス |

### 3.2 Chain of Responsibility パターン

```python
def get_connection_config(self, key: str, ...) -> Any:
    """設定値解決チェーン"""

    # Chain 1: myVault (最優先)
    try:
        value = self.get_secret(key, project)
        return self._convert_type(value, value_type)
    except ValueError:
        pass

    # Chain 2: Environment variable (フォールバック)
    env_value = getattr(settings, key, None)
    if env_value is not None:
        return self._convert_type(str(env_value), value_type)

    # Chain 3: Default value (最終フォールバック)
    if default is not None:
        return default

    # Chain end: Error
    raise ValueError(f"Config '{key}' not found")
```

### 3.3 Cache-Aside パターン

```
┌─────────────────────────────────────────────────────────────┐
│                     Request Flow                             │
├─────────────────────────────────────────────────────────────┤
│  1. get_connection_config("VALKEY_HOST")                    │
│     │                                                        │
│     ▼                                                        │
│  2. Check Cache ─────────────────────────────▶ HIT: Return  │
│     │                                                        │
│     ▼ MISS                                                   │
│  3. Fetch from myVault                                       │
│     │                                                        │
│     ├─▶ SUCCESS: Update Cache → Return                      │
│     │                                                        │
│     └─▶ FAIL: Fallback to env → Return                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. データモデル設計

### 4.1 myVault シークレット設計

#### 新規追加するシークレット

| キー名 | 型 | 値の例 | 説明 |
|-------|-----|-------|------|
| `LANGFUSE_HOST` | `str` | `http://localhost:3001` | Langfuse Self-hosted URL |
| `VALKEY_HOST` | `str` | `localhost` | Valkey ホスト名 |
| `VALKEY_PORT` | `int` | `6379` | Valkey ポート番号 |
| `VALKEY_DB` | `int` | `0` | Valkey データベース番号 |
| `VALKEY_TTL` | `int` | `86400` | Valkey TTL（秒） |

#### キー命名規則

```
{SERVICE}_{CONFIG_TYPE}

命名例:
├── LANGFUSE_HOST           → Langfuse の接続先ホスト
├── LANGFUSE_PUBLIC_KEY     → Langfuse の公開キー
├── LANGFUSE_SECRET_KEY     → Langfuse のシークレットキー
├── VALKEY_HOST             → Valkey の接続先ホスト
├── VALKEY_PORT             → Valkey のポート番号
├── VALKEY_DB               → Valkey のデータベース番号
└── VALKEY_TTL              → Valkey の TTL 設定
```

### 4.2 キャッシュデータ構造

```python
# 既存のキャッシュ構造を継続利用
self._cache: Dict[str, Dict[str, Tuple[str, float]]] = {
    "default_project": {
        "LANGFUSE_HOST": ("http://localhost:3001", 1733472000.0),
        "VALKEY_HOST": ("localhost", 1733472000.0),
        "VALKEY_PORT": ("6379", 1733472000.0),  # 文字列で保存、取得時に型変換
    }
}
```

---

## 5. API設計

### 5.1 SecretsManager API 拡張

#### 新規メソッド: `get_connection_config()`

```python
def get_connection_config(
    self,
    key: str,
    project: Optional[str] = None,
    *,
    default: Optional[Any] = None,
    value_type: type = str,
) -> Any:
    """Get connection configuration with type conversion.

    Priority:
    1. myVault (if enabled) → use project or default project
    2. Environment variable (fallback)
    3. Default value (if provided)
    4. Raise ValueError if not found

    Args:
        key: Config key name (e.g., "VALKEY_PORT")
        project: Optional project name (uses default if not specified)
        default: Default value if not found anywhere
        value_type: Type to convert value to (str, int, bool)

    Returns:
        Configuration value with appropriate type

    Raises:
        ValueError: If config not found and no default provided

    Examples:
        >>> secrets_manager.get_connection_config("VALKEY_HOST")
        "localhost"

        >>> secrets_manager.get_connection_config("VALKEY_PORT", value_type=int)
        6379

        >>> secrets_manager.get_connection_config("VALKEY_ENABLED", value_type=bool)
        True
    """
```

#### ヘルパーメソッド: `_convert_type()`

```python
def _convert_type(self, value: str, value_type: type) -> Any:
    """Convert string value to specified type.

    Args:
        value: String value to convert
        value_type: Target type (str, int, bool)

    Returns:
        Converted value

    Raises:
        ValueError: If conversion fails
    """
    if value_type == str:
        return value
    elif value_type == int:
        return int(value)
    elif value_type == bool:
        return value.lower() in ("true", "1", "yes", "on")
    else:
        raise ValueError(f"Unsupported type: {value_type}")
```

### 5.2 使用例

```python
# expertAgent/app/main.py

from core.secrets import secrets_manager

# Valkey 接続情報を myVault 優先で取得
valkey_host = secrets_manager.get_connection_config(
    "VALKEY_HOST",
    default=settings.VALKEY_HOST,
)
valkey_port = secrets_manager.get_connection_config(
    "VALKEY_PORT",
    default=settings.VALKEY_PORT,
    value_type=int,
)
valkey_db = secrets_manager.get_connection_config(
    "VALKEY_DB",
    default=settings.VALKEY_DB,
    value_type=int,
)

# ValkeyClient 初期化
valkey_client = ValkeyClient(
    host=valkey_host,
    port=valkey_port,
    db=valkey_db,
)
```

---

## 6. セキュリティ設計

### 6.1 脅威分析

| 脅威 | リスク | 対策 |
|------|-------|------|
| myVault への不正アクセス | 低 | 内部ネットワークのみ、サービストークン認証 |
| 接続情報の漏洩 | 中 | myVault 暗号化ストレージ使用 |
| ログへの機密情報出力 | 中 | 接続情報のログ出力時マスキング |
| 環境変数の漏洩 | 低 | `.env` ファイルは .gitignore 対象 |

### 6.2 セキュリティ対策

```python
# ログ出力時のマスキング
def _log_config_retrieval(self, key: str, source: str, value: str) -> None:
    """Log configuration retrieval with masking."""
    # ポート番号などの非機密情報はそのまま出力
    if key.endswith("_PORT") or key.endswith("_DB") or key.endswith("_TTL"):
        logger.info(f"Config '{key}' retrieved from {source}: {value}")
    # ホスト名は部分マスキング
    elif key.endswith("_HOST"):
        masked = value[:10] + "***" if len(value) > 10 else value
        logger.info(f"Config '{key}' retrieved from {source}: {masked}")
    # その他は完全マスキング
    else:
        logger.info(f"Config '{key}' retrieved from {source}: ***")
```

---

## 7. パフォーマンス設計

### 7.1 パフォーマンス目標

| メトリクス | 目標値 | 測定方法 |
|-----------|--------|---------|
| キャッシュヒット時 | < 1ms | ログ出力 |
| myVault 取得時 | < 50ms | ログ出力 |
| 環境変数フォールバック時 | < 1ms | ログ出力 |

### 7.2 キャッシング戦略

| 項目 | 値 | 理由 |
|------|-----|------|
| **TTL** | 300秒（5分） | 既存の `SECRETS_CACHE_TTL` を利用 |
| **キャッシュキー** | `{project}:{key}` | プロジェクト別にキャッシュ |
| **無効化** | 手動（`clear_cache()`） | 設定変更時に明示的にクリア |

### 7.3 起動時の最適化

```python
# 起動時に必要な設定を一括取得（オプション）
async def prefetch_connection_configs(self) -> None:
    """Prefetch all connection configs at startup."""
    config_keys = [
        "LANGFUSE_HOST",
        "VALKEY_HOST",
        "VALKEY_PORT",
        "VALKEY_DB",
        "VALKEY_TTL",
    ]
    for key in config_keys:
        try:
            self.get_connection_config(key)
        except ValueError:
            logger.debug(f"Config '{key}' not found in myVault")
```

---

## 8. 設計上の決定事項とトレードオフ

### 8.1 主要な設計決定

| 決定事項 | 採用案 | 代替案 | 理由 |
|---------|--------|-------|------|
| 実装アプローチ | secrets_manager 拡張 | 新規 ConfigManager | 既存パターン再利用、最小変更 |
| 型変換方式 | 取得時に変換 | 保存時に型情報付与 | myVault スキーマ変更不要 |
| キャッシュ | 既存キャッシュ利用 | 専用キャッシュ新設 | 実装シンプル、TTL 共有 |
| フォールバック | env var → default | default のみ | 後方互換性維持 |

### 8.2 トレードオフ分析

#### 決定1: secrets_manager 拡張 vs 新規 ConfigManager

| 観点 | secrets_manager 拡張 | 新規 ConfigManager |
|------|---------------------|-------------------|
| **コード変更量** | 小（50-100行） | 大（200-300行） |
| **関心の分離** | 低（シークレットと混在） | 高（明確に分離） |
| **学習コスト** | 低（既存API拡張） | 中（新規API） |
| **テスト工数** | 小 | 中 |

**結論**: コード変更量と学習コストを優先し、secrets_manager 拡張を採用。

#### 決定2: 型変換タイミング

| 観点 | 取得時変換 | 保存時型情報 |
|------|-----------|-------------|
| **myVault 変更** | 不要 | スキーマ変更必要 |
| **型安全性** | 呼び出し側で指定 | myVault で保証 |
| **柔軟性** | 高い | 低い |

**結論**: myVault スキーマ変更不要を優先し、取得時変換を採用。

### 8.3 将来の拡張性

| 拡張項目 | 対応方針 |
|---------|---------|
| 新規サービス追加 | `get_connection_config()` で同様に対応 |
| 型サポート拡張 | `_convert_type()` に新規型追加 |
| バリデーション追加 | `get_connection_config()` にバリデーション引数追加 |

---

## 9. 実装計画

### 9.1 変更対象ファイル

| ファイル | 変更内容 | 影響度 |
|---------|---------|-------|
| `expertAgent/core/secrets.py` | `get_connection_config()`, `_convert_type()` 追加 | 中 |
| `expertAgent/app/main.py` | Valkey 初期化を myVault 優先に変更 | 低 |
| `expertAgent/app/services/langfuse_service.py` | `LANGFUSE_HOST` 取得を変更 | 低 |
| `expertAgent/app/api/v1/ab_test_endpoints.py` | Valkey 設定取得を変更 | 低 |
| `expertAgent/app/api/v1/diagnostic_endpoints.py` | Valkey 設定取得を変更 | 低 |
| `expertAgent/app/services/metrics_aggregation_service.py` | Valkey 設定取得を変更 | 低 |

### 9.2 新規追加ファイル

| ファイル | 内容 |
|---------|------|
| `expertAgent/tests/unit/test_secrets_connection_config.py` | `get_connection_config()` 単体テスト |

### 9.3 実装ステップ

```
Phase 1: SecretsManager 拡張
├── 1.1 get_connection_config() メソッド追加
├── 1.2 _convert_type() ヘルパー追加
├── 1.3 単体テスト作成
└── 1.4 Ruff/MyPy エラー修正

Phase 2: サービス初期化変更
├── 2.1 main.py Valkey 初期化変更
├── 2.2 langfuse_service.py HOST 取得変更
├── 2.3 ab_test_endpoints.py 変更
├── 2.4 diagnostic_endpoints.py 変更
└── 2.5 metrics_aggregation_service.py 変更

Phase 3: テスト・品質保証
├── 3.1 結合テスト作成
├── 3.2 ローカル動作確認
└── 3.3 CI/CD パス確認
```

---

## 10. CLAUDE.md 原則への準拠

### 10.1 SOLID原則

| 原則 | 対応 |
|------|------|
| **S** (単一責任) | `get_connection_config()` は設定値解決のみ、型変換は `_convert_type()` に分離 |
| **O** (開放/閉鎖) | 新規型サポートは `_convert_type()` のみ変更で対応可能 |
| **L** (リスコフ置換) | N/A（継承なし） |
| **I** (インターフェース分離) | `get_secret()` と `get_connection_config()` を分離 |
| **D** (依存性逆転) | `MyVaultClient` を注入可能に設計（既存） |

### 10.2 KISS / YAGNI / DRY

| 原則 | 対応 |
|------|------|
| **KISS** | 既存の `get_secret()` を内部で再利用、新規ロジック最小化 |
| **YAGNI** | CommonUI 設定画面は Nice to Have として後回し |
| **DRY** | キャッシュ機構、myVault 通信は既存コードを再利用 |

---

## 11. リスクと緩和策

| リスク | 影響度 | 発生確率 | 緩和策 |
|-------|--------|---------|-------|
| 型変換エラー | 中 | 中 | バリデーションとエラーメッセージの充実 |
| 既存テスト失敗 | 中 | 低 | モックで myVault 依存を分離 |
| 後方互換性破壊 | 高 | 低 | 環境変数フォールバックを必ず維持 |
| パフォーマンス劣化 | 低 | 低 | キャッシュ TTL の適切な設定 |

---

## 関連ドキュメント

- [Issue #248](https://github.com/Kewton/MySwiftAgent/issues/248)
- [requirements.md](./requirements.md) - 要件定義書
- `expertAgent/core/secrets.py` - 現行実装
- `expertAgent/core/myvault_client.py` - myVault クライアント
- `docs/design/myvault-integration.md` - myVault 連携設計
