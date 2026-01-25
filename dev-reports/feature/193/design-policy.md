# Issue #193 設計方針書

## Marp Report API: Job ID not found エラー - インメモリ状態管理による永続化問題

**作成日**: 2025-12-05
**Issue**: [#193](https://github.com/kewton/MySwiftAgent/issues/193)
**要件定義書**: [requirements.md](./requirements.md)
**ステータス**: Draft

---

## 1. アーキテクチャ設計

### 1.1 システム構成図

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              myAgentDesk                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                     MarpViewer.svelte                               ││
│  │                           │                                         ││
│  │                           ▼                                         ││
│  │                    marp-api.ts                                      ││
│  └─────────────────────────────────────────────────────────────────────┘│
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ HTTP GET /v1/marp-report/{job_id}
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                             expertAgent                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                  marp_report_endpoints.py                           ││
│  │                           │                                         ││
│  │                           ▼                                         ││
│  │            ┌──────────────────────────────────┐                     ││
│  │            │    JobCreationStateManager       │                     ││
│  │            │  ┌────────────────────────────┐  │                     ││
│  │            │  │  L1: In-Memory Cache       │  │ ◀── Hit: < 1ms      ││
│  │            │  │  (Python dict)             │  │                     ││
│  │            │  └─────────────┬──────────────┘  │                     ││
│  │            │                │ miss            │                     ││
│  │            │  ┌─────────────▼──────────────┐  │                     ││
│  │            │  │  L2: Valkey Persistence    │  │ ◀── Hit: < 10ms     ││
│  │            │  │  (ValkeyClient)            │  │                     ││
│  │            │  └─────────────┬──────────────┘  │                     ││
│  │            │                │ TTL: 24h        │                     ││
│  │            └────────────────┼─────────────────┘                     ││
│  └─────────────────────────────┼───────────────────────────────────────┘│
└────────────────────────────────┼────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              Valkey                                      │
│                    (Redis-compatible KVS)                                │
│                                                                          │
│  Key: job:creation:{job_id}                                              │
│  Value: JSON (JobCreationStatus)                                         │
│  TTL: 86400 seconds (24 hours)                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 レイヤー構成

| レイヤー | コンポーネント | 責務 |
|---------|--------------|------|
| **プレゼンテーション層** | `marp_report_endpoints.py` | HTTPリクエスト処理、レスポンス生成 |
| **ビジネスロジック層** | `JobCreationStateManager` | ジョブ状態管理、キャッシュ制御 |
| **データアクセス層** | `ValkeyClient` | Valkey との通信 |
| **インフラストラクチャ層** | Valkey | 永続化ストレージ |

### 1.3 データフロー

#### Write Path（ジョブ作成完了時）

```
1. job_generator_endpoints.py: ジョブ作成完了
2. JobCreationStateManager.mark_completed()
   2.1 L1 (Memory): ステータス更新
   2.2 L2 (Valkey): 永続化 (TTL: 24h)
```

#### Read Path（スライド取得時）

```
1. GET /v1/marp-report/{job_id}
2. JobCreationStateManager.get_status_async(job_id)
   2.1 L1 (Memory) Check: Hit → Return
   2.2 L1 Miss → L2 (Valkey) Check
       2.2.1 L2 Hit → Populate L1 → Return
       2.2.2 L2 Miss → Return None (404)
```

---

## 2. 技術選定

### 2.1 技術スタック

| カテゴリ | 選定技術 | 選定理由 |
|---------|---------|---------|
| **永続化ストレージ** | Valkey (Redis互換) | 既存インフラ活用、高速、TTL対応 |
| **キャッシュクライアント** | `ValkeyClient` (既存) | 再利用、テスト済み、async対応 |
| **データモデル** | Pydantic `BaseModel` | 既存の `JobCreationStatus` が対応済み |
| **シリアライズ** | JSON | Pydantic `.model_dump()` / `.model_validate()` |

### 2.2 既存コンポーネントの活用

| コンポーネント | ファイル | 活用方法 |
|--------------|---------|---------|
| `ValkeyClient` | `app/services/valkey_client.py` | そのまま利用 |
| `Settings` | `core/config.py` | 既存の `VALKEY_*` 設定を利用 |
| `JobCreationStatus` | `app/services/job_creation_state.py` | Pydantic モデルとして活用 |

### 2.3 Valkey 設定（既存）

```python
# core/config.py - 既に定義済み
VALKEY_ENABLED: bool = Field(default=False)
VALKEY_HOST: str = Field(default="localhost")
VALKEY_PORT: int = Field(default=6379)
VALKEY_DB: int = Field(default=0)
VALKEY_TTL: int = Field(default=86400)  # 24 hours
```

---

## 3. 設計パターン

### 3.1 適用パターン

| パターン | 適用箇所 | 理由 |
|---------|---------|------|
| **Cache-Aside** | `JobCreationStateManager` | L1/L2 キャッシュの読み取り戦略 |
| **Write-Through** | `mark_completed()` | データ整合性確保 |
| **Graceful Degradation** | Valkey 接続失敗時 | 可用性維持（インメモリのみで継続） |

### 3.2 Cache-Aside パターン

```python
async def get_status_async(self, job_id: str) -> Optional[JobCreationStatus]:
    # L1: Memory cache check
    if job_id in self._memory_cache:
        logger.debug(f"L1 cache hit for job_id={job_id}")
        return self._memory_cache[job_id]

    # L2: Valkey check
    if self._valkey_client:
        try:
            data = await self._valkey_client.get(f"job:creation:{job_id}")
            if data:
                logger.debug(f"L2 cache hit for job_id={job_id}")
                status = JobCreationStatus.model_validate(data)
                self._memory_cache[job_id] = status  # Populate L1
                return status
        except Exception as e:
            logger.warning(f"Valkey read failed for job_id={job_id}: {e}")

    logger.debug(f"Cache miss for job_id={job_id}")
    return None
```

### 3.3 Write-Through パターン

```python
async def mark_completed_async(
    self,
    job_id: str,
    job_master_id: Optional[str] = None,
    result: Optional[dict[str, Any]] = None,
) -> None:
    # Update L1 (Memory)
    if job_id in self._memory_cache:
        status = self._memory_cache[job_id]
        status.status = "completed"
        status.progress = 100
        status.end_time = datetime.now()
        status.job_master_id = job_master_id
        status.result = result

        # Write-through to L2 (Valkey)
        if self._valkey_client:
            try:
                await self._valkey_client.set(
                    f"job:creation:{job_id}",
                    status.model_dump(mode="json"),
                    ttl=self._ttl_seconds,
                )
                logger.info(f"Persisted job status to Valkey: job_id={job_id}")
            except Exception as e:
                logger.error(f"Valkey write failed for job_id={job_id}: {e}")
```

---

## 4. データモデル設計

### 4.1 JobCreationStatus（既存・変更なし）

```python
class JobCreationStatus(BaseModel):
    """Job creation status model."""

    job_id: str
    status: str  # 'creating' | 'completed' | 'failed'
    progress: int  # 0-100
    start_time: datetime
    end_time: Optional[datetime] = None
    job_master_id: Optional[str] = None
    error_message: Optional[str] = None
    result: Optional[dict[str, Any]] = None
```

**注**: 既に Pydantic `BaseModel` を継承しているため、追加の JSON シリアライズ対応は不要。

### 4.2 Valkey キー設計

| 項目 | 値 |
|------|-----|
| **Key Format** | `job:creation:{job_id}` |
| **Value** | JSON (JobCreationStatus.model_dump()) |
| **TTL** | 86400 seconds (24 hours) |
| **Namespace** | `job:creation:` |

#### データサンプル

```json
{
  "job_id": "a47a3db4-dd83-49a5-91b6-e4c7c1d939e6",
  "status": "completed",
  "progress": 100,
  "start_time": "2025-12-05T10:30:00",
  "end_time": "2025-12-05T10:30:45",
  "job_master_id": "jm_abc123",
  "error_message": null,
  "result": {
    "status": "success",
    "job_id": "a47a3db4-dd83-49a5-91b6-e4c7c1d939e6",
    "task_breakdown": [...],
    "requirement_relaxation_suggestions": [...]
  }
}
```

---

## 5. API設計

### 5.1 既存API（変更なし）

```
GET /v1/marp-report/{job_id}?format={format}
```

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| `job_id` | string (path) | ジョブID (UUID) |
| `format` | string (query) | 出力形式: html, pdf, png |

### 5.2 エラーレスポンス改善

| ステータス | 現在のメッセージ | 改善後のメッセージ |
|-----------|----------------|------------------|
| 404 | `Job ID not found: {job_id}` | `Job not found or expired. Job results are kept for 24 hours.` |
| 400 | `Job is not completed yet` | (変更なし) |
| 500 | `Internal server error` | (変更なし) |

---

## 6. セキュリティ設計

### 6.1 脅威分析

| 脅威 | リスク | 対策 |
|------|-------|------|
| Valkey への不正アクセス | 低 | 内部ネットワークのみ、認証なし（既存設計） |
| Job ID の推測攻撃 | 低 | UUID v4 による十分なエントロピー |
| データ漏洩 | 低 | TTL による自動削除（24時間） |

### 6.2 セキュリティ対策

- **入力検証**: job_id は UUID 形式を検証（既存）
- **ログ**: センシティブデータ（result内容）のログ出力を避ける
- **TTL**: 24時間で自動削除されるため、長期的なデータ残留リスクなし

---

## 7. パフォーマンス設計

### 7.1 パフォーマンス目標

| メトリクス | 目標値 | 測定方法 |
|-----------|--------|---------|
| L1 キャッシュヒット時 | < 1ms | ログ出力 |
| L2 キャッシュヒット時 | < 10ms | ログ出力 |
| キャッシュミス時 | < 20ms | ログ出力 |

### 7.2 キャッシング戦略

```
┌─────────────────────────────────────────────────────────────┐
│                    Request Flow                              │
├─────────────────────────────────────────────────────────────┤
│  1. Check L1 (Memory) ─────────────────────────▶ HIT: Return│
│     │                                                        │
│     ▼ MISS                                                   │
│  2. Check L2 (Valkey) ─────────────────────────▶ HIT:       │
│     │                                            Populate L1 │
│     │                                            Return      │
│     ▼ MISS                                                   │
│  3. Return 404                                               │
└─────────────────────────────────────────────────────────────┘
```

### 7.3 メモリ管理

| 項目 | 対策 |
|------|------|
| L1 キャッシュサイズ | 明示的な制限なし（プロセス再起動でクリア） |
| L1 エビクション | 既存の `cleanup_old_jobs()` を非同期化 |
| L2 TTL | 24時間で自動削除 |

---

## 8. 設計上の決定事項とトレードオフ

### 8.1 主要な設計決定

| 決定事項 | 採用案 | 代替案 | 理由 |
|---------|--------|-------|------|
| 永続化方式 | Valkey | JobQueue DB | 既存インフラ活用、高速、TTL対応 |
| キャッシュ構造 | 2層 (L1+L2) | L2のみ | 高頻度アクセス時のパフォーマンス |
| API互換性 | 同期→非同期 | 完全同期維持 | Valkey は非同期、FastAPI は async 推奨 |
| エラーハンドリング | Graceful Degradation | Fail Fast | 可用性優先 |

### 8.2 トレードオフ分析

#### 決定1: Valkey vs JobQueue DB

| 観点 | Valkey | JobQueue DB |
|------|--------|-------------|
| **パフォーマンス** | O(1) 読み取り | HTTP + SQL オーバーヘッド |
| **永続性** | TTL 後に消失 | 永続 |
| **複雑性** | 低（既存インフラ） | 中（スキーマ変更必要） |
| **可用性** | Valkey 依存 | JobQueue 依存 |

**結論**: パフォーマンスと複雑性を優先し、Valkey を採用。24時間 TTL は実用上十分。

#### 決定2: 同期 vs 非同期 API

| 観点 | 非同期 (async) | 同期 |
|------|---------------|------|
| **Valkey 連携** | ネイティブ対応 | 同期ラッパー必要 |
| **スケーラビリティ** | 高い | 低い |
| **既存コード影響** | `get_status` → `get_status_async` | なし |

**結論**: 非同期を採用。エンドポイントは既に async なので自然に統合可能。

### 8.3 将来の拡張性

| 拡張項目 | 対応方針 |
|---------|---------|
| マルチインスタンス | Valkey がステート共有を担保（対応済み） |
| JobQueue DB フォールバック | L3 として追加可能（今回はスコープ外） |
| TTL 設定の動的変更 | 環境変数で対応（今回はスコープ外） |

---

## 9. 実装計画

### 9.1 変更対象ファイル

| ファイル | 変更内容 | 影響度 |
|---------|---------|-------|
| `expertAgent/app/services/job_creation_state.py` | Valkey 連携追加、非同期メソッド追加 | 高 |
| `expertAgent/app/api/v1/job_generator_endpoints.py` | 非同期呼び出しに変更 | 中 |
| `expertAgent/app/api/v1/marp_report_endpoints.py` | 非同期呼び出しに変更、エラーメッセージ改善 | 中 |
| `expertAgent/core/config.py` | 変更なし（既存設定を利用） | なし |

### 9.2 新規追加ファイル

| ファイル | 内容 |
|---------|------|
| `expertAgent/tests/unit/test_job_creation_state_valkey.py` | Valkey 連携の単体テスト |
| `tests/integration/test_marp_report_persistence.py` | 永続化の結合テスト |

### 9.3 実装ステップ

```
Phase 1: JobCreationStateManager 拡張
├── 1.1 非同期メソッドの追加 (get_status_async, mark_completed_async, etc.)
├── 1.2 ValkeyClient 統合
├── 1.3 2層キャッシュロジック実装
└── 1.4 Graceful Degradation 実装

Phase 2: エンドポイント更新
├── 2.1 marp_report_endpoints.py の非同期対応
├── 2.2 job_generator_endpoints.py の非同期対応
└── 2.3 エラーメッセージ改善

Phase 3: テスト
├── 3.1 単体テスト作成
├── 3.2 結合テスト作成
└── 3.3 受入テスト実行
```

---

## 10. CLAUDE.md 原則への準拠

### 10.1 SOLID原則

| 原則 | 対応 |
|------|------|
| **S** (単一責任) | `JobCreationStateManager` はジョブ状態管理のみを担当 |
| **O** (開放/閉鎖) | Valkey 連携を追加しても既存インターフェース維持 |
| **L** (リスコフ置換) | N/A（継承なし） |
| **I** (インターフェース分離) | 同期/非同期メソッドを分離 |
| **D** (依存性逆転) | `ValkeyClient` を注入可能に設計 |

### 10.2 KISS / YAGNI / DRY

| 原則 | 対応 |
|------|------|
| **KISS** | 既存の `ValkeyClient` をそのまま利用、新規コンポーネント最小化 |
| **YAGNI** | JobQueue DB 連携は将来拡張として除外 |
| **DRY** | `ConversationStoreValkey` のパターンを参考に実装 |

---

## 11. リスクと緩和策

| リスク | 影響度 | 発生確率 | 緩和策 |
|-------|--------|---------|-------|
| Valkey 接続失敗 | 中 | 低 | Graceful Degradation（インメモリのみで継続） |
| datetime シリアライズ | 中 | 中 | Pydantic の `mode="json"` で ISO 形式に変換 |
| 既存テスト失敗 | 中 | 中 | モックで Valkey 依存を分離 |
| 同期→非同期の破壊的変更 | 高 | 高 | 同期メソッドも維持（deprecated） |

---

## 関連ドキュメント

- [Issue #193](https://github.com/kewton/MySwiftAgent/issues/193)
- [requirements.md](./requirements.md) - 要件定義書
- `expertAgent/app/services/job_creation_state.py` - 現行実装
- `expertAgent/app/stores/conversation_store_valkey.py` - 参考実装
