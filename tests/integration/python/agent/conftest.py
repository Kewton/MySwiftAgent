"""L2 Agent conftest.py - Agent service integration test fixtures.

This module provides fixtures specific to agent services:
- expertagent_client: Client for ExpertAgent service
- mock_myvault: Mock MyVault client for testing without real MyVault
- LLM API key management
- Mock fixtures for external services
"""

import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio

# ============================================================================
# ExpertAgent Client Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def expertagent_client(
    service_urls: dict[str, str],
) -> httpx.AsyncClient:
    """Provide an async client configured for ExpertAgent service.

    Args:
        service_urls: Dictionary of service URLs.

    Yields:
        httpx.AsyncClient: Client configured for ExpertAgent.
    """
    base_url = service_urls["expertagent"]
    async with httpx.AsyncClient(
        base_url=base_url,
        timeout=60.0,  # Longer timeout for LLM operations
    ) as client:
        yield client


# ============================================================================
# Mock MyVault Fixtures
# ============================================================================


@pytest.fixture
def mock_myvault() -> MagicMock:
    """Create a mock MyVault client.

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


@pytest.fixture(scope="session", autouse=True)
def enable_myvault_for_ci() -> None:
    """Enable MyVault mock for CI environments.

    This fixture automatically enables MyVault mock when running
    in CI environments where real MyVault is unavailable.
    """
    # Check if we're in CI or MyVault is not available
    if os.getenv("CI") or not os.getenv("MYVAULT_ENABLED"):
        os.environ["MYVAULT_ENABLED"] = "true"


# ============================================================================
# LLM API Key Fixtures
# ============================================================================


@pytest.fixture(scope="session")
async def llm_api_key() -> str:
    """Get LLM API key for E2E tests.

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


# ============================================================================
# JobQueue Client Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_jobqueue_client() -> MagicMock:
    """Create a mock JobQueue client for testing.

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
    mock_client.create_interface_master = AsyncMock(
        return_value={"id": "im_test789", "name": "TestInterface"}
    )
    mock_client.add_task_to_workflow = AsyncMock(
        return_value={"id": "jmt_test789", "workflow_id": "jm_test123"}
    )
    mock_client.validate_workflow = AsyncMock(
        return_value={"is_valid": True, "errors": [], "warnings": []}
    )
    mock_client.list_workflow_tasks = AsyncMock(
        return_value=[
            {"id": "jmt_001", "order": 0, "task_master_id": "tm_test456"},
            {"id": "jmt_002", "order": 1, "task_master_id": "tm_test457"},
        ]
    )
    mock_client.create_job = AsyncMock(
        return_value={
            "id": "job_uuid_test",
            "name": "Test Job",
            "master_id": "jm_test123",
        }
    )
    return mock_client


@pytest.fixture
def mock_schema_matcher() -> MagicMock:
    """Create a mock SchemaMatcher for testing.

    Returns:
        MagicMock: Mock matcher with schema operations stubbed.
    """
    mock_matcher = MagicMock()
    mock_matcher.find_or_create_interface_master = AsyncMock(
        return_value={"id": "im_test789", "name": "TestInterface"}
    )
    mock_matcher.find_or_create_task_master = AsyncMock(
        return_value={"id": "tm_test456", "name": "TestTask"}
    )
    return mock_matcher


@pytest.fixture(autouse=True, scope="function")
def mock_interface_definition_dependencies(
    mock_jobqueue_client: MagicMock,
    mock_schema_matcher: MagicMock,
) -> Any:
    """Auto-mock interface_definition node dependencies for all integration tests.

    This fixture automatically mocks JobqueueClient and SchemaMatcher used by
    the interface_definition node to prevent external API calls during tests.

    Yields:
        tuple: (mock_jobqueue_client_class, mock_schema_matcher_class)
    """
    try:
        with (
            patch(
                "aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.JobqueueClient"
            ) as mock_client_class,
            patch(
                "aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.SchemaMatcher"
            ) as mock_matcher_class,
        ):
            mock_client_class.return_value = mock_jobqueue_client
            mock_matcher_class.return_value = mock_schema_matcher
            yield mock_client_class, mock_matcher_class
    except ModuleNotFoundError:
        # Module not available, skip mocking
        yield None, None


# ============================================================================
# Gmail Service Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_gmail_service(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Mock Gmail service with basic response.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        dict: Mock result data.
    """
    mock_result: dict[str, Any] = {
        "total_count": 5,
        "returned_count": 5,
        "emails": [],
    }

    def mock_get_emails(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return mock_result

    try:
        monkeypatch.setattr(
            "app.api.v1.gmail_utility_endpoints.get_emails_by_keyword",
            mock_get_emails,
        )
    except AttributeError:
        pass  # Module not available

    return mock_result


@pytest.fixture
def mock_gmail_service_with_data(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Mock Gmail service with sample email data.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        dict: Mock result with sample emails.
    """
    mock_result: dict[str, Any] = {
        "total_count": 2,
        "returned_count": 2,
        "emails": [
            {
                "id": "abc123",
                "subject": "Test Email 1",
                "from": "sender1@example.com",
                "date": "Mon, 14 Oct 2025 07:10:00 +0900",
                "body_text": "This is test email 1",
                "snippet": "This is test email 1",
                "is_unread": True,
                "has_attachments": False,
                "labels": ["INBOX"],
                "to": ["recipient@example.com"],
                "cc": [],
                "thread_id": "thread123",
            },
            {
                "id": "def456",
                "subject": "Test Email 2",
                "from": "sender2@example.com",
                "date": "Tue, 15 Oct 2025 08:00:00 +0900",
                "body_text": "This is test email 2",
                "snippet": "This is test email 2",
                "is_unread": False,
                "has_attachments": True,
                "labels": ["INBOX", "IMPORTANT"],
                "to": ["recipient@example.com"],
                "cc": ["cc@example.com"],
                "thread_id": "thread456",
                "attachments": [{"filename": "test.pdf"}],
            },
        ],
    }

    def mock_get_emails(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return mock_result

    try:
        monkeypatch.setattr(
            "app.api.v1.gmail_utility_endpoints.get_emails_by_keyword",
            mock_get_emails,
        )
    except AttributeError:
        pass  # Module not available

    return mock_result
