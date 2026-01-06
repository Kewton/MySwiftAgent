# 現行アーキテクチャ vs 提案アーキテクチャ 比較

## 1. 構造比較

### 現行アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│             JobTaskGeneratorAgent (単一グラフ)                   │
│                                                                  │
│  ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐            │
│  │req_    │──▶│evalua- │──▶│inter-  │──▶│schema_ │            │
│  │analysis│   │tor     │   │face_def│   │enrich  │            │
│  └────────┘   └────────┘   └────────┘   └────────┘            │
│       ▲           │             ▲           │                   │
│       │           │             │           │                   │
│       └───────────┘             │           │                   │
│       (retry)                   │           │                   │
│                                 │           ▼                   │
│  ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐            │
│  │job_reg │◀──│valida- │◀──│master_ │◀──│evalua- │            │
│  │        │   │tion    │   │creation│   │tor     │            │
│  └────────┘   └────────┘   └────────┘   └────────┘            │
│       │           ▲                         ▲                   │
│       │           └─────────────────────────┘                   │
│       │                    (retry)                              │
│       ▼                                                         │
│  ┌────────┐                                                     │
│  │workflow│                                                     │
│  │_gen    │──▶ END                                             │
│  └────────┘                                                     │
│                                                                  │
│  状態: 30+ フィールド (フラット構造)                            │
│  リトライ: retry_count を複数ノードで管理                        │
└─────────────────────────────────────────────────────────────────┘
```

### 提案アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestrator Layer                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ JobGenerationOrchestrator                                  │  │
│  │ - フェーズ間遷移制御                                       │  │
│  │ - グローバル状態管理                                       │  │
│  │ - 進捗報告                                                │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
     ┌────────────────────────┼────────────────────────┐
     │                        │                        │
     ▼                        ▼                        ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ Phase 1      │      │ Phase 2      │      │ Phase 3      │
│ TaskBreakdown│─────▶│InterfaceDesign│────▶│ Registration │
│              │      │              │      │              │
│ 状態: 8項目  │      │ 状態: 8項目  │      │ 状態: 6項目  │
│ retry: 独立  │      │ retry: 独立  │      │ retry: 独立  │
└──────────────┘      └──────────────┘      └──────────────┘
                                                   │
                                                   ▼
                                           ┌──────────────┐
                                           │ Phase 4      │
                                           │ WorkflowGen  │
                                           │              │
                                           │ 状態: 10項目 │
                                           │ retry: 独立  │
                                           └──────────────┘
```

---

## 2. 主要な違い

| 観点 | 現行 | 提案 | 改善効果 |
|-----|------|------|---------|
| **グラフ構造** | 単一の巨大グラフ（8ノード） | 4つの独立したサブワークフロー | 責務分離、テスト容易 |
| **状態管理** | フラット構造（30+フィールド） | 階層構造（各8-10フィールド） | 可読性、保守性向上 |
| **リトライ管理** | 分散（複数箇所で管理） | 集約（各フェーズ内で完結） | バグ防止、追跡容易 |
| **ルーター** | 複雑な条件分岐（10+条件） | シンプルな状態遷移（3-5条件） | デバッグ容易 |
| **依存関係** | 暗黙的（状態フィールド依存） | 明示的（入出力型定義） | 契約明確化 |
| **テスト** | 結合テスト中心 | 単体テスト + 結合テスト | カバレッジ向上 |
| **観測可能性** | ログベース | トレース + メトリクス + 構造化ログ | 問題特定容易 |

---

## 3. 状態フィールド比較

### 現行: JobTaskGeneratorState (30+ fields)

```python
class JobTaskGeneratorState(TypedDict):
    # Input (2)
    user_requirement: str
    max_retry: int

    # Intermediate (10)
    task_breakdown: list[dict]
    overall_summary: str
    interface_definitions: dict
    schema_enrichment_stats: dict
    task_masters: list[dict]
    task_master_ids: list[str]
    job_master: dict
    job_master_id: str | None

    # Feasibility (4)
    feasibility_analysis: dict | None
    infeasible_tasks: list[dict]
    alternative_proposals: list[dict]
    api_extension_proposals: list[dict]

    # Evaluation (5)
    evaluation_result: dict | None
    evaluation_retry_count: int
    evaluation_errors: list[str]
    evaluation_feedback: str | None
    evaluator_stage: str

    # Validation (4)
    validation_result: dict | None
    retry_count: int  # ← 問題の中心
    validation_errors: list[str]
    schema_validation_errors: list[dict]

    # Output (3)
    job_id: str | None
    status: str
    error_message: str | None

    # Issue-specific (5)
    workflow_results: list[dict]
    phase: str
    tracking_job_id: str | None
    job_body_parameters: list[dict]
    interface_warnings: list[str]
    derived_fields_degradation_count: int
```

### 提案: 分割された状態

```python
# Phase 1: TaskBreakdownState (8 fields)
class TaskBreakdownState(TypedDict):
    user_requirement: str       # 入力
    capabilities: list[dict]    # 入力
    parsed_intent: dict | None  # 中間
    raw_tasks: list[dict]       # 中間
    feasibility: list[dict]     # 中間
    final_tasks: list[dict]     # 出力
    status: str                 # 出力
    retry: RetryState           # リトライ（独立）

# Phase 2: InterfaceDesignState (8 fields)
class InterfaceDesignState(TypedDict):
    tasks: list[dict]           # 入力
    openapi_specs: dict         # 入力
    raw_schemas: dict           # 中間
    compatibility: dict         # 中間
    enriched_schemas: dict      # 中間
    final_interfaces: dict      # 出力
    status: str                 # 出力
    retry: RetryState           # リトライ（独立）

# Phase 3: RegistrationState (6 fields)
class RegistrationState(TypedDict):
    tasks: list[dict]           # 入力
    interfaces: dict            # 入力
    master_ids: dict            # 出力
    job_id: str | None          # 出力
    status: str                 # 出力
    retry: RetryState           # リトライ（独立）

# Phase 4: WorkflowGenState (10 fields)
class WorkflowGenState(TypedDict):
    task_master_id: str         # 入力
    task_data: dict             # 入力
    yaml_content: str           # 中間
    sample_input: dict          # 中間
    test_result: dict | None    # 中間
    validation: dict | None     # 中間
    final_yaml: str             # 出力
    status: str                 # 出力
    retry: RetryState           # リトライ（独立）
```

---

## 4. リトライ管理比較

### 現行の問題

```python
# interface_definition.py - retry_count の管理が分散
if (
    evaluation_feedback
    or (validation_result and not validation_result.get("is_valid", True))
    or schema_validation_errors
    # interface_warnings が抜けている！ ← バグ
):
    updated_retry = current_retry + 1
else:
    updated_retry = 0  # リセットされる

# agent.py - evaluator_router でチェック
if interface_warnings and retry_count < MAX_RETRY_COUNT:
    return "interface_definition"  # ここで無限ループ
```

### 提案の解決策

```python
# 各フェーズ内で完結するリトライ管理
class InterfaceDesignWorkflow:
    async def execute(self, input: InterfaceDesignInput) -> InterfaceDesignOutput:
        state = InterfaceDesignState(
            tasks=input.tasks,
            retry=RetryState(max_count=3),  # フェーズ専用
        )

        while state.retry.can_retry():
            result = await self._try_design(state)

            if result.status == "success":
                return result

            if result.status == "needs_retry":
                state.retry.record(reason=result.error)
                continue

            # 回復不能なエラー
            return InterfaceDesignOutput(status="failed", ...)

        return InterfaceDesignOutput(status="max_retries", ...)
```

---

## 5. ルーター比較

### 現行: 複雑な条件分岐

```python
def evaluator_router(state) -> Literal[...]:
    evaluation_result = state.get("evaluation_result")
    evaluator_stage = state.get("evaluator_stage")
    retry_count = state.get("retry_count", 0)
    error_message = state.get("error_message")

    if error_message:
        return "END"
    if not evaluation_result:
        return "END"

    is_valid = evaluation_result.get("is_valid", False)
    all_tasks_feasible = evaluation_result.get("all_tasks_feasible", True)
    all_apis_specific = evaluation_result.get("all_apis_specific", True)

    if evaluator_stage == "after_task_breakdown":
        if not task_breakdown:
            return "END"
        if is_valid and all_tasks_feasible and all_apis_specific:
            return "interface_definition"
        if retry_count < MAX_RETRY_COUNT:
            return "requirement_analysis"
        return "END"

    if evaluator_stage == "after_interface_definition":
        schema_errors = state.get("schema_validation_errors", [])
        if schema_errors and retry_count < MAX_RETRY_COUNT:
            return "interface_definition"

        interface_warnings = state.get("interface_warnings", [])
        if interface_warnings and retry_count < MAX_RETRY_COUNT:
            return "interface_definition"

        if is_valid and all_tasks_feasible:
            return "master_creation"
        if retry_count < MAX_RETRY_COUNT:
            return "interface_definition"
        return "END"

    return "END"
```

### 提案: シンプルな状態遷移

```python
class Orchestrator:
    async def _execute_phase(self, phase: Phase, context: Context) -> PhaseResult:
        workflow = self.workflows[phase]
        result = await workflow.execute(context.get_input(phase))

        # シンプルな遷移ロジック
        if result.status == PhaseStatus.SUCCESS:
            return result

        if result.status == PhaseStatus.NEEDS_RELAXATION:
            return result

        # FAILED - フェーズ内でリトライ済み
        return result

    async def execute(self, request: Request) -> Result:
        context = Context(request)

        for phase in [Phase.BREAKDOWN, Phase.INTERFACE, Phase.REGISTER, Phase.WORKFLOW]:
            result = await self._execute_phase(phase, context)

            if result.status != PhaseStatus.SUCCESS:
                return self._handle_non_success(phase, result)

            context.update(phase, result)

        return self._build_success(context)
```

---

## 6. テスト容易性比較

### 現行: 結合テスト依存

```python
# 全体を通してテストするしかない
@pytest.mark.asyncio
async def test_job_generation():
    state = create_initial_state(
        user_requirement="...",
        max_retry=5,
    )

    agent = create_job_task_generator_agent()
    result = await agent.ainvoke(state)

    # 8ノード全体の結果を検証
    assert result["status"] == "success"
```

### 提案: 単体テスト可能

```python
# 各フェーズを独立してテスト
@pytest.mark.asyncio
async def test_task_breakdown_workflow():
    workflow = TaskBreakdownWorkflow(
        llm_client=MockLLMClient(),
        capabilities=load_test_capabilities(),
    )

    input = TaskBreakdownInput(
        user_requirement="Gmail未読メールを要約してSlackに投稿",
    )

    result = await workflow.execute(input)

    assert result.status == PhaseStatus.SUCCESS
    assert len(result.tasks) == 3


@pytest.mark.asyncio
async def test_interface_design_workflow():
    workflow = InterfaceDesignWorkflow(
        llm_client=MockLLMClient(),
    )

    input = InterfaceDesignInput(
        tasks=[...],  # Phase 1 の出力をモック
    )

    result = await workflow.execute(input)

    assert result.status == PhaseStatus.SUCCESS
    assert "task_1" in result.interfaces


# 互換性チェックの単体テスト
def test_compatibility_checker():
    checker = CompatibilityChecker()

    interfaces = {
        "task_1": InterfaceSchema(
            output_schema={"properties": {"result": {"type": "string"}}},
        ),
        "task_2": InterfaceSchema(
            input_schema={"required": ["result", "missing_field"]},
        ),
    }

    report = checker.check(tasks, interfaces)

    assert not report.is_compatible
    assert len(report.issues) == 1
    assert report.issues[0].type == "MISSING_REQUIRED_FIELD"
```

---

## 7. 移行インパクト

### コード変更量（推定）

| 項目 | 現行 | 提案 | 変更量 |
|-----|------|------|--------|
| agent.py | 319行 | 150行 (Orchestrator) | -50% |
| state.py | 179行 | 4ファイル × 50行 = 200行 | +10% |
| nodes/ | 8ファイル × 200行 = 1600行 | 4ワークフロー × 300行 = 1200行 | -25% |
| routers | agent.py内 | 削除（各ワークフロー内） | -100% |
| tests | ~500行 | ~1500行 | +200% |

### リスク評価

| リスク | 影響度 | 発生確率 | 緩和策 |
|-------|--------|---------|-------|
| 移行中の機能停止 | High | Medium | Feature flag による並行運用 |
| 新バグの混入 | High | Medium | 段階的移行 + 結合テスト強化 |
| パフォーマンス劣化 | Medium | Low | ベンチマーク比較 |
| 学習コスト | Low | High | ドキュメント整備 |

---

## 8. 結論

提案アーキテクチャは以下の点で現行より優れている：

1. **バグ防止**: リトライ管理の一元化により、Issue #342 のような無限ループバグを構造的に防止
2. **保守性**: 各フェーズが独立しているため、変更の影響範囲が限定的
3. **テスト性**: 単体テストが書きやすく、カバレッジ向上が容易
4. **観測可能性**: フェーズ単位でのトレーシングにより、問題箇所の特定が容易
5. **拡張性**: 新機能追加時に既存コードへの影響が最小限

移行には一定の工数が必要だが、長期的な保守コスト削減と品質向上を考慮すると、投資に見合う価値がある。

---

**作成日**: 2026-01-07
**作成者**: Claude Code
