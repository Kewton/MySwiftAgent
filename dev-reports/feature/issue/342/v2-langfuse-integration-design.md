# V2 Langfuse統合 設計方針書

**Issue**: #342 V2 Job Generator Langfuse統合
**作成日**: 2026-01-07
**更新日**: 2026-01-07
**ステータス**: 設計完了・実装待ち
**レビュー**: 条件付き承認 → 指摘事項反映済み

---

## 1. 現状の問題

### 1.1 症状
- V2 Job Generatorで生成されたジョブのMain TraceリンクをクリックするとLangfuseで「Trace not found」と表示される
- V2のLLM呼び出しがLangfuseに記録されていない

### 1.2 根本原因

**問題1: invoke_structured_llmがcallbacksを受け取らない**

```
┌─────────────────────────────────────────────────────────────────┐
│ V1 アーキテクチャ（動作中）                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  API Endpoint                                                   │
│       │                                                         │
│       ▼                                                         │
│  langfuse_handler = langfuse_service.get_callback_handler()     │
│       │                                                         │
│       ▼                                                         │
│  agent.ainvoke(state, config={"callbacks": [langfuse_handler]}) │
│       │                                                         │
│       ▼                                                         │
│  LangChain/LangGraph が自動的にLangfuseにトレースを送信 ✅       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ V2 アーキテクチャ（問題あり）                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  API Endpoint                                                   │
│       │                                                         │
│       ▼                                                         │
│  langfuse_handler = langfuse_service.get_callback_handler()     │
│       │                                                         │
│       ▼                                                         │
│  JobGeneratorV2Adapter(langfuse_handler=langfuse_handler)       │
│       │                                                         │
│       ▼                                                         │
│  ObservabilityContext(tracer=langfuse_handler) ← 保存される     │
│       │                                                         │
│       ▼                                                         │
│  invoke_structured_llm() ← ObservabilityContextを使用しない ❌   │
│       │                                                         │
│       ▼                                                         │
│  ChatAnthropic().with_structured_output() ← callbackなし ❌     │
│       │                                                         │
│       ▼                                                         │
│  Langfuseにトレースが送信されない ❌                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**問題2: ExecutionContextがworkflowに伝播していない（レビュー指摘）**

```python
# adapter.py:221 - contextをビルドするが結果を破棄している！
_ = self._create_context_builder(actual_job_id, user_requirement).build()

# orchestrator.py:154-159 - 新しいcontextを作成（ObservabilityContextなし）
context = (
    ContextBuilder()
    .with_job_id(job_id)
    .with_user_requirement(request.user_requirement)
    .build()  # ← ObservabilityContextが設定されない！
)
```

**影響フロー:**
```
adapter._langfuse_handler
    ↓
adapter._create_context_builder() で ObservabilityContext に設定
    ↓
context がビルドされるが、orchestrator.run_workflow() に渡されない ❌
    ↓
orchestrator が新しい context を作成（langfuse_handler なし）
    ↓
workflow.execute(input, context) に渡される context は tracer=None
    ↓
invoke_structured_llm に callbacks を渡しても context.observability.tracer は None ❌
```

### 1.3 影響範囲

| コンポーネント | ファイル | 問題 |
|---------------|----------|------|
| adapter.py | `jobGeneratorV2/adapter.py` | **contextをorchestratorに渡していない** |
| orchestrator.py | `jobGeneratorV2/orchestrator.py` | **context引数を受け取っていない** |
| llm_utils.py | `jobGeneratorV2/llm_utils.py` | LangfuseコールバックをLLM呼び出しに渡していない |
| decomposer.py | `workflows/task_breakdown/decomposer.py` | ExecutionContextのObservabilityContextを使用していない |
| designer.py | `workflows/interface_design/designer.py` | 同上 |

---

## 2. 設計方針

### 2.1 アプローチ比較

| アプローチ | メリット | デメリット | 推奨度 |
|-----------|---------|-----------|--------|
| **A. invoke_structured_llmにcallbacks引数追加** | シンプル、局所的変更 | 全呼び出し箇所でcontext.observability.tracerを渡す必要 | ⭐⭐⭐ |
| **B. グローバルコンテキストでcallback管理** | 呼び出し箇所の変更不要 | グローバル状態は避けるべき | ⭐ |
| **C. ExecutionContextをinvoke_structured_llmに渡す** | 型安全、将来拡張性 | 大きな変更が必要 | ⭐⭐ |

### 2.2 推奨アプローチ: A + Context伝播修正

**理由**:
1. 最小限の変更で実装可能
2. 既存のV2アーキテクチャを大きく変更しない
3. LangChainの標準的なcallbackパターンに準拠
4. **Context伝播修正により、ObservabilityContextが正しくworkflowに到達する**

---

## 3. 実装計画

### 3.0 Phase 0: ExecutionContext伝播の修正（最優先）

**ファイル1**: `aiagent/langgraph/jobGeneratorV2/orchestrator.py`

```python
async def run_workflow(
    self,
    request: JobGenerationRequest,
    context: "ExecutionContext | None" = None,  # 追加
) -> JobGenerationResult:
    """Run the complete job generation workflow.

    Args:
        request: The job generation request
        context: Optional pre-built ExecutionContext with observability settings

    Returns:
        JobGenerationResult with the outcome
    """
    job_id = str(uuid.uuid4())
    logger.info("Starting job generation workflow: %s", job_id)

    # Use provided context or create default
    if context is None:
        context = (
            ContextBuilder()
            .with_job_id(job_id)
            .with_user_requirement(request.user_requirement)
            .build()
        )
    else:
        # Update job_id in provided context if needed
        context.job_id = job_id

    # ... 既存のコード ...
```

**ファイル2**: `aiagent/langgraph/jobGeneratorV2/adapter.py`

```python
async def generate(
    self,
    user_requirement: str,
    project_id: str = "default",
    max_tasks: int = 10,
    job_id: str | None = None,
) -> "JobGeneratorResponse":
    """Generate job and tasks using V2 architecture."""
    logger.info(
        "JobGeneratorV2Adapter.generate called: %s...",
        user_requirement[:100],
    )

    # Create request
    request = JobGenerationRequest(
        user_requirement=user_requirement,
        project_id=project_id,
        max_tasks=max_tasks,
    )

    # Create and build context with ObservabilityContext
    import uuid

    actual_job_id = job_id or str(uuid.uuid4())
    context = self._create_context_builder(actual_job_id, user_requirement).build()

    # Run workflow with context (修正: contextを渡す)
    result = await self._orchestrator.run_workflow(request, context=context)

    # Convert result to response
    return self._convert_result(result, actual_job_id)
```

### 3.1 Phase 1: invoke_structured_llmの拡張

**ファイル**: `aiagent/langgraph/jobGeneratorV2/llm_utils.py`

```python
from typing import Any

def get_callbacks_from_context(context: "ExecutionContext") -> list[Any]:
    """Extract LangChain callbacks from ExecutionContext.

    DRY原則: 各workflowで重複するコードを共通化

    Args:
        context: ExecutionContext with observability settings

    Returns:
        List of LangChain callbacks (may be empty)
    """
    if context.observability and context.observability.tracer:
        return [context.observability.tracer]
    return []


async def invoke_structured_llm(
    messages: list[dict[str, str]] | None = None,
    response_model: type[TModel] | None = None,
    *,
    system_prompt: str | None = None,
    user_prompt: str | None = None,
    model_name: str = "claude-haiku-4-5",
    temperature: float = 0.7,
    context_label: str = "llm_call",
    model_env_var: str | None = None,
    default_model: str | None = None,
    validator: Any = None,
    callbacks: list[Any] | None = None,  # 追加
    **kwargs: Any,
) -> StructuredCallResult[TModel]:
    """Invoke LLM with structured output.

    Args:
        ...
        callbacks: Optional list of LangChain callbacks (e.g., LangfuseCallbackHandler)
    """
    # ... 既存のコード ...

    # LLM呼び出し時にcallbacksを渡す
    structured_llm = llm.with_structured_output(response_model, include_raw=True)

    if callbacks:
        raw_result = await structured_llm.ainvoke(
            lc_messages,
            config={"callbacks": callbacks}
        )
    else:
        raw_result = await structured_llm.ainvoke(lc_messages)

    # ... 残りのコード ...
```

### 3.2 Phase 2: 呼び出し箇所の更新

**ファイル**: `workflows/task_breakdown/decomposer.py`

```python
from aiagent.langgraph.jobGeneratorV2.llm_utils import (
    get_callbacks_from_context,
    invoke_structured_llm,
)

class TaskDecomposerSubWorkflow:
    async def decompose(
        self,
        input_data: TaskBreakdownInput,
        context: "ExecutionContext",
    ) -> list[TaskDefinition]:
        # ... 既存のコード ...

        # callbacksをcontextから取得（ヘルパー関数使用）
        callbacks = get_callbacks_from_context(context)

        call_result = await invoke_structured_llm(
            messages=messages,
            response_model=TaskBreakdownResponse,
            context_label="task_decomposer",
            model_env_var="JOB_GENERATOR_REQUIREMENT_ANALYSIS_MODEL",
            default_model=context.llm.model_name,
            validator=_validate_task_breakdown_response,
            callbacks=callbacks,  # 追加
        )
```

### 3.3 対象ファイル一覧（更新）

| ファイル | 変更内容 | 優先度 |
|----------|----------|--------|
| `orchestrator.py` | **context引数追加、渡されたcontextを使用** | P0 |
| `adapter.py` | **contextをrun_workflowに渡す** | P0 |
| `llm_utils.py` | callbacks引数追加、ヘルパー関数追加 | P1 |
| `decomposer.py` | get_callbacks_from_context使用、callbacksを渡す | P1 |
| `alternative.py` | 同上 | P2 |
| `designer.py` | 同上 | P2 |
| `llm_generator.py` | 同上（WORKFLOW_GEN用） | P3 |

---

## 4. テスト計画

### 4.0 Context伝播テスト（追加）

```python
# tests/unit/test_context_propagation.py

def test_adapter_passes_context_to_orchestrator():
    """adapterがcontextをorchestratorに渡すことを確認"""
    mock_orchestrator = MagicMock()
    adapter = JobGeneratorV2Adapter(
        langfuse_handler=MagicMock(),
    )
    adapter._orchestrator = mock_orchestrator

    await adapter.generate(user_requirement="test")

    # run_workflowにcontext引数が渡されたことを確認
    call_args = mock_orchestrator.run_workflow.call_args
    assert call_args.kwargs.get("context") is not None


def test_orchestrator_uses_provided_context():
    """orchestratorが渡されたcontextを使用することを確認"""
    mock_tracer = MagicMock()
    context = ExecutionContext(
        job_id="test",
        user_requirement="test",
        observability=ObservabilityContext(tracer=mock_tracer),
    )

    orchestrator = JobGenerationOrchestrator(...)
    # contextが内部でそのまま使用されることを確認


def test_workflow_receives_context_with_tracer():
    """workflowにtracer付きcontextが渡されることを確認"""
    mock_tracer = MagicMock()
    context = ExecutionContext(
        job_id="test",
        user_requirement="test",
        observability=ObservabilityContext(tracer=mock_tracer),
    )

    callbacks = get_callbacks_from_context(context)
    assert mock_tracer in callbacks
```

### 4.1 単体テスト

```python
# tests/unit/test_llm_utils_callbacks.py

@pytest.mark.asyncio
async def test_invoke_structured_llm_with_callbacks():
    """callbacks引数が正しくLLM呼び出しに渡されることを確認"""
    mock_callback = MagicMock()

    result = await invoke_structured_llm(
        system_prompt="test",
        user_prompt="test",
        response_model=TestModel,
        callbacks=[mock_callback],
    )

    # callbackが呼び出されたことを確認
    mock_callback.on_llm_start.assert_called()


def test_get_callbacks_from_context_with_tracer():
    """tracerがある場合、callbacksリストに含まれることを確認"""
    mock_tracer = MagicMock()
    context = ExecutionContext(
        job_id="test",
        user_requirement="test",
        observability=ObservabilityContext(tracer=mock_tracer),
    )

    callbacks = get_callbacks_from_context(context)
    assert callbacks == [mock_tracer]


def test_get_callbacks_from_context_without_tracer():
    """tracerがない場合、空のリストを返すことを確認"""
    context = ExecutionContext(
        job_id="test",
        user_requirement="test",
    )

    callbacks = get_callbacks_from_context(context)
    assert callbacks == []
```

### 4.2 結合テスト

```python
# tests/integration/test_v2_langfuse_integration.py

@pytest.mark.asyncio
async def test_v2_job_generation_creates_langfuse_trace():
    """V2 Job GeneratorがLangfuseトレースを作成することを確認"""
    # Mock Langfuse
    mock_handler = create_mock_langfuse_handler()

    adapter = JobGeneratorV2Adapter(
        langfuse_handler=mock_handler,
    )

    response = await adapter.generate(
        user_requirement="テスト要件",
    )

    # トレースが記録されたことを確認
    assert mock_handler.trace_id is not None


@pytest.mark.asyncio
async def test_end_to_end_context_flow():
    """adapter → orchestrator → workflow → invoke_structured_llm の
    context伝播が正しく動作することを確認"""
    mock_tracer = MagicMock()

    adapter = JobGeneratorV2Adapter(
        langfuse_handler=mock_tracer,
    )

    # generate実行後、mock_tracerのon_llm_startが呼ばれることを確認
    with patch('...invoke_structured_llm') as mock_llm:
        await adapter.generate(user_requirement="test")

        # callbacksにmock_tracerが含まれていることを確認
        call_args = mock_llm.call_args
        assert mock_tracer in call_args.kwargs.get("callbacks", [])
```

### 4.3 E2E検証

1. Generate Pageでジョブ生成
2. Main Traceリンクをクリック
3. Langfuseでトレースが表示されることを確認
4. LLM呼び出しのプロンプトが確認できることを確認

---

## 5. リスクと対策

| リスク | 影響 | 対策 |
|--------|------|------|
| **context伝播が不完全** | トレースが記録されない | Phase 0で最優先対応、テストで検証 |
| callbacksが正しく伝播しない | トレースが記録されない | 各レイヤーでログ出力して追跡 |
| パフォーマンス低下 | LLM呼び出し遅延 | callbacksが空の場合はconfigを渡さない |
| 既存テストの破壊 | CI失敗 | callbacks=None、context=Noneをデフォルトにして後方互換性確保 |

---

## 6. 実装優先度

| 優先度 | タスク | 理由 |
|--------|--------|------|
| **P0** | **orchestrator.pyのcontext引数追加** | **根本原因の修正** |
| **P0** | **adapter.pyでcontextをrun_workflowに渡す** | **根本原因の修正** |
| P1 | llm_utils.pyのcallbacks引数追加 | 基盤部分 |
| P1 | llm_utils.pyのヘルパー関数追加 | DRY原則 |
| P1 | decomposer.pyの修正 | TASK_BREAKDOWN phaseで最初にLLM呼び出し |
| P2 | designer.pyの修正 | INTERFACE_DESIGN phase |
| P2 | alternative.pyの修正 | 代替案生成時のみ |
| P3 | llm_generator.pyの修正 | WORKFLOW_GEN phase（LLM使用時） |

---

## 7. 成功基準

1. **機能要件**
   - [ ] ExecutionContextがadapter → orchestrator → workflowに正しく伝播する
   - [ ] V2で生成したジョブのMain Traceリンクが機能する
   - [ ] Langfuseでプロンプトと応答が確認できる
   - [ ] 各フェーズのLLM呼び出しがトレースに記録される

2. **非機能要件**
   - [ ] 既存のV2テストが全てパスする
   - [ ] V1の動作に影響がない
   - [ ] callbacksなしの場合もパフォーマンス低下なし
   - [ ] context=Noneの場合も後方互換性を維持

---

## 8. 参考資料

- [LangChain Callbacks Documentation](https://python.langchain.com/docs/modules/callbacks/)
- [Langfuse LangChain Integration](https://langfuse.com/docs/integrations/langchain)
- Issue #278: Langfuse統合（V1実装）
- Issue #305: trace_id事前生成

---

## 9. 見積もり（更新）

| フェーズ | 作業内容 | 見積もり |
|---------|----------|----------|
| **Phase 0** | **context伝播修正（orchestrator.py, adapter.py）** | **1.5時間** |
| Phase 1 | llm_utils.py修正（callbacks引数 + ヘルパー関数） | 1時間 |
| Phase 2 | workflow修正（4ファイル） | 2時間 |
| Phase 3 | 単体テスト追加（context伝播 + callbacks） | 1.5時間 |
| Phase 4 | 結合テスト追加 | 1時間 |
| Phase 5 | E2E検証 | 0.5時間 |
| **合計** | | **7.5時間** |

---

## 10. レビュー履歴

| 日付 | レビュアー | 結果 | 指摘事項 |
|------|-----------|------|----------|
| 2026-01-07 | Claude | 条件付き承認 | context伝播問題を指摘、Phase 0追加が必要 |
| 2026-01-07 | - | 指摘反映完了 | Phase 0追加、見積もり更新、テスト計画拡充 |
