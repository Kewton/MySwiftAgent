"""WorkflowGeneratorClient for mySwiftAgentCore integration.

Issue #361: HTTP client for mySwiftAgentCore workflow generation API.

This module provides:
- WorkflowGeneratorClient: Main client class
- Error classes: WorkflowGeneratorError hierarchy
- Integration with circuit breaker and metrics

Usage:
    async with WorkflowGeneratorClient(
        base_url="http://localhost:8006",
        timeout=30.0,
    ) as client:
        response = await client.generate_workflows(
            tasks=[...],
            capabilities=[...],
            project_id="default_project",
            trace_id="trace-123",
        )
"""

import json
import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .interfaces.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
)
from .interfaces.http_client import HttpResponse, HttpxClientAdapter, IHttpClient
from .interfaces.metrics import IMetricsCollector, NoOpMetricsCollector, RequestMetrics
from .types.workflow_generator import (
    BatchStatus,
    BatchWorkflowGenerationResponse,
    FailedTask,
    GenerationOptions,
    RecoverySuggestion,
    TaskRequest,
    WorkflowResult,
    WorkflowStatus,
)

logger = logging.getLogger(__name__)


class WorkflowGeneratorError(Exception):
    """Base exception for WorkflowGeneratorClient errors."""

    pass


class WorkflowGeneratorTimeoutError(WorkflowGeneratorError):
    """Timeout error for workflow generation requests.

    Attributes:
        url: Request URL that timed out
        timeout_ms: Configured timeout in milliseconds
    """

    def __init__(self, url: str, timeout_ms: int):
        super().__init__(f"Request to {url} timed out after {timeout_ms}ms")
        self.url = url
        self.timeout_ms = timeout_ms


class WorkflowGeneratorHTTPError(WorkflowGeneratorError):
    """HTTP error from workflow generation API.

    Attributes:
        status_code: HTTP status code
        message: Error message
        details: Additional error details
    """

    def __init__(
        self,
        status_code: int,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.message = message
        self.details = details or {}


class WorkflowGeneratorValidationError(WorkflowGeneratorError):
    """Validation error for workflow generation."""

    pass


class CapabilityFetchError(WorkflowGeneratorError):
    """Error when fetching capabilities from mySwiftAgentCore.

    Issue #385: Explicit error for capability fetch failures.

    Attributes:
        project_id: The project ID that failed to fetch capabilities for
    """

    def __init__(self, message: str, project_id: str | None = None):
        super().__init__(message)
        self.project_id = project_id


class WorkflowGeneratorClient:
    """Client for mySwiftAgentCore workflow generation API.

    Provides async interface for batch workflow generation with:
    - Automatic retry with exponential backoff
    - Circuit breaker for fault tolerance
    - Metrics collection
    - Langfuse trace propagation

    Example:
        async with WorkflowGeneratorClient(
            base_url="http://localhost:8006",
            timeout=30.0,
        ) as client:
            response = await client.generate_workflows(
                tasks=[TaskRequest(...)],
                capabilities=[...],
                project_id="default_project",
                trace_id="trace-123",
            )

    Attributes:
        base_url: mySwiftAgentCore base URL
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        retry_delay: Base delay between retries
        auth_headers: Additional authentication headers
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8006",
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        auth_headers: dict[str, str] | None = None,
        http_client: IHttpClient | None = None,
        metrics_collector: IMetricsCollector | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ):
        """Initialize WorkflowGeneratorClient.

        Args:
            base_url: mySwiftAgentCore base URL
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for transient errors
            retry_delay: Base delay between retries (exponential backoff)
            auth_headers: Additional headers for authentication
            http_client: Custom HTTP client (for testing)
            metrics_collector: Custom metrics collector
            circuit_breaker: Custom circuit breaker
        """
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.auth_headers = auth_headers or {}

        # Dependency injection
        self._http_client = http_client
        self._own_client = http_client is None
        self._metrics = metrics_collector or NoOpMetricsCollector()
        self._circuit_breaker = circuit_breaker or CircuitBreaker()

    async def __aenter__(self) -> "WorkflowGeneratorClient":
        """Async context manager entry.

        Creates HTTP client if not injected.
        """
        if self._own_client:
            self._http_client = HttpxClientAdapter(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit.

        Closes HTTP client if we own it.
        """
        if self._own_client and self._http_client:
            await self._http_client.close()

    async def fetch_capabilities(
        self,
        project_id: str,
    ) -> list[dict[str, Any]]:
        """Fetch available capabilities for a project.

        Issue #385: Fetch capabilities from mySwiftAgentCore API.

        Args:
            project_id: Project ID to fetch capabilities for

        Returns:
            List of capability dictionaries

        Raises:
            CapabilityFetchError: On fetch failure (timeout, connection, HTTP error)
        """
        url = f"/api/v1/capabilities?project={project_id}"

        try:
            if self._http_client is None:
                raise CapabilityFetchError(
                    "HTTP client not initialized",
                    project_id=project_id,
                )

            response = await self._http_client.get(url=url)

            # Check HTTP status
            if response.status_code >= 400:
                raise CapabilityFetchError(
                    f"HTTP {response.status_code} error fetching capabilities",
                    project_id=project_id,
                )

            # Parse response
            capabilities: list[dict[str, Any]] = response.json_data.get(
                "capabilities", []
            )
            return capabilities

        except httpx.TimeoutException as e:
            raise CapabilityFetchError(
                f"Timeout fetching capabilities for project {project_id}",
                project_id=project_id,
            ) from e

        except httpx.ConnectError as e:
            raise CapabilityFetchError(
                f"Connection error fetching capabilities for project {project_id}",
                project_id=project_id,
            ) from e

        except httpx.NetworkError as e:
            raise CapabilityFetchError(
                f"Network error fetching capabilities for project {project_id}",
                project_id=project_id,
            ) from e

    async def generate_workflows(
        self,
        tasks: list[TaskRequest],
        capabilities: list[dict[str, Any]],
        project_id: str,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        options: GenerationOptions | None = None,
    ) -> BatchWorkflowGenerationResponse:
        """Generate workflows for multiple tasks.

        Calls mySwiftAgentCore's batch workflow generation API.
        Includes retry logic, circuit breaker, and metrics.

        Args:
            tasks: List of tasks to generate workflows for
            capabilities: Available capabilities (APIs, agents)
            project_id: Target project ID
            trace_id: Langfuse trace ID for distributed tracing
            parent_span_id: Parent span ID for trace nesting
            options: Generation options

        Returns:
            BatchWorkflowGenerationResponse with results

        Raises:
            WorkflowGeneratorTimeoutError: On request timeout
            WorkflowGeneratorHTTPError: On HTTP error
            WorkflowGeneratorValidationError: On validation error
            CircuitBreakerOpenError: When circuit is open
        """
        return await self._circuit_breaker.call(
            self._execute_request,
            tasks=tasks,
            capabilities=capabilities,
            project_id=project_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            options=options,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def _execute_request(
        self,
        tasks: list[TaskRequest],
        capabilities: list[dict[str, Any]],
        project_id: str,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        options: GenerationOptions | None = None,
    ) -> BatchWorkflowGenerationResponse:
        """Execute the HTTP request with retry logic.

        Args:
            tasks: Tasks to generate workflows for
            capabilities: Available capabilities
            project_id: Target project ID
            trace_id: Langfuse trace ID
            parent_span_id: Parent span ID
            options: Generation options

        Returns:
            BatchWorkflowGenerationResponse

        Raises:
            WorkflowGeneratorTimeoutError: On timeout
            WorkflowGeneratorHTTPError: On HTTP error
        """
        url = "/api/v1/generator/workflow/batch"

        # Build request body
        request_body = self._build_request_body(
            tasks, capabilities, project_id, trace_id, parent_span_id, options
        )

        # Build headers
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            **self.auth_headers,
        }
        if trace_id:
            headers["X-Trace-Id"] = trace_id
        if parent_span_id:
            headers["X-Parent-Span-Id"] = parent_span_id

        try:
            if self._http_client is None:
                raise WorkflowGeneratorError("HTTP client not initialized")

            response = await self._http_client.post(
                url=url,
                json=request_body,
                headers=headers,
            )

            # Record metrics
            self._metrics.record_request(
                RequestMetrics(
                    url=url,
                    method="POST",
                    status_code=response.status_code,
                    latency_ms=response.elapsed_ms,
                    request_size_bytes=len(json.dumps(request_body)),
                    response_size_bytes=len(json.dumps(response.json_data)),
                    success=200 <= response.status_code < 300,
                )
            )

            return self._parse_response(response)

        except httpx.TimeoutException as e:
            self._metrics.increment_counter(
                "workflow_generator_timeout_total",
                {"url": url},
            )
            raise WorkflowGeneratorTimeoutError(url, int(self.timeout * 1000)) from e

        except httpx.HTTPStatusError as e:
            raise WorkflowGeneratorHTTPError(
                status_code=e.response.status_code,
                message=str(e),
                details={"url": url},
            ) from e

    def _build_request_body(
        self,
        tasks: list[TaskRequest],
        capabilities: list[dict[str, Any]],
        project_id: str,
        trace_id: str | None,
        parent_span_id: str | None,
        options: GenerationOptions | None,
    ) -> dict[str, Any]:
        """Build request body for API call.

        Args:
            tasks: Tasks to include
            capabilities: Capabilities to include
            project_id: Project ID
            trace_id: Trace ID
            parent_span_id: Parent span ID
            options: Generation options

        Returns:
            Request body as dict
        """
        body: dict[str, Any] = {
            "tasks": [
                {
                    "task_id": t.task_id,
                    "name": t.name,
                    "description": t.description,
                    "interface": {
                        "input": t.interface.input,
                        "output": t.interface.output,
                    },
                }
                for t in tasks
            ],
            "capabilities": capabilities,
            "project_id": project_id,
        }

        if options:
            body["options"] = {
                "max_concurrency": options.max_concurrency,
                "timeout_per_task_ms": options.timeout_per_task_ms,
                "validate_before_register": options.validate_before_register,
            }

        if trace_id or parent_span_id:
            body["trace_context"] = {}
            if trace_id:
                body["trace_context"]["trace_id"] = trace_id
            if parent_span_id:
                body["trace_context"]["parent_span_id"] = parent_span_id

        return body

    def _parse_response(
        self,
        response: HttpResponse,
    ) -> BatchWorkflowGenerationResponse:
        """Parse HTTP response to BatchWorkflowGenerationResponse.

        Args:
            response: HTTP response

        Returns:
            BatchWorkflowGenerationResponse
        """
        data = response.json_data

        # Parse status
        # Issue #396: Infer status from success field when status is not present
        # mySwiftAgentCore returns "success" (boolean), not "status" (string)
        status_str = data.get("status")
        if status_str:
            try:
                status = BatchStatus(status_str)
            except ValueError:
                status = BatchStatus.FAILED
        else:
            # Infer status from success field and counts
            success = data.get("success", False)
            failed_count = len(data.get("failed_tasks", []))
            workflow_count = len(data.get("workflows", {}))

            if success and failed_count == 0 and workflow_count > 0:
                status = BatchStatus.SUCCESS
            elif workflow_count > 0 and failed_count > 0:
                status = BatchStatus.PARTIAL_SUCCESS
            else:
                status = BatchStatus.FAILED

        # Parse workflows
        # Fix: mySwiftAgentCore returns "registered" field instead of "status"
        # Infer status from "registered" when "status" is not present
        workflows: dict[str, WorkflowResult] = {}
        for task_id, wf_data in data.get("workflows", {}).items():
            if isinstance(wf_data, dict):
                # Check for explicit status field first, then infer from registered
                if "status" in wf_data:
                    wf_status = WorkflowStatus(wf_data["status"])
                elif wf_data.get("registered", False):
                    wf_status = WorkflowStatus.SUCCESS
                else:
                    wf_status = WorkflowStatus.FAILED
                workflows[task_id] = WorkflowResult(
                    workflow_name=wf_data.get("workflow_name", ""),
                    status=wf_status,
                    error=wf_data.get("error"),
                )

        # Parse failed tasks
        failed_tasks: list[FailedTask] | None = None
        if "failed_tasks" in data and data["failed_tasks"]:
            failed_tasks = [
                FailedTask(
                    task_id=ft.get("task_id", ""),
                    error_type=ft.get("error_type", "unknown"),
                    message=ft.get("message", ""),
                )
                for ft in data["failed_tasks"]
            ]

        # Parse recovery suggestion
        recovery_suggestion: RecoverySuggestion | None = None
        if "recovery_suggestion" in data and data["recovery_suggestion"]:
            try:
                recovery_suggestion = RecoverySuggestion(data["recovery_suggestion"])
            except ValueError:
                pass

        return BatchWorkflowGenerationResponse(
            status=status,
            success=data.get("success", False),
            workflows=workflows,
            failed_tasks=failed_tasks,
            recovery_suggestion=recovery_suggestion,
            total_tasks=data.get("total_tasks", 0),
            succeeded_tasks=data.get("succeeded_tasks", 0),
            failed_task_count=data.get("failed_task_count", 0),
        )


# Re-export for convenient imports
__all__ = [
    "CapabilityFetchError",
    "CircuitBreakerOpenError",
    "WorkflowGeneratorClient",
    "WorkflowGeneratorError",
    "WorkflowGeneratorHTTPError",
    "WorkflowGeneratorTimeoutError",
    "WorkflowGeneratorValidationError",
]
