# Job Generator Agent アーキテクチャ設計書

## 1. Executive Summary

本ドキュメントは、Job Generator Agent の「あるべき姿」を定義する。
現行システムの問題点を踏まえつつ、ゼロベースで理想的なアーキテクチャを設計する。

### 設計方針

| 原則 | 説明 |
|-----|------|
| **Separation of Concerns** | 責務を明確に分離し、独立したコンポーネントに分割 |
| **Single Responsibility** | 各コンポーネントは1つの責務のみを持つ |
| **Explicit Contracts** | コンポーネント間のインターフェースを明示的に定義 |
| **Observable State** | すべての状態遷移が追跡可能 |
| **Testable Units** | 各コンポーネントが独立してテスト可能 |
| **Resilient** | 障害時の回復機構を明確に設計 |

---

## 2. ビジネス要件

### 2.1 コア機能

**入力**: 自然言語によるワークフロー要件
**出力**: 実行可能な Job（jobqueue 登録済み）+ GraphAI YAML ワークフロー

### 2.2 機能要件

| 機能 | 説明 | 優先度 |
|-----|------|--------|
| タスク分解 | 自然言語要件を実行可能なタスクに分解 | Must |
| 実現可能性評価 | 利用可能な機能（capabilities）との照合 | Must |
| インターフェース定義 | タスク間の入出力 JSON Schema 定義 | Must |
| スキーマ強化 | OpenAPI 仕様との照合・補完 | Should |
| DB 登録 | TaskMaster/JobMaster の永続化 | Must |
| ワークフロー生成 | GraphAI YAML の自動生成 | Must |
| 自己修復 | バリデーションエラー時の自動修正 | Should |
| 要求緩和提案 | 実現不可能な要求に対する代替案提示 | Should |

### 2.3 非機能要件

| 要件 | 目標値 |
|-----|--------|
| 処理時間 | 通常: 1-3分、最大: 5分 |
| 成功率 | 70% 以上（初回） |
| リトライ上限 | 各フェーズ 3回、全体 5回 |
| 観測可能性 | 全状態遷移が Langfuse で追跡可能 |
| テストカバレッジ | 単体 90%、結合 50% |

---

## 3. アーキテクチャ概要

### 3.1 レイヤー構成

```
┌─────────────────────────────────────────────────────────────────────┐
│                        API Layer (FastAPI)                          │
│  POST /job-generator  │  GET /jobs/{id}/status  │  DELETE /jobs/{id}│
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Orchestrator Layer                               │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              JobGenerationOrchestrator                       │   │
│  │  - 全体フロー制御                                            │   │
│  │  - フェーズ間の状態遷移管理                                   │   │
│  │  - グローバルリトライポリシー                                 │   │
│  │  - 進捗報告                                                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
│  Phase 1          │   │  Phase 2          │   │  Phase 3          │
│  TaskBreakdown    │──▶│  InterfaceDesign  │──▶│  Registration     │
│  Workflow         │   │  Workflow         │   │  Workflow         │
└───────────────────┘   └───────────────────┘   └───────────────────┘
                                                          │
                                                          ▼
                                                ┌───────────────────┐
                                                │  Phase 4          │
                                                │  WorkflowGen      │
                                                │  Workflow         │
                                                └───────────────────┘
```

### 3.2 コンポーネント責務

| レイヤー | コンポーネント | 責務 |
|---------|--------------|------|
| API | JobGeneratorEndpoint | HTTPリクエスト処理、バリデーション |
| Orchestrator | JobGenerationOrchestrator | フェーズ間の遷移制御、進捗管理 |
| Workflow | TaskBreakdownWorkflow | 要件分析、タスク分解、実現可能性評価 |
| Workflow | InterfaceDesignWorkflow | インターフェース定義、スキーマ強化、互換性検証 |
| Workflow | RegistrationWorkflow | DB登録、バリデーション |
| Workflow | WorkflowGenWorkflow | GraphAI YAML生成、テスト実行 |

---

## 4. 詳細設計

### 4.1 Orchestrator Layer

#### 4.1.1 JobGenerationOrchestrator

```python
class JobGenerationOrchestrator:
    """ジョブ生成全体を制御するオーケストレーター"""

    def __init__(
        self,
        task_breakdown_workflow: TaskBreakdownWorkflow,
        interface_design_workflow: InterfaceDesignWorkflow,
        registration_workflow: RegistrationWorkflow,
        workflow_gen_workflow: WorkflowGenWorkflow,
        retry_policy: RetryPolicy,
        progress_reporter: ProgressReporter,
    ):
        self.workflows = {
            Phase.TASK_BREAKDOWN: task_breakdown_workflow,
            Phase.INTERFACE_DESIGN: interface_design_workflow,
            Phase.REGISTRATION: registration_workflow,
            Phase.WORKFLOW_GEN: workflow_gen_workflow,
        }
        self.retry_policy = retry_policy
        self.progress_reporter = progress_reporter

    async def execute(
        self,
        request: JobGenerationRequest,
    ) -> JobGenerationResult:
        """ジョブ生成を実行"""
        context = OrchestratorContext(request)

        for phase in Phase:
            result = await self._execute_phase(phase, context)

            if result.status == PhaseStatus.FAILED:
                return self._handle_failure(phase, result, context)

            if result.status == PhaseStatus.NEEDS_RELAXATION:
                return self._handle_relaxation(result, context)

            context.update(phase, result)
            self.progress_reporter.report(phase, context)

        return self._build_success_result(context)
```

#### 4.1.2 状態管理

```python
class OrchestratorContext:
    """オーケストレーターの実行コンテキスト"""

    # 入力
    request: JobGenerationRequest

    # フェーズ結果
    task_breakdown_result: TaskBreakdownResult | None
    interface_design_result: InterfaceDesignResult | None
    registration_result: RegistrationResult | None
    workflow_gen_result: WorkflowGenResult | None

    # メタデータ
    current_phase: Phase
    phase_history: list[PhaseExecution]
    total_duration: timedelta
    total_cost: Decimal
```

#### 4.1.3 フェーズ定義

```python
class Phase(Enum):
    """ジョブ生成のフェーズ"""
    TASK_BREAKDOWN = "task_breakdown"      # Phase 1
    INTERFACE_DESIGN = "interface_design"  # Phase 2
    REGISTRATION = "registration"          # Phase 3
    WORKFLOW_GEN = "workflow_gen"          # Phase 4

class PhaseStatus(Enum):
    """フェーズの実行結果ステータス"""
    SUCCESS = "success"
    FAILED = "failed"
    NEEDS_RETRY = "needs_retry"
    NEEDS_RELAXATION = "needs_relaxation"
```

### 4.2 Phase 1: TaskBreakdownWorkflow

#### 4.2.1 責務

Phase 1 は以下の3つの責務を持つが、**単一責任原則に従い内部で明確に分離**する：

| サブコンポーネント | 責務 | 入力 | 出力 |
|------------------|------|------|------|
| **TaskDecomposerSubWorkflow** | 自然言語要件をタスクリストに分解 | user_requirement | raw_tasks |
| **FeasibilitySubWorkflow** | 各タスクの実現可能性を評価 | raw_tasks, capabilities | feasibility_report |
| **AlternativeSubWorkflow** | 実現不可能なタスクに対する代替案を提案 | infeasible_tasks | alternatives |

#### 4.2.2 内部アーキテクチャ（MF-1 対応）

```python
class TaskBreakdownWorkflow(WorkflowProtocol):
    """Phase 1: タスク分解ワークフロー

    責務を3つのサブワークフローに分離し、単一責任原則を遵守。
    各サブワークフローは独立してテスト可能。
    """

    def __init__(
        self,
        decomposer: TaskDecomposerSubWorkflow,
        feasibility_checker: FeasibilitySubWorkflow,
        alternative_proposer: AlternativeSubWorkflow,
    ):
        self.decomposer = decomposer
        self.feasibility_checker = feasibility_checker
        self.alternative_proposer = alternative_proposer

    async def execute(
        self,
        input: TaskBreakdownInput,
        context: ExecutionContext,
    ) -> TaskBreakdownOutput:
        """タスク分解を実行（3フェーズの内部処理）"""

        # Sub-phase 1: タスク分解
        decomposition_result = await self.decomposer.execute(
            DecomposerInput(
                user_requirement=input.user_requirement,
            ),
            context.llm,
        )

        # Sub-phase 2: 実現可能性評価
        feasibility_result = await self.feasibility_checker.execute(
            FeasibilityInput(
                tasks=decomposition_result.tasks,
                capabilities=input.available_capabilities,
            ),
            context.llm,
        )

        # Sub-phase 3: 代替案提案（必要な場合のみ）
        if feasibility_result.infeasible_tasks:
            alternative_result = await self.alternative_proposer.execute(
                AlternativeInput(
                    infeasible_tasks=feasibility_result.infeasible_tasks,
                    capabilities=input.available_capabilities,
                ),
                context.llm,
            )

            if not alternative_result.has_alternatives:
                return TaskBreakdownOutput(
                    status=PhaseStatus.NEEDS_RELAXATION,
                    relaxation_suggestions=alternative_result.relaxation_suggestions,
                )

            # 代替案でタスクを更新
            final_tasks = self._merge_alternatives(
                decomposition_result.tasks,
                alternative_result.alternatives,
            )
        else:
            final_tasks = decomposition_result.tasks

        return TaskBreakdownOutput(
            status=PhaseStatus.SUCCESS,
            tasks=final_tasks,
            feasibility_report=feasibility_result.report,
        )


class TaskDecomposerSubWorkflow:
    """サブワークフロー: タスク分解（単一責務）"""

    async def execute(
        self,
        input: DecomposerInput,
        llm_context: LLMContext,
    ) -> DecomposerOutput:
        """自然言語をタスクリストに分解"""
        ...


class FeasibilitySubWorkflow:
    """サブワークフロー: 実現可能性評価（単一責務）"""

    async def execute(
        self,
        input: FeasibilityInput,
        llm_context: LLMContext,
    ) -> FeasibilityOutput:
        """capabilities.yaml との照合"""
        ...


class AlternativeSubWorkflow:
    """サブワークフロー: 代替案提案（単一責務）"""

    async def execute(
        self,
        input: AlternativeInput,
        llm_context: LLMContext,
    ) -> AlternativeOutput:
        """実現不可能なタスクの代替案を生成"""
        ...
```

#### 4.2.3 ワークフロー図

```
START
  │
  ▼
┌─────────────────┐
│ RequirementParser│  ← 自然言語をパース、意図を抽出
└─────────────────┘
  │
  ▼
┌─────────────────┐
│ TaskDecomposer  │  ← タスクに分解（LLM）
└─────────────────┘
  │
  ▼
┌─────────────────┐
│FeasibilityChecker│  ← capabilities.yaml との照合
└─────────────────┘
  │
  ├── [全タスク実現可能] ──────────────────────┐
  │                                           │
  │ [実現不可能タスクあり]                      │
  │     │                                     │
  │     ▼                                     │
  │ ┌─────────────────┐                       │
  │ │AlternativeProposer│ ← 代替案生成（LLM）  │
  │ └─────────────────┘                       │
  │     │                                     │
  │     ├── [代替案あり] ─────────────────────┤
  │     │                                     │
  │     │ [代替案なし]                         │
  │     │     │                               │
  │     │     ▼                               │
  │     │ ┌─────────────────┐                 │
  │     │ │RelaxationGenerator│ ← 緩和提案    │
  │     │ └─────────────────┘                 │
  │     │     │                               │
  │     │     ▼                               │
  │     │   NEEDS_RELAXATION ──────────────▶ END
  │     │                                     │
  │     ▼                                     │
  │   代替案で再分解                           │
  │     │                                     │
  └─────┴─────────────────────────────────────┤
                                              │
                                              ▼
                                           SUCCESS
```

#### 4.2.3 入出力定義

```python
@dataclass
class TaskBreakdownInput:
    """TaskBreakdownWorkflow の入力"""
    user_requirement: str
    available_capabilities: list[Capability]
    max_tasks: int = 10

@dataclass
class TaskBreakdownOutput:
    """TaskBreakdownWorkflow の出力"""
    status: PhaseStatus
    tasks: list[TaskDefinition]
    feasibility_report: FeasibilityReport
    relaxation_suggestions: list[RelaxationSuggestion] | None
```

#### 4.2.4 状態定義（最小限）

```python
class TaskBreakdownState(TypedDict):
    """TaskBreakdownWorkflow の内部状態"""
    # 入力（不変）
    user_requirement: str
    capabilities: list[dict]

    # 中間結果
    parsed_intent: dict | None
    raw_tasks: list[dict]
    feasibility_results: list[dict]
    alternatives: list[dict]

    # 出力
    final_tasks: list[dict]
    status: str
    error: str | None

    # リトライ管理（このフェーズ専用）
    retry_count: int
    max_retry: int
```

### 4.3 Phase 2: InterfaceDesignWorkflow

#### 4.3.1 責務

1. 各タスクの入出力インターフェース（JSON Schema）を定義
2. タスクチェーン間の互換性を検証
3. OpenAPI スキーマとの照合・強化

#### 4.3.2 ワークフロー図

```
START (tasks: list[TaskDefinition])
  │
  ▼
┌─────────────────┐
│ SchemaGenerator │  ← 各タスクの I/O スキーマ生成（LLM）
└─────────────────┘
  │
  ▼
┌─────────────────────┐
│CompatibilityChecker │  ← タスク間の互換性検証
└─────────────────────┘
  │
  ├── [互換性OK] ─────────────────────────────┐
  │                                           │
  │ [互換性NG]                                │
  │     │                                     │
  │     ▼                                     │
  │ ┌─────────────────┐                       │
  │ │ SchemaAdjuster  │  ← スキーマ調整（LLM） │
  │ └─────────────────┘                       │
  │     │                                     │
  │     └── [リトライ] ───────────────────────┤
  │                                           │
  └───────────────────────────────────────────┤
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │ SchemaEnricher  │  ← OpenAPI との照合
                                    └─────────────────┘
                                              │
                                              ▼
                                           SUCCESS
```

#### 4.3.3 入出力定義

```python
@dataclass
class InterfaceDesignInput:
    """InterfaceDesignWorkflow の入力"""
    tasks: list[TaskDefinition]
    openapi_specs: dict[str, OpenAPISpec]

@dataclass
class InterfaceDesignOutput:
    """InterfaceDesignWorkflow の出力"""
    status: PhaseStatus
    interfaces: dict[str, InterfaceSchema]
    compatibility_report: CompatibilityReport
    enrichment_report: EnrichmentReport
```

#### 4.3.4 互換性検証ルール

```python
class CompatibilityChecker:
    """タスクチェーン間の互換性を検証"""

    def check(
        self,
        tasks: list[TaskDefinition],
        interfaces: dict[str, InterfaceSchema],
    ) -> CompatibilityReport:
        issues = []

        for i in range(len(tasks) - 1):
            current = tasks[i]
            next_task = tasks[i + 1]

            current_output = interfaces[current.id].output_schema
            next_input = interfaces[next_task.id].input_schema

            # Rule 1: 必須フィールドの提供
            missing = self._check_required_fields(
                current_output, next_input
            )
            if missing:
                issues.append(CompatibilityIssue(
                    type="MISSING_REQUIRED_FIELD",
                    source_task=current.id,
                    target_task=next_task.id,
                    fields=missing,
                ))

            # Rule 2: 型の互換性
            type_mismatches = self._check_type_compatibility(
                current_output, next_input
            )
            if type_mismatches:
                issues.append(CompatibilityIssue(
                    type="TYPE_MISMATCH",
                    source_task=current.id,
                    target_task=next_task.id,
                    fields=type_mismatches,
                ))

        return CompatibilityReport(
            is_compatible=len(issues) == 0,
            issues=issues,
        )
```

### 4.4 Phase 3: RegistrationWorkflow

#### 4.4.1 責務

1. InterfaceMaster の登録（既存検索 or 新規作成）
2. TaskMaster の登録
3. JobMaster / JobMasterTask の登録
4. 登録内容のバリデーション

#### 4.4.2 ワークフロー図

```
START (tasks + interfaces)
  │
  ▼
┌─────────────────────┐
│InterfaceMasterFinder│  ← 既存 InterfaceMaster 検索
└─────────────────────┘
  │
  ├── [既存あり] ──▶ ID 取得
  │
  │ [既存なし]
  │     │
  │     ▼
  │ ┌─────────────────────┐
  │ │InterfaceMasterCreator│  ← 新規作成
  │ └─────────────────────┘
  │     │
  └─────┴─────────────────────────────────────┐
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │TaskMasterCreator │
                                    └─────────────────┘
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │ JobMasterCreator│
                                    └─────────────────┘
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │  JobRegistrar   │  ← jobqueue に登録
                                    └─────────────────┘
                                              │
                                              ▼
                                           SUCCESS
```

#### 4.4.3 入出力定義

```python
@dataclass
class RegistrationInput:
    """RegistrationWorkflow の入力"""
    tasks: list[TaskDefinition]
    interfaces: dict[str, InterfaceSchema]

@dataclass
class RegistrationOutput:
    """RegistrationWorkflow の出力"""
    status: PhaseStatus
    job_master_id: str
    task_master_ids: list[str]
    interface_master_ids: list[str]
    job_id: str
```

### 4.5 Phase 4: WorkflowGenWorkflow

#### 4.5.1 責務

1. GraphAI YAML ワークフローの生成
2. スキーマバリデーション
3. サンプル入力生成とテスト実行
4. 品質評価と自己修復

#### 4.5.2 ワークフロー図

```
START (task_master_id, task_data)
  │
  ▼
┌─────────────────┐
│ YAMLGenerator   │  ← GraphAI YAML 生成（LLM）
└─────────────────┘
  │
  ▼
┌─────────────────┐
│ SchemaValidator │  ← YAML 構文 + スキーマ検証
└─────────────────┘
  │
  ├── [検証OK] ─────────────────────────────┐
  │                                         │
  │ [検証NG]                                │
  │     │                                   │
  │     ▼                                   │
  │   SelfRepair ──▶ YAMLGenerator (リトライ)│
  │                                         │
  └─────────────────────────────────────────┤
                                            │
                                            ▼
                                  ┌─────────────────┐
                                  │SampleInputGenerator│
                                  └─────────────────┘
                                            │
                                            ▼
                                  ┌─────────────────┐
                                  │ WorkflowTester  │  ← graphAiServer で実行
                                  └─────────────────┘
                                            │
                                            ├── [実行成功] ────────────────┐
                                            │                             │
                                            │ [実行失敗]                   │
                                            │     │                       │
                                            │     ▼                       │
                                            │   SelfRepair (リトライ)      │
                                            │                             │
                                            └─────────────────────────────┤
                                                                          │
                                                                          ▼
                                                                ┌─────────────────┐
                                                                │ QualityEvaluator│
                                                                └─────────────────┘
                                                                          │
                                                                          ▼
                                                                       SUCCESS
```

---

## 5. 状態管理設計

### 5.1 設計原則

| 原則 | 説明 |
|-----|------|
| **最小状態** | 各ワークフローは必要最小限の状態のみ保持 |
| **不変入力** | 入力は処理中に変更しない |
| **明示的遷移** | 状態遷移は明示的なイベントで発生 |
| **ローカルリトライ** | リトライはフェーズ内で完結 |

### 5.2 状態の階層

```
OrchestratorContext (グローバル状態)
├── request: JobGenerationRequest (不変)
├── current_phase: Phase
├── phase_results: dict[Phase, PhaseResult]
└── metadata: ExecutionMetadata

TaskBreakdownState (Phase 1 ローカル状態)
├── input: TaskBreakdownInput (不変)
├── intermediate: dict (中間結果)
├── output: TaskBreakdownOutput | None
└── retry: RetryState

InterfaceDesignState (Phase 2 ローカル状態)
├── input: InterfaceDesignInput (不変)
├── intermediate: dict
├── output: InterfaceDesignOutput | None
└── retry: RetryState

... (以下同様)
```

### 5.3 リトライ管理

```python
@dataclass
class RetryState:
    """リトライ状態（各フェーズ共通）"""
    count: int = 0
    max_count: int = 3
    history: list[RetryAttempt] = field(default_factory=list)

    def can_retry(self) -> bool:
        return self.count < self.max_count

    def record(self, reason: str, error: Exception | None = None):
        self.count += 1
        self.history.append(RetryAttempt(
            attempt=self.count,
            reason=reason,
            error=str(error) if error else None,
            timestamp=datetime.now(),
        ))

@dataclass
class RetryAttempt:
    """リトライ試行の記録"""
    attempt: int
    reason: str
    error: str | None
    timestamp: datetime
```

### 5.4 状態遷移図

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Orchestrator State Machine                      │
└─────────────────────────────────────────────────────────────────────┘

          ┌──────────┐
          │INITIALIZED│
          └────┬─────┘
               │ start()
               ▼
          ┌──────────┐
     ┌───▶│ PHASE_1  │◀──┐
     │    │(Breakdown)│   │ retry()
     │    └────┬─────┘   │
     │         │ success()
     │         ▼          │
     │    ┌──────────┐    │
     │ ┌─▶│ PHASE_2  │◀──┐│
     │ │  │(Interface)│  ││
     │ │  └────┬─────┘  ││
     │ │       │ success()│
     │ │       ▼        ││
     │ │  ┌──────────┐  ││
     │ │  │ PHASE_3  │◀─┘│
     │ │  │(Register)│   │
     │ │  └────┬─────┘   │
     │ │       │ success()
     │ │       ▼         │
     │ │  ┌──────────┐   │
     │ │  │ PHASE_4  │◀──┘
     │ │  │(Workflow)│
     │ │  └────┬─────┘
     │ │       │
     │ │       ├── success() ──▶ ┌─────────┐
     │ │       │                 │COMPLETED│
     │ │       │                 └─────────┘
     │ │       │
     │ └───────┼── retry() (フェーズ内)
     │         │
     │         ├── fail() ──────▶ ┌──────┐
     │         │                  │FAILED│
     │         │                  └──────┘
     │         │
     └─────────┴── relaxation() ─▶ ┌──────────┐
                                   │RELAXATION│
                                   └──────────┘
```

---

## 6. インターフェース設計

### 6.1 ワークフロー間インターフェース

```python
class WorkflowProtocol(Protocol):
    """全ワークフローが実装すべきプロトコル"""

    async def execute(
        self,
        input: WorkflowInput,
        context: ExecutionContext,
    ) -> WorkflowOutput:
        """ワークフローを実行"""
        ...

    def get_retry_policy(self) -> RetryPolicy:
        """リトライポリシーを取得"""
        ...
```

### 6.2 ExecutionContext 設計（MF-2 対応）

**問題**: 全依存を1つのクラスに集約すると God Object 化する

**解決策**: 目的別に分割された Context クラスを使用し、各ワークフローは必要な Context のみを受け取る

#### 6.2.1 Context 階層構造

```
ExecutionContext (ファサード)
├── LLMContext         ← LLM呼び出し関連
├── StorageContext     ← DB/永続化関連
├── IntegrationContext ← 外部サービス連携
└── ObservabilityContext ← 監視・ログ関連
```

#### 6.2.2 Context 定義

```python
@dataclass(frozen=True)
class LLMContext:
    """LLM 呼び出しに必要なコンテキスト"""
    client: LLMClient
    model_config: ModelConfig
    tracer: Tracer  # LLM呼び出しのトレーシング用

    async def generate(
        self,
        prompt: str,
        response_model: type[T],
        **kwargs,
    ) -> T:
        """構造化出力を生成"""
        with self.tracer.start_span("llm.generate") as span:
            span.set_attribute("model", self.model_config.model_name)
            span.set_attribute("prompt_length", len(prompt))
            result = await self.client.generate(
                prompt=prompt,
                model=self.model_config.model_name,
                response_model=response_model,
                **kwargs,
            )
            span.set_attribute("output_length", len(str(result)))
            return result


@dataclass(frozen=True)
class StorageContext:
    """永続化に必要なコンテキスト"""
    db_client: DatabaseClient
    cache_client: CacheClient | None = None

    async def get_task_master(self, task_id: str) -> TaskMaster:
        """TaskMaster を取得"""
        ...

    async def save_task_master(self, task: TaskMaster) -> str:
        """TaskMaster を保存"""
        ...


@dataclass(frozen=True)
class IntegrationContext:
    """外部サービス連携に必要なコンテキスト"""
    jobqueue_client: JobqueueClient
    graphai_client: GraphAIClient
    myvault_client: MyVaultClient

    async def register_job(self, job: JobDefinition) -> str:
        """jobqueue にジョブを登録"""
        ...

    async def execute_workflow(self, yaml: str, input: dict) -> dict:
        """GraphAI でワークフローを実行"""
        ...


@dataclass(frozen=True)
class ObservabilityContext:
    """観測可能性に必要なコンテキスト"""
    tracer: Tracer
    logger: Logger
    metrics: MetricsCollector

    def start_span(self, name: str, **attributes) -> Span:
        """新しいスパンを開始"""
        return self.tracer.start_span(name, attributes=attributes)

    def log_event(self, event: str, **kwargs):
        """構造化ログを出力"""
        self.logger.info(event, extra=kwargs)

    def record_metric(self, name: str, value: float, **labels):
        """メトリクスを記録"""
        self.metrics.record(name, value, labels)


@dataclass
class ExecutionContext:
    """実行コンテキスト（ファサード）

    各サブコンテキストへのアクセスを提供。
    ワークフローは必要なサブコンテキストのみを使用する。

    使用例:
    - TaskBreakdownWorkflow: llm, observability のみ使用
    - RegistrationWorkflow: storage, integration, observability を使用
    """
    llm: LLMContext
    storage: StorageContext
    integration: IntegrationContext
    observability: ObservabilityContext

    # メタデータ
    job_id: str
    request_id: str
    correlation_id: str

    @classmethod
    def create(
        cls,
        config: Config,
        job_id: str,
        request_id: str,
    ) -> "ExecutionContext":
        """ファクトリメソッド"""
        correlation_id = str(uuid.uuid4())
        tracer = create_tracer(config.langfuse)
        logger = create_logger(config.logging)

        return cls(
            llm=LLMContext(
                client=create_llm_client(config.llm),
                model_config=config.llm,
                tracer=tracer,
            ),
            storage=StorageContext(
                db_client=create_db_client(config.database),
                cache_client=create_cache_client(config.cache) if config.cache else None,
            ),
            integration=IntegrationContext(
                jobqueue_client=create_jobqueue_client(config.jobqueue),
                graphai_client=create_graphai_client(config.graphai),
                myvault_client=create_myvault_client(config.myvault),
            ),
            observability=ObservabilityContext(
                tracer=tracer,
                logger=logger,
                metrics=create_metrics_collector(config.metrics),
            ),
            job_id=job_id,
            request_id=request_id,
            correlation_id=correlation_id,
        )
```

#### 6.2.3 ワークフローでの使用例

```python
class TaskBreakdownWorkflow(WorkflowProtocol):
    """LLMContext のみを使用"""

    async def execute(
        self,
        input: TaskBreakdownInput,
        context: ExecutionContext,
    ) -> TaskBreakdownOutput:
        # 必要なコンテキストのみを使用
        llm = context.llm
        obs = context.observability

        obs.log_event("task_breakdown_started", task_count=0)

        # LLM呼び出し
        result = await llm.generate(
            prompt=self._build_prompt(input),
            response_model=TaskBreakdownResponse,
        )

        obs.record_metric(
            "task_breakdown_tasks_generated",
            len(result.tasks),
        )

        return TaskBreakdownOutput(...)


class RegistrationWorkflow(WorkflowProtocol):
    """StorageContext と IntegrationContext を使用"""

    async def execute(
        self,
        input: RegistrationInput,
        context: ExecutionContext,
    ) -> RegistrationOutput:
        storage = context.storage
        integration = context.integration
        obs = context.observability

        # DB登録
        for task in input.tasks:
            task_id = await storage.save_task_master(task)
            obs.log_event("task_master_saved", task_id=task_id)

        # jobqueue 登録
        job_id = await integration.register_job(input.job_definition)

        return RegistrationOutput(job_id=job_id, ...)
```

#### 6.2.4 利点

| 観点 | 説明 |
|-----|------|
| **単一責任** | 各 Context は1つの責務に集中 |
| **テスト容易性** | 必要な Context のみをモック可能 |
| **依存性の明示化** | ワークフローが何に依存するか明確 |
| **変更の局所化** | LLM変更は LLMContext のみに影響 |
| **型安全性** | コンパイル時に依存性の不整合を検出 |

### 6.3 フェーズ間データフロー

```
Phase 1 Output                    Phase 2 Input
┌─────────────────────┐          ┌─────────────────────┐
│ tasks: [            │          │ tasks: [            │
│   TaskDefinition    │────────▶│   TaskDefinition    │
│ ]                   │          │ ]                   │
│ feasibility_report  │          │ openapi_specs       │
└─────────────────────┘          └─────────────────────┘

Phase 2 Output                    Phase 3 Input
┌─────────────────────┐          ┌─────────────────────┐
│ tasks              │           │ tasks               │
│ interfaces: {       │────────▶│ interfaces: {       │
│   task_id: Schema   │          │   task_id: Schema   │
│ }                   │          │ }                   │
└─────────────────────┘          └─────────────────────┘

Phase 3 Output                    Phase 4 Input
┌─────────────────────┐          ┌─────────────────────┐
│ job_master_id       │          │ task_master_id      │
│ task_master_ids     │────────▶│ task_data: {        │
│ job_id              │          │   interfaces, ...   │
└─────────────────────┘          │ }                   │
                                 └─────────────────────┘
```

---

## 7. 観測可能性設計

### 7.1 トレーシング

```python
class TracingDecorator:
    """ワークフロー実行のトレーシング"""

    def trace_phase(self, phase: Phase):
        def decorator(func):
            @wraps(func)
            async def wrapper(input, context):
                with context.tracer.start_span(
                    name=f"phase.{phase.value}",
                    attributes={
                        "phase": phase.value,
                        "input_size": len(str(input)),
                    },
                ) as span:
                    try:
                        result = await func(input, context)
                        span.set_attribute("status", result.status.value)
                        return result
                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR))
                        span.record_exception(e)
                        raise
            return wrapper
        return decorator
```

### 7.2 メトリクス

```python
# Prometheus メトリクス定義
job_generation_duration = Histogram(
    "job_generation_duration_seconds",
    "Duration of job generation",
    ["phase", "status"],
    buckets=[1, 5, 10, 30, 60, 120, 300],
)

job_generation_retries = Counter(
    "job_generation_retries_total",
    "Number of retries in job generation",
    ["phase", "reason"],
)

job_generation_success = Counter(
    "job_generation_success_total",
    "Number of successful job generations",
    ["relaxed"],  # True if relaxation was applied
)

job_generation_failure = Counter(
    "job_generation_failure_total",
    "Number of failed job generations",
    ["phase", "error_type"],
)
```

### 7.3 ログ構造

```python
# 構造化ログ例
logger.info(
    "phase_started",
    extra={
        "job_id": context.job_id,
        "phase": phase.value,
        "retry_count": retry_state.count,
        "input_tasks": len(input.tasks),
    },
)

logger.info(
    "phase_completed",
    extra={
        "job_id": context.job_id,
        "phase": phase.value,
        "status": result.status.value,
        "duration_ms": duration.total_seconds() * 1000,
        "output_size": len(str(result)),
    },
)
```

---

## 8. エラーハンドリング設計

### 8.1 エラー分類

| カテゴリ | 例 | リカバリー |
|---------|-----|----------|
| **Transient** | LLM API タイムアウト | 自動リトライ |
| **Validation** | スキーマ不整合 | 修正してリトライ |
| **Business** | 実現不可能な要求 | 緩和提案 |
| **Fatal** | DB 接続失敗 | 即座に失敗 |

### 8.2 フェーズ間エラー回復戦略（MF-3 対応）

**問題**: Phase N の失敗が Phase N-1 への巻き戻しを要する場合の設計が未定義

**解決策**: 明示的なエラー回復戦略を定義し、オーケストレーターで一貫したハンドリングを実装

#### 8.2.1 エラー回復戦略の定義

```python
class ErrorRecoveryStrategy(Enum):
    """エラー回復戦略"""

    FAIL_FAST = "fail_fast"
    """即座に失敗。回復不能なエラー用。"""

    RETRY_CURRENT = "retry_current"
    """現フェーズ内でリトライ。一時的エラー用。"""

    ROLLBACK_ONE = "rollback_one"
    """1フェーズ戻って再実行。前フェーズの出力に問題がある場合。"""

    ROLLBACK_TO_BREAKDOWN = "rollback_to_breakdown"
    """Phase 1 (TaskBreakdown) まで戻る。根本的な設計変更が必要な場合。"""

    RELAXATION = "relaxation"
    """要求緩和を提案。ビジネス制約で実現不可能な場合。"""


@dataclass
class ErrorRecoveryDecision:
    """エラー回復の判断結果"""
    strategy: ErrorRecoveryStrategy
    target_phase: Phase | None  # ROLLBACK時の戻り先
    feedback: str | None  # リトライ時のフィードバック
    relaxation_suggestions: list[str] | None  # RELAXATION時の提案
    should_notify_user: bool  # ユーザー通知が必要か
```

#### 8.2.2 フェーズ別回復戦略マトリクス

| 失敗フェーズ | エラー種別 | 回復戦略 | 理由 |
|------------|----------|----------|------|
| Phase 1 | Validation | RETRY_CURRENT | タスク分解の再試行 |
| Phase 1 | Business | RELAXATION | 要求が実現不可能 |
| Phase 2 | Validation | RETRY_CURRENT | スキーマ修正で解決可能 |
| Phase 2 | Compatibility | ROLLBACK_TO_BREAKDOWN | タスク構造の見直しが必要 |
| Phase 3 | DB Error | RETRY_CURRENT | 一時的な接続問題 |
| Phase 3 | Constraint | ROLLBACK_ONE | インターフェース定義の見直し |
| Phase 4 | Validation | RETRY_CURRENT | YAML修正で解決可能 |
| Phase 4 | Execution | ROLLBACK_ONE | インターフェース不整合の可能性 |
| Any | Fatal | FAIL_FAST | 回復不能 |

#### 8.2.3 回復戦略決定ロジック

```python
class ErrorRecoveryManager:
    """エラー回復戦略を決定・実行"""

    # フェーズごとの最大ロールバック回数
    MAX_ROLLBACKS_PER_PHASE = 2

    def decide_recovery(
        self,
        phase: Phase,
        error: WorkflowError,
        context: OrchestratorContext,
    ) -> ErrorRecoveryDecision:
        """エラーに対する回復戦略を決定"""

        # 1. エラータイプに基づく基本戦略
        base_strategy = self._get_base_strategy(error)

        # 2. リトライ上限チェック
        if base_strategy == ErrorRecoveryStrategy.RETRY_CURRENT:
            if not context.can_retry(phase):
                # リトライ上限超過 → ロールバックまたは失敗
                return self._escalate_strategy(phase, error, context)

        # 3. ロールバック上限チェック
        if base_strategy in (
            ErrorRecoveryStrategy.ROLLBACK_ONE,
            ErrorRecoveryStrategy.ROLLBACK_TO_BREAKDOWN,
        ):
            rollback_count = context.get_rollback_count(phase)
            if rollback_count >= self.MAX_ROLLBACKS_PER_PHASE:
                # ロールバック上限超過 → 緩和提案または失敗
                if self._can_relax(error):
                    return ErrorRecoveryDecision(
                        strategy=ErrorRecoveryStrategy.RELAXATION,
                        target_phase=None,
                        feedback=None,
                        relaxation_suggestions=self._generate_relaxations(error),
                        should_notify_user=True,
                    )
                return ErrorRecoveryDecision(
                    strategy=ErrorRecoveryStrategy.FAIL_FAST,
                    target_phase=None,
                    feedback=f"Max rollbacks exceeded for phase {phase}",
                    relaxation_suggestions=None,
                    should_notify_user=True,
                )

        # 4. 戦略に応じた詳細決定
        return self._build_decision(base_strategy, phase, error, context)

    def _get_base_strategy(self, error: WorkflowError) -> ErrorRecoveryStrategy:
        """エラータイプから基本戦略を取得"""
        strategy_map = {
            ErrorType.TRANSIENT: ErrorRecoveryStrategy.RETRY_CURRENT,
            ErrorType.VALIDATION: ErrorRecoveryStrategy.RETRY_CURRENT,
            ErrorType.COMPATIBILITY: ErrorRecoveryStrategy.ROLLBACK_ONE,
            ErrorType.BUSINESS: ErrorRecoveryStrategy.RELAXATION,
            ErrorType.FATAL: ErrorRecoveryStrategy.FAIL_FAST,
        }
        return strategy_map.get(error.error_type, ErrorRecoveryStrategy.FAIL_FAST)

    def _escalate_strategy(
        self,
        phase: Phase,
        error: WorkflowError,
        context: OrchestratorContext,
    ) -> ErrorRecoveryDecision:
        """リトライ上限超過時の戦略エスカレーション"""
        if phase == Phase.TASK_BREAKDOWN:
            # Phase 1 でリトライ上限 → 緩和提案
            return ErrorRecoveryDecision(
                strategy=ErrorRecoveryStrategy.RELAXATION,
                target_phase=None,
                feedback=None,
                relaxation_suggestions=self._generate_relaxations(error),
                should_notify_user=True,
            )

        # 後続フェーズでリトライ上限 → 前フェーズへロールバック
        target = self._get_rollback_target(phase)
        return ErrorRecoveryDecision(
            strategy=ErrorRecoveryStrategy.ROLLBACK_ONE,
            target_phase=target,
            feedback=self._generate_rollback_feedback(error),
            relaxation_suggestions=None,
            should_notify_user=False,
        )

    def _get_rollback_target(self, current_phase: Phase) -> Phase:
        """ロールバック先フェーズを決定"""
        rollback_targets = {
            Phase.INTERFACE_DESIGN: Phase.TASK_BREAKDOWN,
            Phase.REGISTRATION: Phase.INTERFACE_DESIGN,
            Phase.WORKFLOW_GEN: Phase.REGISTRATION,
        }
        return rollback_targets.get(current_phase, Phase.TASK_BREAKDOWN)
```

#### 8.2.4 オーケストレーターでの統合

```python
class JobGenerationOrchestrator:
    """エラー回復戦略を統合したオーケストレーター"""

    def __init__(
        self,
        workflows: dict[Phase, WorkflowProtocol],
        recovery_manager: ErrorRecoveryManager,
        progress_reporter: ProgressReporter,
    ):
        self.workflows = workflows
        self.recovery_manager = recovery_manager
        self.progress_reporter = progress_reporter

    async def execute(
        self,
        request: JobGenerationRequest,
    ) -> JobGenerationResult:
        context = OrchestratorContext(request)
        current_phase = Phase.TASK_BREAKDOWN

        while current_phase is not None:
            try:
                result = await self._execute_phase(current_phase, context)

                if result.status == PhaseStatus.SUCCESS:
                    context.update(current_phase, result)
                    self.progress_reporter.report(current_phase, context)
                    current_phase = self._get_next_phase(current_phase)
                    continue

                # PhaseStatus.NEEDS_RELAXATION などの非SUCCESS
                return self._handle_non_success(result, context)

            except WorkflowError as e:
                decision = self.recovery_manager.decide_recovery(
                    current_phase, e, context
                )
                current_phase = await self._apply_recovery(
                    decision, current_phase, context
                )

        return self._build_success_result(context)

    async def _apply_recovery(
        self,
        decision: ErrorRecoveryDecision,
        current_phase: Phase,
        context: OrchestratorContext,
    ) -> Phase | None:
        """回復戦略を適用し、次のフェーズを返す"""

        if decision.should_notify_user:
            self.progress_reporter.report_recovery(
                current_phase, decision, context
            )

        match decision.strategy:
            case ErrorRecoveryStrategy.FAIL_FAST:
                # 失敗を確定
                context.set_failed(decision.feedback)
                return None

            case ErrorRecoveryStrategy.RETRY_CURRENT:
                # 現フェーズをリトライ
                context.record_retry(current_phase, decision.feedback)
                return current_phase

            case ErrorRecoveryStrategy.ROLLBACK_ONE:
                # 1フェーズ戻る
                context.record_rollback(current_phase, decision.target_phase)
                context.invalidate_from(decision.target_phase)
                return decision.target_phase

            case ErrorRecoveryStrategy.ROLLBACK_TO_BREAKDOWN:
                # Phase 1 まで戻る
                context.record_rollback(current_phase, Phase.TASK_BREAKDOWN)
                context.invalidate_all()
                return Phase.TASK_BREAKDOWN

            case ErrorRecoveryStrategy.RELAXATION:
                # 緩和提案で終了
                context.set_relaxation(decision.relaxation_suggestions)
                return None

        return None
```

#### 8.2.5 状態の無効化と復元

```python
class OrchestratorContext:
    """ロールバック時の状態管理"""

    def invalidate_from(self, phase: Phase):
        """指定フェーズ以降の結果を無効化"""
        phases_to_invalidate = self._get_phases_from(phase)
        for p in phases_to_invalidate:
            self.phase_results[p] = None

    def invalidate_all(self):
        """全フェーズの結果を無効化"""
        self.phase_results = {p: None for p in Phase}

    def record_rollback(self, from_phase: Phase, to_phase: Phase):
        """ロールバックを記録"""
        self.rollback_history.append(RollbackRecord(
            from_phase=from_phase,
            to_phase=to_phase,
            timestamp=datetime.now(),
        ))

    def get_rollback_count(self, phase: Phase) -> int:
        """特定フェーズへのロールバック回数を取得"""
        return sum(
            1 for r in self.rollback_history
            if r.to_phase == phase
        )
```

#### 8.2.6 回復戦略の可視化（Langfuse 連携）

```python
class RecoveryTracer:
    """エラー回復のトレーシング"""

    def trace_recovery(
        self,
        decision: ErrorRecoveryDecision,
        phase: Phase,
        context: OrchestratorContext,
    ):
        """回復戦略をトレースに記録"""
        with context.observability.start_span("error_recovery") as span:
            span.set_attribute("strategy", decision.strategy.value)
            span.set_attribute("current_phase", phase.value)
            span.set_attribute("target_phase", decision.target_phase.value if decision.target_phase else None)
            span.set_attribute("retry_count", context.get_retry_count(phase))
            span.set_attribute("rollback_count", context.get_rollback_count(phase))
            span.set_attribute("should_notify_user", decision.should_notify_user)

            # イベントとして詳細を記録
            span.add_event(
                "recovery_decision",
                {
                    "feedback": decision.feedback,
                    "relaxation_suggestions": decision.relaxation_suggestions,
                },
            )
```

### 8.3 エラーハンドリングフロー

```python
class ErrorHandler:
    """エラーハンドリング"""

    async def handle(
        self,
        error: Exception,
        phase: Phase,
        context: OrchestratorContext,
    ) -> ErrorHandlingResult:
        error_type = self._classify(error)

        if error_type == ErrorType.TRANSIENT:
            if context.can_retry(phase):
                return ErrorHandlingResult(action=Action.RETRY)
            return ErrorHandlingResult(action=Action.FAIL)

        if error_type == ErrorType.VALIDATION:
            if context.can_retry(phase):
                feedback = self._generate_feedback(error)
                return ErrorHandlingResult(
                    action=Action.RETRY,
                    feedback=feedback,
                )
            return ErrorHandlingResult(action=Action.FAIL)

        if error_type == ErrorType.BUSINESS:
            suggestions = await self._generate_relaxations(error, context)
            return ErrorHandlingResult(
                action=Action.RELAXATION,
                suggestions=suggestions,
            )

        # Fatal
        return ErrorHandlingResult(action=Action.FAIL)
```

---

## 9. テスト戦略

### 9.1 テストレベル

| レベル | 対象 | カバレッジ目標 |
|-------|------|--------------|
| Unit | 各ノード（Worker） | 90% |
| Integration | 各ワークフロー | 50% |
| E2E | オーケストレーター全体 | 主要シナリオ |

### 9.2 テスト構成

```
tests/
├── unit/
│   ├── test_task_breakdown/
│   │   ├── test_requirement_parser.py
│   │   ├── test_task_decomposer.py
│   │   ├── test_feasibility_checker.py
│   │   └── test_alternative_proposer.py
│   ├── test_interface_design/
│   │   ├── test_schema_generator.py
│   │   ├── test_compatibility_checker.py
│   │   └── test_schema_enricher.py
│   └── ...
├── integration/
│   ├── test_task_breakdown_workflow.py
│   ├── test_interface_design_workflow.py
│   ├── test_registration_workflow.py
│   └── test_workflow_gen_workflow.py
└── e2e/
    └── test_job_generation_scenarios.py
```

### 9.3 テストフィクスチャ

```python
@pytest.fixture
def mock_llm_client():
    """LLM クライアントのモック"""
    client = Mock(spec=LLMClient)
    client.generate.return_value = TaskBreakdownResponse(
        tasks=[
            TaskDefinition(id="task_1", name="Task 1", ...),
            TaskDefinition(id="task_2", name="Task 2", ...),
        ]
    )
    return client

@pytest.fixture
def mock_context(mock_llm_client):
    """実行コンテキストのモック"""
    return ExecutionContext(
        llm_client=mock_llm_client,
        db_client=Mock(spec=DatabaseClient),
        jobqueue_client=Mock(spec=JobqueueClient),
        tracer=NoOpTracer(),
        logger=logging.getLogger("test"),
    )
```

---

## 10. セキュリティ設計

### 10.1 セキュリティ要件

#### 10.1.1 脅威モデル

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Trust Boundary                                   │
│  ┌──────────────┐                                                       │
│  │   User       │                                                       │
│  │ (Untrusted)  │                                                       │
│  └──────┬───────┘                                                       │
│         │ HTTP Request                                                  │
│         ▼                                                               │
│  ┌──────────────┐        ┌──────────────┐        ┌──────────────┐     │
│  │   API Layer  │───────▶│ Orchestrator │───────▶│   LLM API    │     │
│  │ (FastAPI)    │        │              │        │  (External)  │     │
│  └──────────────┘        └──────────────┘        └──────────────┘     │
│         │                       │                                       │
│         │                       ▼                                       │
│         │                ┌──────────────┐                              │
│         │                │   Database   │                              │
│         │                │  (Internal)  │                              │
│         │                └──────────────┘                              │
│         │                                                               │
│         ▼                                                               │
│  ┌──────────────┐        ┌──────────────┐                              │
│  │   jobqueue   │───────▶│ graphAiServer│                              │
│  │  (Internal)  │        │  (Internal)  │                              │
│  └──────────────┘        └──────────────┘                              │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 10.1.2 主要な脅威と対策

| 脅威 | 影響度 | 発生確率 | 対策 |
|-----|--------|---------|------|
| **LLM プロンプトインジェクション** | High | Medium | 入力サニタイズ、プロンプトテンプレート化 |
| **機密データ漏洩（ログ）** | High | Medium | マスキング、ログレベル制御 |
| **認証バイパス** | High | Low | API層での認証強制 |
| **DoS攻撃** | Medium | Medium | Rate Limiting、タイムアウト |
| **SQLインジェクション** | High | Low | Pydantic/ORM使用 |
| **不正なワークフロー実行** | Medium | Low | サンドボックス実行 |

### 10.2 認証・認可設計

#### 10.2.1 認証フロー

```python
class AuthenticationMiddleware:
    """API層での認証ミドルウェア"""

    async def __call__(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # 1. トークン抽出
        token = self._extract_token(request)
        if not token:
            raise HTTPException(status_code=401, detail="Missing authentication")

        # 2. トークン検証
        try:
            payload = await self.token_verifier.verify(token)
        except TokenExpiredError:
            raise HTTPException(status_code=401, detail="Token expired")
        except InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

        # 3. ユーザーコンテキスト設定
        request.state.user = UserContext(
            user_id=payload["sub"],
            roles=payload.get("roles", []),
            permissions=payload.get("permissions", []),
        )

        return await call_next(request)
```

#### 10.2.2 認可ポリシー

```python
class AuthorizationPolicy:
    """リソースへのアクセス制御"""

    POLICIES = {
        "job:create": ["user", "admin"],
        "job:read": ["user", "admin"],
        "job:delete": ["admin"],
        "job:admin": ["admin"],
    }

    def check_permission(
        self,
        user: UserContext,
        action: str,
        resource: str | None = None,
    ) -> bool:
        """権限チェック"""
        required_roles = self.POLICIES.get(action, [])

        # ロールベースチェック
        if any(role in user.roles for role in required_roles):
            return True

        # リソースベースチェック（オーナーシップ）
        if resource and self._is_resource_owner(user, resource):
            return True

        return False

    def _is_resource_owner(self, user: UserContext, resource_id: str) -> bool:
        """リソースオーナーシップの確認"""
        # 実装: DBからリソースのオーナーを取得して比較
        ...
```

### 10.3 入力検証とサニタイズ

#### 10.3.1 ユーザー入力の検証

```python
class UserRequirementValidator:
    """ユーザー要件の入力検証"""

    # 禁止パターン（プロンプトインジェクション対策）
    INJECTION_PATTERNS = [
        r"ignore\s+(previous|all)\s+instructions",
        r"system\s*:\s*",
        r"<\|.*\|>",  # 特殊トークン
        r"\{\{.*\}\}",  # テンプレート構文
    ]

    # 入力制限
    MAX_LENGTH = 10000
    MIN_LENGTH = 10

    def validate(self, requirement: str) -> ValidationResult:
        """入力を検証"""
        errors = []

        # 長さチェック
        if len(requirement) < self.MIN_LENGTH:
            errors.append(f"Requirement too short (min: {self.MIN_LENGTH})")
        if len(requirement) > self.MAX_LENGTH:
            errors.append(f"Requirement too long (max: {self.MAX_LENGTH})")

        # インジェクションパターンチェック
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, requirement, re.IGNORECASE):
                errors.append("Potentially malicious content detected")
                break

        # Unicode正規化
        normalized = unicodedata.normalize("NFKC", requirement)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_value=normalized,
        )


class InputSanitizer:
    """入力のサニタイズ"""

    def sanitize_for_llm(self, text: str) -> str:
        """LLMプロンプト用にサニタイズ"""
        # 1. 制御文字の除去
        text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)

        # 2. 危険なパターンのエスケープ
        text = text.replace("```", "'''")  # コードブロック
        text = text.replace("{{", "{ {")  # テンプレート
        text = text.replace("}}", "} }")

        # 3. 長さ制限
        if len(text) > 10000:
            text = text[:10000] + "... (truncated)"

        return text
```

#### 10.3.2 LLMプロンプトの安全性

```python
class SecurePromptBuilder:
    """安全なプロンプト構築"""

    def build_task_breakdown_prompt(
        self,
        requirement: str,
        capabilities: list[Capability],
    ) -> str:
        """タスク分解用プロンプトを安全に構築"""
        # サニタイズ済み入力のみ使用
        sanitized_req = self.sanitizer.sanitize_for_llm(requirement)

        # テンプレート化されたプロンプト（インジェクション耐性）
        return self.template.render(
            # ユーザー入力は明確にマーク
            user_requirement=f"<user_input>{sanitized_req}</user_input>",
            # システム定義は変更不可
            capabilities=capabilities,
            # 指示は固定
            instructions=TASK_BREAKDOWN_INSTRUCTIONS,
        )
```

### 10.4 機密データ保護

#### 10.4.1 ログマスキング

```python
class SensitiveDataMasker:
    """機密データのマスキング"""

    # マスキング対象パターン
    PATTERNS = {
        "api_key": r"(api[_-]?key|apikey)[=:]\s*['\"]?([a-zA-Z0-9_-]{20,})['\"]?",
        "password": r"(password|passwd|pwd)[=:]\s*['\"]?([^\s'\"]+)['\"]?",
        "token": r"(bearer|token)[=:]\s*['\"]?([a-zA-Z0-9._-]+)['\"]?",
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    }

    def mask(self, text: str) -> str:
        """機密データをマスキング"""
        masked = text
        for name, pattern in self.PATTERNS.items():
            masked = re.sub(
                pattern,
                f"[MASKED:{name}]",
                masked,
                flags=re.IGNORECASE,
            )
        return masked


class SecureLogger:
    """セキュアなロガー"""

    def __init__(self, logger: Logger, masker: SensitiveDataMasker):
        self.logger = logger
        self.masker = masker

    def info(self, message: str, **kwargs):
        """マスキング済みログ出力"""
        masked_message = self.masker.mask(message)
        masked_kwargs = {
            k: self.masker.mask(str(v)) if isinstance(v, str) else v
            for k, v in kwargs.items()
        }
        self.logger.info(masked_message, extra=masked_kwargs)
```

#### 10.4.2 データ暗号化

```python
class DataEncryption:
    """保存データの暗号化"""

    def __init__(self, key_provider: KeyProvider):
        self.key_provider = key_provider

    def encrypt_sensitive_field(self, value: str, context: str) -> str:
        """フィールドレベル暗号化"""
        key = self.key_provider.get_key(context)
        fernet = Fernet(key)
        return fernet.encrypt(value.encode()).decode()

    def decrypt_sensitive_field(self, encrypted: str, context: str) -> str:
        """フィールドレベル復号"""
        key = self.key_provider.get_key(context)
        fernet = Fernet(key)
        return fernet.decrypt(encrypted.encode()).decode()
```

### 10.5 Rate Limiting とリソース保護

#### 10.5.1 Rate Limiting 設計

```python
class RateLimiter:
    """リクエストのレート制限"""

    # 制限設定
    LIMITS = {
        "job:create": RateLimit(requests=10, window=60),      # 10 req/min
        "job:status": RateLimit(requests=100, window=60),     # 100 req/min
        "llm:generate": RateLimit(requests=20, window=60),    # 20 req/min
    }

    async def check(
        self,
        user_id: str,
        action: str,
    ) -> RateLimitResult:
        """レート制限をチェック"""
        limit = self.LIMITS.get(action)
        if not limit:
            return RateLimitResult(allowed=True)

        key = f"ratelimit:{user_id}:{action}"
        current = await self.redis.incr(key)

        if current == 1:
            await self.redis.expire(key, limit.window)

        remaining = max(0, limit.requests - current)
        reset_at = await self.redis.ttl(key)

        return RateLimitResult(
            allowed=current <= limit.requests,
            remaining=remaining,
            reset_at=reset_at,
        )
```

#### 10.5.2 リソース制限

```python
class ResourceLimiter:
    """計算リソースの制限"""

    # ジョブごとの制限
    MAX_TASKS_PER_JOB = 10
    MAX_EXECUTION_TIME = 300  # 5分
    MAX_LLM_CALLS_PER_JOB = 50

    def check_task_limit(self, task_count: int) -> None:
        """タスク数制限"""
        if task_count > self.MAX_TASKS_PER_JOB:
            raise ResourceLimitError(
                f"Task count exceeds limit: {task_count} > {self.MAX_TASKS_PER_JOB}"
            )

    def check_llm_calls(self, current_count: int) -> None:
        """LLM呼び出し回数制限"""
        if current_count >= self.MAX_LLM_CALLS_PER_JOB:
            raise ResourceLimitError(
                f"LLM call limit reached: {current_count}"
            )
```

### 10.6 監査ログ

#### 10.6.1 監査イベントの定義

```python
class AuditEventType(Enum):
    """監査イベント種別"""
    JOB_CREATED = "job.created"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    JOB_DELETED = "job.deleted"
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    PERMISSION_DENIED = "permission.denied"
    RATE_LIMIT_EXCEEDED = "ratelimit.exceeded"
    SECURITY_VIOLATION = "security.violation"


@dataclass
class AuditEvent:
    """監査イベント"""
    event_type: AuditEventType
    timestamp: datetime
    user_id: str | None
    resource_id: str | None
    action: str
    result: str  # success, failure, denied
    details: dict
    ip_address: str
    user_agent: str
```

#### 10.6.2 監査ログ出力

```python
class AuditLogger:
    """監査ログの出力"""

    def __init__(
        self,
        storage: AuditStorage,
        notifier: SecurityNotifier | None = None,
    ):
        self.storage = storage
        self.notifier = notifier

    async def log(self, event: AuditEvent):
        """監査イベントを記録"""
        # 永続化
        await self.storage.store(event)

        # 重要イベントの通知
        if self._is_security_critical(event):
            if self.notifier:
                await self.notifier.notify(event)

    def _is_security_critical(self, event: AuditEvent) -> bool:
        """セキュリティ上重要なイベントか判定"""
        critical_types = {
            AuditEventType.AUTH_FAILURE,
            AuditEventType.PERMISSION_DENIED,
            AuditEventType.SECURITY_VIOLATION,
        }
        return event.event_type in critical_types
```

### 10.7 依存関係のセキュリティ

#### 10.7.1 依存関係管理ポリシー

| 項目 | ポリシー |
|-----|---------|
| **定期スキャン** | 週次で `pip-audit` / `safety` 実行 |
| **自動更新** | Dependabot で脆弱性パッチ自動PR |
| **バージョン固定** | `requirements.txt` で厳密なバージョン指定 |
| **承認プロセス** | 新規依存追加時はセキュリティレビュー必須 |

#### 10.7.2 CI/CD でのセキュリティチェック

```yaml
# .github/workflows/security.yml
name: Security Scan

on:
  push:
    branches: [main, develop]
  schedule:
    - cron: '0 0 * * 0'  # 週次

jobs:
  dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run pip-audit
        run: |
          pip install pip-audit
          pip-audit --strict --require-hashes

      - name: Run Bandit (SAST)
        run: |
          pip install bandit
          bandit -r expertAgent/ -ll

      - name: Run Trivy
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          severity: 'CRITICAL,HIGH'
```

### 10.8 インシデント対応

#### 10.8.1 セキュリティインシデント分類

| レベル | 定義 | 対応時間 |
|-------|------|---------|
| **Critical** | 認証バイパス、データ漏洩 | 即時 |
| **High** | 権限昇格、DoS | 4時間以内 |
| **Medium** | 情報漏洩（限定的） | 24時間以内 |
| **Low** | ログ不備、設定ミス | 1週間以内 |

#### 10.8.2 対応手順

```
1. 検知 → 2. 初期評価 → 3. 封じ込め → 4. 根本原因分析 → 5. 復旧 → 6. 事後レビュー

封じ込め手順:
- 影響範囲の特定
- 必要に応じてサービス停止
- 影響を受けたトークン/APIキーの無効化
- 監査ログの保全
```

---

## 11. 移行計画

### 11.1 移行フェーズ

| Phase | 内容 | 期間 |
|-------|------|------|
| **Phase A** | 新アーキテクチャの基盤実装 | 2週間 |
| **Phase B** | TaskBreakdownWorkflow 移行 | 1週間 |
| **Phase C** | InterfaceDesignWorkflow 移行 | 1週間 |
| **Phase D** | Registration/WorkflowGen 移行 | 1週間 |
| **Phase E** | 統合テスト・旧実装削除 | 1週間 |

### 11.2 移行戦略

```
Step 1: 新旧並行運用
┌──────────────────────────────────────────────────┐
│ API Endpoint                                      │
│ POST /v1/job-generator                           │
└──────────────────────────────────────────────────┘
              │
              ├── feature_flag: new_architecture
              │
    ┌─────────┴─────────┐
    │                   │
    ▼                   ▼
┌─────────┐       ┌─────────┐
│旧実装    │       │新実装    │
│(現行)    │       │(Phase A)│
└─────────┘       └─────────┘

Step 2: 段階的切り替え
- 10% → 50% → 100% のトラフィック移行
- 問題発生時は即座にロールバック

Step 3: 旧実装削除
- 新実装が安定したら旧コードを削除
```

---

## 12. 付録

### A. 用語集

| 用語 | 定義 |
|-----|------|
| **Phase** | ジョブ生成の大きな処理段階（4フェーズ） |
| **Workflow** | LangGraph で定義された処理フロー |
| **Node** | ワークフロー内の単一処理ステップ |
| **Orchestrator** | フェーズ間の遷移を制御するコンポーネント |
| **Capability** | 利用可能な GraphAI Agent/API の定義 |

### B. 参考資料

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [GraphAI Specification](../../../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)
- [現行実装分析](../../../workspace/agent-analysis-report.md)

---

**作成日**: 2026-01-07
**作成者**: Claude Code
**対象Issue**: #342
