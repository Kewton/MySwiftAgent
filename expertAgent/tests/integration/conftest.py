"""Pytest configuration and fixtures for integration tests.

This module provides fixtures for E2E tests that require real LLM API calls.
API keys are obtained from environment variables or MyVault, with proper fallback
to skip tests if API keys are unavailable.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(scope="session")
async def llm_api_key() -> str:
    """Get LLM API key for E2E tests.

    Priority order:
    1. Environment variable TEST_GOOGLE_API_KEY (CI/CD)
    2. MyVault (local development)
    3. Skip test if unavailable

    Returns:
        str: Google API key for testing.

    Raises:
        pytest.skip: If API key cannot be obtained.

    Usage:
        @pytest.mark.e2e
        @pytest.mark.llm_required
        async def test_workflow_with_real_llm(llm_api_key):
            # Use llm_api_key for actual LLM API calls
            ...
    """
    # Priority 1: Environment variable (CI/CD)
    api_key = os.getenv("TEST_GOOGLE_API_KEY")
    if api_key:
        return api_key

    # Priority 2: MyVault (local development)
    try:
        from app.core.myvault_client import MyVaultClient

        vault_client = MyVaultClient()
        api_key = await vault_client.get_secret("GOOGLE_API_KEY")
        if api_key:
            return api_key
    except Exception as e:
        pytest.skip(f"MyVault unavailable: {e}")

    # Priority 3: Skip test if API key not available
    pytest.skip(
        "LLM API key not available. "
        "Set TEST_GOOGLE_API_KEY environment variable or configure MyVault."
    )


@pytest.fixture(autouse=True, scope="function")
def mock_interface_definition_dependencies():
    """Auto-mock interface_definition node dependencies for all integration tests.

    This fixture automatically mocks JobqueueClient and SchemaMatcher used by
    the interface_definition node to prevent external API calls during tests.

    The fixture is auto-used (autouse=True) for all integration tests to ensure
    consistent behavior across all E2E test scenarios.

    Yields:
        tuple: (mock_jobqueue_client, mock_schema_matcher)

    Related Issue: GitHub Actions CI failures due to "All connection attempts failed"
    when interface_definition node tries to connect to jobqueue API.
    """
    # Helper functions to create mocks (copied from test_e2e_workflow.py)
    def create_mock_jobqueue_client():
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

    def create_mock_schema_matcher():
        mock_matcher = MagicMock()
        mock_matcher.find_or_create_interface_master = AsyncMock(
            return_value={"id": "im_test789", "name": "TestInterface"}
        )
        mock_matcher.find_or_create_task_master = AsyncMock(
            return_value={"id": "tm_test456", "name": "TestTask"}
        )
        return mock_matcher

    # Apply patches for interface_definition node
    with patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.JobqueueClient"
    ) as mock_client_class, patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.SchemaMatcher"
    ) as mock_matcher_class:
        # Setup return values
        mock_client_class.return_value = create_mock_jobqueue_client()
        mock_matcher_class.return_value = create_mock_schema_matcher()

        yield mock_client_class, mock_matcher_class
