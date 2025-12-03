"""L2 E2E conftest.py - End-to-end acceptance test fixtures.

This module provides fixtures specific to E2E acceptance tests:
- full_stack_services: Verify all services are running
- e2e_test_data: Sample test data for E2E scenarios
- cleanup_test_data: Cleanup fixture for test data

Hierarchy:
- Inherits from L0 (tests/conftest.py): project_root, markers
- Inherits from L1 (tests/acceptance/python/conftest.py): env_config, service_urls
"""

import uuid
from typing import Any, Generator

import httpx
import pytest


@pytest.fixture(scope="session")
def full_stack_services(
    service_urls: dict[str, str],
) -> Generator[dict[str, str], None, None]:
    """Ensure full stack (all services) is running for E2E tests.

    This fixture verifies that all services across all layers are available.

    Args:
        service_urls: Dictionary of service URLs.

    Yields:
        dict[str, str]: The service URLs if all services are available.

    Raises:
        pytest.skip: If any required service is unavailable.
    """
    unavailable = []

    for name, url in service_urls.items():
        try:
            response = httpx.get(f"{url}/health", timeout=10.0)
            if response.status_code != 200:
                unavailable.append(f"{name} ({url}): status {response.status_code}")
        except httpx.RequestError as e:
            unavailable.append(f"{name} ({url}): {e}")

    if unavailable:
        pytest.skip(
            f"E2E tests require all services running. "
            f"Unavailable: {', '.join(unavailable)}. "
            "Please start all services with 'make dev-all'."
        )

    yield service_urls


@pytest.fixture
def e2e_test_data() -> dict[str, Any]:
    """Provide sample test data for E2E scenarios.

    Returns:
        dict: Sample test data including job requests, workflows, etc.
    """
    test_id = str(uuid.uuid4())[:8]
    return {
        "test_id": test_id,
        "job_request": {
            "title": f"E2E Test Job {test_id}",
            "description": "Automated E2E test job for acceptance testing",
            "tasks": [
                {"name": "task1", "type": "simple", "order": 0},
                {"name": "task2", "type": "simple", "order": 1},
            ],
        },
        "workflow_request": {
            "name": f"E2E Test Workflow {test_id}",
            "description": "Automated E2E test workflow",
            "steps": [
                {"name": "step1", "action": "initialize"},
                {"name": "step2", "action": "process"},
                {"name": "step3", "action": "finalize"},
            ],
        },
        "user_data": {
            "email": f"test_{test_id}@example.com",
            "name": f"Test User {test_id}",
        },
    }


@pytest.fixture
def cleanup_test_data(
    service_urls: dict[str, str],
) -> Generator[list[dict[str, str]], None, None]:
    """Provide a cleanup mechanism for test data created during E2E tests.

    Yields:
        list: List to register created resources for cleanup.
    """
    created_resources: list[dict[str, str]] = []

    yield created_resources

    # Cleanup registered resources
    for resource in created_resources:
        service = resource.get("service")
        endpoint = resource.get("endpoint")
        resource_id = resource.get("id")

        if service and endpoint and resource_id:
            url = service_urls.get(service)
            if url:
                try:
                    httpx.delete(f"{url}{endpoint}/{resource_id}", timeout=5.0)
                except httpx.RequestError:
                    pass  # Ignore cleanup failures


@pytest.fixture
def e2e_timeout() -> int:
    """Get the E2E test timeout value.

    Returns:
        int: Timeout in seconds for E2E operations (default: 120).
    """
    return 120


@pytest.fixture
def scenario_context() -> dict[str, Any]:
    """Provide a shared context for multi-step E2E scenarios.

    Returns:
        dict: Empty context dictionary for storing scenario state.
    """
    return {}
