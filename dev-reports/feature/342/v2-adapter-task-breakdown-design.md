# V2 Adapter task_breakdown 対応設計書

## 概要

Job Generator V2 のアダプターが `task_breakdown=None` を返す設計により、フロントエンド（myAgentDesk）でタスクが表示されない問題の解決設計。

**作成日**: 2026-01-07
**最終更新**: 2026-01-07（レビュー指摘修正）
**関連Issue**: #342 Phase F
**ステータス**: 設計完了（実装待ち）

---

## 1. 現状分析

### 1.1 問題の症状

| 項目 | V1 | V2 |
|------|----|----|
| Job生成 | ✅ Success | ✅ Success |
| タスク表示 | ✅ 3 tasks | ❌ 0 tasks |
| ワークフロー表示 | ✅ 3 workflows | ❌ 0 workflows |
| Langfuseトレース | ✅ 確認可能 | ❌ Not found |

### 1.2 根本原因

`expertAgent/aiagent/langgraph/jobGeneratorV2/adapter.py:238` で意図的に `task_breakdown=None` を設定：

```python
def _convert_result(self, result: JobGenerationResult, job_id: str) -> "JobGeneratorResponse":
    if result.success:
        return JobGeneratorResponse(
            status="success",
            job_id=result.job_id or job_id,
            job_master_id=result.job_master_id,
            task_breakdown=None,  # ← ここが問題
            interface_definitions=None,  # ← これも問題
            workflow_yaml=result.workflow_yaml,
            evaluation=None,
            trace_id=self.trace_id,
        )
```

### 1.3 V2の内部データフロー

```
JobGeneratorV2Adapter.generate()
    ↓
ExecutionContext 作成
    ↓
Orchestrator.run_workflow()
    ↓
    phase_outputs = {}  ← 各フェーズの出力を保持
    ↓
TaskBreakdownWorkflow.execute()
    → TaskDecomposerSubWorkflow.decompose()
    → TaskBreakdownOutput(tasks=list[TaskDefinition])
    → phase_outputs[TASK_BREAKDOWN] = output  ← ここにタスク情報
    ↓
InterfaceDesignWorkflow.execute()
    → SchemaGeneratorSubWorkflow.generate()
    → InterfaceDesignOutput(interfaces=dict[str, InterfaceSchema])
    → phase_outputs[INTERFACE_DESIGN] = output  ← ここにインターフェース情報
    ↓
RegistrationWorkflow.execute()
    → phase_outputs[REGISTRATION] = output
    ↓
WorkflowGenWorkflow.execute()
    → phase_outputs[WORKFLOW_GEN] = output
    ↓
_create_result(phase_outputs)  ← tasks/interfaces を含めずに JobGenerationResult 作成
    ↓
_convert_result()  ← task_breakdown=None に変換（情報が失われる）
```

**重要**: タスク情報は `phase_outputs` dict に存在するが、`JobGenerationResult` に含まれていない。

---

## 2. 設計方針

### 2.1 方針A: JobGenerationResult の拡張（推奨）

**概要**: `JobGenerationResult` にタスク情報を保持し、アダプターで変換する。

**メリット**:
- V2内部の型システムを活かせる
- 段階的な移行が可能
- V1との互換性を維持

**変更箇所**:
1. `types.py`: `JobGenerationResult` に `tasks` フィールド追加
2. `orchestrator.py`: `_create_result()` で `phase_outputs` からタスク情報を含める
3. `adapter.py`: `_convert_result()` でタスク情報を変換

### 2.2 方針B: ExecutionContext からの抽出（不採用）

**概要**: `ExecutionContext` に蓄積されたタスク情報をアダプターで抽出。

**不採用理由**:
- **ExecutionContext には `tasks` / `interfaces` フィールドが存在しない**
- 現在の `ExecutionContext` はリトライ管理とサブコンテキスト（LLM, Storage等）のみを保持
- フィールド追加は設計変更が大きい

### 2.3 方針C: 別APIエンドポイントの追加（不採用）

**概要**: タスク詳細取得用の専用APIを追加。

**不採用理由**:
- フロントエンドの変更が必要
- 追加のAPI呼び出しが必要
- 複雑度が増す

### 2.4 採用方針: **方針A（JobGenerationResult の拡張）**

理由:
1. 最小限の変更で実現可能
2. V1との互換性を維持
3. 型安全性を保持
4. テストが容易

---

## 3. 詳細設計

### 3.1 types.py の変更

```python
@dataclass
class JobGenerationResult:
    """Result of job generation."""

    success: bool
    job_id: str | None = None
    job_master_id: str | None = None
    task_master_ids: list[str] = field(default_factory=list)
    workflow_yaml: str | None = None
    error: str | None = None
    relaxation_suggestions: list[RelaxationSuggestion] = field(default_factory=list)

    # 新規追加フィールド
    tasks: list[TaskDefinition] = field(default_factory=list)
    interfaces: dict[str, InterfaceSchema] = field(default_factory=dict)
```

### 3.2 orchestrator.py の変更

`_create_result()` メソッドで `phase_outputs` からタスク情報を含める：

```python
def _create_result(
    self,
    phase_outputs: dict[Phase, Any],
) -> JobGenerationResult:
    """Create final result from all phase outputs.

    Args:
        phase_outputs: Outputs from all phases

    Returns:
        JobGenerationResult
    """
    # 各フェーズの出力を取得
    breakdown_output: TaskBreakdownOutput = phase_outputs[Phase.TASK_BREAKDOWN]
    interface_output: InterfaceDesignOutput = phase_outputs[Phase.INTERFACE_DESIGN]
    registration_output: RegistrationOutput = phase_outputs[Phase.REGISTRATION]
    workflow_output: WorkflowGenOutput = phase_outputs[Phase.WORKFLOW_GEN]

    return JobGenerationResult(
        success=True,
        job_id=registration_output.job_id,
        job_master_id=registration_output.job_master_id,
        task_master_ids=registration_output.task_master_ids,
        workflow_yaml=workflow_output.workflow_yaml,
        # 新規追加: phase_outputs から取得
        tasks=breakdown_output.tasks,
        interfaces=interface_output.interfaces,
    )
```

### 3.3 adapter.py の変更

`_convert_result()` でタスク情報を変換。

**重要**: `JobGeneratorResponse` のスキーマ型に合わせる：
- `task_breakdown`: `list[dict[str, Any]] | None`
- `interface_definitions`: `dict[str, dict[str, Any]] | None`

```python
def _convert_result(self, result: JobGenerationResult, job_id: str) -> "JobGeneratorResponse":
    if result.success:
        # V2のTaskDefinitionをlist[dict]に変換
        task_breakdown = self._convert_tasks_to_breakdown(result.tasks) if result.tasks else None

        # V2のInterfaceSchemaをdict[str, dict]に変換
        interface_definitions = self._convert_interfaces(result.interfaces) if result.interfaces else None

        return JobGeneratorResponse(
            status="success",
            job_id=result.job_id or job_id,
            job_master_id=result.job_master_id,
            task_breakdown=task_breakdown,  # 変換後のデータを設定
            interface_definitions=interface_definitions,  # 変換後のデータを設定
            evaluation_result=None,
            infeasible_tasks=[],
            alternative_proposals=[],
            api_extension_proposals=[],
            requirement_relaxation_suggestions=[
                {
                    "original_requirement": s.original_requirement,
                    "suggested_alternative": s.suggested_alternative,
                    "reason": s.reason,
                }
                for s in result.relaxation_suggestions
            ],
            validation_errors=[],
            error_message=None,
            langfuse_trace_id=None,
        )

def _convert_tasks_to_breakdown(self, tasks: list[TaskDefinition]) -> list[dict[str, Any]]:
    """V2 TaskDefinition を list[dict] に変換.

    JobGeneratorResponse.task_breakdown の型は list[dict[str, Any]] | None
    """
    return [
        {
            "task_id": task.id,
            "name": task.name,
            "description": task.description,
            "dependencies": task.dependencies,
            "priority": task.priority,
            "task_type": task.task_type,
            "recommended_api": task.recommended_api,
        }
        for task in tasks
    ]

def _convert_interfaces(
    self,
    interfaces: dict[str, InterfaceSchema],
) -> dict[str, dict[str, Any]]:
    """V2 InterfaceSchema を dict[str, dict] に変換.

    JobGeneratorResponse.interface_definitions の型は dict[str, dict[str, Any]] | None
    """
    return {
        task_id: {
            "input_schema": schema.input_schema,
            "output_schema": schema.output_schema,
            "description": schema.description,
        }
        for task_id, schema in interfaces.items()
    }
```

---

## 4. 影響範囲

### 4.1 変更ファイル一覧

| ファイル | 変更内容 | 影響度 |
|---------|---------|--------|
| `types.py` | `JobGenerationResult` にフィールド追加 | 低 |
| `orchestrator.py` | `_create_result()` でタスク情報を含める | 中 |
| `adapter.py` | 変換メソッド追加、`_convert_result()` 修正 | 中 |

**注**: `context.py` の変更は不要（`ExecutionContext` は変更しない）

### 4.2 テスト影響

| テスト種別 | 対応 |
|-----------|------|
| 単体テスト | `adapter.py` の変換ロジックテスト追加 |
| 結合テスト | V2 APIレスポンスにtask_breakdown含まれることを確認 |
| 受入テスト | フロントエンドでタスク表示を確認 |

### 4.3 後方互換性

- V1 API は変更なし
- V2 API は拡張のみ（既存フィールドの意味変更なし）
- フロントエンドは変更不要（既存のtask_breakdownフィールドを使用）

---

## 5. Langfuseトレース問題

### 5.1 問題

V2で生成されたジョブのトレースがLangfuseで "Trace not found" となる。

### 5.2 推定原因

1. V2のLangfuse統合が未完了
2. プロジェクトID/設定の不一致
3. トレースID生成タイミングの問題

### 5.3 調査項目

1. `llm_utils.py` での Langfuse トレース生成確認
2. `ObservabilityContext.tracer` の設定確認
3. Langfuse プロジェクト設定の確認

### 5.4 対応方針

本設計書のスコープ外として、別Issue（または追加タスク）で対応。

---

## 6. 実装順序

```
Phase 1: types.py 変更
    ↓
    JobGenerationResult に tasks, interfaces フィールド追加
    ↓
Phase 2: orchestrator.py 修正
    ↓
    _create_result() で phase_outputs からタスク情報を含める
    ↓
Phase 3: adapter.py 変換ロジック追加
    ↓
    _convert_tasks_to_breakdown(), _convert_interfaces() 追加
    _convert_result() 修正
    ↓
Phase 4: 単体テスト追加
    ↓
    test_adapter.py に変換ロジックのテスト追加
    ↓
Phase 5: 結合テスト追加
    ↓
    V2 APIレスポンスの検証
    ↓
Phase 6: E2Eテスト（フロントエンド確認）
    ↓
    myAgentDesk でタスク表示を確認
```

---

## 7. リスク評価

| リスク | 影響度 | 対策 |
|--------|--------|------|
| phase_outputs の不整合 | 中 | フェーズ失敗時のフォールバック処理を追加 |
| 変換ロジックのバグ | 低 | 単体テストで十分にカバー |
| パフォーマンス劣化 | 低 | タスク数は通常10以下のため問題なし |
| V1との挙動差異 | 中 | 受入テストで確認 |

---

## 8. 参考資料

### 8.1 関連ファイル

- `expertAgent/aiagent/langgraph/jobGeneratorV2/adapter.py`
- `expertAgent/aiagent/langgraph/jobGeneratorV2/types.py`
- `expertAgent/aiagent/langgraph/jobGeneratorV2/orchestrator.py`
- `expertAgent/app/schemas/job_generator.py` (V1のスキーマ定義)

### 8.2 型定義参照

**JobGeneratorResponse (job_generator.py:87-95)**:
```python
task_breakdown: list[dict[str, Any]] | None = Field(...)
interface_definitions: dict[str, dict[str, Any]] | None = Field(...)
```

**TaskBreakdownOutput (types.py)**:
```python
@dataclass
class TaskBreakdownOutput:
    status: PhaseStatus
    tasks: list[TaskDefinition] = field(default_factory=list)
    ...
```

**InterfaceDesignOutput (types.py)**:
```python
@dataclass
class InterfaceDesignOutput:
    status: PhaseStatus
    interfaces: dict[str, InterfaceSchema] = field(default_factory=dict)
    ...
```

---

## 9. 変更履歴

| 日付 | 変更内容 | 担当 |
|------|---------|------|
| 2026-01-07 | 初版作成 | Claude Code |
| 2026-01-07 | レビュー指摘修正: Section 3.2, 3.3, 3.4, 4.1, 6 | Claude Code |

### 9.1 レビュー指摘修正内容

1. **Section 3.2**: `context.tasks` → `phase_outputs[Phase.TASK_BREAKDOWN].tasks` に修正
2. **Section 3.3**: 変換先の型を `list[dict[str, Any]]` / `dict[str, dict[str, Any]]` に修正
3. **Section 3.4**: 削除（`ExecutionContext` には `tasks`/`interfaces` フィールドが存在しないため）
4. **Section 4.1**: `context.py` を削除
5. **Section 6**: `context.py` 確認フェーズを削除

---

## 10. 承認

| 役割 | 名前 | 日付 | 署名 |
|------|------|------|------|
| 設計者 | Claude Code | 2026-01-07 | ✅ |
| レビュアー | Claude Code | 2026-01-07 | ✅ |
| 承認者 | - | - | - |
