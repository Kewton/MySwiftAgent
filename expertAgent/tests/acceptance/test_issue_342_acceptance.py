"""
Issue #342 受入テスト（L3: ローカル受入テスト）

Job/Task Generator Agent アーキテクチャ刷新の受入テスト

前提条件:
- サービスが起動していること (./scripts/dev-start.sh または make dev-all)
- .env に必要なAPIキーが設定されていること
- USE_JOB_GENERATOR_V2=true が設定されていること（V2テスト時）

実行方法:
  cd expertAgent
  uv run pytest tests/acceptance/test_issue_342_acceptance.py -v

受入条件:
1. V2 アーキテクチャが正しく動作すること
2. フェーズ間のデータフローが正しいこと
3. リトライ上限が機能し、無限ループが発生しないこと
4. Feature flag による V1/V2 切り替えが機能すること
5. エラー時の適切なリカバリ処理
"""

import os

import pytest
import requests


@pytest.mark.acceptance
class TestIssue342Acceptance:
    """Issue #342: Job/Task Generator Agent アーキテクチャ刷新"""

    # サービスURL
    EXPERT_AGENT_URL = "http://localhost:8004"
    MYVAULT_URL = "http://localhost:8003"
    JOBQUEUE_URL = "http://localhost:8001"
    GRAPHAI_SERVER_URL = "http://localhost:8005"

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
                    pytest.skip(
                        f"{name} is not healthy (status: {response.status_code})"
                    )
            except requests.exceptions.ConnectionError:
                pytest.skip(
                    f"{name} is not running at {url}. "
                    "Run: ./scripts/dev-start.sh or make dev-all"
                )

    # ==========================================================================
    # 受入条件1: V2 アーキテクチャが正しく動作すること
    # ==========================================================================

    def test_v2_adapter_exists_and_importable(self) -> None:
        """V2アダプターが存在しインポート可能であること

        受入条件1: V2アーキテクチャの基本構造
        検証方法: アダプタークラスがインポートできることを確認
        """
        # Act & Assert
        from aiagent.langgraph.jobGeneratorV2 import JobGeneratorV2Adapter

        assert JobGeneratorV2Adapter is not None

    def test_v2_orchestrator_has_all_phases(self) -> None:
        """V2オーケストレーターが全4フェーズを持つこと

        受入条件1: V2アーキテクチャの完全性
        検証方法: オーケストレーターが全フェーズを持つことを確認
        """
        # Arrange
        from aiagent.langgraph.jobGeneratorV2 import (
            ErrorRecoveryManager,
            JobGenerationOrchestrator,
            Phase,
        )

        # Act
        recovery_manager = ErrorRecoveryManager()
        orchestrator = JobGenerationOrchestrator(recovery_manager=recovery_manager)
        phase_order = orchestrator.get_phase_order()

        # Assert
        assert len(phase_order) == 4
        assert Phase.TASK_BREAKDOWN in phase_order
        assert Phase.INTERFACE_DESIGN in phase_order
        assert Phase.REGISTRATION in phase_order
        assert Phase.WORKFLOW_GEN in phase_order

    def test_v2_adapter_creates_all_workflows(self) -> None:
        """V2アダプターが全ワークフローを作成すること

        受入条件1: V2アーキテクチャの完全性
        検証方法: アダプターが全ワークフローを登録することを確認
        """
        # Arrange
        from aiagent.langgraph.jobGeneratorV2 import JobGeneratorV2Adapter, Phase

        # Act
        adapter = JobGeneratorV2Adapter(max_retry=5)

        # Assert
        for phase in Phase:
            workflow = adapter._orchestrator.get_workflow(phase)
            assert workflow is not None, f"Workflow for {phase.value} should exist"

    # ==========================================================================
    # 受入条件2: フェーズ間のデータフローが正しいこと
    # ==========================================================================

    def test_phase_execution_order(self) -> None:
        """フェーズが正しい順序で実行されること

        受入条件2: フェーズ間データフロー
        検証方法: フェーズ順序が正しいことを確認
        """
        # Arrange
        from aiagent.langgraph.jobGeneratorV2 import (
            ErrorRecoveryManager,
            JobGenerationOrchestrator,
            Phase,
        )

        recovery_manager = ErrorRecoveryManager()
        orchestrator = JobGenerationOrchestrator(recovery_manager=recovery_manager)

        # Act
        order = orchestrator.get_phase_order()

        # Assert: 正しい順序
        assert order[0] == Phase.TASK_BREAKDOWN
        assert order[1] == Phase.INTERFACE_DESIGN
        assert order[2] == Phase.REGISTRATION
        assert order[3] == Phase.WORKFLOW_GEN

    def test_next_phase_transitions(self) -> None:
        """フェーズ遷移が正しく定義されていること

        受入条件2: フェーズ間データフロー
        検証方法: 次フェーズの取得が正しいことを確認
        """
        # Arrange
        from aiagent.langgraph.jobGeneratorV2 import (
            ErrorRecoveryManager,
            JobGenerationOrchestrator,
            Phase,
        )

        recovery_manager = ErrorRecoveryManager()
        orchestrator = JobGenerationOrchestrator(recovery_manager=recovery_manager)

        # Act & Assert
        assert orchestrator.get_next_phase(Phase.TASK_BREAKDOWN) == Phase.INTERFACE_DESIGN
        assert orchestrator.get_next_phase(Phase.INTERFACE_DESIGN) == Phase.REGISTRATION
        assert orchestrator.get_next_phase(Phase.REGISTRATION) == Phase.WORKFLOW_GEN
        assert orchestrator.get_next_phase(Phase.WORKFLOW_GEN) is None

    # ==========================================================================
    # 受入条件3: リトライ上限が機能し、無限ループが発生しないこと
    # ==========================================================================

    def test_retry_state_per_phase(self) -> None:
        """各フェーズがリトライ状態を持つこと

        受入条件3: リトライ上限
        検証方法: フェーズごとにリトライ状態が分離されていることを確認
        """
        # Arrange
        from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        context = ExecutionContext(
            job_id="test-job",
            user_requirement="Test",
            max_phase_retries=3,
        )

        # Act
        context.record_retry(Phase.TASK_BREAKDOWN, "Error 1")
        context.record_retry(Phase.TASK_BREAKDOWN, "Error 2")
        context.record_retry(Phase.INTERFACE_DESIGN, "Error 3")

        # Assert: フェーズごとに分離
        assert context.get_phase_retry_state(Phase.TASK_BREAKDOWN).count == 2
        assert context.get_phase_retry_state(Phase.INTERFACE_DESIGN).count == 1
        assert context.get_phase_retry_state(Phase.REGISTRATION).count == 0

    def test_retry_limit_per_phase(self) -> None:
        """フェーズごとのリトライ上限が機能すること

        受入条件3: リトライ上限
        検証方法: 上限到達後にリトライ不可になることを確認
        """
        # Arrange
        from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        context = ExecutionContext(
            job_id="test-job",
            user_requirement="Test",
            max_phase_retries=2,
        )

        # Act: 上限までリトライを記録
        context.record_retry(Phase.TASK_BREAKDOWN, "Error 1")
        context.record_retry(Phase.TASK_BREAKDOWN, "Error 2")

        # Assert: 上限到達
        assert context.can_retry(Phase.TASK_BREAKDOWN) is False
        # 他のフェーズはまだリトライ可能
        assert context.can_retry(Phase.INTERFACE_DESIGN) is True

    def test_total_retry_limit(self) -> None:
        """総リトライ上限が機能すること

        受入条件3: リトライ上限
        検証方法: 総上限到達後に全フェーズでリトライ不可になることを確認
        """
        # Arrange
        from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        context = ExecutionContext(
            job_id="test-job",
            user_requirement="Test",
            max_total_retries=3,
            max_phase_retries=5,  # フェーズ上限より総上限が先に到達
        )

        # Act: 複数フェーズでリトライを記録
        context.record_retry(Phase.TASK_BREAKDOWN, "Error 1")
        context.record_retry(Phase.INTERFACE_DESIGN, "Error 2")
        context.record_retry(Phase.REGISTRATION, "Error 3")

        # Assert: 総上限到達
        assert context.total_retry_count() == 3
        assert context.can_retry_any() is False
        # 全フェーズでリトライ不可
        for phase in Phase:
            assert context.can_retry(phase) is False

    # ==========================================================================
    # 受入条件4: Feature flag による V1/V2 切り替えが機能すること
    # ==========================================================================

    def test_feature_flag_exists(self) -> None:
        """Feature flag が存在すること

        受入条件4: V1/V2切り替え
        検証方法: 設定とフラグ関数が存在することを確認
        """
        # Arrange & Act
        from core.config import settings
        from core.feature_flags import use_job_generator_v2

        # Assert
        assert hasattr(settings, "USE_JOB_GENERATOR_V2")
        assert callable(use_job_generator_v2)

    def test_feature_flag_default_false(self) -> None:
        """Feature flag のデフォルトが False であること

        受入条件4: V1/V2切り替え（後方互換性）
        検証方法: 環境変数未設定時にFalseを返すことを確認
        """
        # Note: このテストは環境変数が設定されている場合はスキップ
        if os.getenv("USE_JOB_GENERATOR_V2"):
            pytest.skip("USE_JOB_GENERATOR_V2 is set in environment")

        # Arrange & Act
        from core.feature_flags import use_job_generator_v2

        # Assert: デフォルトはFalse（V1を使用）
        result = use_job_generator_v2()
        assert result is False

    def test_feature_flag_returns_bool(self) -> None:
        """Feature flag が boolean を返すこと

        受入条件4: V1/V2切り替え
        検証方法: 関数が常にboolを返すことを確認
        """
        # Arrange & Act
        from core.feature_flags import use_job_generator_v2

        result = use_job_generator_v2()

        # Assert
        assert isinstance(result, bool)

    # ==========================================================================
    # 受入条件5: エラー時の適切なリカバリ処理
    # ==========================================================================

    def test_error_recovery_manager_exists(self) -> None:
        """ErrorRecoveryManager が存在すること

        受入条件5: エラーリカバリ
        検証方法: リカバリマネージャーがインポートできることを確認
        """
        # Act & Assert
        from aiagent.langgraph.jobGeneratorV2 import ErrorRecoveryManager

        manager = ErrorRecoveryManager()
        assert manager is not None

    def test_error_recovery_strategies(self) -> None:
        """エラーリカバリ戦略が定義されていること

        受入条件5: エラーリカバリ
        検証方法: 各戦略が定義されていることを確認
        """
        # Arrange & Act
        from aiagent.langgraph.jobGeneratorV2 import ErrorRecoveryStrategy

        # Assert: 必要な戦略が存在
        assert hasattr(ErrorRecoveryStrategy, "RETRY_CURRENT")
        assert hasattr(ErrorRecoveryStrategy, "ROLLBACK_ONE")
        assert hasattr(ErrorRecoveryStrategy, "FAIL_FAST")
        assert hasattr(ErrorRecoveryStrategy, "RELAXATION")

    def test_workflow_error_types(self) -> None:
        """WorkflowError タイプが定義されていること

        受入条件5: エラーリカバリ
        検証方法: 各エラータイプが定義されていることを確認
        """
        # Arrange & Act
        from aiagent.langgraph.jobGeneratorV2 import ErrorType

        # Assert: 必要なエラータイプが存在
        assert hasattr(ErrorType, "TRANSIENT")
        assert hasattr(ErrorType, "VALIDATION")
        assert hasattr(ErrorType, "BUSINESS_CONSTRAINT")
        assert hasattr(ErrorType, "FATAL")

    # ==========================================================================
    # 統合テスト: E2E確認
    # ==========================================================================

    def test_health_check_all_services(self) -> None:
        """すべての関連サービスがヘルスチェックに応答する

        E2E確認: サービス起動確認
        """
        # expertAgent
        response = requests.get(f"{self.EXPERT_AGENT_URL}/health", timeout=10)
        assert response.status_code == 200

        # myVault
        response = requests.get(f"{self.MYVAULT_URL}/health", timeout=10)
        assert response.status_code == 200

    def test_v2_adapter_response_conversion(self) -> None:
        """V2アダプターがレスポンスを正しく変換すること

        E2E確認: レスポンス変換
        検証方法: 成功・失敗の両ケースで変換が正しいことを確認
        """
        # Arrange
        from aiagent.langgraph.jobGeneratorV2 import JobGeneratorV2Adapter
        from aiagent.langgraph.jobGeneratorV2.types import (
            JobGenerationResult,
            RelaxationSuggestion,
        )

        adapter = JobGeneratorV2Adapter(max_retry=5)

        # Test 1: 成功ケース
        success_result = JobGenerationResult(
            success=True,
            job_id="job_123",
            job_master_id="jm_123",
            task_master_ids=["tm_001"],
            workflow_yaml="version: 0.6",
        )
        success_response = adapter._convert_result(success_result, "job_123")

        assert success_response.status == "success"
        assert success_response.job_id == "job_123"
        assert success_response.error_message is None

        # Test 2: 失敗ケース
        failure_result = JobGenerationResult(
            success=False,
            error="Requirements could not be satisfied",
        )
        failure_response = adapter._convert_result(failure_result, "job_456")

        assert failure_response.status == "failed"
        assert failure_response.error_message == "Requirements could not be satisfied"

        # Test 3: 緩和提案付き失敗ケース
        partial_result = JobGenerationResult(
            success=False,
            relaxation_suggestions=[
                RelaxationSuggestion(
                    original_requirement="Send emails automatically",
                    suggested_alternative="Create email drafts",
                    reason="Full automation not supported",
                )
            ],
        )
        partial_response = adapter._convert_result(partial_result, "job_789")

        assert partial_response.status == "partial_success"
        assert len(partial_response.requirement_relaxation_suggestions) == 1

    def test_job_generator_endpoint_exists(self) -> None:
        """Job Generator APIエンドポイントが存在すること

        E2E確認: API存在確認
        検証方法: エンドポイントが404ではないことを確認
        Note: 実際のジョブ生成テストはAPIキーが必要
        """
        # Note: POST without body will fail validation, but endpoint exists
        endpoint = f"{self.EXPERT_AGENT_URL}/aiagent-api/v1/job-generator"

        # Check endpoint exists (method not allowed or validation error, not 404)
        try:
            response = requests.options(endpoint, timeout=5)
            # Any response other than connection error means endpoint exists
            assert response.status_code != 404
        except requests.exceptions.RequestException:
            # If CORS not configured, try GET (should return 405 Method Not Allowed)
            response = requests.get(endpoint, timeout=5)
            assert response.status_code in [405, 422, 200]


@pytest.mark.acceptance
class TestIssue342V2EndToEnd:
    """Issue #342: V2 E2Eテスト（V2有効時のみ実行）"""

    EXPERT_AGENT_URL = "http://localhost:8004"

    @pytest.fixture(autouse=True)
    def skip_if_v2_disabled(self) -> None:
        """V2が無効の場合はスキップ"""
        from core.feature_flags import use_job_generator_v2

        if not use_job_generator_v2():
            pytest.skip("USE_JOB_GENERATOR_V2 is not enabled")

    @pytest.fixture(autouse=True)
    def check_services_running(self) -> None:
        """サービス起動確認"""
        try:
            response = requests.get(f"{self.EXPERT_AGENT_URL}/health", timeout=5)
            if response.status_code != 200:
                pytest.skip("expertAgent is not healthy")
        except requests.exceptions.ConnectionError:
            pytest.skip("expertAgent is not running")

    def test_v2_job_generation_simple_requirement(self) -> None:
        """V2で簡単な要求からジョブ生成できること

        受入条件1,2: V2アーキテクチャとデータフロー
        検証方法: 実際のAPI呼び出しでジョブ生成を確認
        Note: このテストは USE_JOB_GENERATOR_V2=true 時のみ実行
        """
        # Arrange
        endpoint = f"{self.EXPERT_AGENT_URL}/aiagent-api/v1/job-generator"
        payload = {
            "user_requirement": "テストメールを送信する",
            "max_retry": 2,  # 低い値でテスト高速化
        }

        # Act
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )

        # Assert: APIが応答すること
        assert response.status_code in [200, 202], (
            f"Expected 200/202, got {response.status_code}. "
            f"Response: {response.text[:500]}"
        )

        data = response.json()
        # status フィールドが存在すること
        assert "status" in data, f"Response should have 'status' field: {data}"
        # job_id が返されること（async の場合は creating 状態で返される）
        assert "job_id" in data or data.get("status") == "creating", (
            f"Response should have 'job_id': {data}"
        )
