# Issue #194: Langfuse Trace not found エラー - 設計方針書

> 作成日: 2025-12-11
> 更新日: 2025-12-11
> Issue: [#194](https://github.com/kewton/MySwiftAgent/issues/194)
> 関連ドキュメント: [requirements.md](./requirements.md), [architecture-review.md](./architecture-review.md)
> ステータス: レビュー承認済み

---

## 1. アーキテクチャ設計

### 1.1 現状のアーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                        chat_endpoints.py                         │
│  ┌─────────────────┐    ┌─────────────────────────────────────┐ │
│  │ save_message()  │    │ stream_requirement_clarification() │ │
│  │ (trace_id無し)  │    │ (CallbackHandler経由でtrace生成)   │ │
│  └────────┬────────┘    └──────────────────┬──────────────────┘ │
│           │ ❌ trace_idが渡されない         │                    │
└───────────┼─────────────────────────────────┼────────────────────┘
            ▼                                 ▼
┌───────────────────────┐          ┌─────────────────────┐
│  conversation_store   │          │  langfuse_service   │
│  (インメモリ)         │          │  (シングルトン)      │
│  trace_id保存不可     │          │  trace_id生成       │
└───────────────────────┘          └─────────────────────┘
```

### 1.2 目標アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                        chat_endpoints.py                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ conversation_service.save_with_metadata()                │   │
│  │ (trace_id, job_id, user_id等を含む)                      │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │ ✅ trace_idが渡される                │
└───────────────────────────┼─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ConversationService                           │
│  ┌─────────────────────┐    ┌─────────────────────────────┐    │
│  │ save_with_metadata()│───▶│ ConversationStoreValkey     │    │
│  │ + IndexManager更新  │    │ (永続化ストレージ)          │    │
│  └─────────────────────┘    └─────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │     Valkey      │
                   │ (Redis互換)     │
                   └─────────────────┘
```

### 1.3 レイヤー構成

本実装は以下のレイヤー構成に従います：

| レイヤー | 責務 | 該当ファイル |
|---------|------|-------------|
| API Layer | HTTPリクエスト処理、バリデーション | `chat_endpoints.py` |
| Service Layer | ビジネスロジック、トランザクション制御 | `conversation_service.py`, `langfuse_service.py` |
| Store Layer | データ永続化、インデックス管理 | `conversation_store_valkey.py`, `index_manager.py` |
| Schema Layer | データ構造定義、シリアライゼーション | `conversation_metadata.py`, `diagnostic.py` |

---

## 2. 技術選定

### 2.1 既存技術の活用

| 技術 | 用途 | 選定理由 |
|------|------|---------|
| **Valkey** | 会話データ永続化 | 既にDiagnostics APIで使用、Redis互換で高速 |
| **ConversationStoreValkey** | ストレージ抽象化 | 既存実装済み、メタデータ保存対応 |
| **IndexManager** | フィルタ検索 | 既存実装済み、job_id/user_id等のインデックス管理 |
| **ConversationService** | データアクセス統合 | `save_with_metadata()`が既に定義済み |
| **LangfuseService** | トレーシング | シングルトンで既に実装済み |

### 2.2 新規実装不要の理由

**重要**: 新規クラス・モジュールの追加は不要です。

| 機能 | 現状 | 対応方針 |
|------|------|---------|
| trace_id保存 | `save_with_metadata()`定義済み | 呼び出し箇所の追加のみ |
| Valkey永続化 | `ConversationStoreValkey`実装済み | 既存利用 |
| インデックス更新 | `IndexManager`実装済み | `save_with_metadata()`経由で自動 |

---

## 3. 設計パターン

### 3.1 適用パターン

#### Repository パターン（既存）

```python
# ConversationStoreValkey - データアクセス抽象化
class ConversationStoreValkey:
    async def save_conversation(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        trace_id: Optional[str] = None,  # ✅ 既にサポート
        **metadata
    ) -> bool
```

#### Service パターン（既存）

```python
# ConversationService - ビジネスロジック統合
class ConversationService:
    async def save_with_metadata(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        metadata: ConversationMetadata,  # ✅ trace_id含む
    ) -> bool
```

#### Singleton パターン（既存）

```python
# LangfuseService - アプリケーション全体で1インスタンス
langfuse_service = LangfuseService()

# CallbackHandler経由でtrace_id取得
handler = langfuse_service.get_callback_handler()
# ... LLM呼び出し後 ...
trace_id = handler.last_trace_id  # ✅ 取得可能
```

### 3.2 依存性注入（DI） - SF-1対応

**SF-1: グローバル変数排除 → FastAPI DIパターン統一**

現状の`conversation_store`グローバル変数を排除し、FastAPIのDependsパターンに統一します。

```python
# 現状（非推奨）
from app.services.conversation.conversation_store import conversation_store
conversation_store.save_message(...)

# 目標: サービスのDI
async def get_conversation_service() -> AsyncGenerator[ConversationService, None]:
    async with ConversationStoreValkey() as store:
        index_manager = IndexManager(store._client)
        yield ConversationService(store, index_manager)

# エンドポイントでの使用
@router.post("/requirement-definition")
async def requirement_definition(
    request: RequirementChatRequest,
    service: ConversationService = Depends(get_conversation_service)
):
    ...
```

**効果**:
- テスタビリティ向上（モック注入が容易）
- 依存関係の明示化
- グローバル状態の排除

### 3.3 trace_id取得ヘルパー - SF-2対応

**SF-2: trace_id取得ヘルパーメソッド追加**

`handler.last_trace_id`の取得を安全に行うヘルパーメソッドを`LangfuseService`に追加します。

```python
# langfuse_service.py に追加
def extract_trace_id(self, handler: CallbackHandler | None) -> str | None:
    """Extract trace_id from handler after LLM invocation.

    Args:
        handler: CallbackHandler instance after LLM call

    Returns:
        trace_id if available, None otherwise
    """
    if handler is None:
        return None
    if not hasattr(handler, 'last_trace_id'):
        logger.warning("CallbackHandler does not have last_trace_id attribute")
        return None
    return handler.last_trace_id
```

**効果**:
- コードの意図が明確化
- エラーハンドリングの集約
- None安全な取得

---

## 4. データモデル

### 4.1 Valkeyデータ構造

**キー命名規則**: `conversation:{conversation_id}`

```json
{
  "conversation_id": "conv-xxx",
  "messages": [
    {
      "role": "user",
      "content": "売上データを分析したい",
      "timestamp": "2025-12-11T10:00:00Z"
    },
    {
      "role": "assistant",
      "content": "承知しました。どのようなデータソースをお使いですか？",
      "timestamp": "2025-12-11T10:00:05Z"
    }
  ],
  "metadata": {
    "trace_id": "uuid-xxx",
    "job_id": "job-xxx",
    "user_id": "user-xxx",
    "project_id": "default_project",
    "created_at": "2025-12-11T10:00:00Z",
    "updated_at": "2025-12-11T10:00:05Z"
  }
}
```

### 4.2 ConversationMetadata スキーマ

```python
# app/schemas/conversation_metadata.py (既存)
@dataclass
class ConversationMetadata:
    trace_id: Optional[str] = None
    job_id: Optional[str] = None
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    workflow_id: Optional[str] = None
    prompt_version: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

### 4.3 インデックス構造

```
idx:job:{job_id}       → Set[conversation_id]
idx:user:{user_id}     → Set[conversation_id]
idx:project:{project_id} → Set[conversation_id]
idx:date:{YYYY-MM-DD}  → Set[conversation_id]
```

---

## 5. API設計

### 5.1 変更対象API

| API | 変更内容 |
|-----|---------|
| `POST /chat/requirement-definition` | `save_with_metadata()`使用に変更 |
| `GET /diagnostics/conversations` | 変更なし（既にValkey対応） |
| `GET /diagnostics/conversations/{id}` | 変更なし（既にValkey対応） |

### 5.2 後方互換性

- **APIレスポンス形式**: 変更なし
- **既存クライアント**: 影響なし
- **インメモリストア**: 段階的に非推奨化

---

## 6. セキュリティ考慮事項

### 6.1 シークレット管理

| シークレット | 管理方法 |
|-------------|---------|
| Langfuse APIキー | myVault経由で取得（`secrets_manager.get_secret()`） |
| Valkey接続情報 | myVault経由で取得 |

### 6.2 データ保護

- `trace_url`はサーバーサイドで生成（XSS対策）
- `trace_id`はUUID形式（推測困難）
- 会話データはproject_id単位で分離

---

## 7. パフォーマンス考慮事項

### 7.1 非同期処理

```python
# Langfuseトレース送信は非同期（ユーザー応答をブロックしない）
handler = langfuse_service.get_callback_handler()
# ... LLM呼び出し ...
# トレースは内部バッファに蓄積され、非同期で送信される
```

### 7.2 SSE内のエラーハンドリング - SF-3対応

**SF-3: SSE内のエラーハンドリング強化**

`event_generator()`内でのValkey保存失敗時、SSEストリームは継続しトレーシングのみ断念します。

```python
# chat_endpoints.py の event_generator() 内
async def event_generator() -> AsyncGenerator[Dict[str, Any], None]:
    try:
        # ... LLMストリーミング処理 ...

        # Valkey保存（失敗してもSSEは継続）
        try:
            trace_id = langfuse_service.extract_trace_id(handler)
            metadata = ConversationMetadata(
                trace_id=trace_id,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await service.save_with_metadata(
                conversation_id=request.conversation_id,
                messages=messages,
                metadata=metadata,
            )
        except Exception as e:
            logger.warning(
                f"Failed to save conversation to Valkey: {e}. "
                "SSE stream continues, but trace_id will not be persisted."
            )
            # SSEは継続、トレーシングは断念

        yield {"event": "message", "data": json.dumps({"type": "done"})}

    except Exception as e:
        # 致命的エラー時のみSSEエラーイベントを送信
        logger.error(f"Error in SSE stream: {e}")
        yield {"event": "message", "data": json.dumps({"type": "error", ...})}
```

**効果**:
- フェイルオープン設計の実現
- Valkey障害時もチャット機能は継続
- 障害の可視化（ログ出力）

### 7.3 レイテンシ目標

| 操作 | 目標レイテンシ |
|------|--------------|
| Valkey書き込み | < 50ms |
| Diagnostics API応答 | < 200ms (100件取得時) |
| Langfuseトレース送信 | 非同期（制限なし） |

### 7.4 接続プーリング

```python
# ConversationStoreValkeyはコンテキストマネージャーで接続管理
async with ConversationStoreValkey() as store:
    # 接続は自動的にプールから取得/返却
    ...
```

---

## 8. トレードオフ分析

### 8.1 設計判断

| 判断項目 | 選択肢 | 採用 | 理由 |
|---------|--------|-----|------|
| ストレージ統一タイミング | 即時 vs 段階的 | 即時 | 根本原因解決のため |
| 新規サービス作成 | 新規 vs 既存活用 | 既存活用 | `save_with_metadata()`が既存 |
| インメモリストア | 削除 vs 並行運用 | 並行運用 | 後方互換性確保 |
| フィーチャーフラグ | 導入 vs 直接切替 | 直接切替 | 変更箇所が限定的 |

### 8.2 リスク緩和策

| リスク | 緩和策 |
|--------|-------|
| Valkey接続障害 | フェイルオープン設計（監視障害がメイン機能に影響しない） |
| 既存テスト破壊 | 単体テスト追加、結合テスト実施 |
| データ移行漏れ | インメモリストアとの並行運用期間 |

---

## 9. 実装計画

### Phase 1: フロントエンド改善（即効性）

```
myAgentDesk/src/routes/mlops/diagnostics/+page.svelte
├── デモデータ判定ロジック追加
├── 「デモデータ表示中」バナー追加
└── 無効なtrace_url時のリンク非表示
```

### Phase 2: バックエンド改善（根本解決）

**実装時に反映するアーキテクチャレビュー推奨項目:**

| ID | 内容 | 対象 |
|----|------|------|
| SF-1 | グローバル変数排除 → FastAPI DIパターン統一 | `chat_endpoints.py` |
| SF-2 | trace_id取得ヘルパーメソッド追加 | `langfuse_service.py` |
| SF-3 | SSE内のエラーハンドリング強化 | `chat_endpoints.py` |

```
expertAgent/app/api/v1/chat_endpoints.py
├── ConversationService DIの追加（SF-1）
├── save_message() → save_with_metadata() 置換
├── trace_id取得ロジック追加（SF-2: extract_trace_id使用）
└── Valkey保存失敗時のエラーハンドリング（SF-3）

expertAgent/app/services/langfuse_service.py
└── extract_trace_id() ヘルパーメソッド追加（SF-2）
```

### Phase 3: Langfuse連携強化（オプション）

```
expertAgent/app/api/v1/observability_endpoints.py
├── /langfuse/health エンドポイント追加
└── 設定確認API実装
```

---

## 10. 検証基準

### 10.1 Phase 2 完了基準

- [ ] `save_with_metadata()`がchat_endpoints.pyから呼び出されている
- [ ] trace_idがValkeyのメタデータに保存されている
- [ ] Diagnostics APIのレスポンスに有効な`langfuse_trace_url`が含まれる
- [ ] 単体テストカバレッジ90%以上
- [ ] 結合テストでChat→Diagnosticsフロー確認

### 10.2 E2Eテスト項目

1. チャットセッション開始 → メッセージ送信
2. Diagnostics API呼び出し → trace_url確認
3. Langfuse UIでトレース確認（手動）

---

## 11. 参照ドキュメント

- [要件定義書](./requirements.md)
- [architecture-overview.md](../../../docs/design/architecture-overview.md)
- [service-dependencies.md](../../../docs/arch/service-dependencies.md)
- [API_REFERENCE.md](../../../expertAgent/docs/API_REFERENCE.md)
