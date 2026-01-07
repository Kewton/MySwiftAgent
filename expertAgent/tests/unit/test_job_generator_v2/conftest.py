"""Pytest configuration for Job Generator V2 unit tests.

This conftest.py provides fixtures and configuration specific to
the Job Generator V2 tests, without the full application dependencies.

Uses anyio for async test support (via pytest-anyio plugin).
"""

import pytest


# Minimal fixtures for testing
@pytest.fixture
def sample_job_id() -> str:
    """Sample job ID for testing."""
    return "test-job-123"


@pytest.fixture
def sample_user_requirement() -> str:
    """Sample user requirement for testing."""
    return "Search Gmail for recent emails and summarize them"


# Use anyio for async test support
@pytest.fixture
def anyio_backend():
    """Set the async backend to asyncio."""
    return "asyncio"
