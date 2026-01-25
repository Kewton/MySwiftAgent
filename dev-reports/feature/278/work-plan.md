# 作業計画書: Job/Workflow GeneratorへのLangfuseトレース統合

> Issue: [#278](https://github.com/kewton/MySwiftAgent/issues/278)
> 作成日: 2025-12-13
> ステータス: 計画完了

---

## 関連ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| [要件定義書](./requirements.md) | ユーザーストーリー、受入条件、機能要件 |
| [設計方針書](./design-policy.md) | アーキテクチャ設計、技術選定、設計パターン |
| [アーキテクチャレビュー](./architecture-review.md) | 設計品質評価、改善提案 |

---

## 受入条件（Acceptance Criteria）

### L2受入条件（Issue単位）

| ID | 条件 | 検証方法 |
|----|------|---------|
| AC1 | Job Task GeneratorのLLM呼び出しがLangfuseにトレースされる | 結合テスト + 手動確認 |
| AC2 | Workflow GeneratorのLLM呼び出しがLangfuseにトレースされる | 結合テスト + 手動確認 |
| AC3 | API応答に`langfuse_trace_id`フィールドが含まれる | 単体テスト + 結合テスト |
| AC4 | Langfuse無効時も既存機能が正常動作する | 単体テスト + E2Eテスト |

---

## タスク分解

### Phase 1: Core Implementation

#### Task 1.1: StructuredCallResult に trace_id フィールド追加

| 項目 | 内容 |
|------|------|
| **対象ファイル** | `aiagent/langgraph/jobTaskGeneratorAgents/utils/llm_invocation.py:36-43` |
| **変更内容** | `trace_id: str \| None = None` フィールド追加 |
| **L3受入基準** | - dataclassにtrace_idフィールドが存在する<br>- デフォルト値がNone |
| **依存タスク** | なし |

```python
# Before
@dataclass(slots=True)
class StructuredCallResult(Generic[TModel]):
    result: TModel
    recovered_via_json: bool
    raw_text: str | None
    model_name: str

# After
@dataclass(slots=True)
class StructuredCallResult(Generic[TModel]):
    result: TModel
    recovered_via_json: bool
    raw_text: str | None
    model_name: str
    trace_id: str | None = None  # Issue #278
```

---

#### Task 1.2: invoke_structured_llm に callback_handler 引数追加

| 項目 | 内容 |
|------|------|
| **対象ファイル** | `aiagent/langgraph/jobTaskGeneratorAgents/utils/llm_invocation.py:163-260` |
| **変更内容** | `callback_handler: CallbackHandler \| None = None` 引数追加 |
| **L3受入基準** | - 関数シグネチャにcallback_handler引数が存在<br>- デフォルト値がNone<br>- 型ヒントが正しい |
| **依存タスク** | Task 1.1 |

```python
# Before
async def invoke_structured_llm(
    *,
    messages: list[dict[str, str]],
    response_model: type[TModel],
    context_label: str,
    model_env_var: str,
    default_model: str,
    validator: Callable[[TModel], TModel] | None = None,
    max_tokens_env_var: str = "JOB_GENERATOR_MAX_TOKENS",
    default_max_tokens: int = 8192,
) -> StructuredCallResult[TModel]:

# After
from langfuse.callback import CallbackHandler

async def invoke_structured_llm(
    *,
    messages: list[dict[str, str]],
    response_model: type[TModel],
    context_label: str,
    model_env_var: str,
    default_model: str,
    callback_handler: CallbackHandler | None = None,  # Issue #278
    validator: Callable[[TModel], TModel] | None = None,
    max_tokens_env_var: str = "JOB_GENERATOR_MAX_TOKENS",
    default_max_tokens: int = 8192,
) -> StructuredCallResult[TModel]:
```

---

#### Task 1.3: ainvoke() に config 渡し

| 項目 | 内容 |
|------|------|
| **対象ファイル** | `aiagent/langgraph/jobTaskGeneratorAgents/utils/llm_invocation.py:188-189` |
| **変更内容** | `config={"callbacks": [callback_handler]}` を ainvoke() に渡す |
| **L3受入基準** | - callback_handlerがNoneでない場合、configが渡される<br>- callback_handlerがNoneの場合、configは渡されない |
| **依存タスク** | Task 1.2 |

```python
# Before
structured_response = cast(
    TModel | None,
    await structured_model.ainvoke(messages),
)

# After
config: dict[str, Any] = {}
if callback_handler:
    config["callbacks"] = [callback_handler]

structured_response = cast(
    TModel | None,
    await structured_model.ainvoke(messages, config=config if config else None),
)
```

---

#### Task 1.4: trace_id 抽出・返却ロジック追加

| 項目 | 内容 |
|------|------|
| **対象ファイル** | `aiagent/langgraph/jobTaskGeneratorAgents/utils/llm_invocation.py` |
| **変更内容** | StructuredCallResult返却時にtrace_id抽出 |
| **L3受入基準** | - 成功時にtrace_idが設定される<br>- JSON fallback時もtrace_idが設定される<br>- callback_handler=None時はtrace_id=None |
| **依存タスク** | Task 1.3 |

```python
from app.services.langfuse_service import LangfuseService

# 成功時
trace_id = LangfuseService.extract_trace_id(callback_handler)
return StructuredCallResult(
    result=validated,
    recovered_via_json=False,
    raw_text=None,
    model_name=perf_tracker.model_name,
    trace_id=trace_id,  # Issue #278
)

# JSON fallback時も同様
return StructuredCallResult(
    result=validated,
    recovered_via_json=True,
    raw_text=raw_text,
    model_name=perf_tracker.model_name,
    trace_id=trace_id,  # Issue #278
)
```

---

#### Task 1.5: 単体テスト追加

| 項目 | 内容 |
|------|------|
| **対象ファイル** | `tests/unit/test_llm_invocation_langfuse.py` (既存拡張) |
| **変更内容** | SF-1, SF-3テストを実装テストに変換 |
| **L3受入基準** | - callback_handler引数テストがパス<br>- trace_id抽出テストがパス<br>- Langfuse無効時テストがパス |
| **依存タスク** | Task 1.4 |

```python
# 既存のskipテストを実装テストに変換
class TestStructuredOutputCallbackPropagation:
    def test_invoke_structured_llm_signature_has_callback_handler_param(self):
        # pytest.skip() を削除し、assertのみ残す
        assert "callback_handler" in param_names

    def test_structured_call_result_has_trace_id_field(self):
        # pytest.skip() を削除し、assertのみ残す
        assert "trace_id" in field_names
```

---

### Phase 2: Job Generator Integration

#### Task 2.1: JobGeneratorResponse に langfuse_trace_id フィールド追加

| 項目 | 内容 |
|------|------|
| **対象ファイル** | `app/schemas/job_generator.py:45-117` |
| **変更内容** | `langfuse_trace_id: str \| None` フィールド追加 |
| **L3受入基準** | - フィールドが存在<br>- OpenAPI schemaに反映<br>- デフォルト値がNone |
| **依存タスク** | Phase 1完了 |

```python
class JobGeneratorResponse(BaseModel):
    # ... existing fields ...

    # Issue #278: Langfuse observability
    langfuse_trace_id: str | None = Field(
        default=None,
        description="Langfuse trace ID for observability (null if Langfuse disabled)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
```

---

#### Task 2.2: job_generator_endpoints.py で handler 取得・trace_id 返却

| 項目 | 内容 |
|------|------|
| **対象ファイル** | `app/api/v1/job_generator_endpoints.py` |
| **変更内容** | エンドポイントでhandler取得、agent実行、trace_id返却 |
| **L3受入基準** | - Langfuse有効時にhandlerが取得される<br>- agent.ainvoke()にconfig渡し<br>- レスポンスにtrace_id含まれる |
| **依存タスク** | Task 2.1 |

```python
from app.services.langfuse_service import langfuse_service

async def generate_job_and_tasks(request: JobGeneratorRequest) -> JobGeneratorResponse:
    # Issue #278: Get Langfuse handler
    handler = langfuse_service.get_callback_handler(
        trace_name="job_task_generation",
        session_id=job_id,
        tags=["job_generator"],
    )

    try:
        # Agent実行（handler伝播）
        config = {"callbacks": [handler]} if handler else {}
        final_state = await agent.ainvoke(initial_state, config=config)

        # trace_id抽出
        trace_id = langfuse_service.extract_trace_id(handler)

        return JobGeneratorResponse(
            status="success",
            job_id=job_id,
            langfuse_trace_id=trace_id,  # Issue #278
            ...
        )
    finally:
        langfuse_service.flush()
```

---

#### Task 2.3: Job Generator 結合テスト追加

| 項目 | 内容 |
|------|------|
| **対象ファイル** | `tests/integration/test_job_generator_langfuse.py` (新規) |
| **変更内容** | Langfuse統合の結合テスト |
| **L3受入基準** | - 有効時にtrace_idが返却される<br>- 無効時にtrace_id=null<br>- 既存テストが破損しない |
| **依存タスク** | Task 2.2 |

---

### Phase 3: Workflow Generator Integration

#### Task 3.1: WorkflowGeneratorResponse に langfuse_trace_id フィールド追加

| 項目 | 内容 |
|------|------|
| **対象ファイル** | `app/schemas/workflow_generator.py:105-150` |
| **変更内容** | `langfuse_trace_id: str \| None` フィールド追加 |
| **L3受入基準** | - フィールドが存在<br>- OpenAPI schemaに反映<br>- デフォルト値がNone |
| **依存タスク** | Phase 1完了 |

```python
class WorkflowGeneratorResponse(BaseModel):
    # ... existing fields ...

    # Issue #278: Langfuse observability
    langfuse_trace_id: str | None = Field(
        default=None,
        description="Langfuse trace ID for observability (null if Langfuse disabled)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
```

---

#### Task 3.2: workflow_generator_endpoints.py で handler 取得・trace_id 返却

| 項目 | 内容 |
|------|------|
| **対象ファイル** | `app/api/v1/workflow_generator_endpoints.py` |
| **変更内容** | エンドポイントでhandler取得、generator実行、trace_id返却 |
| **L3受入基準** | - Langfuse有効時にhandlerが取得される<br>- レスポンスにtrace_id含まれる |
| **依存タスク** | Task 3.1 |

---

#### Task 3.3: Workflow Generator 結合テスト追加

| 項目 | 内容 |
|------|------|
| **対象ファイル** | `tests/integration/test_workflow_generator_langfuse.py` (新規) |
| **変更内容** | Langfuse統合の結合テスト |
| **L3受入基準** | - 有効時にtrace_idが返却される<br>- 無効時にtrace_id=null |
| **依存タスク** | Task 3.2 |

---

### Phase 4: Documentation & Testing

#### Task 4.1: API_REFERENCE.md 更新

| 項目 | 内容 |
|------|------|
| **対象ファイル** | `docs/API_REFERENCE.md` |
| **変更内容** | langfuse_trace_idフィールドのドキュメント追加 |
| **L3受入基準** | - Job Generatorセクションにtrace_id説明<br>- Workflow Generatorセクションにtrace_id説明 |
| **依存タスク** | Phase 2, Phase 3完了 |
| **備考** | SF-2（Data Privacy Notice）は既に対応済み |

---

#### Task 4.2: E2Eテスト追加

| 項目 | 内容 |
|------|------|
| **対象ファイル** | `tests/acceptance/test_langfuse_integration.py` (新規) |
| **変更内容** | Langfuse有効/無効時のE2Eテスト |
| **L3受入基準** | - Langfuse有効時にトレースが記録される<br>- Langfuse無効時にエラーが発生しない |
| **依存タスク** | Phase 2, Phase 3完了 |

---

## 依存関係図

```mermaid
graph TD
    subgraph "Phase 1: Core"
        T1.1[Task 1.1<br>StructuredCallResult.trace_id]
        T1.2[Task 1.2<br>callback_handler引数]
        T1.3[Task 1.3<br>ainvoke() config渡し]
        T1.4[Task 1.4<br>trace_id抽出]
        T1.5[Task 1.5<br>単体テスト]
    end

    subgraph "Phase 2: Job Generator"
        T2.1[Task 2.1<br>Response.trace_id]
        T2.2[Task 2.2<br>Endpoint実装]
        T2.3[Task 2.3<br>結合テスト]
    end

    subgraph "Phase 3: Workflow Generator"
        T3.1[Task 3.1<br>Response.trace_id]
        T3.2[Task 3.2<br>Endpoint実装]
        T3.3[Task 3.3<br>結合テスト]
    end

    subgraph "Phase 4: Docs & Test"
        T4.1[Task 4.1<br>API_REFERENCE更新]
        T4.2[Task 4.2<br>E2Eテスト]
    end

    T1.1 --> T1.2
    T1.2 --> T1.3
    T1.3 --> T1.4
    T1.4 --> T1.5

    T1.5 --> T2.1
    T1.5 --> T3.1

    T2.1 --> T2.2
    T2.2 --> T2.3

    T3.1 --> T3.2
    T3.2 --> T3.3

    T2.3 --> T4.1
    T3.3 --> T4.1
    T4.1 --> T4.2
```

---

## 変更対象ファイル一覧

| ファイル | Phase | 変更種別 | 影響度 |
|---------|-------|---------|--------|
| `aiagent/langgraph/jobTaskGeneratorAgents/utils/llm_invocation.py` | 1 | 修正 | 中 |
| `app/schemas/job_generator.py` | 2 | 修正 | 低 |
| `app/schemas/workflow_generator.py` | 3 | 修正 | 低 |
| `app/api/v1/job_generator_endpoints.py` | 2 | 修正 | 中 |
| `app/api/v1/workflow_generator_endpoints.py` | 3 | 修正 | 中 |
| `tests/unit/test_llm_invocation_langfuse.py` | 1 | 修正 | 低 |
| `tests/integration/test_job_generator_langfuse.py` | 2 | 新規 | 低 |
| `tests/integration/test_workflow_generator_langfuse.py` | 3 | 新規 | 低 |
| `docs/API_REFERENCE.md` | 4 | 修正 | 低 |
| `tests/acceptance/test_langfuse_integration.py` | 4 | 新規 | 低 |

---

## L3受入テスト計画

### テストケース一覧

| ID | テストケース | 対応AC | 検証方法 |
|----|-------------|--------|---------|
| L3-1 | callback_handler引数がinvoke_structured_llmに存在する | AC1 | 単体テスト |
| L3-2 | trace_idフィールドがStructuredCallResultに存在する | AC1 | 単体テスト |
| L3-3 | callback_handler渡し時にainvoke()にconfig伝播される | AC1 | 単体テスト |
| L3-4 | trace_idがLLM呼び出し成功時に抽出される | AC1 | 単体テスト |
| L3-5 | trace_idがJSON fallback時も抽出される | AC1 | 単体テスト |
| L3-6 | JobGeneratorResponseにlangfuse_trace_idフィールドが存在する | AC3 | 単体テスト |
| L3-7 | WorkflowGeneratorResponseにlangfuse_trace_idフィールドが存在する | AC3 | 単体テスト |
| L3-8 | Job Generator API呼び出し時にtrace_idが返却される | AC1, AC3 | 結合テスト |
| L3-9 | Workflow Generator API呼び出し時にtrace_idが返却される | AC2, AC3 | 結合テスト |
| L3-10 | Langfuse無効時にtrace_id=nullで正常動作する | AC4 | 結合テスト |
| L3-11 | Langfuse無効時に既存機能が影響を受けない | AC4 | E2Eテスト |
| L3-12 | LLM呼び出しエラー時もtrace_idが取得可能 | AC1 | 単体テスト |

---

## 品質基準

### コードカバレッジ目標

| テスト種別 | 目標 | 備考 |
|-----------|------|------|
| 単体テスト | 90%以上 | llm_invocation.py変更部分 |
| 結合テスト | 50%以上 | エンドポイント変更部分 |

### 静的解析

- Ruff: エラーゼロ
- MyPy: エラーゼロ

### プッシュ前チェック

```bash
./scripts/pre-push-check-all.sh
```

---

## リスク対策

| リスク | 対策 | 担当Phase |
|--------|------|-----------|
| with_structured_output()でconfig非対応 | SF-1事前検証テスト（対応済み） | Phase 1前 |
| trace_id抽出タイミング不整合 | handler.last_trace_idで取得 | Phase 1 |
| 既存テスト破損 | Optional引数で後方互換性確保 | Phase 1 |
| LLM入出力漏洩 | SF-2ドキュメント追加（対応済み） | Phase 4 |

---

## 事前対応済み事項

アーキテクチャレビューの改善提案（SF-1, SF-2, SF-3）は既に対応済み：

| 提案 | 対応内容 | 対応ファイル |
|------|---------|-------------|
| SF-1 | with_structured_output()事前検証テスト | `tests/unit/test_llm_invocation_langfuse.py` |
| SF-2 | LLM入出力機密性ドキュメント | `docs/API_REFERENCE.md` (Data Privacy Notice) |
| SF-3 | エラー時trace_id伝播テスト | `tests/unit/test_llm_invocation_langfuse.py` |

---

## 実装順序

```
1. Phase 1: Core Implementation
   └── Task 1.1 → 1.2 → 1.3 → 1.4 → 1.5 (順次実行)

2. Phase 2 & Phase 3: 並列実行可能
   ├── Phase 2: Job Generator Integration
   │   └── Task 2.1 → 2.2 → 2.3
   └── Phase 3: Workflow Generator Integration
       └── Task 3.1 → 3.2 → 3.3

3. Phase 4: Documentation & Testing
   └── Task 4.1 → 4.2 (Phase 2, 3完了後)
```

---

## 参照ドキュメント

- [expertAgent API Reference](../../../expertAgent/docs/API_REFERENCE.md)
- [設計方針書](./design-policy.md)
- [アーキテクチャレビュー](./architecture-review.md)
- [要件定義書](./requirements.md)
- [Langfuse LangChain Integration](https://langfuse.com/docs/integrations/langchain/tracing)
