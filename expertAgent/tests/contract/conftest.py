"""Pytest fixtures for contract tests.

Issue #356: TaskFlow Contract Tests implementation.

This module provides fixtures for:
- TaskFlowAdapter instance
- Sample workflow data (dict and JSON string formats)
- GraphAiServer validation URL
- Fixture loading utilities

Design Patterns Applied:
- Factory Pattern: WorkflowBuilder for creating test workflows
- Template Pattern: Base workflow structure with customizable fields
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.adapter import (
    TaskFlowAdapter,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.schemas.taskflow_schema import (
    TaskFlowStep,
    TaskFlowWorkflow,
    UnifiedStepConfig,
)

# Path to fixture files
FIXTURES_DIR = Path(__file__).parent / "fixtures"
VALID_WORKFLOWS_DIR = FIXTURES_DIR / "valid_workflows"

# Default GraphAiServer URL
# Uses port 8005 which is the standard port in local development environment
# See: docs/ops/local-development.md for port configuration
DEFAULT_GRAPHAI_SERVER_URL = "http://localhost:8005"


# ============================================================================
# Builder Helpers (Factory Pattern)
# ============================================================================


def create_api_rest_step(
    step_id: str,
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: str | dict[str, Any] | None = None,
    timeout_ms: int = 30000,
) -> dict[str, Any]:
    """Create an API REST step configuration.

    Factory method for creating consistent API REST step structures.

    Args:
        step_id: Unique step identifier
        url: API endpoint URL
        method: HTTP method (GET, POST, etc.)
        headers: Optional HTTP headers
        body: Optional request body (JSON string or dict)
        timeout_ms: Request timeout in milliseconds

    Returns:
        Step configuration dict
    """
    config: dict[str, Any] = {
        "step_type": "api_rest",
        "method": method,
        "url": url,
        "timeout_ms": timeout_ms,
    }
    if headers:
        config["headers"] = headers
    if body is not None:
        config["body"] = body

    return {
        "id": step_id,
        "type": "api_rest",
        "config": config,
    }


def create_transform_step(
    step_id: str,
    template: str,
    mode: str = "template",
) -> dict[str, Any]:
    """Create a transform step configuration.

    Factory method for creating consistent transform step structures.

    Args:
        step_id: Unique step identifier
        template: Template string for transformation
        mode: Transform mode (default: "template")

    Returns:
        Step configuration dict
    """
    return {
        "id": step_id,
        "type": "transform",
        "config": {
            "step_type": "transform",
            "mode": mode,
            "template": template,
        },
    }


def create_workflow(
    name: str,
    description: str = "",
    input_schema: str | dict[str, Any] = "",
    output_schema: str | dict[str, Any] = "",
    output: str | dict[str, Any] = "",
    steps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a workflow configuration.

    Factory method for creating consistent workflow structures.

    Args:
        name: Workflow name
        description: Workflow description
        input_schema: Input schema (JSON string or dict)
        output_schema: Output schema (JSON string or dict)
        output: Output mapping (JSON string or dict)
        steps: List of step configurations

    Returns:
        Workflow configuration dict
    """
    return {
        "workflow_name": name,
        "description": description,
        "input_schema": input_schema,
        "output_schema": output_schema,
        "output": output,
        "steps": steps or [],
    }


# ============================================================================
# Pytest Fixtures
# ============================================================================


@pytest.fixture
def adapter() -> TaskFlowAdapter:
    """Create TaskFlowAdapter instance."""
    return TaskFlowAdapter()


@pytest.fixture
def sample_workflow_with_json_strings() -> dict[str, Any]:
    """Sample workflow with JSON string fields (LLM output format).

    This represents the typical output from an LLM, where dict fields
    may be serialized as JSON strings.
    """
    return {
        "workflow_name": "test_api_workflow",
        "description": "A test workflow for contract testing",
        "input_schema": '{"query": "string", "limit": "number"}',
        "output_schema": '{"results": "array", "total": "number"}',
        "output": '{"results": "${step_001.output.data}", "total": "${step_001.output.count}"}',
        "steps": [
            {
                "id": "step_001",
                "type": "api_rest",
                "config": {
                    "step_type": "api_rest",
                    "method": "POST",
                    "url": "https://api.example.com/search",
                    "headers": {"Content-Type": "application/json"},
                    "body": '{"q": "${inputs.query}", "max_results": "${inputs.limit}"}',
                    "timeout_ms": 30000,
                },
            }
        ],
    }


@pytest.fixture
def sample_workflow_with_objects() -> dict[str, Any]:
    """Sample workflow with already-parsed object fields.

    This represents workflows that have dict fields as proper objects.
    """
    return {
        "workflow_name": "test_api_workflow",
        "description": "A test workflow for contract testing",
        "input_schema": {"query": "string", "limit": "number"},
        "output_schema": {"results": "array", "total": "number"},
        "output": {
            "results": "${step_001.output.data}",
            "total": "${step_001.output.count}",
        },
        "steps": [
            {
                "id": "step_001",
                "type": "api_rest",
                "config": {
                    "step_type": "api_rest",
                    "method": "POST",
                    "url": "https://api.example.com/search",
                    "headers": {"Content-Type": "application/json"},
                    "body": {"q": "${inputs.query}", "max_results": "${inputs.limit}"},
                    "timeout_ms": 30000,
                },
            }
        ],
    }


@pytest.fixture
def sample_pydantic_workflow() -> TaskFlowWorkflow:
    """Sample workflow as Pydantic model instance.

    This represents workflows created using TaskFlowWorkflow Pydantic model.
    """
    return TaskFlowWorkflow(
        workflow_name="pydantic_test_workflow",
        description="A test workflow created with Pydantic",
        input_schema='{"query": "string"}',
        output_schema='{"result": "string"}',
        output='{"result": "${step_001.output.data}"}',
        steps=[
            TaskFlowStep(
                id="step_001",
                type="api_rest",
                config=UnifiedStepConfig(
                    step_type="api_rest",
                    method="GET",
                    url="https://api.example.com/data",
                ),
            )
        ],
    )


@pytest.fixture
def sample_multi_step_workflow() -> dict[str, Any]:
    """Sample multi-step workflow for comprehensive testing.

    Uses factory functions for consistent step creation.
    """
    return create_workflow(
        name="multi_step_workflow",
        description="A workflow with multiple steps",
        input_schema='{"query": "string"}',
        output_schema='{"processed_result": "string"}',
        output='{"processed_result": "${step_002.output.result}"}',
        steps=[
            create_api_rest_step(
                step_id="step_001",
                url="https://api.example.com/fetch",
                method="GET",
            ),
            create_transform_step(
                step_id="step_002",
                template="Processed: ${step_001.output}",
            ),
        ],
    )


@pytest.fixture
def graphai_validate_url() -> str:
    """GraphAiServer workflow validation URL.

    Returns the URL for the GraphAiServer validation endpoint.
    This is used for integration tests that verify workflows against
    the actual GraphAiServer.
    """
    base_url = os.environ.get("GRAPHAI_SERVER_URL", DEFAULT_GRAPHAI_SERVER_URL)
    return f"{base_url}/api/v2/workflows/validate"


def load_fixture_workflow(fixture_name: str) -> dict[str, Any]:
    """Load a workflow fixture from the fixtures directory.

    Args:
        fixture_name: Name of the fixture file (without .json extension)

    Returns:
        Workflow dict loaded from the fixture file

    Raises:
        FileNotFoundError: If the fixture file does not exist
    """
    fixture_path = VALID_WORKFLOWS_DIR / f"{fixture_name}.json"
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture not found: {fixture_path}")

    with open(fixture_path) as f:
        data: dict[str, Any] = json.load(f)
        return data


def list_fixture_workflows() -> list[str]:
    """List all available fixture workflow names.

    Returns:
        List of fixture names (without .json extension)
    """
    if not VALID_WORKFLOWS_DIR.exists():
        return []

    return [f.stem for f in VALID_WORKFLOWS_DIR.glob("*.json")]


@pytest.fixture
def fixture_workflows() -> list[tuple[str, dict[str, Any]]]:
    """Load all fixture workflows for parametrized testing.

    Returns:
        List of tuples containing (fixture_name, workflow_dict)
    """
    workflows = []
    for name in list_fixture_workflows():
        try:
            workflow = load_fixture_workflow(name)
            workflows.append((name, workflow))
        except (FileNotFoundError, json.JSONDecodeError):
            continue
    return workflows


# ============================================================================
# Integration Test Helpers
# ============================================================================


def check_graphai_server_health(validate_url: str, timeout: float = 5.0) -> bool:
    """Check if GraphAiServer is available.

    Args:
        validate_url: The validation endpoint URL
        timeout: Request timeout in seconds

    Returns:
        True if server is available, False otherwise
    """
    import httpx

    try:
        # Extract base URL and check health
        base_url = validate_url.rsplit("/api", 1)[0]
        response = httpx.get(f"{base_url}/health", timeout=timeout)
        return response.status_code == 200
    except (httpx.RequestError, httpx.TimeoutException):
        return False


@pytest.fixture
def skip_if_graphai_unavailable(graphai_validate_url: str) -> None:
    """Skip test if GraphAiServer is not available.

    This fixture should be used in integration tests that require
    a running GraphAiServer instance.
    """
    if not check_graphai_server_health(graphai_validate_url):
        pytest.skip("GraphAiServer not reachable")
