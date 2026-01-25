# Issue #193 アーキテクチャレビュー

## Marp Report API: Job ID not found エラー - インメモリ状態管理による永続化問題

**レビュー日**: 2025-12-05
**レビュアー**: Claude (Senior Software Architect)
**対象ドキュメント**:
- [requirements.md](./requirements.md)
- [design-policy.md](./design-policy.md)

---

## 1. 設計原則の遵守確認

### 1.1 SOLID原則チェック

| 原則 | 状態 | 評価 | コメント |
|------|------|------|---------|
| **S** (単一責任) | [x] | PASS | `JobCreationStateManager` はジョブ状態管理のみを担当 |
| **O** (開放/閉鎖) | [x] | PASS | Valkey 連携を追加しても既存メソッドシグネチャを維持 |
| **L** (リスコフ置換) | [-] | N/A | 継承関係なし |
| **I** (インターフェース分離) | [!] | **要改善** | 同期/非同期メソッドの共存に課題あり（後述） |
| **D** (依存性逆転) | [x] | PASS | `ValkeyClient` を注入可能に設計 |

### 1.2 その他の原則

| 原則 | 状態 | 評価 | コメント |
|------|------|------|---------|
| **KISS** | [x] | PASS | 既存 `ValkeyClient` を活用、新規コンポーネント最小化 |
| **YAGNI** | [x] | PASS | JobQueue DB 連携は将来拡張として適切に除外 |
| **DRY** | [x] | PASS | `ConversationStoreValkey` のパターンを参考に |

---

## 2. アーキテクチャ評価

### 2.1 構造的品質

| 評価項目 | スコア(1-5) | コメント |
|---------|------------|----------|
| **モジュール性** | 4 | 2層キャッシュ構造は適切。ただし ValkeyClient との結合度に注意 |
| **結合度** | 4 | 依存性注入で疎結合を実現。グローバルシングルトン問題あり |
| **凝集度** | 5 | `JobCreationStateManager` は単一責任で凝集度が高い |
| **拡張性** | 4 | L3（DB）追加が容易な設計。マルチインスタンス対応済み |
| **保守性** | 4 | 既存パターンを踏襲しており、保守しやすい |

**総合スコア: 4.2/5**

### 2.2 パフォーマンス観点

| 項目 | 評価 | コメント |
|------|------|---------|
| **レスポンスタイム** | PASS | L1: <1ms, L2: <10ms は妥当 |
| **スループット** | PASS | 非同期化によりI/Oブロッキングを回避 |
| **リソース効率** | PASS | メモリキャッシュ + TTL で適切に管理 |
| **スケーラビリティ** | PASS | Valkey により水平スケール可能 |

### 2.3 データフロー分析

```
Write Path (評価: PASS)
┌──────────────────────────────────────────────────────────────┐
│ job_generator_endpoints.py                                    │
│         │                                                     │
│         ▼                                                     │
│ mark_completed_async()                                        │
│         │                                                     │
│         ├──▶ L1 Update (Memory) ─── 同期的、高速            │
│         │                                                     │
│         └──▶ L2 Write (Valkey) ──── TTL: 24h, Write-Through │
└──────────────────────────────────────────────────────────────┘

Read Path (評価: PASS)
┌──────────────────────────────────────────────────────────────┐
│ marp_report_endpoints.py                                      │
│         │                                                     │
│         ▼                                                     │
│ get_status_async()                                            │
│         │                                                     │
│         ├──▶ L1 Check (Memory) ─── Hit → Return              │
│         │         │                                           │
│         │         ▼ Miss                                      │
│         └──▶ L2 Check (Valkey) ─── Hit → Populate L1 → Return│
│                   │                                           │
│                   ▼ Miss                                      │
│               Return None (404)                               │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. セキュリティレビュー

### 3.1 OWASP Top 10 チェック

| 脅威 | 状態 | コメント |
|------|------|---------|
| **インジェクション** | [x] | Valkey キーは `job:creation:{job_id}` 形式で固定 |
| **認証の破綻** | [-] | 内部API、認証不要（既存設計） |
| **機微データの露出** | [!] | `result` に機微データが含まれる可能性（後述） |
| **XXE** | [-] | XML 不使用 |
| **アクセス制御** | [-] | 内部ネットワークのみ |
| **セキュリティ設定** | [x] | 既存 Valkey 設定を踏襲 |
| **XSS** | [-] | API のみ、UI 非該当 |
| **デシリアライゼーション** | [x] | Pydantic `model_validate()` で安全 |
| **既知の脆弱性** | [x] | 既存ライブラリを使用 |
| **ログ不足** | [!] | センシティブデータのログ出力に注意（後述） |

### 3.2 セキュリティ懸念事項

#### 懸念1: result フィールドのデータ内容

```python
result: Optional[dict[str, Any]] = None  # 任意のデータが格納される
```

**リスク**: `result` には `requirement_relaxation_suggestions` などビジネスデータが含まれる。Valkey に永続化する際、意図しないデータ露出のリスクがある。

**推奨対策**:
- Valkey への保存前にセンシティブフィールドをサニタイズするか、保存対象を明示的に定義
- Valkey のアクセス制御を強化（パスワード認証の検討）

#### 懸念2: ログ出力

```python
logger.info(f"Persisted job status to Valkey: job_id={job_id}")
```

**リスク**: デバッグ時に `result` 内容をログ出力すると、センシティブデータが漏洩する可能性。

**推奨対策**:
- `result` フィールドはログに出力しない
- ログレベルを適切に設定

---

## 4. 既存システムとの整合性

### 4.1 統合ポイント

| 項目 | 状態 | コメント |
|------|------|---------|
| **API互換性** | [x] | `GET /v1/marp-report/{job_id}` のインターフェース維持 |
| **データモデル整合性** | [x] | 既存 `JobCreationStatus` をそのまま使用 |
| **認証/認可** | [-] | 変更なし |
| **ログ/監視** | [x] | 既存ログ基盤を活用、キャッシュ hit/miss をログ出力 |

### 4.2 技術スタックの適合性

| 項目 | 状態 | コメント |
|------|------|---------|
| **既存技術との親和性** | [x] | `ValkeyClient` は既に本番運用中 |
| **チームのスキルセット** | [x] | Python async、Valkey の経験あり |
| **運用負荷への影響** | [x] | TTL で自動クリーンアップ、運用負荷低 |

### 4.3 グローバルシングルトン問題

**現行実装**:
```python
# expertAgent/app/services/job_creation_state.py:141
job_state_manager = JobCreationStateManager()
```

**問題点**:
- シングルトンは依存性注入が困難
- テストでモック化しにくい
- Valkey クライアントの初期化タイミングが不明確

**推奨対策**:
```python
# 改善案: FastAPI Depends を使用した依存性注入
from functools import lru_cache

@lru_cache
def get_job_state_manager() -> JobCreationStateManager:
    return JobCreationStateManager(valkey_client=get_valkey_client())

# エンドポイントでの使用
@router.get("/marp-report/{job_id}")
async def get_marp_report(
    job_id: str,
    state_manager: JobCreationStateManager = Depends(get_job_state_manager),
):
    ...
```

---

## 5. リスク評価

| リスク種別 | 内容 | 影響度 | 発生確率 | 対策優先度 |
|-----------|------|-------|---------|-----------|
| **技術的リスク** | Valkey 接続失敗時のデグレード | 中 | 低 | 中 |
| **技術的リスク** | 同期→非同期の破壊的変更 | 高 | 高 | **高** |
| **技術的リスク** | datetime シリアライズエラー | 中 | 中 | 中 |
| **運用リスク** | L1 キャッシュのメモリ肥大化 | 低 | 低 | 低 |
| **セキュリティリスク** | センシティブデータのログ出力 | 中 | 中 | 中 |
| **ビジネスリスク** | 24時間後のデータ消失 | 低 | 確実 | 低（仕様） |

### 5.1 重要リスク: 同期→非同期の破壊的変更

**現行コード**（job_generator_endpoints.py:96）:
```python
status = job_state_manager.get_status(job_id)  # 同期呼び出し
```

**設計方針**:
```python
status = await job_state_manager.get_status_async(job_id)  # 非同期呼び出し
```

**影響範囲**:
- `expertAgent/app/api/v1/job_generator_endpoints.py` (6箇所)
- `expertAgent/app/api/v1/marp_report_endpoints.py` (1箇所)

**推奨対策**:
1. 同期メソッドを `@deprecated` で維持（後方互換性）
2. 非同期メソッドを新規追加（`get_status_async`, `mark_completed_async` など）
3. 段階的に呼び出し元を非同期に移行

---

## 6. 改善提案

### 6.1 必須改善項目（Must Fix）

#### MF-1: 同期メソッドの後方互換性維持

**問題**: 設計方針では同期→非同期の移行が前提だが、既存コードへの影響が大きい。

**修正案**:
```python
class JobCreationStateManager:
    # 既存の同期メソッドを維持（deprecated）
    def get_status(self, job_id: str) -> Optional[JobCreationStatus]:
        """Deprecated: Use get_status_async instead."""
        return self._memory_cache.get(job_id)

    # 新規の非同期メソッドを追加
    async def get_status_async(self, job_id: str) -> Optional[JobCreationStatus]:
        # L1 check
        if job_id in self._memory_cache:
            return self._memory_cache[job_id]
        # L2 check
        ...
```

#### MF-2: Valkey クライアントの初期化

**問題**: グローバルシングルトンでは Valkey 接続の初期化タイミングが不明確。

**修正案**:
```python
class JobCreationStateManager:
    def __init__(
        self,
        valkey_client: Optional[ValkeyClient] = None,
        ttl_seconds: int = 86400,
    ) -> None:
        self._memory_cache: dict[str, JobCreationStatus] = {}
        self._valkey_client = valkey_client
        self._ttl_seconds = ttl_seconds
        self._valkey_connected = False

    async def connect_valkey(self) -> None:
        """Valkey 接続を確立（アプリ起動時に呼び出し）"""
        if self._valkey_client:
            try:
                await self._valkey_client.connect()
                self._valkey_connected = True
            except Exception as e:
                logger.warning(f"Valkey connection failed, using memory-only: {e}")
```

### 6.2 推奨改善項目（Should Fix）

#### SF-1: 依存性注入パターンの適用

**現状**: グローバルシングルトン `job_state_manager`

**推奨**:
```python
# app/dependencies.py
from functools import lru_cache

@lru_cache
def get_job_state_manager() -> JobCreationStateManager:
    from core.config import settings

    valkey_client = None
    if settings.VALKEY_ENABLED:
        valkey_client = ValkeyClient(
            host=settings.VALKEY_HOST,
            port=settings.VALKEY_PORT,
            db=settings.VALKEY_DB,
        )

    return JobCreationStateManager(
        valkey_client=valkey_client,
        ttl_seconds=settings.VALKEY_TTL,
    )
```

#### SF-2: エラーメッセージの国際化対応準備

**現状**:
```python
msg = "Job not found or expired. Job results are kept for 24 hours."
```

**推奨**: 将来の国際化に備え、メッセージキーを定義
```python
# errors.py
ERROR_JOB_NOT_FOUND = "error.job.not_found_or_expired"
ERROR_MESSAGES = {
    ERROR_JOB_NOT_FOUND: "Job not found or expired. Job results are kept for {ttl_hours} hours.",
}
```

### 6.3 検討事項（Consider）

#### C-1: L1 キャッシュのサイズ制限

**現状**: 明示的なサイズ制限なし

**検討**: LRU キャッシュへの置き換え
```python
from functools import lru_cache
# または
from cachetools import LRUCache

self._memory_cache = LRUCache(maxsize=1000)
```

#### C-2: キャッシュメトリクスの監視

**検討**: Prometheus メトリクスとしてキャッシュ hit/miss を公開
```python
from prometheus_client import Counter

cache_hits = Counter('job_cache_hits_total', 'Cache hits', ['layer'])
cache_misses = Counter('job_cache_misses_total', 'Cache misses', ['layer'])
```

---

## 7. ベストプラクティスとの比較

### 7.1 業界標準との差異

| パターン | 設計方針 | 業界標準 | 差異 |
|---------|---------|---------|------|
| **キャッシュ戦略** | Cache-Aside | Cache-Aside | 一致 |
| **書き込み戦略** | Write-Through | Write-Through | 一致 |
| **フェイルオーバー** | Graceful Degradation | Circuit Breaker | 簡略化 |
| **依存性注入** | グローバルシングルトン | DI Container | 改善推奨 |

### 7.2 代替アーキテクチャ案

#### 代替案1: Circuit Breaker パターン

```python
from circuitbreaker import circuit

class JobCreationStateManager:
    @circuit(failure_threshold=5, recovery_timeout=30)
    async def _valkey_get(self, key: str) -> Optional[dict]:
        return await self._valkey_client.get(key)
```

- **メリット**: 障害時の自動復旧、リソース保護
- **デメリット**: 追加ライブラリ依存、複雑性増加

**結論**: 現時点では Graceful Degradation で十分。将来的に検討。

#### 代替案2: Repository パターン

```python
class JobStateRepository(ABC):
    @abstractmethod
    async def get(self, job_id: str) -> Optional[JobCreationStatus]: ...

    @abstractmethod
    async def save(self, status: JobCreationStatus) -> None: ...

class MemoryJobStateRepository(JobStateRepository): ...
class ValkeyJobStateRepository(JobStateRepository): ...
class CompositeJobStateRepository(JobStateRepository):
    """L1 + L2 を組み合わせた複合リポジトリ"""
    ...
```

- **メリット**: テスト容易性、単一責任の明確化
- **デメリット**: 過度な抽象化、YAGNI 違反の可能性

**結論**: 現設計で十分。大規模リファクタリング時に検討。

---

## 8. 総合評価

### 8.1 レビューサマリ

| 項目 | 評価 |
|------|------|
| **全体評価** | ⭐⭐⭐⭐☆ (4/5) |
| **強み** | 既存インフラ活用、シンプルな2層キャッシュ、明確なデータフロー |
| **弱み** | グローバルシングルトン、同期→非同期の移行戦略が不完全 |

### 8.2 評価詳細

| カテゴリ | スコア | コメント |
|---------|--------|---------|
| **アーキテクチャ** | 4/5 | 2層キャッシュは適切、DI パターンに改善余地 |
| **パフォーマンス** | 5/5 | 目標値は妥当、非同期化で改善 |
| **セキュリティ** | 4/5 | 基本的な対策は十分、センシティブデータ取り扱いに注意 |
| **保守性** | 4/5 | 既存パターンを踏襲、テスト容易性に改善余地 |
| **実現可能性** | 5/5 | 既存コンポーネントの活用で低リスク |

### 8.3 総評

設計方針は全体的に妥当であり、Issue #193 の問題を効果的に解決できる。特に以下の点を評価:

1. **既存インフラの活用**: `ValkeyClient` と既存の Valkey 設定を活用することで、新規インフラ導入のリスクを回避
2. **段階的な移行**: 2層キャッシュにより、Valkey 障害時もインメモリで継続動作
3. **YAGNI の遵守**: JobQueue DB 連携を将来拡張として適切にスコープ外に

ただし、以下の点は実装前に対応が必要:

1. **同期→非同期の移行戦略**: 既存コードへの影響を最小化するため、同期メソッドの維持が必要
2. **グローバルシングルトンの改善**: テスト容易性のため、依存性注入パターンの適用を推奨

---

## 9. 承認判定

### ☑️ 条件付き承認（Conditionally Approved）

以下の条件を満たすことで実装着手を承認:

| 条件 | 必須度 | 対応方針 |
|------|-------|---------|
| MF-1: 同期メソッドの後方互換性維持 | **必須** | 同期メソッドを deprecated として維持 |
| MF-2: Valkey クライアントの初期化方法の明確化 | **必須** | 設計方針書に追記 |
| SF-1: 依存性注入パターンの検討 | 推奨 | Issue 分割時にスコープを判断 |

---

## 10. 次のステップ

1. **設計方針書の更新**: MF-1, MF-2 の対応を設計方針書に反映
2. **Issue 分割**: `/issue-split` でサブ Issue に分割
   - Issue A: `JobCreationStateManager` の非同期拡張
   - Issue B: エンドポイントの非同期呼び出し対応
   - Issue C: 単体テスト・結合テストの作成
3. **TDD 開発**: `/tdd-impl` で実装開始

---

## 関連ドキュメント

- [Issue #193](https://github.com/kewton/MySwiftAgent/issues/193)
- [requirements.md](./requirements.md) - 要件定義書
- [design-policy.md](./design-policy.md) - 設計方針書
- `expertAgent/app/services/job_creation_state.py` - 現行実装
- `expertAgent/app/stores/conversation_store_valkey.py` - 参考実装
