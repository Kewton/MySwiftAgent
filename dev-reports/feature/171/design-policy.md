# Issue #171 設計方針書

## Issue: 診断情報取得API実装（拡張版）

**Issue番号**: #171
**作成日**: 2025-11-15
**作成者**: Claude Code
**親Issue**: #152（要件定義エージェントへのMLOps導入）

---

## 1. 設計方針の概要

Issue #171は、conversation_idベースの診断情報取得だけでなく、**job/user/project/workflow単位での分析を可能にする**診断APIを実装します。これにより、MLOps基盤として必要な可観測性と分析機能を提供します。

### 主要な設計決定

1. **セカンダリインデックス戦略**: Redis SETを活用した高速検索
2. **後方互換性保証**: 既存のconversation_idベース操作を維持
3. **メタデータ取得元**: リクエストコンテキスト経由
4. **ページネーション**: デフォルト100件、最大1000件
5. **パフォーマンス目標**: 単一取得1秒、一覧取得2秒以内

---

## 2. データモデル設計

### 2.1 Valkeyデータ構造拡張

#### 現在の実装（Issue #169）

```python
# キー: conversation:{conversation_id}
conversation_data = {
    "conversation_id": "conv-123",
    "messages": [
        {"role": "user", "content": "...", "timestamp": "..."},
        {"role": "assistant", "content": "...", "timestamp": "..."}
    ],
    "metadata": {
        "updated_at": "2025-11-15T10:30:00Z",
        "trace_id": "trace-456",
        "prompt_version": "v1.0",
        # **kwargs で追加フィールド可能
    }
}
```

#### 拡張後の実装（Issue #171）

```python
# キー: conversation:{conversation_id}
conversation_data = {
    "conversation_id": "conv-123",
    "messages": [...],  # 同上
    "metadata": {
        # 既存フィールド
        "updated_at": "2025-11-15T10:30:00Z",
        "trace_id": "trace-456",
        "prompt_version": "v1.0",

        # 拡張フィールド（必須）
        "job_id": "job_12345",           # ジョブID
        "task_id": "task_67890",         # タスクID
        "workflow_id": "workflow_abc",   # ワークフローID
        "user_id": "user_alice",         # ユーザーID
        "project_id": "project_x",       # プロジェクトID

        # 拡張フィールド（オプション）
        "organization_id": "org_123",    # 組織ID（将来の拡張）
        "environment": "production"       # 環境（dev/staging/production）
    }
}
```

### 2.2 セカンダリインデックス設計

Redis SETを使用してセカンダリインデックスを実装：

```python
# Job単位インデックス
# key: job_index:{job_id}
# value: Set[conversation_id]
"job_index:job_12345" -> {"conv-123", "conv-456", "conv-789"}

# User単位インデックス
# key: user_index:{user_id}
"user_index:user_alice" -> {"conv-123", "conv-456"}

# Project単位インデックス
# key: project_index:{project_id}
"project_index:project_x" -> {"conv-123", "conv-789"}

# Workflow単位インデックス
# key: workflow_index:{workflow_id}
"workflow_index:workflow_abc" -> {"conv-123"}

# 日付単位インデックス
# key: date_index:{YYYY-MM-DD}
"date_index:2025-11-15" -> {"conv-123", "conv-456", "conv-789"}
```

#### インデックス更新戦略

```python
async def save_conversation_with_indexes(
    conversation_id: str,
    messages: List[Dict[str, Any]],
    job_id: str,
    user_id: str,
    project_id: str,
    workflow_id: str,
    **kwargs
) -> bool:
    """会話保存とインデックス更新をトランザクション的に実行"""

    # 1. 会話データ保存
    await conversation_store.save_conversation(
        conversation_id=conversation_id,
        messages=messages,
        job_id=job_id,
        user_id=user_id,
        project_id=project_id,
        workflow_id=workflow_id,
        **kwargs
    )

    # 2. セカンダリインデックス更新（並行実行）
    await asyncio.gather(
        index_manager.add_to_job_index(job_id, conversation_id),
        index_manager.add_to_user_index(user_id, conversation_id),
        index_manager.add_to_project_index(project_id, conversation_id),
        index_manager.add_to_workflow_index(workflow_id, conversation_id),
        index_manager.add_to_date_index(date.today(), conversation_id)
    )

    return True
```

---

## 3. メタデータ取得元の設計

### 3.1 取得方法の選択肢

#### Option A: リクエストコンテキスト（採用）

```python
from contextvars import ContextVar

# グローバルコンテキスト変数
current_job_id: ContextVar[Optional[str]] = ContextVar("current_job_id", default=None)
current_user_id: ContextVar[Optional[str]] = ContextVar("current_user_id", default=None)
current_project_id: ContextVar[Optional[str]] = ContextVar("current_project_id", default=None)
current_workflow_id: ContextVar[Optional[str]] = ContextVar("current_workflow_id", default=None)

# ミドルウェアで設定
@app.middleware("http")
async def set_context_middleware(request: Request, call_next):
    # リクエストヘッダーまたはクエリパラメータから取得
    job_id = request.headers.get("X-Job-ID") or request.query_params.get("job_id")
    user_id = request.headers.get("X-User-ID") or request.query_params.get("user_id")
    project_id = request.headers.get("X-Project-ID") or request.query_params.get("project_id")
    workflow_id = request.headers.get("X-Workflow-ID") or request.query_params.get("workflow_id")

    # コンテキストに設定
    current_job_id.set(job_id)
    current_user_id.set(user_id)
    current_project_id.set(project_id)
    current_workflow_id.set(workflow_id)

    response = await call_next(request)
    return response
```

**利点**:
- グローバルにアクセス可能
- 関数引数を汚染しない
- FastAPIの依存性注入と相性が良い

**欠点**:
- デバッグが難しい場合がある
- テストでモックが必要

#### Option B: リクエストヘッダー（補完的に使用）

```python
# カスタムヘッダー経由
X-Job-ID: job_12345
X-User-ID: user_alice
X-Project-ID: project_x
X-Workflow-ID: workflow_abc
```

**利点**:
- 明示的で分かりやすい
- リバースプロキシで設定可能

**欠点**:
- すべてのリクエストでヘッダー設定が必要
- クライアントの実装負担が増加

### 3.2 採用する設計

**リクエストコンテキスト（Option A）を主とし、リクエストヘッダー（Option B）から値を取得する**

```python
# expertAgent/app/middleware/context_middleware.py
from contextvars import ContextVar
from fastapi import Request
from typing import Optional

# グローバルコンテキスト変数
current_job_id: ContextVar[Optional[str]] = ContextVar("current_job_id", default=None)
current_user_id: ContextVar[Optional[str]] = ContextVar("current_user_id", default=None)
current_project_id: ContextVar[Optional[str]] = ContextVar("current_project_id", default=None)
current_workflow_id: ContextVar[Optional[str]] = ContextVar("current_workflow_id", default=None)

async def set_request_context(request: Request):
    """リクエストコンテキストを設定"""
    # ヘッダーから取得（優先度1）
    job_id = request.headers.get("X-Job-ID")
    user_id = request.headers.get("X-User-ID")
    project_id = request.headers.get("X-Project-ID")
    workflow_id = request.headers.get("X-Workflow-ID")

    # クエリパラメータから取得（優先度2、フォールバック）
    if not job_id:
        job_id = request.query_params.get("job_id")
    if not user_id:
        user_id = request.query_params.get("user_id")
    if not project_id:
        project_id = request.query_params.get("project_id")
    if not workflow_id:
        workflow_id = request.query_params.get("workflow_id")

    # コンテキストに設定
    current_job_id.set(job_id)
    current_user_id.set(user_id)
    current_project_id.set(project_id)
    current_workflow_id.set(workflow_id)
```

---

## 4. API設計

### 4.1 エンドポイント仕様

#### Endpoint 1: 単一会話診断情報取得

```
GET /v1/chat/diagnostics/{conversation_id}
```

**レスポンス**:
```json
{
  "conversation_id": "conv-123",
  "metadata": {
    "job_id": "job_12345",
    "task_id": "task_67890",
    "workflow_id": "workflow_abc",
    "user_id": "user_alice",
    "project_id": "project_x",
    "trace_id": "trace-456",
    "prompt_version": "v1.0",
    "updated_at": "2025-11-15T10:30:00Z"
  },
  "system_prompt": "You are an AI assistant...",
  "messages": [
    {
      "role": "user",
      "content": "Hello",
      "timestamp": "2025-11-15T10:30:00Z",
      "token_count": 5
    },
    {
      "role": "assistant",
      "content": "Hi! How can I help?",
      "timestamp": "2025-11-15T10:30:05Z",
      "token_count": 8
    }
  ],
  "token_usage": {
    "prompt_tokens": 100,
    "completion_tokens": 50,
    "total_tokens": 150
  },
  "langfuse_trace": {
    "trace_id": "trace-456",
    "trace_url": "http://localhost:3000/traces/trace-456"
  }
}
```

#### Endpoint 2: 会話一覧取得（フィルタリング対応）

```
GET /v1/chat/diagnostics?job_id={job_id}&user_id={user_id}&project_id={project_id}&workflow_id={workflow_id}&start_date={YYYY-MM-DD}&end_date={YYYY-MM-DD}&limit=100&offset=0
```

**クエリパラメータ**:
- `job_id` (optional): Job ID でフィルタ
- `user_id` (optional): User ID でフィルタ
- `project_id` (optional): Project ID でフィルタ
- `workflow_id` (optional): Workflow ID でフィルタ
- `start_date` (optional): 開始日（YYYY-MM-DD）
- `end_date` (optional): 終了日（YYYY-MM-DD）
- `limit` (optional, default=100, max=1000): 取得件数
- `offset` (optional, default=0): オフセット

**レスポンス**:
```json
{
  "conversations": [
    {
      "conversation_id": "conv-123",
      "metadata": {...},
      "summary": {
        "message_count": 10,
        "total_tokens": 1500,
        "duration_seconds": 120
      }
    }
  ],
  "pagination": {
    "total": 456,
    "limit": 100,
    "offset": 0,
    "has_next": true
  }
}
```

### 4.2 フィルタリングロジック

```python
async def list_conversations(
    job_id: Optional[str] = None,
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100,
    offset: int = 0
) -> DiagnosticListResponse:
    """会話一覧取得（フィルタリング対応）"""

    # 1. セカンダリインデックスから候補取得
    candidate_sets = []

    if job_id:
        candidate_sets.append(await index_manager.get_job_index(job_id))
    if user_id:
        candidate_sets.append(await index_manager.get_user_index(user_id))
    if project_id:
        candidate_sets.append(await index_manager.get_project_index(project_id))
    if workflow_id:
        candidate_sets.append(await index_manager.get_workflow_index(workflow_id))

    # 日付範囲フィルタ
    if start_date or end_date:
        date_sets = await index_manager.get_date_range_index(start_date, end_date)
        candidate_sets.append(date_sets)

    # 2. Set intersection（積集合）で絞り込み
    if not candidate_sets:
        # フィルタなし: 全会話取得（非推奨、ページネーション必須）
        conversation_ids = await get_all_conversation_ids()
    else:
        # 複数フィルタの AND 条件
        conversation_ids = set.intersection(*candidate_sets)

    # 3. ページネーション適用
    total = len(conversation_ids)
    conversation_ids_page = sorted(conversation_ids)[offset:offset+limit]

    # 4. 会話データ取得（並行実行）
    conversations = await asyncio.gather(*[
        get_conversation(conv_id) for conv_id in conversation_ids_page
    ])

    return DiagnosticListResponse(
        conversations=conversations,
        pagination=PaginationMetadata(
            total=total,
            limit=limit,
            offset=offset,
            has_next=(offset + limit < total)
        )
    )
```

---

## 5. Langfuse統合拡張

### 5.1 タグ付け戦略

Langfuseにjob_id, user_id, project_id, workflow_idをタグとして追加：

```python
from langfuse import Langfuse

langfuse = Langfuse()

# トレース作成時にタグ付け
trace = langfuse.trace(
    name="requirement_definition",
    user_id=user_id,  # Langfuse組み込みフィールド
    metadata={
        "job_id": job_id,
        "task_id": task_id,
        "workflow_id": workflow_id,
        "project_id": project_id,
    },
    tags=[
        f"job:{job_id}",
        f"user:{user_id}",
        f"project:{project_id}",
        f"workflow:{workflow_id}"
    ]
)
```

### 5.2 Langfuseダッシュボードでのフィルタリング

Langfuse UI上でタグベースのフィルタリングが可能：

```
# Langfuse UIでのフィルタ例
tags: job:job_12345
tags: user:user_alice
tags: project:project_x
```

---

## 6. パフォーマンス最適化

### 6.1 レスポンスタイム目標

| 操作 | 目標 | 最大許容 |
|------|------|---------|
| 単一会話取得 | 500ms | 1秒 |
| 一覧取得（100件） | 1秒 | 2秒 |
| 一覧取得（1000件） | 5秒 | 10秒 |

### 6.2 最適化戦略

#### 6.2.1 セカンダリインデックスの最適化

```python
# Redis SET intersection（ネイティブ実装、高速）
# SINTER job_index:job_12345 user_index:user_alice project_index:project_x
intersection = await redis_client.sinter(
    f"job_index:{job_id}",
    f"user_index:{user_id}",
    f"project_index:{project_id}"
)
```

#### 6.2.2 バッチ取得

```python
# Pipeline使用で複数会話を一括取得
async def get_conversations_batch(conversation_ids: List[str]) -> List[Dict]:
    pipeline = redis_client.pipeline()
    for conv_id in conversation_ids:
        pipeline.get(f"conversation:{conv_id}")
    results = await pipeline.execute()
    return [json.loads(r) for r in results if r]
```

#### 6.2.3 キャッシュ戦略

```python
# 頻繁にアクセスされるJob/Userのインデックスをキャッシュ
from functools import lru_cache
from datetime import timedelta

@lru_cache(maxsize=1000)
async def get_job_index_cached(job_id: str) -> Set[str]:
    """Job インデックスをキャッシュ（TTL: 5分）"""
    return await index_manager.get_job_index(job_id)
```

---

## 7. セキュリティ考慮事項

### 7.1 認証・認可（Phase 1では未実装、将来の拡張）

```python
# 将来の実装例
async def check_access_permission(
    user_id: str,
    conversation_id: str
) -> bool:
    """ユーザーが会話にアクセスする権限があるか確認"""
    conversation = await get_conversation(conversation_id)

    # 自分の会話か確認
    if conversation["metadata"]["user_id"] == user_id:
        return True

    # 同じプロジェクトメンバーか確認
    if await is_project_member(user_id, conversation["metadata"]["project_id"]):
        return True

    return False
```

### 7.2 機密情報のマスキング

```python
def mask_sensitive_data(conversation: Dict) -> Dict:
    """機密情報をマスク"""
    # プロンプト内のAPIキー、パスワード等をマスク
    for message in conversation["messages"]:
        message["content"] = mask_api_keys(message["content"])
        message["content"] = mask_passwords(message["content"])

    return conversation
```

---

## 8. 後方互換性保証

### 8.1 既存データの扱い

```python
async def get_conversation_with_fallback(conversation_id: str) -> Dict:
    """後方互換性を持った会話取得"""
    conversation = await conversation_store.get_conversation(conversation_id)

    if not conversation:
        return None

    # メタデータが存在しない場合のデフォルト値
    metadata = conversation.get("metadata", {})
    metadata.setdefault("job_id", "unknown")
    metadata.setdefault("user_id", "unknown")
    metadata.setdefault("project_id", "default")
    metadata.setdefault("workflow_id", "unknown")

    conversation["metadata"] = metadata
    return conversation
```

### 8.2 インデックスの遅延構築

```python
async def rebuild_indexes_for_old_data():
    """既存データに対してインデックスを遅延構築"""
    all_conversations = await get_all_conversations()

    for conversation in all_conversations:
        metadata = conversation.get("metadata", {})

        # メタデータが存在する場合のみインデックス構築
        if "job_id" in metadata:
            await index_manager.add_to_job_index(
                metadata["job_id"],
                conversation["conversation_id"]
            )
        # 以下同様...
```

---

## 9. エラーハンドリング

### 9.1 エラー分類

| エラーコード | 説明 | HTTPステータス |
|-------------|------|----------------|
| `CONVERSATION_NOT_FOUND` | 会話が見つからない | 404 |
| `INVALID_FILTER_PARAMS` | 無効なフィルタパラメータ | 400 |
| `VALKEY_CONNECTION_ERROR` | Valkey接続エラー | 500 |
| `LANGFUSE_CONNECTION_ERROR` | Langfuse接続エラー | 500 |
| `PAGINATION_LIMIT_EXCEEDED` | ページネーション上限超過 | 400 |

### 9.2 エラーレスポンス

```json
{
  "error": {
    "code": "CONVERSATION_NOT_FOUND",
    "message": "Conversation with ID 'conv-123' not found",
    "details": {
      "conversation_id": "conv-123"
    }
  }
}
```

---

## 10. テスト戦略

### 10.1 単体テスト

- セカンダリインデックス操作
- フィルタリングロジック
- ページネーション
- 後方互換性
- エラーハンドリング

### 10.2 結合テスト

- エンドツーエンド（単一取得）
- エンドツーエンド（一覧取得）
- 複合フィルタ
- パフォーマンステスト
- 大量データテスト

### 10.3 パフォーマンステスト

```python
@pytest.mark.performance
async def test_list_conversations_performance():
    """一覧取得のパフォーマンステスト"""
    # 1000件のテストデータ作成
    await create_test_conversations(1000)

    # フィルタリング実行
    start = time.time()
    response = await list_conversations(
        job_id="test_job",
        limit=100
    )
    elapsed = time.time() - start

    # 2秒以内で完了することを確認
    assert elapsed < 2.0
    assert len(response.conversations) == 100
```

---

## 11. デプロイメント戦略

### 11.1 段階的ロールアウト

1. **Phase 1**: データ構造拡張のみデプロイ（後方互換性確認）
2. **Phase 2**: セカンダリインデックス有効化（バックグラウンドで構築）
3. **Phase 3**: 新API（一覧取得）を内部テスト環境で公開
4. **Phase 4**: 本番環境への段階的ロールアウト

### 11.2 ロールバック戦略

```python
# フィーチャーフラグで新機能を制御
ENABLE_EXTENDED_DIAGNOSTICS = os.getenv("ENABLE_EXTENDED_DIAGNOSTICS", "false") == "true"

if ENABLE_EXTENDED_DIAGNOSTICS:
    # 新機能（一覧取得）を有効化
    router.add_api_route("/v1/chat/diagnostics", list_conversations)
else:
    # 旧機能のみ
    pass
```

---

## 12. モニタリング・可観測性

### 12.1 メトリクス

- **APIレスポンスタイム**: 単一取得、一覧取得
- **インデックスヒット率**: セカンダリインデックスの有効性
- **Valkey接続エラー率**
- **Langfuse接続エラー率**
- **ページネーション使用率**: limit/offset分布

### 12.2 ロギング

```python
logger.info(
    "List conversations requested",
    extra={
        "job_id": job_id,
        "user_id": user_id,
        "project_id": project_id,
        "limit": limit,
        "offset": offset,
        "result_count": len(conversations),
        "elapsed_ms": elapsed_ms
    }
)
```

---

## 13. 参考資料

### 技術ドキュメント
- [Redis SET Commands](https://redis.io/commands/?group=set)
- [Langfuse Tags](https://langfuse.com/docs/tracing-features/tags)
- [FastAPI contextvars](https://fastapi.tiangolo.com/advanced/using-request-directly/)

### 内部ドキュメント
- [Valkey永続化実装 (#169)](https://github.com/Kewton/MySwiftAgent/pull/181)
- [Issue分割計画書 (#152)](https://github.com/Kewton/MySwiftAgent/blob/develop/dev-reports/feature/issue/152/issue-split.md)

---

**作成日**: 2025-11-15
**承認者**: (実装前にレビュー)
**次の更新**: 実装中に設計変更があった場合
