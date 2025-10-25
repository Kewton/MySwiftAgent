"""Pytest configuration and fixtures for integration tests.

This module provides fixtures for E2E tests that require real LLM API calls.
API keys are obtained from environment variables or MyVault, with proper fallback
to skip tests if API keys are unavailable.
"""

import os

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
