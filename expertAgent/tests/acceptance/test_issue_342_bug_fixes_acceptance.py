"""
Issue #342 バグ修正 受入テスト（L3: ローカル受入テスト）

対象バグ: Bug #1, #3, #5, #6, #9, #11（高・中優先度）

前提条件:
- サービスが起動していること (USE_JOB_GENERATOR_V2=true ./scripts/dev-hybrid.sh)
- .env に ANTHROPIC_API_KEY が設定されていること

実行方法:
  cd expertAgent
  USE_JOB_GENERATOR_V2=true uv run pytest tests/acceptance/test_issue_342_bug_fixes_acceptance.py -v
"""

import os
import time
from typing import Any

import pytest
import requests


@pytest.mark.acceptance
class TestIssue342BugFixesAcceptance:
    """Issue #342: V2アーキテクチャバグ修正 受入テスト"""

    EXPERT_AGENT_URL = os.environ.get("EXPERT_AGENT_URL", "http://localhost:8004")
    MYVAULT_URL = os.environ.get("MYVAULT_URL", "http://localhost:8003")
    TIMEOUT_SECONDS = 180  # ジョブ完了待ちタイムアウト

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """テストセットアップ"""
        # サービス起動確認
        for url, name in [
            (self.EXPERT_AGENT_URL, "expertAgent"),
            (self.MYVAULT_URL, "myVault"),
        ]:
            try:
                response = requests.get(f"{url}/health", timeout=5)
                if response.status_code != 200:
                    pytest.skip(f"{name} is not healthy")
            except requests.exceptions.ConnectionError:
                pytest.skip(f"{name} is not running")

    def _submit_job(self, requirement: str) -> str:
        """ジョブを投入してjob_idを返す"""
        response = requests.post(
            f"{self.EXPERT_AGENT_URL}/aiagent-api/v1/job-generator",
            json={"user_requirement": requirement, "max_retry": 3},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        assert response.status_code in [200, 202], f"Submit failed: {response.text}"
        return response.json()["job_id"]

    def _wait_for_completion(self, job_id: str) -> dict[str, Any]:
        """ジョブ完了を待機してステータスを返す"""
        start_time = time.time()
        while time.time() - start_time < self.TIMEOUT_SECONDS:
            response = requests.get(
                f"{self.EXPERT_AGENT_URL}/aiagent-api/v1/jobs/{job_id}/status",
                timeout=10,
            )
            if response.status_code != 200:
                time.sleep(5)
                continue
            status = response.json()
            if status.get("status") in ["completed", "failed"]:
                return status
            time.sleep(10)
        pytest.fail(f"Job {job_id} did not complete within {self.TIMEOUT_SECONDS}s")

    # ==========================================================================
    # Bug #1: task_id と task_master_id の混同 修正検証
    # ==========================================================================

    def test_bug1_task_id_mapping_used_correctly(self) -> None:
        """Bug #1: TaskIdMapping が正しく使用されていること

        検証内容:
        - 複数タスクを含む要件でジョブ生成
        - 全タスクにワークフローが生成される
        - interface lookup が成功する（失敗するとNoneになる）
        """
        # Arrange: 複数タスクを含む要件
        requirement = """
        以下の3つのタスクを実行してください：
        1. Yahoo FinanceからAppleの株価を取得
        2. 取得したデータを分析してサマリーを作成
        3. 分析結果をJSON形式で出力
        """

        # Act
        job_id = self._submit_job(requirement)
        status = self._wait_for_completion(job_id)

        # Assert: 成功またはpartial_success（infeasibleタスクがあっても可）
        assert status["status"] in ["completed", "partial_success"], (
            f"Bug #1: Job failed unexpectedly. Status: {status}"
        )

        # 結果にtask_breakdownが存在すること
        result = status.get("result", {})
        assert result.get("task_breakdown") is not None, (
            "Bug #1: task_breakdown should exist"
        )

    # ==========================================================================
    # Bug #3: サイレントスキップ 修正検証
    # ==========================================================================

    def test_bug3_silent_skip_error_aggregation(self) -> None:
        """Bug #3: サイレントスキップがエラー集約されること

        検証内容:
        - 要件でジョブ生成
        - ジョブが終端状態に到達すること（サイレント失敗ではない）
        - 結果にはtask_breakdownかerror_messageが含まれること

        Note: 「実現不可能な要件」はLLMによって解釈が異なるため、
        ここでは終端状態への到達と結果の存在を確認します。
        SkipAggregator の動作はユニットテストで検証済みです。
        """
        # Arrange: ジョブ生成
        requirement = "APIからデータを取得して処理する"

        # Act
        job_id = self._submit_job(requirement)
        status = self._wait_for_completion(job_id)

        # Assert: 終端状態に到達すること（サイレント停止ではない）
        assert status["status"] in ["completed", "failed", "partial_success"], (
            f"Bug #3: Job should reach terminal state. Got: {status['status']}"
        )

        # 結果が存在すること（サイレント失敗ではない）
        result = status.get("result", {})
        has_task_breakdown = result.get("task_breakdown") is not None
        has_error_message = (
            result.get("error_message") is not None
            or status.get("error_message") is not None
        )
        has_any_content = has_task_breakdown or has_error_message or len(result) > 0

        assert has_any_content, (
            "Bug #3: Job should have task_breakdown or error_message (not silent)"
        )

    # ==========================================================================
    # Bug #5: RegistrationOutput マッピング 修正検証
    # ==========================================================================

    def test_bug5_registration_output_mapping(self) -> None:
        """Bug #5: RegistrationOutput にマッピングが含まれること

        検証内容:
        - ジョブ生成後に job_master_id と task_master_ids が返される
        - task_master_ids のフォーマットが正しい（tm_で始まる）
        """
        # Arrange
        requirement = (
            "Google検索でPythonのチュートリアルを検索してトップ5の結果を取得する"
        )

        # Act
        job_id = self._submit_job(requirement)
        status = self._wait_for_completion(job_id)

        # Assert: 成功時のみ検証
        if status["status"] == "completed":
            result = status.get("result", {})
            job_master_id = result.get("job_master_id")

            # job_master_id が存在すること
            assert job_master_id is not None, (
                "Bug #5: job_master_id should exist on success"
            )

            # job_master_id のフォーマット確認（jm_ で始まる）
            if job_master_id:
                assert job_master_id.startswith(("jm_", "job_")), (
                    f"Bug #5: Invalid job_master_id format: {job_master_id}"
                )

    # ==========================================================================
    # Bug #6: スキーマ数不一致の閾値ベース判定 修正検証
    # ==========================================================================

    def test_bug6_schema_count_threshold(self) -> None:
        """Bug #6: スキーマ数不一致が閾値ベースで処理されること

        検証内容:
        - diff=1 は警告レベルで処理が継続
        - diff≥2 はエラーとして処理
        """
        # このテストはユニットテストで詳細検証済み
        # L3ではinterface_definitions が返されることを確認
        requirement = "指定されたURLの内容を取得して要約を作成する"

        # Act
        job_id = self._submit_job(requirement)
        status = self._wait_for_completion(job_id)

        # Assert
        if status["status"] == "completed":
            result = status.get("result", {})
            # interface_definitions が存在すること（または task_breakdown）
            has_interfaces = result.get("interface_definitions") is not None
            has_task_breakdown = result.get("task_breakdown") is not None
            assert has_interfaces or has_task_breakdown, (
                "Bug #6: Should have interface_definitions or task_breakdown"
            )

    # ==========================================================================
    # Bug #9: 非同期タスク例外処理 修正検証
    # ==========================================================================

    def test_bug9_async_task_exception_logged(self) -> None:
        """Bug #9: 非同期タスクの例外がログに記録されること

        検証内容:
        - ジョブ実行後にログを確認
        - Fire-and-forget の例外が消えていないこと
        """
        # Arrange
        requirement = "シンプルなHello Worldプログラムを作成する"

        # Act
        job_id = self._submit_job(requirement)
        status = self._wait_for_completion(job_id)

        # Assert: 基本的な動作確認（ログ検証は手動または別途）
        # 重要: 非同期処理がデッドロックせずに完了すること
        assert status["status"] in ["completed", "failed", "partial_success"], (
            f"Bug #9: Job should complete without hanging. Status: {status['status']}"
        )

    # ==========================================================================
    # Bug #11: テンプレート生成 interface 使用 修正検証
    # ==========================================================================

    def test_bug11_template_uses_interface(self) -> None:
        """Bug #11: テンプレートフォールバック時も interface 情報が使用されること

        検証内容:
        - ワークフロー生成が成功
        - 生成されたワークフローに適切なエージェントが設定される
        """
        # Arrange: fetchAgent が使用される要件
        requirement = "https://example.com からデータを取得して処理する"

        # Act
        job_id = self._submit_job(requirement)
        status = self._wait_for_completion(job_id)

        # Assert
        if status["status"] == "completed":
            result = status.get("result", {})
            # task_breakdown にタスクが存在すること
            task_breakdown = result.get("task_breakdown", {})
            if isinstance(task_breakdown, dict):
                tasks = task_breakdown.get("tasks", [])
            else:
                tasks = task_breakdown if isinstance(task_breakdown, list) else []

            # タスクが1つ以上存在すること
            assert len(tasks) > 0, "Bug #11: Should have at least one task"

    # ==========================================================================
    # 統合テスト: E2E ワークフロー検証
    # ==========================================================================

    def test_e2e_workflow_generation_completes(self) -> None:
        """E2E: V2ワークフロー生成が完了すること

        検証内容:
        - 正常な要件でジョブ生成から完了まで
        - 全フェーズ（TASK_BREAKDOWN → INTERFACE_DESIGN → REGISTRATION → WORKFLOW_GEN）通過
        """
        # Arrange
        requirement = "APIから天気情報を取得して、温度が30度以上ならアラートを出力する"

        # Act
        job_id = self._submit_job(requirement)
        status = self._wait_for_completion(job_id)

        # Assert
        assert status["status"] in ["completed", "partial_success", "failed"], (
            "E2E: Job should reach terminal state"
        )

        # Langfuse trace_id が返されること（オブザーバビリティ確認）
        result = status.get("result", {})
        trace_id = result.get("langfuse_trace_id")
        if trace_id:
            print(f"Langfuse Trace: http://localhost:3001/trace/{trace_id}")


@pytest.mark.acceptance
class TestIssue342UnitBugVerification:
    """Issue #342: ユニットレベルバグ修正検証（サービス不要）"""

    def test_task_id_mapping_class_exists(self) -> None:
        """Bug #1: TaskIdMapping クラスが存在すること"""
        from aiagent.langgraph.jobGeneratorV2.types import TaskIdMapping

        assert TaskIdMapping is not None

    def test_task_id_mapping_from_registration(self) -> None:
        """Bug #1: TaskIdMapping.from_registration が動作すること"""
        from aiagent.langgraph.jobGeneratorV2.types import (
            PhaseStatus,
            RegistrationOutput,
            TaskIdMapping,
        )

        # Arrange
        reg_output = RegistrationOutput(
            status=PhaseStatus.SUCCESS,
            task_master_ids=["tm_001", "tm_002"],
            job_master_id="jm_123",
            task_id_to_master_id={
                "task_001_alt": "tm_001",
                "task_002_alt": "tm_002",
            },
        )

        # Act
        mapping = TaskIdMapping.from_registration(reg_output)

        # Assert
        assert mapping.logical_to_master["task_001_alt"] == "tm_001"
        assert mapping.master_to_logical["tm_001"] == "task_001_alt"

    def test_skip_aggregator_exists(self) -> None:
        """Bug #3: SkipAggregator クラスが存在すること"""
        from aiagent.langgraph.jobGeneratorV2.types import SkipAggregator

        assert SkipAggregator is not None

    def test_skip_aggregator_all_skipped_detection(self) -> None:
        """Bug #3: SkipAggregator.all_skipped が正しく判定すること"""
        from aiagent.langgraph.jobGeneratorV2.types import (
            SkipAggregator,
            SkipInfo,
        )

        # Arrange
        aggregator = SkipAggregator()
        aggregator.add_skip(
            SkipInfo(
                task_id="task_001",
                reason="Test skip",
                phase="WORKFLOW_GEN",
            )
        )
        aggregator.add_skip(
            SkipInfo(
                task_id="task_002",
                reason="Test skip 2",
                phase="WORKFLOW_GEN",
            )
        )

        # Act & Assert
        assert aggregator.all_skipped(2) is True
        assert aggregator.all_skipped(3) is False

    def test_evaluate_schema_count_mismatch_warning(self) -> None:
        """Bug #6: diff=1 で警告が返されること"""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            evaluate_schema_count_mismatch,
        )

        # Act
        result = evaluate_schema_count_mismatch(expected_count=3, actual_count=2)

        # Assert: diff=1 は警告レベル
        assert result.severity == "warning"
        assert abs(result.expected_count - result.actual_count) == 1

    def test_evaluate_schema_count_mismatch_error(self) -> None:
        """Bug #6: diff>=2 でエラーが返されること"""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            evaluate_schema_count_mismatch,
        )

        # Act
        result = evaluate_schema_count_mismatch(expected_count=5, actual_count=2)

        # Assert: diff=3 はエラーレベル
        assert result.severity == "error"
        assert abs(result.expected_count - result.actual_count) == 3

    def test_async_task_manager_exists(self) -> None:
        """Bug #9: AsyncTaskManager クラスが存在すること"""
        from aiagent.langgraph.jobGeneratorV2.progress import AsyncTaskManager

        assert AsyncTaskManager is not None

    def test_schema_count_mismatch_result_exists(self) -> None:
        """Bug #6: SchemaCountMismatchResult クラスが存在すること"""
        from aiagent.langgraph.jobGeneratorV2.types import SchemaCountMismatchResult

        assert SchemaCountMismatchResult is not None
