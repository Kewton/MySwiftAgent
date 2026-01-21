"""Unit tests for WorkflowGeneratorClient.

Issue #361: Tests for mySwiftAgentCore workflow generation API client.

These tests verify:
- AC-1: WorkflowGeneratorClient implementation
- AC-2: Unit test coverage 90%+
- AC-4: trace_id propagation to mySwiftAgentCore
- AC-5: Error recovery_suggestion handling
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiagent.clients.interfaces.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
)
from aiagent.clients.interfaces.http_client import (
    HttpResponse,
    HttpxClientAdapter,
    IHttpClient,
)
from aiagent.clients.interfaces.metrics import (
    IMetricsCollector,
    LoggingMetricsCollector,
    NoOpMetricsCollector,
    RequestMetrics,
)
from aiagent.clients.types.workflow_generator import (
    BatchStatus,
    BatchWorkflowGenerationResponse,
    FailedTask,
    GenerationOptions,
    RecoverySuggestion,
    TaskInterface,
    TaskRequest,
    TraceContext,
    WorkflowResult,
    WorkflowStatus,
)
from aiagent.clients.workflow_generator_client import (
    WorkflowGeneratorClient,
    WorkflowGeneratorError,
    WorkflowGeneratorHTTPError,
    WorkflowGeneratorTimeoutError,
    WorkflowGeneratorValidationError,
)


class TestBatchStatus:
    """Tests for BatchStatus enum."""

    def test_batch_status_values(self):
        """Test BatchStatus enum has correct values."""
        assert BatchStatus.SUCCESS.value == "success"
        assert BatchStatus.PARTIAL_SUCCESS.value == "partial_success"
        assert BatchStatus.FAILED.value == "failed"

    def test_batch_status_from_string(self):
        """Test BatchStatus can be created from string."""
        assert BatchStatus("success") == BatchStatus.SUCCESS
        assert BatchStatus("partial_success") == BatchStatus.PARTIAL_SUCCESS
        assert BatchStatus("failed") == BatchStatus.FAILED


class TestWorkflowStatus:
    """Tests for WorkflowStatus enum."""

    def test_workflow_status_values(self):
        """Test WorkflowStatus enum has correct values."""
        assert WorkflowStatus.SUCCESS.value == "success"
        assert WorkflowStatus.FAILED.value == "failed"


class TestRecoverySuggestion:
    """Tests for RecoverySuggestion enum."""

    def test_recovery_suggestion_values(self):
        """Test RecoverySuggestion enum has correct values."""
        assert RecoverySuggestion.ROLLBACK_TO_ANALYSIS.value == "ROLLBACK_TO_ANALYSIS"
        assert RecoverySuggestion.RELAXATION.value == "RELAXATION"


class TestTaskInterface:
    """Tests for TaskInterface dataclass."""

    def test_task_interface_creation(self):
        """Test TaskInterface can be created."""
        interface = TaskInterface(
            input={"query": "string"},
            output={"results": "array"},
        )
        assert interface.input == {"query": "string"}
        assert interface.output == {"results": "array"}


class TestTaskRequest:
    """Tests for TaskRequest dataclass."""

    def test_task_request_creation(self):
        """Test TaskRequest can be created."""
        request = TaskRequest(
            task_id="task_001",
            name="Search Gmail",
            description="Search for emails",
            interface=TaskInterface(
                input={"query": "string"},
                output={"emails": "array"},
            ),
        )
        assert request.task_id == "task_001"
        assert request.name == "Search Gmail"
        assert request.description == "Search for emails"
        assert request.interface.input == {"query": "string"}


class TestTraceContext:
    """Tests for TraceContext dataclass."""

    def test_trace_context_creation(self):
        """Test TraceContext with trace_id only."""
        ctx = TraceContext(trace_id="trace-123")
        assert ctx.trace_id == "trace-123"
        assert ctx.parent_span_id is None

    def test_trace_context_with_parent_span(self):
        """Test TraceContext with parent_span_id."""
        ctx = TraceContext(trace_id="trace-123", parent_span_id="span-456")
        assert ctx.trace_id == "trace-123"
        assert ctx.parent_span_id == "span-456"


class TestGenerationOptions:
    """Tests for GenerationOptions dataclass."""

    def test_generation_options_defaults(self):
        """Test GenerationOptions default values."""
        opts = GenerationOptions()
        assert opts.max_concurrency == 10
        assert opts.timeout_per_task_ms == 180000
        assert opts.validate_before_register is True

    def test_generation_options_custom(self):
        """Test GenerationOptions with custom values."""
        opts = GenerationOptions(
            max_concurrency=5,
            timeout_per_task_ms=60000,
            validate_before_register=False,
        )
        assert opts.max_concurrency == 5
        assert opts.timeout_per_task_ms == 60000
        assert opts.validate_before_register is False


class TestWorkflowResult:
    """Tests for WorkflowResult dataclass."""

    def test_workflow_result_success(self):
        """Test WorkflowResult for successful workflow."""
        result = WorkflowResult(
            workflow_name="workflow_task_001",
            status=WorkflowStatus.SUCCESS,
        )
        assert result.workflow_name == "workflow_task_001"
        assert result.status == WorkflowStatus.SUCCESS
        assert result.error is None

    def test_workflow_result_failed(self):
        """Test WorkflowResult for failed workflow."""
        result = WorkflowResult(
            workflow_name="workflow_task_001",
            status=WorkflowStatus.FAILED,
            error="Validation failed",
        )
        assert result.status == WorkflowStatus.FAILED
        assert result.error == "Validation failed"


class TestFailedTask:
    """Tests for FailedTask dataclass."""

    def test_failed_task_creation(self):
        """Test FailedTask creation."""
        task = FailedTask(
            task_id="task_001",
            error_type="validation_error",
            message="Schema validation failed",
        )
        assert task.task_id == "task_001"
        assert task.error_type == "validation_error"
        assert task.message == "Schema validation failed"


class TestBatchWorkflowGenerationResponse:
    """Tests for BatchWorkflowGenerationResponse dataclass."""

    def test_response_success(self):
        """Test BatchWorkflowGenerationResponse for full success."""
        workflows = {
            "task_001": WorkflowResult(
                workflow_name="workflow_task_001",
                status=WorkflowStatus.SUCCESS,
            ),
            "task_002": WorkflowResult(
                workflow_name="workflow_task_002",
                status=WorkflowStatus.SUCCESS,
            ),
        }
        response = BatchWorkflowGenerationResponse.from_results(workflows=workflows)

        assert response.status == BatchStatus.SUCCESS
        assert response.success is True
        assert response.total_tasks == 2
        assert response.succeeded_tasks == 2
        assert response.failed_task_count == 0
        assert response.recovery_suggestion is None

    def test_response_partial_success(self):
        """Test BatchWorkflowGenerationResponse for partial success."""
        workflows = {
            "task_001": WorkflowResult(
                workflow_name="workflow_task_001",
                status=WorkflowStatus.SUCCESS,
            ),
        }
        failed_tasks = [
            FailedTask(
                task_id="task_002",
                error_type="generation_error",
                message="Failed to generate",
            ),
        ]
        response = BatchWorkflowGenerationResponse.from_results(
            workflows=workflows,
            failed_tasks=failed_tasks,
        )

        assert response.status == BatchStatus.PARTIAL_SUCCESS
        assert (
            response.success is True
        )  # partial_success is still "success" for success flag
        assert response.total_tasks == 2
        assert response.succeeded_tasks == 1
        assert response.failed_task_count == 1

    def test_response_all_failed(self):
        """Test BatchWorkflowGenerationResponse for all failed."""
        failed_tasks = [
            FailedTask(
                task_id="task_001",
                error_type="generation_error",
                message="Failed to generate",
            ),
        ]
        response = BatchWorkflowGenerationResponse.from_results(
            workflows={},
            failed_tasks=failed_tasks,
            recovery_suggestion=RecoverySuggestion.ROLLBACK_TO_ANALYSIS,
        )

        assert response.status == BatchStatus.FAILED
        assert response.success is False
        assert response.total_tasks == 1
        assert response.succeeded_tasks == 0
        assert response.failed_task_count == 1
        assert response.recovery_suggestion == RecoverySuggestion.ROLLBACK_TO_ANALYSIS

    def test_response_direct_creation(self):
        """Test BatchWorkflowGenerationResponse direct creation."""
        response = BatchWorkflowGenerationResponse(
            status=BatchStatus.SUCCESS,
            success=True,
            workflows={
                "task_001": WorkflowResult(
                    workflow_name="workflow_task_001",
                    status=WorkflowStatus.SUCCESS,
                ),
            },
            total_tasks=1,
            succeeded_tasks=1,
            failed_task_count=0,
        )

        assert response.status == BatchStatus.SUCCESS
        assert response.success is True


class TestHttpResponse:
    """Tests for HttpResponse dataclass."""

    def test_http_response_creation(self):
        """Test HttpResponse creation."""
        response = HttpResponse(
            status_code=200,
            json_data={"status": "success"},
            headers={"Content-Type": "application/json"},
            elapsed_ms=150.0,
        )
        assert response.status_code == 200
        assert response.json_data == {"status": "success"}
        assert response.elapsed_ms == 150.0


class TestRequestMetrics:
    """Tests for RequestMetrics dataclass."""

    def test_request_metrics_creation(self):
        """Test RequestMetrics creation."""
        metrics = RequestMetrics(
            url="/api/v1/generator/workflow/batch",
            method="POST",
            status_code=200,
            latency_ms=150.0,
            request_size_bytes=1024,
            response_size_bytes=2048,
            success=True,
        )
        assert metrics.url == "/api/v1/generator/workflow/batch"
        assert metrics.method == "POST"
        assert metrics.success is True
        assert metrics.error_type is None

    def test_request_metrics_with_error(self):
        """Test RequestMetrics with error."""
        metrics = RequestMetrics(
            url="/api/v1/generator/workflow/batch",
            method="POST",
            status_code=500,
            latency_ms=100.0,
            request_size_bytes=1024,
            response_size_bytes=256,
            success=False,
            error_type="internal_server_error",
        )
        assert metrics.success is False
        assert metrics.error_type == "internal_server_error"


class TestNoOpMetricsCollector:
    """Tests for NoOpMetricsCollector."""

    def test_noop_record_request(self):
        """Test NoOpMetricsCollector.record_request does nothing."""
        collector = NoOpMetricsCollector()
        metrics = RequestMetrics(
            url="/test",
            method="GET",
            status_code=200,
            latency_ms=10.0,
            request_size_bytes=0,
            response_size_bytes=0,
            success=True,
        )
        # Should not raise
        collector.record_request(metrics)

    def test_noop_increment_counter(self):
        """Test NoOpMetricsCollector.increment_counter does nothing."""
        collector = NoOpMetricsCollector()
        # Should not raise
        collector.increment_counter("test_counter", {"label": "value"})


class TestLoggingMetricsCollector:
    """Tests for LoggingMetricsCollector."""

    def test_logging_record_request(self):
        """Test LoggingMetricsCollector logs request metrics."""
        import logging

        logger = logging.getLogger("test")
        collector = LoggingMetricsCollector(logger)
        metrics = RequestMetrics(
            url="/test",
            method="POST",
            status_code=200,
            latency_ms=50.0,
            request_size_bytes=100,
            response_size_bytes=200,
            success=True,
        )

        with patch.object(logger, "info") as mock_info:
            collector.record_request(metrics)
            mock_info.assert_called_once()


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig."""

    def test_default_config(self):
        """Test CircuitBreakerConfig default values."""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.success_threshold == 3
        assert config.timeout_seconds == 30.0
        assert config.excluded_exceptions == ()

    def test_custom_config(self):
        """Test CircuitBreakerConfig with custom values."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout_seconds=60.0,
            excluded_exceptions=(ValueError,),
        )
        assert config.failure_threshold == 3
        assert config.success_threshold == 2
        assert config.timeout_seconds == 60.0
        assert config.excluded_exceptions == (ValueError,)


class TestCircuitState:
    """Tests for CircuitState enum."""

    def test_circuit_state_values(self):
        """Test CircuitState enum values."""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    @pytest.fixture
    def circuit_breaker(self):
        """Create a circuit breaker with test config."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=2,
            timeout_seconds=0.1,  # Short timeout for testing
        )
        return CircuitBreaker(config=config)

    def test_initial_state_is_closed(self, circuit_breaker: CircuitBreaker):
        """Test circuit breaker starts in CLOSED state."""
        assert circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_successful_call_stays_closed(self, circuit_breaker: CircuitBreaker):
        """Test successful calls keep circuit CLOSED."""

        async def success_func():
            return "success"

        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_failures_open_circuit(self, circuit_breaker: CircuitBreaker):
        """Test consecutive failures open the circuit."""

        async def failing_func():
            raise RuntimeError("Test error")

        # First failure
        with pytest.raises(RuntimeError):
            await circuit_breaker.call(failing_func)
        assert circuit_breaker.state == CircuitState.CLOSED

        # Second failure - should open circuit
        with pytest.raises(RuntimeError):
            await circuit_breaker.call(failing_func)
        assert circuit_breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_circuit_rejects_calls(self, circuit_breaker: CircuitBreaker):
        """Test open circuit rejects new calls."""

        async def failing_func():
            raise RuntimeError("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitState.OPEN

        # New call should be rejected
        with pytest.raises(CircuitBreakerOpenError):
            await circuit_breaker.call(failing_func)

    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open(
        self, circuit_breaker: CircuitBreaker
    ):
        """Test circuit transitions to HALF_OPEN after timeout."""

        async def failing_func():
            raise RuntimeError("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Check state transition happens on next call attempt
        async def success_func():
            return "success"

        result = await circuit_breaker.call(success_func)
        assert result == "success"
        # After one success in HALF_OPEN, should still be HALF_OPEN
        # (needs success_threshold successes to close)

    @pytest.mark.asyncio
    async def test_excluded_exceptions_not_counted(
        self, circuit_breaker: CircuitBreaker
    ):
        """Test excluded exceptions don't affect circuit state."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            excluded_exceptions=(ValueError,),
        )
        cb = CircuitBreaker(config=config)

        async def value_error_func():
            raise ValueError("Excluded error")

        # Excluded exception should be raised but not counted
        with pytest.raises(ValueError):
            await cb.call(value_error_func)

        assert cb.state == CircuitState.CLOSED


class TestWorkflowGeneratorErrors:
    """Tests for WorkflowGeneratorError hierarchy."""

    def test_base_error(self):
        """Test WorkflowGeneratorError base class."""
        error = WorkflowGeneratorError("Test error")
        assert str(error) == "Test error"

    def test_timeout_error(self):
        """Test WorkflowGeneratorTimeoutError."""
        error = WorkflowGeneratorTimeoutError(
            url="/api/v1/generator/workflow/batch",
            timeout_ms=30000,
        )
        assert "/api/v1/generator/workflow/batch" in str(error)
        assert "30000" in str(error)

    def test_http_error(self):
        """Test WorkflowGeneratorHTTPError."""
        error = WorkflowGeneratorHTTPError(
            status_code=500,
            message="Internal Server Error",
            details={"url": "/test"},
        )
        assert "500" in str(error)
        assert "Internal Server Error" in str(error)

    def test_validation_error(self):
        """Test WorkflowGeneratorValidationError."""
        error = WorkflowGeneratorValidationError("Invalid schema")
        assert "Invalid schema" in str(error)


class TestHttpxClientAdapter:
    """Tests for HttpxClientAdapter."""

    @pytest.mark.asyncio
    async def test_adapter_post(self):
        """Test HttpxClientAdapter.post method."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success"}
            mock_response.headers = {"Content-Type": "application/json"}
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            adapter = HttpxClientAdapter(base_url="http://localhost:8006", timeout=30.0)

            response = await adapter.post(
                url="/api/v1/test",
                json={"data": "test"},
                headers={"X-Trace-Id": "trace-123"},
            )

            assert response.status_code == 200
            assert response.json_data == {"status": "success"}

    @pytest.mark.asyncio
    async def test_adapter_close(self):
        """Test HttpxClientAdapter.close method."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            adapter = HttpxClientAdapter(base_url="http://localhost:8006")
            await adapter.close()

            mock_client.aclose.assert_called_once()


class TestWorkflowGeneratorClient:
    """Tests for WorkflowGeneratorClient."""

    @pytest.fixture
    def mock_http_client(self):
        """Create a mock HTTP client."""
        mock = AsyncMock(spec=IHttpClient)
        return mock

    @pytest.fixture
    def mock_metrics(self):
        """Create a mock metrics collector."""
        mock = MagicMock(spec=IMetricsCollector)
        return mock

    @pytest.fixture
    def mock_circuit_breaker(self):
        """Create a mock circuit breaker."""
        cb = CircuitBreaker()
        return cb

    def test_client_initialization(self):
        """Test WorkflowGeneratorClient initialization."""
        client = WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            timeout=30.0,
            max_retries=3,
        )
        assert client.base_url == "http://localhost:8006"
        assert client.timeout == 30.0
        assert client.max_retries == 3

    def test_client_with_auth_headers(self):
        """Test WorkflowGeneratorClient with auth headers."""
        client = WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            auth_headers={"X-API-Key": "secret-key"},
        )
        assert client.auth_headers == {"X-API-Key": "secret-key"}

    def test_client_with_dependency_injection(
        self,
        mock_http_client,
        mock_metrics,
        mock_circuit_breaker,
    ):
        """Test WorkflowGeneratorClient with dependency injection."""
        client = WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            http_client=mock_http_client,
            metrics_collector=mock_metrics,
            circuit_breaker=mock_circuit_breaker,
        )
        # Client should use injected dependencies
        assert client._http_client == mock_http_client
        assert client._metrics == mock_metrics
        assert client._circuit_breaker == mock_circuit_breaker

    @pytest.mark.asyncio
    async def test_context_manager_creates_client(self):
        """Test async context manager creates HTTP client."""
        with patch(
            "aiagent.clients.workflow_generator_client.HttpxClientAdapter"
        ) as mock_adapter:
            mock_instance = AsyncMock()
            mock_adapter.return_value = mock_instance

            async with WorkflowGeneratorClient(
                base_url="http://localhost:8006"
            ) as client:
                assert client._http_client is mock_instance

            mock_instance.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_with_injected_client(self, mock_http_client):
        """Test context manager with pre-injected client."""
        async with WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            http_client=mock_http_client,
        ) as client:
            assert client._http_client == mock_http_client

        # Should not close injected client
        mock_http_client.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_workflows_success(self, mock_http_client):
        """Test generate_workflows for successful generation."""
        # Setup mock response
        mock_response = HttpResponse(
            status_code=200,
            json_data={
                "status": "success",
                "success": True,
                "workflows": {
                    "task_001": {
                        "workflow_name": "workflow_task_001",
                        "status": "success",
                    },
                },
                "total_tasks": 1,
                "succeeded_tasks": 1,
                "failed_task_count": 0,
            },
            headers={"Content-Type": "application/json"},
            elapsed_ms=100.0,
        )
        mock_http_client.post.return_value = mock_response

        async with WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            http_client=mock_http_client,
        ) as client:
            tasks = [
                TaskRequest(
                    task_id="task_001",
                    name="Search Gmail",
                    description="Search for emails",
                    interface=TaskInterface(
                        input={"query": "string"},
                        output={"emails": "array"},
                    ),
                ),
            ]

            response = await client.generate_workflows(
                tasks=tasks,
                capabilities=[],
                project_id="default_project",
                trace_id="trace-123",
            )

            assert response.status == BatchStatus.SUCCESS
            assert response.success is True
            assert len(response.workflows) == 1

    @pytest.mark.asyncio
    async def test_generate_workflows_with_trace_headers(self, mock_http_client):
        """Test that trace_id and parent_span_id are sent as headers (AC-4)."""
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
        mock_http_client.post.return_value = mock_response

        async with WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            http_client=mock_http_client,
        ) as client:
            await client.generate_workflows(
                tasks=[],
                capabilities=[],
                project_id="default",
                trace_id="trace-abc",
                parent_span_id="span-xyz",
            )

            # Verify headers were passed
            call_args = mock_http_client.post.call_args
            headers = call_args.kwargs.get("headers", {})
            assert headers.get("X-Trace-Id") == "trace-abc"
            assert headers.get("X-Parent-Span-Id") == "span-xyz"

    @pytest.mark.asyncio
    async def test_generate_workflows_partial_success(self, mock_http_client):
        """Test generate_workflows for partial success."""
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
        mock_http_client.post.return_value = mock_response

        async with WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            http_client=mock_http_client,
        ) as client:
            response = await client.generate_workflows(
                tasks=[],
                capabilities=[],
                project_id="default",
            )

            assert response.status == BatchStatus.PARTIAL_SUCCESS
            assert response.succeeded_tasks == 1
            assert response.failed_task_count == 1

    @pytest.mark.asyncio
    async def test_generate_workflows_with_recovery_suggestion(self, mock_http_client):
        """Test generate_workflows returns recovery_suggestion (AC-5)."""
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
        mock_http_client.post.return_value = mock_response

        async with WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            http_client=mock_http_client,
        ) as client:
            response = await client.generate_workflows(
                tasks=[],
                capabilities=[],
                project_id="default",
            )

            assert response.status == BatchStatus.FAILED
            assert response.success is False
            assert (
                response.recovery_suggestion == RecoverySuggestion.ROLLBACK_TO_ANALYSIS
            )

    @pytest.mark.asyncio
    async def test_generate_workflows_http_error(self, mock_http_client):
        """Test generate_workflows handles HTTP errors."""
        import httpx

        mock_http_client.post.side_effect = httpx.HTTPStatusError(
            message="Internal Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )

        async with WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            http_client=mock_http_client,
        ) as client:
            with pytest.raises(WorkflowGeneratorHTTPError) as exc_info:
                await client.generate_workflows(
                    tasks=[],
                    capabilities=[],
                    project_id="default",
                )

            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_generate_workflows_timeout(self, mock_http_client):
        """Test generate_workflows handles timeout."""
        import httpx

        mock_http_client.post.side_effect = httpx.TimeoutException(
            message="Request timed out"
        )

        async with WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            http_client=mock_http_client,
            timeout=30.0,
        ) as client:
            with pytest.raises(WorkflowGeneratorTimeoutError) as exc_info:
                await client.generate_workflows(
                    tasks=[],
                    capabilities=[],
                    project_id="default",
                )

            assert "30000" in str(exc_info.value)  # timeout in ms

    @pytest.mark.asyncio
    async def test_generate_workflows_circuit_breaker_open(self, mock_http_client):
        """Test generate_workflows respects circuit breaker."""
        # Create client with circuit breaker in OPEN state
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker(config=config)

        # Force circuit to OPEN state
        async def fail():
            raise RuntimeError("test")

        with pytest.raises(RuntimeError):
            await cb.call(fail)

        # Circuit should now be OPEN
        assert cb.state == CircuitState.OPEN

        async with WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            http_client=mock_http_client,
            circuit_breaker=cb,
        ) as client:
            with pytest.raises(CircuitBreakerOpenError):
                await client.generate_workflows(
                    tasks=[],
                    capabilities=[],
                    project_id="default",
                )

    @pytest.mark.asyncio
    async def test_generate_workflows_metrics_recorded(
        self,
        mock_http_client,
        mock_metrics,
    ):
        """Test generate_workflows records metrics."""
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
            elapsed_ms=100.0,
        )
        mock_http_client.post.return_value = mock_response

        async with WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            http_client=mock_http_client,
            metrics_collector=mock_metrics,
        ) as client:
            await client.generate_workflows(
                tasks=[],
                capabilities=[],
                project_id="default",
            )

            # Verify metrics were recorded
            mock_metrics.record_request.assert_called_once()
            call_args = mock_metrics.record_request.call_args
            recorded_metrics = call_args[0][0]
            assert recorded_metrics.status_code == 200
            assert recorded_metrics.success is True


class TestWorkflowGeneratorClientBuildRequest:
    """Tests for request building."""

    @pytest.mark.asyncio
    async def test_build_request_body_structure(self):
        """Test that request body has correct structure."""
        mock_http_client = AsyncMock(spec=IHttpClient)
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
        mock_http_client.post.return_value = mock_response

        async with WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            http_client=mock_http_client,
        ) as client:
            tasks = [
                TaskRequest(
                    task_id="task_001",
                    name="Test Task",
                    description="Test description",
                    interface=TaskInterface(
                        input={"query": "string"},
                        output={"result": "string"},
                    ),
                ),
            ]
            capabilities = [{"name": "fetchAgent", "endpoint": "/api/fetch"}]

            await client.generate_workflows(
                tasks=tasks,
                capabilities=capabilities,
                project_id="test_project",
                options=GenerationOptions(max_concurrency=5),
            )

            # Verify request body structure
            call_args = mock_http_client.post.call_args
            request_body = call_args.kwargs.get("json", {})

            assert "tasks" in request_body
            assert "capabilities" in request_body
            assert "project_id" in request_body
            assert request_body["project_id"] == "test_project"
            assert "options" in request_body
            assert request_body["options"]["max_concurrency"] == 5


class TestWorkflowGeneratorClientFetchCapabilities:
    """Tests for fetch_capabilities method (Issue #385).

    Task 2.1: WorkflowGeneratorClient single tests for fetch_capabilities.
    """

    @pytest.fixture
    def mock_http_client(self):
        """Create a mock HTTP client."""
        mock = AsyncMock(spec=IHttpClient)
        return mock

    @pytest.mark.asyncio
    async def test_fetch_capabilities_success(self, mock_http_client):
        """Test successful capability fetch."""
        from aiagent.clients.workflow_generator_client import (
            WorkflowGeneratorClient,
        )

        # Setup mock response
        mock_response = HttpResponse(
            status_code=200,
            json_data={
                "capabilities": [
                    {"name": "fetchAgent", "endpoint": "/api/fetch"},
                    {"name": "searchAgent", "endpoint": "/api/search"},
                ],
            },
            headers={"Content-Type": "application/json"},
            elapsed_ms=50.0,
        )
        mock_http_client.get.return_value = mock_response

        async with WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            http_client=mock_http_client,
        ) as client:
            capabilities = await client.fetch_capabilities("test_project")

            assert len(capabilities) == 2
            assert capabilities[0]["name"] == "fetchAgent"
            assert capabilities[1]["name"] == "searchAgent"

            # Verify the correct URL was called
            call_args = mock_http_client.get.call_args
            assert "project=test_project" in call_args.kwargs.get(
                "url", ""
            ) or "project=test_project" in str(call_args)

    @pytest.mark.asyncio
    async def test_fetch_capabilities_timeout(self, mock_http_client):
        """Test fetch_capabilities handles timeout."""
        import httpx

        from aiagent.clients.workflow_generator_client import (
            CapabilityFetchError,
            WorkflowGeneratorClient,
        )

        mock_http_client.get.side_effect = httpx.TimeoutException(
            message="Request timed out"
        )

        async with WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            http_client=mock_http_client,
            timeout=10.0,
        ) as client:
            with pytest.raises(CapabilityFetchError) as exc_info:
                await client.fetch_capabilities("test_project")

            assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_fetch_capabilities_connection_error(self, mock_http_client):
        """Test fetch_capabilities handles connection error."""
        import httpx

        from aiagent.clients.workflow_generator_client import (
            CapabilityFetchError,
            WorkflowGeneratorClient,
        )

        mock_http_client.get.side_effect = httpx.ConnectError(
            message="Connection refused"
        )

        async with WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            http_client=mock_http_client,
        ) as client:
            with pytest.raises(CapabilityFetchError) as exc_info:
                await client.fetch_capabilities("test_project")

            assert (
                "connection" in str(exc_info.value).lower()
                or "connect" in str(exc_info.value).lower()
            )

    @pytest.mark.asyncio
    async def test_fetch_capabilities_http_error(self, mock_http_client):
        """Test fetch_capabilities handles HTTP errors."""
        from aiagent.clients.workflow_generator_client import (
            CapabilityFetchError,
            WorkflowGeneratorClient,
        )

        mock_response = HttpResponse(
            status_code=500,
            json_data={"error": "Internal Server Error"},
            headers={},
            elapsed_ms=50.0,
        )
        mock_http_client.get.return_value = mock_response

        async with WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            http_client=mock_http_client,
        ) as client:
            with pytest.raises(CapabilityFetchError) as exc_info:
                await client.fetch_capabilities("test_project")

            assert (
                "500" in str(exc_info.value) or "error" in str(exc_info.value).lower()
            )

    @pytest.mark.asyncio
    async def test_fetch_capabilities_empty_response(self, mock_http_client):
        """Test fetch_capabilities handles empty capabilities list."""
        from aiagent.clients.workflow_generator_client import WorkflowGeneratorClient

        mock_response = HttpResponse(
            status_code=200,
            json_data={"capabilities": []},
            headers={},
            elapsed_ms=50.0,
        )
        mock_http_client.get.return_value = mock_response

        async with WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            http_client=mock_http_client,
        ) as client:
            capabilities = await client.fetch_capabilities("test_project")

            assert capabilities == []

    @pytest.mark.asyncio
    async def test_fetch_capabilities_uses_correct_endpoint(self, mock_http_client):
        """Test fetch_capabilities calls correct API endpoint."""
        from aiagent.clients.workflow_generator_client import WorkflowGeneratorClient

        mock_response = HttpResponse(
            status_code=200,
            json_data={"capabilities": []},
            headers={},
            elapsed_ms=50.0,
        )
        mock_http_client.get.return_value = mock_response

        async with WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            http_client=mock_http_client,
        ) as client:
            await client.fetch_capabilities("my_project")

            # Verify GET request was made to correct endpoint
            mock_http_client.get.assert_called_once()
            call_args = mock_http_client.get.call_args
            url = call_args.kwargs.get("url", "")
            assert "/api/v1/capabilities" in url
            assert "project=my_project" in url


class TestCapabilityFetchError:
    """Tests for CapabilityFetchError exception class."""

    def test_capability_fetch_error_exists(self):
        """Test CapabilityFetchError is importable."""
        from aiagent.clients.workflow_generator_client import CapabilityFetchError

        assert CapabilityFetchError is not None

    def test_capability_fetch_error_is_exception(self):
        """Test CapabilityFetchError inherits from WorkflowGeneratorError."""
        from aiagent.clients.workflow_generator_client import (
            CapabilityFetchError,
            WorkflowGeneratorError,
        )

        assert issubclass(CapabilityFetchError, WorkflowGeneratorError)

    def test_capability_fetch_error_message(self):
        """Test CapabilityFetchError can be created with message."""
        from aiagent.clients.workflow_generator_client import CapabilityFetchError

        error = CapabilityFetchError("Failed to fetch capabilities")
        assert "Failed to fetch capabilities" in str(error)

    def test_capability_fetch_error_with_project_id(self):
        """Test CapabilityFetchError stores project_id."""
        from aiagent.clients.workflow_generator_client import CapabilityFetchError

        error = CapabilityFetchError(
            "Failed to fetch",
            project_id="test_project",
        )
        assert error.project_id == "test_project"
