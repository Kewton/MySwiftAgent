# Issue #193 要件定義書

## Marp Report API: Job ID not found エラー - インメモリ状態管理による永続化問題

**作成日**: 2025-12-05
**Issue**: [#193](https://github.com/kewton/MySwiftAgent/issues/193)
**ステータス**: Draft

---

## 現状分析

### 確認した現在のソースコード状態

| ファイル | 状態 | 問題点 |
|---------|------|-------|
| `expertAgent/app/services/job_creation_state.py` | **未修正** | インメモリ (`dict`) で状態管理 |
| `expertAgent/app/api/v1/marp_report_endpoints.py` | **未修正** | `job_state_manager.get_status()` が None の場合 404 |
| `myAgentDesk/src/lib/services/marp-api.ts` | **未修正** | 問題なし（フロント側） |
| `myAgentDesk/src/lib/components/create_job/MarpViewer.svelte` | **未修正** | 問題なし（フロント側） |

### 既存インフラの状況

| コンポーネント | 状態 | 活用可能性 |
|--------------|------|-----------|
| **Valkey/Redis** | 稼働中 | `ValkeyClient` が既に実装済み（TTL対応） |
| **JobQueue DB** | 稼働中 | `JobResult.response_body` に JSON 格納可能だが、スキーマ変更が必要 |

### 問題の再現フロー

```
1. ユーザーが /create_job でジョブを作成
2. createJobAsync でバックエンドに非同期ジョブ作成をリクエスト
3. JobCreationStateManager がインメモリでジョブ状態を保存
4. ジョブ作成完了後、createdJobId がフロントエンドに設定される
5. ユーザーが「スライド」タブをクリック
6. MarpViewer が getMarpReport(jobId) を呼び出す
7. GET /v1/marp-report/{job_id} がバックエンドで実行される
8. job_state_manager.get_status(job_id) でジョブ状態を取得しようとする
9. **問題**: サーバー再起動等でインメモリ状態が消失している場合、None が返る
10. エラー: "Job ID not found: {job_id}"
```

---

## 1. ユーザーストーリー

```
As a MyAgentDesk ユーザー
I want to ジョブ作成後いつでもスライドを表示できること
So that サーバー再起動やページリロードに関係なく、ジョブ結果をプレゼンテーション形式で確認できる
```

---

## 2. 受入条件（Acceptance Criteria）

### AC-1: サーバー再起動耐性
- **Given**: ユーザーがジョブを作成し、スライドを表示している
- **When**: サーバーが再起動される
- **Then**: ページをリロードしてもスライドが表示される

### AC-2: ページリロード耐性
- **Given**: ユーザーがジョブを作成完了した
- **When**: ブラウザでページをリロードする
- **Then**: 「スライド」タブをクリックするとスライドが正常に表示される

### AC-3: 長時間経過後のアクセス
- **Given**: ユーザーが1時間以上前にジョブを作成した
- **When**: 「スライド」タブをクリックする
- **Then**: スライドが正常に表示される（最低24時間保持）

### AC-4: 存在しないジョブID
- **Given**: 存在しないジョブIDでアクセスした場合
- **When**: `/v1/marp-report/{job_id}` を呼び出す
- **Then**: 適切なエラーメッセージが返される（「Job ID not found」ではなく、より具体的なメッセージ）

---

## 3. 機能要件

### 3.1 必須機能（Must Have）

| ID | 要件 | 詳細 |
|----|------|------|
| M-1 | ジョブ結果の永続化 | ジョブ作成完了時に結果をValkey/Redisに保存 |
| M-2 | TTL付きストレージ | 24時間のTTLで自動クリーンアップ |
| M-3 | フォールバック機構 | インメモリキャッシュ + Valkey の2層構造 |
| M-4 | 後方互換性 | 既存API (`GET /v1/marp-report/{job_id}`) のインターフェース維持 |

### 3.2 あると良い機能（Nice to Have）

| ID | 要件 | 詳細 |
|----|------|------|
| N-1 | TTL設定の環境変数化 | `JOB_RESULT_TTL_SECONDS` で設定可能 |
| N-2 | キャッシュヒット率の監視 | Valkey キャッシュの hit/miss をログ出力 |

### 3.3 将来的な拡張（Future Enhancement）

| ID | 要件 | 詳細 |
|----|------|------|
| F-1 | JobQueue DB連携 | Valkeyからデータが消失した場合、JobQueue DBからフォールバック |
| F-2 | マルチインスタンス対応 | 複数の expertAgent インスタンス間でのステート共有 |

---

## 4. 非機能要件

### 4.1 パフォーマンス要件
- Valkey からのジョブ結果取得: **10ms 以下**
- インメモリキャッシュヒット時: **1ms 以下**

### 4.2 可用性要件
- Valkey が利用不可の場合でも、インメモリキャッシュで動作継続
- Valkey 接続エラー時は警告ログを出力し、インメモリのみで動作

### 4.3 データ保持要件
- ジョブ結果の保持期間: **24時間**（TTL）
- Valkey ダウン時: サーバー再起動まではインメモリで保持

---

## 5. 技術的制約

### 5.1 使用する技術スタック
- **永続化ストレージ**: Valkey (Redis互換) - 既存の `ValkeyClient` を活用
- **キャッシュ層**: Python dict（既存の `JobCreationStateManager` を拡張）
- **シリアライゼーション**: JSON

### 5.2 既存システムとの連携

```
┌──────────────────────────────────────────────────────────────┐
│                    expertAgent                                │
│  ┌─────────────────┐    ┌─────────────────────────────────┐  │
│  │ marp_report_    │───▶│  JobCreationStateManager        │  │
│  │ endpoints.py    │    │  ┌─────────────────────────────┐│  │
│  └─────────────────┘    │  │ L1: In-memory Cache (dict)  ││  │
│                         │  └──────────────┬──────────────┘│  │
│                         │                 │ miss          │  │
│                         │  ┌──────────────▼──────────────┐│  │
│                         │  │ L2: Valkey (ValkeyClient)   ││  │
│                         │  └─────────────────────────────┘│  │
│                         └─────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### 5.3 Valkey キー設計

```
Key Format: job:creation:{job_id}
Value: JSON serialized JobCreationStatus
TTL: 86400 seconds (24 hours)
```

### 5.4 データモデル

現在の `JobCreationStatus` dataclass:

```python
@dataclass
class JobCreationStatus:
    job_id: str
    status: str  # "creating", "completed", "failed"
    progress: int  # 0-100
    start_time: datetime
    end_time: Optional[datetime] = None
    job_master_id: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
```

JSON シリアライズ対応のために `to_dict()` / `from_dict()` メソッドの追加が必要。

---

## 6. リスクと対策

### 6.1 技術的リスク

| リスク | 影響度 | 発生確率 | 対策 |
|-------|--------|---------|------|
| Valkey 接続失敗 | 中 | 低 | インメモリキャッシュでグレースフルデグレード |
| シリアライゼーションエラー | 高 | 低 | `JobCreationStatus` の dataclass を JSON 対応に修正 |
| 既存テストの破損 | 中 | 中 | モックを使用してValkey依存を分離 |

### 6.2 ビジネスリスク

| リスク | 影響度 | 発生確率 | 対策 |
|-------|--------|---------|------|
| ユーザー体験の劣化（移行時） | 低 | 低 | 後方互換性を維持した段階的移行 |

---

## 7. 解決策オプションの比較

### Option 1: Valkey 永続化（推奨）

| 項目 | 評価 |
|------|------|
| 実現可能性 | 高い - 既存の `ValkeyClient` をそのまま活用可能 |
| メリット | 高速、TTL自動クリーンアップ、マルチインスタンス対応 |
| デメリット | Valkey 依存 |
| 工数見積 | 小 |

### Option 2: JobQueue DB 連携

| 項目 | 評価 |
|------|------|
| 実現可能性 | 中程度 - スキーマ変更が必要 |
| メリット | 永続化確実、既存スキーマ活用 |
| デメリット | スキーマ変更必要、HTTP通信オーバーヘッド |
| 工数見積 | 中 |

### Option 3: ハイブリッド（インメモリ + Valkey + DB）

| 項目 | 評価 |
|------|------|
| 実現可能性 | 高い |
| メリット | 柔軟、高可用性 |
| デメリット | 複雑性増加 |
| 工数見積 | 大 |

### 推奨: Option 1 - Valkey 永続化

**理由:**
1. 既存の `ValkeyClient` をそのまま活用可能
2. TTL による自動クリーンアップで運用負荷が低い
3. マルチインスタンス環境でも自然に対応可能
4. JobQueue のスキーマ変更が不要

---

## 8. 実装方針

### 8.1 `JobCreationStateManager` の拡張

```python
class JobCreationStateManager:
    def __init__(self, valkey_client: Optional[ValkeyClient] = None) -> None:
        self._memory_cache: dict[str, JobCreationStatus] = {}
        self._valkey_client = valkey_client
        self._ttl_seconds = 86400  # 24 hours

    async def get_status(self, job_id: str) -> Optional[JobCreationStatus]:
        # L1: Memory cache
        if job_id in self._memory_cache:
            return self._memory_cache[job_id]

        # L2: Valkey
        if self._valkey_client:
            data = await self._valkey_client.get(f"job:creation:{job_id}")
            if data:
                status = JobCreationStatus.from_dict(data)
                self._memory_cache[job_id] = status  # Populate L1
                return status

        return None

    async def mark_completed(
        self,
        job_id: str,
        job_master_id: Optional[str] = None,
        result: Optional[dict[str, Any]] = None,
    ) -> None:
        # Update memory cache
        if job_id in self._memory_cache:
            self._memory_cache[job_id].status = "completed"
            self._memory_cache[job_id].result = result
            self._memory_cache[job_id].job_master_id = job_master_id
            self._memory_cache[job_id].end_time = datetime.now()

        # Persist to Valkey
        if self._valkey_client and job_id in self._memory_cache:
            await self._valkey_client.set(
                f"job:creation:{job_id}",
                self._memory_cache[job_id].to_dict(),
                ttl=self._ttl_seconds,
            )
```

---

## 9. 影響範囲

### 変更が必要なファイル

| ファイル | 変更内容 |
|---------|---------|
| `expertAgent/app/services/job_creation_state.py` | Valkey連携の追加、2層キャッシュ実装 |
| `expertAgent/app/api/v1/job_generator_endpoints.py` | `JobCreationStateManager` の初期化変更 |
| `expertAgent/app/api/v1/marp_report_endpoints.py` | 非同期対応（`async def get_status`） |
| `expertAgent/core/config.py` | `JOB_RESULT_TTL_SECONDS` 設定追加 |

### テスト追加

| テストファイル | テスト内容 |
|--------------|-----------|
| `tests/unit/test_job_creation_state_valkey.py` | Valkey連携の単体テスト |
| `tests/integration/test_marp_report_persistence.py` | サーバー再起動後のスライド表示 |

---

## 10. 次のステップ

1. **設計レビュー**: この要件定義の承認
2. **Issue分割**: `/issue-split` でサブIssueに分割
3. **TDD開発**: `/tdd-impl` で実装開始

---

## 関連ドキュメント

- [Issue #193](https://github.com/kewton/MySwiftAgent/issues/193)
- `expertAgent/app/services/job_creation_state.py`
- `expertAgent/app/services/valkey_client.py`
- `expertAgent/app/api/v1/marp_report_endpoints.py`
