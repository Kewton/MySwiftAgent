"""L0 conftest.py - Root level pytest configuration.

This is the root-level conftest.py that provides:
- Custom pytest markers for integration tests
- project_root fixture for accessing the repository root
"""

from pathlib import Path

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers for integration tests."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "llm_required: mark test as requiring LLM API access")
    config.addinivalue_line("markers", "production: mark test as production-critical")
    config.addinivalue_line("markers", "critical: mark test as critical path")
    config.addinivalue_line("markers", "slow: mark test as slow-running")
    # New markers for acceptance tests (Issue #213)
    config.addinivalue_line("markers", "platform: mark test as Platform layer test")
    config.addinivalue_line("markers", "agent: mark test as Agent layer test")
    config.addinivalue_line("markers", "frontend: mark test as Frontend layer test")
    config.addinivalue_line("markers", "requires_api_key: mark test as requiring external API key")
    config.addinivalue_line("markers", "acceptance: mark test as acceptance test (local-only)")


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Get the repository root directory.

    Returns:
        Path: The absolute path to the repository root.
    """
    return Path(__file__).parent.parent
