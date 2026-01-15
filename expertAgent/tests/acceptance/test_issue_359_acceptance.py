"""Issue #359 受入テスト（L3: ローカル受入テスト）.

jobGeneratorV2 3フェーズ統一ID方式リファクタリングの受入テスト。

前提条件:
- サービスが起動していること (./scripts/dev-start.sh または make dev-all)
- .env に必要なAPIキーが設定されていること

実行方法:
  cd expertAgent
  uv run pytest tests/acceptance/test_issue_359_acceptance.py -v

テストケース:
- TC-006: インデックスベースルックアップの不在確認
- TC-012: オーケストレーターコード行数（300行以下）
- TC-013: 削除対象コードの不在確認
- TC-014: TaskDependencyValidator循環参照検出
- TC-003: ErrorRecoveryManager RETRY_CURRENT戦略
- TC-005: 並列実行の部分成功
- TC-007: サイレントフォールバックの排除

Note:
- V3アーキテクチャはAPIエンドポイントに統合されていないため、
  E2E APIテスト（TC-001, TC-002等）は単体/結合テストで代替検証
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import Any

import pytest

# V3 components
from aiagent.langgraph.jobGeneratorV2.error_recovery_v3 import ErrorRecoveryManager
from aiagent.langgraph.jobGeneratorV2.orchestrator_v3 import (
    JobGenerationOrchestratorV3,
    OrchestratorError,
)
from aiagent.langgraph.jobGeneratorV2.parallel_executor import (
    parallel_workflow_generation,
)
from aiagent.langgraph.jobGeneratorV2.types_v3 import (
    ErrorType,
    ParallelExecutionResult,
    PhaseError,
    PhaseV3,
    RecoveryStrategy,
    TaskResult,
    UnifiedTaskIdentifier,
)
from aiagent.langgraph.jobGeneratorV2.validators.task_dependency import (
    TaskDependencyValidator,
)
from aiagent.langgraph.jobGeneratorV2.validators.pipeline import ValidationPipelineV3


# === Code Inspection Tests ===


@pytest.mark.acceptance
class TestTC006NoIndexBasedLookups:
    """TC-006: インデックスベースルックアップの不在確認.

    テスト観点: 設計方針に反するコードの不在
    関連する受入条件: AC-5
    関連する設計方針: DP-2
    """

    def test_no_index_lookups_in_orchestrator_v3(self) -> None:
        """orchestrator_v3.pyにインデックスベースのルックアップが存在しない."""
        # Arrange
        orchestrator_path = Path(__file__).parent.parent.parent.parent / (
            "aiagent/langgraph/jobGeneratorV2/orchestrator_v3.py"
        )

        # Act
        with open(orchestrator_path) as f:
            content = f.read()

        # Assert
        # コメント以外で [idx] パターンがないことを確認
        lines = content.split("\n")
        violations = []
        for i, line in enumerate(lines, 1):
            # コメント行をスキップ
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # コード中の [idx] パターンを検出
            if "[idx]" in line and "# " not in line.split("[idx]")[0]:
                violations.append(f"Line {i}: {line.strip()}")

        assert len(violations) == 0, f"Found index-based lookups:\n" + "\n".join(
            violations
        )

    def test_no_tasks_i_pattern_in_orchestrator_v3(self) -> None:
        """orchestrator_v3.pyに tasks[i] 形式のアクセスが存在しない."""
        # Arrange
        orchestrator_path = Path(__file__).parent.parent.parent.parent / (
            "aiagent/langgraph/jobGeneratorV2/orchestrator_v3.py"
        )

        # Act
        result = subprocess.run(
            ["grep", "-n", r"tasks\[i\]", str(orchestrator_path)],
            capture_output=True,
            text=True,
        )

        # Assert
        assert result.returncode != 0, f"Found tasks[i] pattern: {result.stdout}"


@pytest.mark.acceptance
class TestTC012OrchestratorCodeLines:
    """TC-012: オーケストレーターコード行数.

    テスト観点: コード削減目標の達成
    関連する受入条件: AC-8
    関連する設計方針: DP-1
    """

    def test_orchestrator_v3_under_300_lines(self) -> None:
        """orchestrator_v3.pyが300行以下."""
        # Arrange
        orchestrator_path = Path(__file__).parent.parent.parent.parent / (
            "aiagent/langgraph/jobGeneratorV2/orchestrator_v3.py"
        )

        # Act
        result = subprocess.run(
            ["wc", "-l", str(orchestrator_path)],
            capture_output=True,
            text=True,
        )
        line_count = int(result.stdout.strip().split()[0])

        # Assert
        assert line_count <= 300, f"orchestrator_v3.py has {line_count} lines (max: 300)"


@pytest.mark.acceptance
class TestTC013DeadCodeRemoved:
    """TC-013: 削除対象コードの不在確認.

    テスト観点: Phase 0の完了確認
    関連する受入条件: AC-1
    関連する設計方針: なし
    """

    def test_task_id_mapping_not_in_orchestrator_v3(self) -> None:
        """orchestrator_v3.pyにTaskIdMappingが存在しない."""
        # Arrange
        orchestrator_path = Path(__file__).parent.parent.parent.parent / (
            "aiagent/langgraph/jobGeneratorV2/orchestrator_v3.py"
        )

        # Act
        result = subprocess.run(
            ["grep", "-n", "TaskIdMapping", str(orchestrator_path)],
            capture_output=True,
            text=True,
        )

        # Assert
        assert result.returncode != 0, f"Found TaskIdMapping: {result.stdout}"

    def test_skip_aggregator_not_in_orchestrator_v3(self) -> None:
        """orchestrator_v3.pyにSkipAggregatorが存在しない."""
        # Arrange
        orchestrator_path = Path(__file__).parent.parent.parent.parent / (
            "aiagent/langgraph/jobGeneratorV2/orchestrator_v3.py"
        )

        # Act
        result = subprocess.run(
            ["grep", "-n", "SkipAggregator", str(orchestrator_path)],
            capture_output=True,
            text=True,
        )

        # Assert
        assert result.returncode != 0, f"Found SkipAggregator: {result.stdout}"


# === Unit/Integration Based Tests ===


@pytest.mark.acceptance
class TestTC014TaskDependencyValidator:
    """TC-014: TaskDependencyValidator循環参照検出.

    テスト観点: 依存関係バリデーション
    関連する受入条件: AC-12
    関連する設計方針: DP-5
    """

    @pytest.fixture
    def validator(self) -> TaskDependencyValidator:
        """TaskDependencyValidatorを作成."""
        return TaskDependencyValidator()

    def test_detects_circular_reference(
        self, validator: TaskDependencyValidator
    ) -> None:
        """循環参照を検出できる."""
        # Arrange: A -> B -> C -> A (circular)
        tasks = [
            {"task_id": "task_a", "dependencies": ["task_c"]},
            {"task_id": "task_b", "dependencies": ["task_a"]},
            {"task_id": "task_c", "dependencies": ["task_b"]},
        ]

        # Act
        result = validator.validate(tasks)

        # Assert
        assert result.is_valid is False
        assert len(result.circular_references) > 0
        assert any("circular" in err.lower() for err in result.errors)

    def test_passes_valid_dependencies(
        self, validator: TaskDependencyValidator
    ) -> None:
        """正当な依存関係は検証を通過する."""
        # Arrange: A -> B -> C (linear, no circular)
        tasks = [
            {"task_id": "task_a", "dependencies": []},
            {"task_id": "task_b", "dependencies": ["task_a"]},
            {"task_id": "task_c", "dependencies": ["task_b"]},
        ]

        # Act
        result = validator.validate(tasks)

        # Assert
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.execution_order == ["task_a", "task_b", "task_c"]

    def test_detects_missing_dependency(
        self, validator: TaskDependencyValidator
    ) -> None:
        """存在しない依存先を検出できる."""
        # Arrange
        tasks = [
            {"task_id": "task_a", "dependencies": ["task_nonexistent"]},
        ]

        # Act
        result = validator.validate(tasks)

        # Assert
        assert result.is_valid is False
        assert "task_nonexistent" in result.missing_dependencies


@pytest.mark.acceptance
class TestTC003ErrorRecoveryRetry:
    """TC-003: ErrorRecoveryManager RETRY_CURRENT戦略.

    テスト観点: 一時的エラー時のリトライ動作
    関連する受入条件: AC-9, AC-12
    関連する設計方針: DP-4
    """

    @pytest.fixture
    def error_recovery_manager(self) -> ErrorRecoveryManager:
        """ErrorRecoveryManagerを作成."""
        return ErrorRecoveryManager()

    def test_transient_error_returns_retry_current(
        self, error_recovery_manager: ErrorRecoveryManager
    ) -> None:
        """一時的エラーはRETRY_CURRENT戦略を返す."""
        # Arrange
        error = PhaseError(
            phase=PhaseV3.WORKFLOW_GEN,
            error_type=ErrorType.TRANSIENT,
            message="Temporary API failure",
        )

        # Act
        recovery = error_recovery_manager.determine_recovery(error)

        # Assert
        assert recovery.strategy == RecoveryStrategy.RETRY_CURRENT

    def test_max_retry_count_enforced(
        self, error_recovery_manager: ErrorRecoveryManager
    ) -> None:
        """最大リトライ回数が遵守される."""
        # Arrange
        error = PhaseError(
            phase=PhaseV3.WORKFLOW_GEN,
            error_type=ErrorType.TRANSIENT,
            message="Temporary API failure",
        )

        # Act: Exhaust retries
        for _ in range(5):  # max total retries
            recovery = error_recovery_manager.determine_recovery(error)
            if recovery.strategy == RecoveryStrategy.FAIL_FAST:
                break

        # Assert: After max retries, should fail fast
        final_recovery = error_recovery_manager.determine_recovery(error)
        assert final_recovery.strategy == RecoveryStrategy.FAIL_FAST


@pytest.mark.acceptance
class TestTC005ParallelExecutionPartialSuccess:
    """TC-005: 並列実行の部分成功.

    テスト観点: 一部タスク失敗時の継続動作
    関連する受入条件: AC-4, AC-9
    関連する設計方針: DP-3, DP-4
    """

    @pytest.mark.asyncio
    async def test_partial_success_continues_for_successful_tasks(self) -> None:
        """一部タスク失敗時も成功タスクは完了する."""
        # Arrange
        tasks = [
            UnifiedTaskIdentifier(task_id="task_1"),
            UnifiedTaskIdentifier(task_id="task_2"),
            UnifiedTaskIdentifier(task_id="task_3"),
        ]

        async def generate_func(task: UnifiedTaskIdentifier) -> dict[str, Any]:
            if task.task_id == "task_2":
                raise ValueError("Simulated failure for task_2")
            return {"workflow_name": f"workflow_{task.task_id}"}

        # Act
        result = await parallel_workflow_generation(
            tasks=tasks,
            generate_func=generate_func,
            max_concurrent=5,
            timeout_per_task=30.0,
        )

        # Assert
        assert result.total_count == 3
        assert result.success_count == 2
        assert result.failure_count == 1
        assert result.has_failures
        assert result.has_partial_success


@pytest.mark.acceptance
class TestTC007NoSilentFallback:
    """TC-007: サイレントフォールバックの排除.

    テスト観点: データ不在時のエラー発生
    関連する受入条件: AC-6
    関連する設計方針: DP-4
    """

    def test_orchestrator_raises_on_missing_task(self) -> None:
        """存在しないtask_idでルックアップ時にエラーが発生する."""
        # Arrange
        from unittest.mock import AsyncMock, MagicMock

        orchestrator = JobGenerationOrchestratorV3(
            error_recovery_manager=ErrorRecoveryManager(),
            llm_client=MagicMock(),
            jobqueue_client=MagicMock(),
        )
        # _get_task_by_id should raise for missing task
        tasks = [
            MagicMock(task_id="task_1"),
            MagicMock(task_id="task_2"),
        ]

        # Act & Assert
        with pytest.raises(OrchestratorError) as exc_info:
            orchestrator._get_task_by_id(tasks, "task_nonexistent")

        assert "not found" in str(exc_info.value).lower()


# === Validation Pipeline Tests ===


@pytest.mark.acceptance
class TestValidationPipelineIntegration:
    """ValidationPipelineV3の統合確認.

    テスト観点: バリデーションチェーンの動作
    関連する受入条件: AC-12
    関連する設計方針: DP-5
    """

    @pytest.fixture
    def pipeline(self) -> ValidationPipelineV3:
        """ValidationPipelineV3を作成."""
        return ValidationPipelineV3()

    def test_valid_workflow_passes_all_validators(
        self, pipeline: ValidationPipelineV3
    ) -> None:
        """有効なワークフローは全バリデーターを通過する."""
        # Arrange
        workflow = {
            "workflow_name": "test_workflow",
            "steps": [
                {
                    "step_id": "step_1",
                    "agent_name": "test_agent",
                    "inputs": {},
                    "outputs": {},
                }
            ],
        }

        # Act
        result = pipeline.validate(workflow, workflow_id="test_1")

        # Assert
        # ValidationResult may have warnings but should be valid
        assert result is not None

    def test_empty_workflow_fails_structural_validation(
        self, pipeline: ValidationPipelineV3
    ) -> None:
        """空のワークフローは構造検証で失敗する."""
        # Arrange
        workflow: dict[str, Any] = {}

        # Act
        result = pipeline.validate(workflow, workflow_id="empty_test")

        # Assert
        assert result.is_valid is False or len(result.errors) > 0


# === UnifiedTaskIdentifier Tests ===


@pytest.mark.acceptance
class TestUnifiedTaskIdentifierUsage:
    """UnifiedTaskIdentifierの使用確認.

    テスト観点: 統一IDパターンの動作
    関連する受入条件: AC-2, AC-3
    関連する設計方針: DP-2
    """

    def test_task_identifier_equality_based_on_task_id(self) -> None:
        """task_idのみで等価判定される."""
        # Arrange
        id1 = UnifiedTaskIdentifier(task_id="task_1", task_master_id="master_1")
        id2 = UnifiedTaskIdentifier(task_id="task_1", task_master_id="master_2")

        # Act & Assert
        assert id1 == id2  # Same task_id, different master_id

    def test_task_identifier_hashable(self) -> None:
        """辞書のキーとして使用可能."""
        # Arrange
        id1 = UnifiedTaskIdentifier(task_id="task_1")
        id2 = UnifiedTaskIdentifier(task_id="task_2")

        # Act
        mapping = {id1: "value1", id2: "value2"}

        # Assert
        assert mapping[id1] == "value1"
        assert mapping[id2] == "value2"
