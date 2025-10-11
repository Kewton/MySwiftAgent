"""Pytest configuration and fixtures."""

import os
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from core.secrets import secrets_manager


@pytest.fixture(scope="session", autouse=True)
def enable_myvault_for_ci():
    """
    Enable MyVault for CI environments by providing a mock client.

    This fixture runs automatically for all tests and ensures that
    integration tests don't get skipped in CI due to MyVault being unavailable.
    """
    # Only mock if MyVault is not already enabled (CI environment)
    if not secrets_manager.myvault_enabled:
        # Create a mock MyVault client
        mock_client = MagicMock()

        # Configure mock responses
        mock_client.get_secret.return_value = "mock-secret-value"
        mock_client.get_secrets.return_value = {
            "OPENAI_API_KEY": "mock-openai-key",
            "GOOGLE_API_KEY": "mock-google-key",
            "ANTHROPIC_API_KEY": "mock-anthropic-key",
        }
        mock_client.update_secret.return_value = None
        mock_client.health_check.return_value = True

        # Set the mock client
        secrets_manager.myvault_client = mock_client
        secrets_manager.myvault_enabled = True

        # Also set environment variable for consistency
        os.environ["MYVAULT_ENABLED"] = "true"


@pytest.fixture
def client() -> TestClient:
    """Test client fixture."""
    return TestClient(app)
