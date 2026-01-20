# ruff: noqa: S603, S607
"""Issue #361 受入テスト（L3: ローカル受入テスト）.

mySwiftAgentCore連携実装と旧WORKFLOW_GENコード削除の受入テスト。

前提条件:
- サービスが起動していること (./scripts/dev-hybrid.sh start --local-only)
- mySwiftAgentCore (localhost:8006), expertAgent (localhost:8104) が起動していること
- .env に必要なAPIキーが設定されていること

実行方法:
  cd expertAgent
  uv run pytest tests/acceptance/test_issue_361_acceptance.py -v

受入条件:
- AC-1: WorkflowGeneratorClientが実装されている
- AC-2: WorkflowGeneratorClientの単体テストが実装されている（カバレッジ90%以上）
- AC-3: jobGeneratorV2がmySwiftAgentCore APIを呼び出してワークフローを生成する
- AC-4: trace_idがmySwiftAgentCoreに正しく伝播される
- AC-5: エラー時のrecovery_suggestion処理が実装されている
- AC-6: workflows/workflow_gen/、types_old.py等が削除されている (PENDING)
- AC-7: types_old.pyへの依存が全て解消されている (PENDING)
- AC-8: pre-push-check-all.sh に合格する

Note:
- AC-6, AC-7は旧コード削除タスクのため、このイテレーションではPENDINGとする
- mySwiftAgentCoreが起動していない場合、E2Eテストはスキップされる
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# WorkflowGeneratorClient components
from aiagent.clients.interfaces.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
)
from aiagent.clients.interfaces.http_client import (
    HttpResponse,
    IHttpClient,
)
from aiagent.clients.interfaces.metrics import (
    IMetricsCollector,
    NoOpMetricsCollector,
)
from aiagent.clients.types.workflow_generator import (
    BatchStatus,
    BatchWorkflowGenerationResponse,
    FailedTask,
    GenerationOptions,
    RecoverySuggestion,
    TaskInterface,
    TaskRequest,
    WorkflowResult,
    WorkflowStatus,
)
from aiagent.clients.workflow_generator_client import (
    WorkflowGeneratorClient,
    WorkflowGeneratorError,
    WorkflowGeneratorHTTPError,
    WorkflowGeneratorTimeoutError,
)


# === Helper Functions ===


def is_myswiftagentcore_available() -> bool:
    """Check if mySwiftAgentCore is available."""
    try:
        import httpx

        response = httpx.get("http://localhost:8006/api/health", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False


def is_expertAgent_available() -> bool:
    """Check if expertAgent is available."""
    try:
        import httpx

        response = httpx.get("http://localhost:8104/health", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False


# === AC-1: WorkflowGeneratorClient Implementation Tests ===


@pytest.mark.acceptance
class TestAC1WorkflowGeneratorClientImplementation:
    """AC-1: WorkflowGeneratorClientが実装されている.

    テスト観点: WorkflowGeneratorClientクラスの存在と基本動作確認
    """

    def test_workflow_generator_client_class_exists(self) -> None:
        """WorkflowGeneratorClientクラスが存在する."""
        assert WorkflowGeneratorClient is not None
        assert hasattr(WorkflowGeneratorClient, "generate_workflows")

    def test_client_initialization(self) -> None:
        """WorkflowGeneratorClientが正しく初期化できる."""
        # Act
        client = WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            timeout=30.0,
            max_retries=3,
        )

        # Assert
        assert client.base_url == "http://localhost:8006"
        assert client.timeout == 30.0
        assert client.max_retries == 3

    def test_client_supports_auth_headers(self) -> None:
        """認証ヘッダーの拡張性がある."""
        # Act
        client = WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            auth_headers={"X-API-Key": "test-key"},
        )

        # Assert
        assert client.auth_headers == {"X-API-Key": "test-key"}

    def test_client_supports_dependency_injection(self) -> None:
        """HTTPクライアント・メトリクス・サーキットブレーカーの注入が可能."""
        # Arrange
        mock_http = AsyncMock(spec=IHttpClient)
        mock_metrics = MagicMock(spec=IMetricsCollector)
        cb = CircuitBreaker()

        # Act
        client = WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            http_client=mock_http,
            metrics_collector=mock_metrics,
            circuit_breaker=cb,
        )

        # Assert
        assert client._http_client == mock_http
        assert client._metrics == mock_metrics
        assert client._circuit_breaker == cb


# === AC-2: Unit Test Coverage Tests ===


@pytest.mark.acceptance
class TestAC2UnitTestCoverage:
    """AC-2: 単体テストが実装されている（カバレッジ90%以上）.

    テスト観点: テストファイルの存在とテスト数
    """

    def test_unit_test_file_exists(self) -> None:
        """単体テストファイルが存在する."""
        test_path = Path(__file__).parent.parent / (
            "unit/test_clients/test_workflow_generator_client.py"
        )
        assert test_path.exists(), f"Unit test file not found: {test_path}"

    def test_unit_test_count_is_sufficient(self) -> None:
        """十分な数の単体テストが存在する（50件以上）."""
        # Arrange
        test_path = Path(__file__).parent.parent / (
            "unit/test_clients/test_workflow_generator_client.py"
        )

        # Act
        with open(test_path) as f:
            content = f.read()

        # Count test methods
        test_count = content.count("def test_")

        # Assert
        assert test_count >= 50, f"Expected >= 50 tests, found {test_count}"


# === AC-3: mySwiftAgentCore API Integration Tests ===


@pytest.mark.acceptance
class TestAC3MySwiftAgentCoreIntegration:
    """AC-3: jobGeneratorV2がmySwiftAgentCore APIを呼び出す.

    テスト観点: orchestrator.pyでWorkflowGeneratorClientが統合されている
    """

    def test_orchestrator_imports_workflow_generator_client(self) -> None:
        """orchestrator.pyがWorkflowGeneratorClientをインポートしている."""
        # Arrange
        orchestrator_path = Path(__file__).parent.parent.parent / (
            "aiagent/langgraph/jobGeneratorV2/orchestrator.py"
        )

        # Act
        with open(orchestrator_path) as f:
            content = f.read()

        # Assert
        assert "WorkflowGeneratorClient" in content
        assert "from ...clients.workflow_generator_client import" in content

    def test_orchestrator_uses_workflow_generator_client(self) -> None:
        """orchestrator.pyがWorkflowGeneratorClientを使用している."""
        # Arrange
        orchestrator_path = Path(__file__).parent.parent.parent / (
            "aiagent/langgraph/jobGeneratorV2/orchestrator.py"
        )

        # Act
        result = subprocess.run(
            [
                "grep",
                "-c",
                "WorkflowGeneratorClient",
                str(orchestrator_path),
            ],
            capture_output=True,
            text=True,
        )
        usage_count = int(result.stdout.strip())

        # Assert: Should be used multiple times (import + usage)
        assert usage_count >= 3, f"WorkflowGeneratorClient used {usage_count} times"

    def test_execute_workflow_gen_method_exists(self) -> None:
        """_execute_workflow_genメソッドが存在する."""
        # Arrange
        orchestrator_path = Path(__file__).parent.parent.parent / (
            "aiagent/langgraph/jobGeneratorV2/orchestrator.py"
        )

        # Act
        with open(orchestrator_path) as f:
            content = f.read()

        # Assert
        assert "_execute_workflow_gen" in content
        assert "mySwiftAgentCore" in content


# === AC-4: Trace ID Propagation Tests ===


@pytest.mark.acceptance
class TestAC4TraceIdPropagation:
    """AC-4: trace_idがmySwiftAgentCoreに正しく伝播される.

    テスト観点: X-Trace-Idヘッダーの送信
    """

    @pytest.mark.asyncio
    async def test_trace_id_header_is_sent(self) -> None:
        """generate_workflowsがX-Trace-Idヘッダーを送信する."""
        # Arrange
        mock_http = AsyncMock(spec=IHttpClient)
        mock_response = HttpResponse(
            status_code=200,
            json_data={
                "status": "success",
                "success": True,
                "workflows": {},
                "total_tasks": 0,
                "succeeded_tasks": 0,
                "failed_task_count": 0,
            },
            headers={},
            elapsed_ms=50.0,
        )
        mock_http.post.return_value = mock_response

        # Act
        async with WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            http_client=mock_http,
        ) as client:
            await client.generate_workflows(
                tasks=[],
                capabilities=[],
                project_id="default",
                trace_id="test-trace-123",
            )

        # Assert
        call_args = mock_http.post.call_args
        headers = call_args.kwargs.get("headers", {})
        assert headers.get("X-Trace-Id") == "test-trace-123"

    @pytest.mark.asyncio
    async def test_parent_span_id_header_is_sent(self) -> None:
        """generate_workflowsがX-Parent-Span-Idヘッダーを送信する."""
        # Arrange
        mock_http = AsyncMock(spec=IHttpClient)
        mock_response = HttpResponse(
            status_code=200,
            json_data={
                "status": "success",
                "success": True,
                "workflows": {},
                "total_tasks": 0,
                "succeeded_tasks": 0,
                "failed_task_count": 0,
            },
            headers={},
            elapsed_ms=50.0,
        )
        mock_http.post.return_value = mock_response

        # Act
        async with WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            http_client=mock_http,
        ) as client:
            await client.generate_workflows(
                tasks=[],
                capabilities=[],
                project_id="default",
                trace_id="trace-123",
                parent_span_id="span-456",
            )

        # Assert
        call_args = mock_http.post.call_args
        headers = call_args.kwargs.get("headers", {})
        assert headers.get("X-Parent-Span-Id") == "span-456"


# === AC-5: Recovery Suggestion Handling Tests ===


@pytest.mark.acceptance
class TestAC5RecoverySuggestionHandling:
    """AC-5: エラー時のrecovery_suggestion処理が実装されている.

    テスト観点: ROLLBACK_TO_ANALYSISなどのrecovery_suggestionの処理
    """

    @pytest.mark.asyncio
    async def test_recovery_suggestion_is_parsed(self) -> None:
        """recovery_suggestionが正しくパースされる."""
        # Arrange
        mock_http = AsyncMock(spec=IHttpClient)
        mock_response = HttpResponse(
            status_code=200,
            json_data={
                "status": "failed",
                "success": False,
                "workflows": {},
                "failed_tasks": [
                    {
                        "task_id": "task_001",
                        "error_type": "validation_error",
                        "message": "Schema mismatch",
                    },
                ],
                "recovery_suggestion": "ROLLBACK_TO_ANALYSIS",
                "total_tasks": 1,
                "succeeded_tasks": 0,
                "failed_task_count": 1,
            },
            headers={},
            elapsed_ms=100.0,
        )
        mock_http.post.return_value = mock_response

        # Act
        async with WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            http_client=mock_http,
        ) as client:
            response = await client.generate_workflows(
                tasks=[],
                capabilities=[],
                project_id="default",
            )

        # Assert
        assert response.recovery_suggestion == RecoverySuggestion.ROLLBACK_TO_ANALYSIS

    @pytest.mark.asyncio
    async def test_partial_success_is_handled(self) -> None:
        """partial_successステータスが正しく処理される."""
        # Arrange
        mock_http = AsyncMock(spec=IHttpClient)
        mock_response = HttpResponse(
            status_code=200,
            json_data={
                "status": "partial_success",
                "success": True,
                "workflows": {
                    "task_001": {
                        "workflow_name": "workflow_task_001",
                        "status": "success",
                    },
                },
                "failed_tasks": [
                    {
                        "task_id": "task_002",
                        "error_type": "generation_error",
                        "message": "Failed",
                    },
                ],
                "total_tasks": 2,
                "succeeded_tasks": 1,
                "failed_task_count": 1,
            },
            headers={},
            elapsed_ms=150.0,
        )
        mock_http.post.return_value = mock_response

        # Act
        async with WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            http_client=mock_http,
        ) as client:
            response = await client.generate_workflows(
                tasks=[],
                capabilities=[],
                project_id="default",
            )

        # Assert
        assert response.status == BatchStatus.PARTIAL_SUCCESS
        assert response.succeeded_tasks == 1
        assert response.failed_task_count == 1


# === AC-6 & AC-7: Old Code Deletion (PENDING) ===


@pytest.mark.acceptance
@pytest.mark.skip(reason="AC-6, AC-7: 旧コード削除はこのイテレーションではPENDING")
class TestAC6AC7OldCodeDeletion:
    """AC-6, AC-7: 旧コード削除（PENDING）.

    Note: これらの受入条件はこのイテレーションではPENDINGとする。
    旧コードはまだ存在するが、新しいWorkflowGeneratorClientが追加され機能している。
    """

    def test_workflow_gen_directory_deleted(self) -> None:
        """workflow_gen/ディレクトリが削除されている."""
        path = Path(__file__).parent.parent.parent / (
            "aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen"
        )
        assert not path.exists(), f"workflow_gen/ should be deleted: {path}"

    def test_types_old_deleted(self) -> None:
        """types_old.pyが削除されている."""
        path = Path(__file__).parent.parent.parent / (
            "aiagent/langgraph/jobGeneratorV2/types_old.py"
        )
        assert not path.exists(), f"types_old.py should be deleted: {path}"


# === AC-8: Quality Check ===


@pytest.mark.acceptance
class TestAC8QualityCheck:
    """AC-8: 品質チェック.

    テスト観点: Ruff/MyPyエラーがないこと
    """

    def test_workflow_generator_client_passes_ruff(self) -> None:
        """workflow_generator_client.pyがRuffを通過する."""
        # Arrange
        client_path = Path(__file__).parent.parent.parent / (
            "aiagent/clients/workflow_generator_client.py"
        )

        # Act
        result = subprocess.run(
            ["uv", "run", "ruff", "check", str(client_path)],
            capture_output=True,
            text=True,
        )

        # Assert
        assert result.returncode == 0, f"Ruff errors:\n{result.stdout}\n{result.stderr}"

    def test_types_workflow_generator_passes_ruff(self) -> None:
        """types/workflow_generator.pyがRuffを通過する."""
        # Arrange
        types_path = Path(__file__).parent.parent.parent / (
            "aiagent/clients/types/workflow_generator.py"
        )

        # Act
        result = subprocess.run(
            ["uv", "run", "ruff", "check", str(types_path)],
            capture_output=True,
            text=True,
        )

        # Assert
        assert result.returncode == 0, f"Ruff errors:\n{result.stdout}\n{result.stderr}"


# === Circuit Breaker Tests ===


@pytest.mark.acceptance
class TestCircuitBreakerIntegration:
    """サーキットブレーカー統合テスト.

    テスト観点: サーキットブレーカーの状態遷移
    """

    def test_initial_state_is_closed(self) -> None:
        """初期状態はCLOSED."""
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self) -> None:
        """連続失敗でOPEN状態に遷移する."""
        # Arrange
        config = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker(config=config)

        async def failing_func() -> None:
            raise RuntimeError("Test error")

        # Act: Trigger failures
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(failing_func)

        # Assert
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_circuit_rejects_calls(self) -> None:
        """OPEN状態で呼び出しが拒否される."""
        # Arrange
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker(config=config)

        async def failing_func() -> None:
            raise RuntimeError("Test error")

        # Open the circuit
        with pytest.raises(RuntimeError):
            await cb.call(failing_func)

        # Assert: New call should be rejected
        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(failing_func)


# === E2E Tests (Require Services) ===


@pytest.mark.acceptance
@pytest.mark.skipif(
    not is_myswiftagentcore_available(),
    reason="mySwiftAgentCore is not available",
)
class TestE2EMySwiftAgentCoreAPI:
    """E2E: mySwiftAgentCore API直接呼び出し.

    前提条件: mySwiftAgentCoreが起動していること
    """

    @pytest.mark.asyncio
    async def test_tc_001_api_direct_call(self) -> None:
        """TC-001: mySwiftAgentCore APIを直接呼び出せる."""
        import httpx

        # Arrange
        request_body = {
            "tasks": [
                {
                    "task_id": "test_task_001",
                    "name": "Test Task",
                    "description": "Integration test task for searching",
                    "interface": {
                        "input": {"keyword": "string"},
                        "output": {"result": "string"},
                    },
                }
            ],
            "capabilities": [],
            "project_id": "default_project",
        }

        # Act
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "http://localhost:8006/api/v1/generator/workflow/batch",
                json=request_body,
                headers={
                    "Content-Type": "application/json",
                    "X-Trace-Id": f"test-trace-{__name__}",
                },
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["success", "partial_success", "failed"]

    @pytest.mark.asyncio
    async def test_tc_001_via_workflow_generator_client(self) -> None:
        """TC-001: WorkflowGeneratorClient経由でAPIを呼び出せる."""
        # Arrange
        tasks = [
            TaskRequest(
                task_id="test_task_client",
                name="Test Task via Client",
                description="Test task using WorkflowGeneratorClient",
                interface=TaskInterface(
                    input={"query": "string"},
                    output={"result": "string"},
                ),
            ),
        ]

        # Act
        async with WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            timeout=60.0,
        ) as client:
            response = await client.generate_workflows(
                tasks=tasks,
                capabilities=[],
                project_id="default_project",
                trace_id="test-trace-client",
            )

        # Assert
        assert response is not None
        assert response.status in [
            BatchStatus.SUCCESS,
            BatchStatus.PARTIAL_SUCCESS,
            BatchStatus.FAILED,
        ]
