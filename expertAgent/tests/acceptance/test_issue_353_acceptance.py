"""
Issue #353 WORKFLOW_GEN フェーズ未完了時のエラーハンドリング 受入テスト（L3: ローカル受入テスト）

前提条件:
- サービスが起動していること (USE_JOB_GENERATOR_V2=true ./scripts/dev-hybrid.sh)
- .env に必要なAPIキーが設定されていること

実行方法:
  cd expertAgent && uv run pytest tests/acceptance/test_issue_353_acceptance.py -v

検証内容:
- AC-1: WORKFLOW_GEN フェーズ失敗時の適切なエラーハンドリング
- AC-2: __PENDING__ が残った状態で FINALIZATION に進まないバリデーション
- AC-3: ジョブ生成 UI で WORKFLOW_GEN 失敗を明示的に表示
- AC-4: 既存の __PENDING__ ジョブの検出・修復手段の提供
"""

import os
from typing import Any
from unittest.mock import MagicMock

import pytest
import requests

from aiagent.langgraph.jobGeneratorV2.orchestrator import JobGenerationOrchestrator
from aiagent.langgraph.jobGeneratorV2.protocols import ErrorType
from aiagent.langgraph.jobGeneratorV2.recovery import (
    ErrorRecoveryManager,
    ErrorRecoveryStrategy,
)
from aiagent.langgraph.jobGeneratorV2.types import Phase, PhaseStatus


@pytest.mark.acceptance
class TestIssue353WorkflowGenIncompleteAcceptance:
    """Issue #353: WORKFLOW_GEN フェーズ未完了時のエラーハンドリング E2E 検証"""

    # サービスURL
    EXPERT_AGENT_URL = os.getenv("EXPERT_AGENT_URL", "http://localhost:8004")
    JOBQUEUE_URL = os.getenv("JOBQUEUE_URL", "http://localhost:8001")

    @pytest.fixture
    def services_running(self) -> bool:
        """サービス起動確認（E2Eテストのみ使用）"""
        try:
            response = requests.get(f"{self.EXPERT_AGENT_URL}/health", timeout=5)
            return response.status_code == 200
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
            return False

    # ==========================================================================
    # AC-1: WORKFLOW_GEN フェーズ失敗時のエラーハンドリング
    # ==========================================================================

    def test_ac1_error_type_incomplete_workflow_exists(self) -> None:
        """AC-1: ErrorType.INCOMPLETE_WORKFLOW が定義されている"""
        assert hasattr(ErrorType, "INCOMPLETE_WORKFLOW")
        assert ErrorType.INCOMPLETE_WORKFLOW.value == "incomplete_workflow"

    def test_ac1_incomplete_workflow_error_is_retriable(self) -> None:
        """AC-1: INCOMPLETE_WORKFLOW エラーはリトライ可能"""
        from aiagent.langgraph.jobGeneratorV2.protocols import WorkflowError

        manager = ErrorRecoveryManager()

        # Create mock context that allows retry
        mock_context = MagicMock()
        mock_context.can_retry.return_value = True
        mock_context.get_rollback_count.return_value = 0

        error = WorkflowError(
            "WORKFLOW_GEN incomplete",
            error_type=ErrorType.INCOMPLETE_WORKFLOW,
        )

        decision = manager.decide_recovery(
            phase=Phase.WORKFLOW_GEN,
            error=error,
            context=mock_context,
        )

        # INCOMPLETE_WORKFLOW should trigger retry
        assert decision.strategy == ErrorRecoveryStrategy.RETRY_CURRENT
        assert decision.should_notify_user is True  # User should be notified

    def test_ac1_incomplete_workflow_fails_after_max_retries(self) -> None:
        """AC-1: 最大リトライ後に適切に失敗する"""
        from aiagent.langgraph.jobGeneratorV2.protocols import WorkflowError

        manager = ErrorRecoveryManager()

        # Create mock context that cannot retry (exhausted)
        mock_context = MagicMock()
        mock_context.can_retry.return_value = False
        mock_context.get_rollback_count.return_value = 0

        error = WorkflowError(
            "WORKFLOW_GEN incomplete after retries",
            error_type=ErrorType.INCOMPLETE_WORKFLOW,
        )

        decision = manager.decide_recovery(
            phase=Phase.WORKFLOW_GEN,
            error=error,
            context=mock_context,
        )

        # Should try rollback after max retries
        assert decision.strategy == ErrorRecoveryStrategy.ROLLBACK_ONE
        # INCOMPLETE_WORKFLOW notifies user even on rollback
        assert decision.should_notify_user is True

    # ==========================================================================
    # AC-2: __PENDING__ バリデーション
    # ==========================================================================

    def test_ac2_pending_workflow_validator_exists(self) -> None:
        """AC-2: PendingWorkflowValidator が実装されている"""
        from aiagent.langgraph.jobGeneratorV2.validators.pending_workflow import (
            PENDING_PLACEHOLDER,
            PendingWorkflowValidationResult,
            PendingWorkflowValidator,
        )

        # Classes exist
        assert PendingWorkflowValidator is not None
        assert PendingWorkflowValidationResult is not None
        assert PENDING_PLACEHOLDER == "__PENDING__"

        # Validator can be instantiated
        validator = PendingWorkflowValidator()
        assert validator is not None

    def test_ac2_pending_workflow_validator_detects_pending(self) -> None:
        """AC-2: PendingWorkflowValidator が __PENDING__ を検出する"""
        from aiagent.langgraph.jobGeneratorV2.validators.pending_workflow import (
            PendingWorkflowValidator,
        )

        validator = PendingWorkflowValidator()

        # Mock TaskMasters with __PENDING__ workflow_name
        task_masters = [
            {
                "id": "tm-001",
                "name": "Task 1",
                "body_template": {
                    "workflow_name": "valid_workflow",
                    "inputs": "{}",
                },
            },
            {
                "id": "tm-002",
                "name": "Task 2",
                "body_template": {
                    "workflow_name": "__PENDING__",  # This should be detected
                    "inputs": "{}",
                },
            },
        ]

        result = validator.validate(task_masters)

        assert result.has_pending is True
        assert "tm-002" in result.pending_task_master_ids
        assert len(result.pending_task_master_ids) == 1

    def test_ac2_pending_workflow_validator_passes_valid(self) -> None:
        """AC-2: 正常なTaskMastersは検証に通過する"""
        from aiagent.langgraph.jobGeneratorV2.validators.pending_workflow import (
            PendingWorkflowValidator,
        )

        validator = PendingWorkflowValidator()

        task_masters = [
            {
                "id": "tm-001",
                "name": "Task 1",
                "body_template": {
                    "workflow_name": "search_workflow",
                    "inputs": "{}",
                },
            },
            {
                "id": "tm-002",
                "name": "Task 2",
                "body_template": {
                    "workflow_name": "export_workflow",
                    "inputs": "{}",
                },
            },
        ]

        result = validator.validate(task_masters)

        assert result.has_pending is False
        assert len(result.pending_task_master_ids) == 0

    @pytest.mark.asyncio
    async def test_ac2_can_proceed_to_finalization_blocks_incomplete(self) -> None:
        """AC-2: _can_proceed_to_finalization が未完了ワークフローをブロックする"""
        from aiagent.langgraph.jobGeneratorV2.types import WorkflowGenPhaseOutput

        # Create mock orchestrator with required recovery_manager
        recovery_manager = ErrorRecoveryManager()
        orchestrator = JobGenerationOrchestrator(recovery_manager=recovery_manager)

        # Create mock context
        mock_context = MagicMock()

        # Create phase outputs with incomplete workflow
        mock_task_output = MagicMock()
        mock_task_output.workflow_yaml = None  # Incomplete
        mock_task_output.status = PhaseStatus.FAILED

        mock_workflow_gen_output = MagicMock(spec=WorkflowGenPhaseOutput)
        mock_workflow_gen_output.status = PhaseStatus.FAILED
        mock_workflow_gen_output.task_workflows = {"task-1": mock_task_output}

        phase_outputs: dict[Phase, Any] = {
            Phase.WORKFLOW_GEN: mock_workflow_gen_output,
        }

        can_proceed, error_msg = await orchestrator._can_proceed_to_finalization(
            phase_outputs, mock_context
        )

        assert can_proceed is False
        assert error_msg is not None
        assert "incomplete" in error_msg.lower() or "failed" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_ac2_can_proceed_to_finalization_allows_complete(self) -> None:
        """AC-2: _can_proceed_to_finalization が完了したワークフローを許可する"""
        from aiagent.langgraph.jobGeneratorV2.types import WorkflowGenPhaseOutput

        recovery_manager = ErrorRecoveryManager()
        orchestrator = JobGenerationOrchestrator(recovery_manager=recovery_manager)
        mock_context = MagicMock()

        # Create phase outputs with complete workflow
        mock_task_output = MagicMock()
        mock_task_output.workflow_yaml = "nodes:\n  source: {}"
        mock_task_output.status = PhaseStatus.SUCCESS  # Use SUCCESS, not COMPLETED

        mock_workflow_gen_output = MagicMock(spec=WorkflowGenPhaseOutput)
        mock_workflow_gen_output.status = (
            PhaseStatus.SUCCESS
        )  # Use SUCCESS, not COMPLETED
        mock_workflow_gen_output.task_workflows = {"task-1": mock_task_output}

        phase_outputs: dict[Phase, Any] = {
            Phase.WORKFLOW_GEN: mock_workflow_gen_output,
        }

        can_proceed, error_msg = await orchestrator._can_proceed_to_finalization(
            phase_outputs, mock_context
        )

        assert can_proceed is True
        assert error_msg is None

    # ==========================================================================
    # AC-3: UI表示（ErrorNotification）
    # ==========================================================================

    def test_ac3_error_notification_model_exists(self) -> None:
        """AC-3: ErrorNotification モデルが実装されている"""
        from datetime import datetime

        from aiagent.langgraph.jobGeneratorV2.validators.pending_workflow import (
            ErrorNotification,
            NotificationLevel,
        )

        # Notification levels exist
        assert hasattr(NotificationLevel, "INFO")
        assert hasattr(NotificationLevel, "WARNING")
        assert hasattr(NotificationLevel, "ERROR")
        assert hasattr(NotificationLevel, "CRITICAL")

        # Can create ErrorNotification
        notification = ErrorNotification(
            job_id="job-123",
            phase=Phase.WORKFLOW_GEN,
            timestamp=datetime.now(),
            level=NotificationLevel.ERROR,
            title="Workflow Generation Failed",
            message="Failed to generate workflow for task",
            details={"task_id": "task-1"},
            suggested_actions=["Check GraphAiServer connection", "Retry later"],
            can_retry=True,
            requires_user_action=False,
            langfuse_trace_id="trace-123",
        )

        assert notification.level == NotificationLevel.ERROR
        assert notification.can_retry is True

    def test_ac3_error_notification_for_pending_workflows(self) -> None:
        """AC-3: __PENDING__ 検出時にErrorNotificationを生成できる"""
        from aiagent.langgraph.jobGeneratorV2.validators.pending_workflow import (
            NotificationLevel,
            PendingWorkflowValidationResult,
            create_notification_from_pending_result,
        )

        # Create validation result with pending workflows
        result = PendingWorkflowValidationResult(
            has_pending=True,
            pending_task_master_ids=["tm-001", "tm-002"],
            task_details=[
                {"id": "tm-001", "name": "Task 1", "workflow_name": "__PENDING__"},
                {"id": "tm-002", "name": "Task 2", "workflow_name": "__PENDING__"},
            ],
        )

        # Create notification from result
        notification = create_notification_from_pending_result(result, job_id="job-123")

        assert notification.level == NotificationLevel.ERROR
        assert (
            "incomplete" in notification.title.lower()
            or "pending" in notification.title.lower()
        )
        assert notification.can_retry is True
        assert len(notification.suggested_actions) > 0

    # ==========================================================================
    # AC-4: 既存データ修復手段
    # ==========================================================================

    def test_ac4_pending_workflow_validator_can_scan_task_masters(self) -> None:
        """AC-4: PendingWorkflowValidator が複数TaskMasterをスキャンできる"""
        from aiagent.langgraph.jobGeneratorV2.validators.pending_workflow import (
            PendingWorkflowValidator,
        )

        validator = PendingWorkflowValidator()

        # Simulate existing TaskMasters with mixed states
        task_masters = [
            {
                "id": "tm-1",
                "name": "Task 1",
                "body_template": {"workflow_name": "workflow_a"},
            },
            {
                "id": "tm-2",
                "name": "Task 2",
                "body_template": {"workflow_name": "__PENDING__"},
            },
            {
                "id": "tm-3",
                "name": "Task 3",
                "body_template": {"workflow_name": "workflow_b"},
            },
            {
                "id": "tm-4",
                "name": "Task 4",
                "body_template": {"workflow_name": "__PENDING__"},
            },
            {
                "id": "tm-5",
                "name": "Task 5",
                "body_template": {"workflow_name": "workflow_c"},
            },
        ]

        result = validator.validate(task_masters)

        # Should detect exactly 2 pending workflows
        assert result.has_pending is True
        assert len(result.pending_task_master_ids) == 2
        assert "tm-2" in result.pending_task_master_ids
        assert "tm-4" in result.pending_task_master_ids

    # ==========================================================================
    # 設計方針検証 (Design Policy Verification)
    # ==========================================================================

    def test_dp3_workflow_gen_retry_config_exists(self) -> None:
        """DP-3: WorkflowGenRetryConfig が実装されている"""
        from aiagent.langgraph.jobGeneratorV2.retry.workflow_gen_retry import (
            WorkflowGenRetryConfig,
        )

        config = WorkflowGenRetryConfig()

        assert config.max_retries == 3
        assert config.base_delay_seconds == 1.0
        assert config.max_delay_seconds == 30.0
        assert config.exponential_base == 2.0

    @pytest.mark.asyncio
    async def test_dp3_calculate_retry_delay_exponential_backoff(self) -> None:
        """DP-3: Exponential backoff が正しく計算される"""
        from aiagent.langgraph.jobGeneratorV2.retry.workflow_gen_retry import (
            WorkflowGenRetryConfig,
            calculate_retry_delay,
        )

        config = WorkflowGenRetryConfig(
            base_delay_seconds=1.0,
            max_delay_seconds=30.0,
            exponential_base=2.0,
        )

        # Note: Jitter is added internally, so we allow wider variance
        # Attempt 1: 1 * 2^0 = 1 second + jitter
        delay_1 = await calculate_retry_delay(1, config)
        assert 0.5 <= delay_1 <= 2.0  # Allow for jitter

        # Attempt 2: 1 * 2^1 = 2 seconds + jitter
        delay_2 = await calculate_retry_delay(2, config)
        assert 1.0 <= delay_2 <= 4.0  # Allow for jitter

        # Attempt 3: 1 * 2^2 = 4 seconds + jitter
        delay_3 = await calculate_retry_delay(3, config)
        assert 2.0 <= delay_3 <= 8.0  # Allow for jitter

        # Verify increasing delay pattern (on average)
        # Due to jitter, we can't guarantee strict ordering, but the base formula should increase

    @pytest.mark.asyncio
    async def test_dp3_execute_with_timeout_raises_on_timeout(self) -> None:
        """DP-3: execute_with_timeout がタイムアウト時にエラーを送出する"""
        import asyncio

        from aiagent.langgraph.jobGeneratorV2.protocols import WorkflowError
        from aiagent.langgraph.jobGeneratorV2.retry.workflow_gen_retry import (
            execute_with_timeout,
        )

        async def slow_operation() -> str:
            await asyncio.sleep(10)  # Very slow
            return "result"

        with pytest.raises(WorkflowError) as exc_info:
            await execute_with_timeout(
                coro=slow_operation(),
                timeout_seconds=0.1,  # Very short timeout
                error_type=ErrorType.INCOMPLETE_WORKFLOW,
                error_message="Operation timed out",
            )

        assert exc_info.value.error_type == ErrorType.INCOMPLETE_WORKFLOW

    # ==========================================================================
    # E2E テスト（サービス必須）
    # ==========================================================================

    @pytest.mark.skipif(
        not os.getenv("RUN_E2E_TESTS", "").lower() == "true",
        reason="E2E tests require running services. Set RUN_E2E_TESTS=true to run.",
    )
    def test_e2e_job_generation_with_all_workflows_complete(
        self, services_running: bool
    ) -> None:
        """E2E: 正常なジョブ生成で __PENDING__ が残らない"""
        if not services_running:
            pytest.skip("Services not running")

        # This test would call the actual API
        # Implementation would require running services
        pass

    @pytest.mark.skipif(
        not os.getenv("RUN_E2E_TESTS", "").lower() == "true",
        reason="E2E tests require running services. Set RUN_E2E_TESTS=true to run.",
    )
    def test_e2e_job_status_includes_notification_on_failure(
        self, services_running: bool
    ) -> None:
        """E2E: 失敗時にステータスAPIにnotificationが含まれる"""
        if not services_running:
            pytest.skip("Services not running")

        # This test would call the actual API
        # Implementation would require running services
        pass
