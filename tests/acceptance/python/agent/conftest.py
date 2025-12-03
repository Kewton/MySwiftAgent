"""L2 Agent conftest.py - Agent layer acceptance test fixtures.

This module provides fixtures specific to Agent layer acceptance tests:
- expertagent_client: Client configured for ExpertAgent service
- graphaiserver_client: Client configured for GraphAI Server
- llm_api_key: LLM API key with skip-on-missing behavior
- mock_myvault: Mock MyVault client for testing without real MyVault

Hierarchy:
- Inherits from L0 (tests/conftest.py): project_root, markers
- Inherits from L1 (tests/acceptance/python/conftest.py): env_config, service_urls, check_services_health
"""

import os
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import pytest_asyncio

from tests.acceptance.python.conftest import check_services_health


@pytest_asyncio.fixture
async def expertagent_client(
    service_urls: dict[str, str],
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an async client configured for ExpertAgent service.

    Args:
        service_urls: Dictionary of service URLs.

    Yields:
        httpx.AsyncClient: Client configured for ExpertAgent.
    """
    base_url = service_urls["expertagent"]
    async with httpx.AsyncClient(
        base_url=base_url,
        timeout=120.0,  # Longer timeout for LLM operations
    ) as client:
        yield client


@pytest_asyncio.fixture
async def graphaiserver_client(
    service_urls: dict[str, str],
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an async client configured for GraphAI Server.

    Args:
        service_urls: Dictionary of service URLs.

    Yields:
        httpx.AsyncClient: Client configured for GraphAI Server.
    """
    base_url = service_urls["graphaiserver"]
    async with httpx.AsyncClient(
        base_url=base_url,
        timeout=120.0,  # Longer timeout for workflow operations
    ) as client:
        yield client


@pytest.fixture(scope="session")
def llm_api_key() -> str:
    """Get LLM API key for acceptance tests.

    Priority order:
    1. Environment variable TEST_GOOGLE_API_KEY (CI/CD)
    2. Environment variable GOOGLE_API_KEY
    3. Skip test if unavailable

    Returns:
        str: Google API key for testing.

    Raises:
        pytest.skip: If API key cannot be obtained.
    """
    # Priority 1: Test-specific environment variable
    api_key = os.getenv("TEST_GOOGLE_API_KEY")
    if api_key:
        return api_key

    # Priority 2: Standard environment variable
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        return api_key

    # Priority 3: Skip test if API key not available
    pytest.skip(
        "LLM API key not available. Set TEST_GOOGLE_API_KEY or GOOGLE_API_KEY environment variable."
    )
    return ""  # Never reached, but satisfies type checker


@pytest.fixture
def mock_myvault() -> MagicMock:
    """Create a mock MyVault client for testing.

    Returns:
        MagicMock: Mock client with common operations stubbed.
    """
    mock_client = MagicMock()
    mock_client.get_secret = AsyncMock(return_value="mock-secret-value")
    mock_client.get_secrets = AsyncMock(
        return_value={
            "OPENAI_API_KEY": "mock-openai-key",
            "GOOGLE_API_KEY": "mock-google-key",
            "ANTHROPIC_API_KEY": "mock-anthropic-key",
        }
    )
    mock_client.update_secret = AsyncMock(return_value=None)
    mock_client.health_check = AsyncMock(return_value=True)
    return mock_client


@pytest.fixture
def mock_jobqueue_client() -> MagicMock:
    """Create a mock JobQueue client for agent tests.

    Returns:
        MagicMock: Mock client with job operations stubbed.
    """
    mock_client = MagicMock()
    mock_client.create_job_master = AsyncMock(
        return_value={"id": "jm_test123", "name": "TestJobMaster"}
    )
    mock_client.create_task_master = AsyncMock(
        return_value={"id": "tm_test456", "name": "TestTaskMaster"}
    )
    mock_client.create_job = AsyncMock(
        return_value={
            "id": "job_uuid_test",
            "name": "Test Job",
            "master_id": "jm_test123",
        }
    )
    mock_client.validate_workflow = AsyncMock(
        return_value={"is_valid": True, "errors": [], "warnings": []}
    )
    return mock_client


@pytest.fixture
def agent_services() -> list[str]:
    """List of Agent layer services.

    Returns:
        list[str]: Names of Agent layer services.
    """
    return ["expertagent", "graphaiserver"]


@pytest.fixture
def check_agent_health(
    service_urls: dict[str, str],
    agent_services: list[str],
) -> dict[str, Any]:
    """Check health status of all Agent services.

    Uses the shared check_services_health helper from L1 conftest
    to avoid code duplication with platform/conftest.py.

    Args:
        service_urls: Dictionary of service URLs.
        agent_services: List of agent service names.

    Returns:
        dict[str, Any]: Health status of each Agent service.
    """
    return check_services_health(service_urls, agent_services)
