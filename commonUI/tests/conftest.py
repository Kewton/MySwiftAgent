"""Test configuration and fixtures for CommonUI tests."""

import os
from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_streamlit():
    """Mock Streamlit module for testing."""
    mock_st = Mock()
    mock_st.success = Mock()
    mock_st.error = Mock()
    mock_st.warning = Mock()
    mock_st.info = Mock()
    mock_st.toast = Mock()
    mock_st.secrets = {}
    return mock_st


@pytest.fixture
def clean_environment():
    """Provide a clean environment for testing."""
    # Store original environment
    original_env = os.environ.copy()

    # Clear relevant environment variables
    env_vars_to_clear = [
        'JOBQUEUE_BASE_URL',
        'JOBQUEUE_API_TOKEN',
        'MYSCHEDULER_BASE_URL',
        'MYSCHEDULER_API_TOKEN',
        'POLLING_INTERVAL',
        'DEFAULT_SERVICE',
        'OPERATION_MODE'
    ]

    for var in env_vars_to_clear:
        if var in os.environ:
            del os.environ[var]

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def sample_api_config():
    """Provide sample API configuration for testing."""
    from core.config import APIConfig
    return APIConfig(
        base_url="http://localhost:8001",
        token="test-token-123"
    )