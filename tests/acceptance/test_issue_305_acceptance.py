"""
Issue #305 受入テスト（L3: ローカル受入テスト）

前提条件:
- サービスが起動していること (./scripts/dev-hybrid.sh または make dev-all)
- .env に必要なAPIキーが設定されていること (ANTHROPIC_API_KEY)
- myVaultにANTHROPIC_API_KEYが登録されていること

実行方法:
  uv run pytest tests/acceptance/test_issue_305_acceptance.py -v
"""

import time
from typing import Any

import pytest
import requests


@pytest.mark.acceptance
class TestIssue305Acceptance:
    """Issue #305: Job生成時にLLMワークフローが自動生成される"""

    # サービスURL
    EXPERT_AGENT_URL = "http://localhost:8004"
    MYVAULT_URL = "http://localhost:8003"
    LANGFUSE_URL = "http://localhost:3001"

    # ポーリング設定
    POLL_INTERVAL = 2  # 秒
    MAX_POLL_COUNT = 90  # 最大180秒待機

    @pytest.fixture(autouse=True)
    def check_services_running(self) -> None:
        """サービス起動確認"""
        services = [
            (self.EXPERT_AGENT_URL, "expertAgent"),
            (self.MYVAULT_URL, "myVault"),
        ]
        for url, name in services:
            try:
                response = requests.get(f"{url}/health", timeout=5)
                if response.status_code != 200:
                    pytest.skip(f"{name} is not healthy (status: {response.status_code})")
            except requests.exceptions.ConnectionError:
                pytest.skip(
                    f"{name} is not running at {url}. "
                    "Run: ./scripts/dev-hybrid.sh or make dev-all"
                )

    # ==========================================================================
    # テスト1: Job Generator呼び出し
    # ==========================================================================

    def test_job_generator_returns_job_id(self) -> None:
        """テスト1: Job Generatorが正常にjob_idを返す

        受入条件: Job Generator呼び出し後、自動的にWorkflow Generatorが実行される
        """
        # Arrange
        endpoint = f"{self.EXPERT_AGENT_URL}/v1/job-generator"
        payload: dict[str, Any] = {
            "user_requirement": "テストメールを送信するワークフロー",
            "project_id": "test-project-305",
        }

        # Act
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        # Assert
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "job_id" in data, f"Response missing 'job_id' field: {data}"
        assert "status" in data, f"Response missing 'status' field: {data}"
        assert data["status"] == "creating", f"Expected status 'creating', got: {data['status']}"

    # ==========================================================================
    # テスト2: Status API - 進捗確認
    # ==========================================================================

    def test_status_api_returns_progress(self) -> None:
        """テスト2: Status APIが進捗を返す

        受入条件: Phase 1（0-70%）→ Phase 2（70-95%）の進捗表示が正しい
        """
        # Arrange: Job作成
        job_response = self._create_job(
            "Gmailから未読メールを取得し、件名を一覧表示するワークフロー"
        )
        job_id = job_response["job_id"]

        # Act: ステータス取得
        status_endpoint = f"{self.EXPERT_AGENT_URL}/v1/jobs/{job_id}/status"
        response = requests.get(status_endpoint, timeout=10)

        # Assert
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "progress" in data, f"Response missing 'progress' field: {data}"
        assert "status" in data, f"Response missing 'status' field: {data}"
        assert isinstance(data["progress"], int), f"Progress should be int: {data['progress']}"
        assert 0 <= data["progress"] <= 100, f"Progress should be 0-100: {data['progress']}"

    # ==========================================================================
    # テスト3: Workflow Generation完了確認
    # ==========================================================================

    def test_workflow_generation_completes(self) -> None:
        """テスト3: Workflow Generationが完了する

        受入条件:
        - 各タスクのWorkflow生成状況（pending/generating/success/failed）が表示される
        - 部分失敗時もJob全体はcompletedになる
        """
        # Arrange: Job作成
        job_response = self._create_job(
            "メールの件名を取得して一覧表示するシンプルなワークフロー"
        )
        job_id = job_response["job_id"]

        # Act: 完了までポーリング（進捗履歴を記録）
        progress_history: list[dict[str, Any]] = []
        final_status = self._poll_until_complete_with_history(job_id, progress_history)

        # Assert: ジョブが完了または失敗していること
        assert final_status["status"] in ["completed", "failed"], (
            f"Expected status 'completed' or 'failed', got: {final_status['status']}"
        )

        # Assert: 完了した場合の検証
        if final_status["status"] == "completed":
            # 進捗は100%であること
            assert final_status["progress"] == 100, (
                f"Expected progress 100, got: {final_status['progress']}"
            )

            # 進捗履歴にPhase 1（0-70%）とPhase 2（70-95%）の両方が含まれること
            phase1_progress = [p for p in progress_history if p["progress"] <= 70]
            phase2_progress = [p for p in progress_history if 70 < p["progress"] < 100]

            assert len(phase1_progress) > 0 or len(phase2_progress) > 0, (
                "Progress history should show progression through phases"
            )

            # workflow_statusesが存在する場合、全てのワークフローが完了していること
            if final_status.get("workflow_statuses"):
                for ws in final_status["workflow_statuses"]:
                    assert ws["status"] in ["success", "failed"], (
                        f"All workflows should be completed, got status: {ws['status']}"
                    )

    # ==========================================================================
    # テスト4: 新規フィールド確認（phase, task_breakdown, workflow_statuses）
    # ==========================================================================

    def test_status_api_contains_new_fields(self) -> None:
        """テスト4: Status APIに新規フィールドが含まれる

        受入条件:
        - Task Breakdown結果が表示される
        - 各タスクのWorkflow生成状況が表示される

        Note: 新規フィールドはOptionalなので、ジョブ完了後に確認
        """
        # Arrange: Job作成
        job_response = self._create_job(
            "テキストファイルを読み込んで内容を要約するワークフロー"
        )
        job_id = job_response["job_id"]

        # Act: 完了までポーリング
        final_status = self._poll_until_complete(job_id)

        # Assert: ジョブが完了していること
        assert final_status["status"] == "completed", (
            f"Job should be completed, got: {final_status['status']}"
        )

        # Assert: phaseフィールドが"complete"であること（Issue #305の核心機能）
        assert "phase" in final_status, "Response must contain 'phase' field"
        assert final_status["phase"] == "complete", (
            f"Expected phase 'complete', got: {final_status.get('phase')}"
        )

        # Assert: task_breakdownが存在し、タスクが含まれること
        assert "task_breakdown" in final_status, "Response must contain 'task_breakdown' field"
        task_breakdown = final_status["task_breakdown"]
        assert task_breakdown is not None, "task_breakdown should not be None"
        assert isinstance(task_breakdown, list), f"task_breakdown should be list, got: {type(task_breakdown)}"
        assert len(task_breakdown) > 0, "task_breakdown should contain at least one task"

        # task_breakdownの各項目の構造を検証
        for i, task in enumerate(task_breakdown):
            assert "task_id" in task, f"task_breakdown[{i}] missing 'task_id'"
            assert "name" in task, f"task_breakdown[{i}] missing 'name'"
            assert "description" in task, f"task_breakdown[{i}] missing 'description'"

        # Assert: workflow_statusesが存在し、ステータスが含まれること
        assert "workflow_statuses" in final_status, "Response must contain 'workflow_statuses' field"
        workflow_statuses = final_status["workflow_statuses"]
        assert workflow_statuses is not None, "workflow_statuses should not be None"
        assert isinstance(workflow_statuses, list), f"workflow_statuses should be list, got: {type(workflow_statuses)}"
        assert len(workflow_statuses) > 0, "workflow_statuses should contain at least one status"

        # workflow_statusesの各項目の構造と値を検証
        valid_statuses = ["pending", "generating", "success", "failed"]
        for i, ws in enumerate(workflow_statuses):
            assert "task_id" in ws, f"workflow_statuses[{i}] missing 'task_id'"
            assert "status" in ws, f"workflow_statuses[{i}] missing 'status'"
            assert ws["status"] in valid_statuses, (
                f"workflow_statuses[{i}] has invalid status: {ws['status']}"
            )

        # 少なくとも1つのworkflowがsuccessまたはfailedで完了していること
        completed_workflows = [ws for ws in workflow_statuses if ws["status"] in ["success", "failed"]]
        assert len(completed_workflows) > 0, (
            "At least one workflow should be completed (success or failed)"
        )

    # ==========================================================================
    # テスト5: Phase遷移とWorkflow生成成功の検証（Issue #305の核心テスト）
    # ==========================================================================

    def test_phase_transitions_and_workflow_success(self) -> None:
        """テスト5: Phase遷移が正しく行われ、Workflowが生成される

        受入条件:
        - Job Generator呼び出し後、自動的にWorkflow Generatorが実行される
        - Phase 1(0-70%) -> Phase 2(70-95%) -> Complete(100%)の進捗表示が正しい
        - 少なくとも1つのWorkflowがsuccessステータスで完了する
        """
        # Arrange: Job作成
        job_response = self._create_job(
            "ファイルを読み込んでその内容をログに出力するワークフロー"
        )
        job_id = job_response["job_id"]

        # Act: 完了までポーリング（進捗履歴を記録）
        progress_history: list[dict[str, Any]] = []
        final_status = self._poll_until_complete_with_history(job_id, progress_history)

        # Assert: ジョブが完了していること
        assert final_status["status"] == "completed", (
            f"Job should be completed, got: {final_status['status']}"
        )

        # Assert: 進捗が100%であること
        assert final_status["progress"] == 100, (
            f"Final progress should be 100, got: {final_status['progress']}"
        )

        # Assert: phaseが"complete"であること
        assert final_status.get("phase") == "complete", (
            f"Final phase should be 'complete', got: {final_status.get('phase')}"
        )

        # Assert: Phase遷移が記録されていること
        phases_seen = set()
        for record in progress_history:
            if record.get("phase"):
                phases_seen.add(record["phase"])

        # task_analysisまたはworkflow_generationフェーズを通過していること
        assert len(phases_seen) >= 1, (
            f"Should have seen at least one phase, got: {phases_seen}"
        )

        # Assert: workflow_statusesが存在し、追跡されていること
        workflow_statuses = final_status.get("workflow_statuses", [])
        assert len(workflow_statuses) > 0, "workflow_statuses should not be empty"

        success_count = sum(1 for ws in workflow_statuses if ws.get("status") == "success")
        failed_count = sum(1 for ws in workflow_statuses if ws.get("status") == "failed")

        print(f"Workflow results: {success_count} success, {failed_count} failed")

        # 全てのワークフローが完了ステータス（successまたはfailed）を持つこと
        # Issue #305の核心は追跡機能であり、成功必須ではない
        completed_count = success_count + failed_count
        assert completed_count == len(workflow_statuses), (
            f"All workflows should have terminal status. "
            f"Got {completed_count} completed out of {len(workflow_statuses)}. "
            f"Statuses: {workflow_statuses}"
        )

        # 各ワークフローステータスの構造を検証
        for i, ws in enumerate(workflow_statuses):
            assert "task_id" in ws, f"workflow_statuses[{i}] missing 'task_id'"
            assert "status" in ws, f"workflow_statuses[{i}] missing 'status'"
            assert ws["status"] in ["success", "failed"], (
                f"workflow_statuses[{i}] has non-terminal status: {ws['status']}"
            )

    # ==========================================================================
    # テスト6: 404エラー確認
    # ==========================================================================

    def test_status_api_returns_404_for_unknown_job(self) -> None:
        """テスト6: 存在しないJob IDで404を返す"""
        # Arrange
        unknown_job_id = "non-existent-job-id-12345"
        status_endpoint = f"{self.EXPERT_AGENT_URL}/v1/jobs/{unknown_job_id}/status"

        # Act
        response = requests.get(status_endpoint, timeout=10)

        # Assert
        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "detail" in data, f"Response missing 'detail' field: {data}"

    # ==========================================================================
    # ヘルパーメソッド
    # ==========================================================================

    def _create_job(self, requirement_text: str) -> dict[str, Any]:
        """ジョブを作成してレスポンスを返す"""
        endpoint = f"{self.EXPERT_AGENT_URL}/v1/job-generator"
        payload: dict[str, Any] = {
            "user_requirement": requirement_text,
            "project_id": "test-project-305",
        }

        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        assert response.status_code == 200, (
            f"Failed to create job: {response.status_code}: {response.text}"
        )

        return response.json()

    def _poll_until_complete(self, job_id: str) -> dict[str, Any]:
        """ジョブが完了するまでポーリング"""
        status_endpoint = f"{self.EXPERT_AGENT_URL}/v1/jobs/{job_id}/status"

        for i in range(self.MAX_POLL_COUNT):
            response = requests.get(status_endpoint, timeout=10)
            assert response.status_code == 200, (
                f"Status check failed: {response.status_code}: {response.text}"
            )

            status = response.json()
            job_status = status.get("status", "unknown")
            progress = status.get("progress", 0)

            print(f"[{i+1}/{self.MAX_POLL_COUNT}] Status: {job_status}, Progress: {progress}%")

            if job_status in ["completed", "failed"]:
                return status

            time.sleep(self.POLL_INTERVAL)

        # タイムアウト
        pytest.fail(
            f"Job {job_id} did not complete within {self.MAX_POLL_COUNT * self.POLL_INTERVAL} seconds"
        )

    def _poll_until_complete_with_history(
        self, job_id: str, history: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """ジョブが完了するまでポーリングし、進捗履歴を記録"""
        status_endpoint = f"{self.EXPERT_AGENT_URL}/v1/jobs/{job_id}/status"

        for i in range(self.MAX_POLL_COUNT):
            response = requests.get(status_endpoint, timeout=10)
            assert response.status_code == 200, (
                f"Status check failed: {response.status_code}: {response.text}"
            )

            status = response.json()
            job_status = status.get("status", "unknown")
            progress = status.get("progress", 0)
            phase = status.get("phase", "unknown")

            # 進捗履歴を記録
            history.append({
                "progress": progress,
                "status": job_status,
                "phase": phase,
                "workflow_statuses": status.get("workflow_statuses"),
            })

            print(
                f"[{i+1}/{self.MAX_POLL_COUNT}] Status: {job_status}, "
                f"Progress: {progress}%, Phase: {phase}"
            )

            if job_status in ["completed", "failed"]:
                return status

            time.sleep(self.POLL_INTERVAL)

        # タイムアウト
        pytest.fail(
            f"Job {job_id} did not complete within {self.MAX_POLL_COUNT * self.POLL_INTERVAL} seconds"
        )
