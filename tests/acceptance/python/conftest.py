"""L1 conftest.py - Python acceptance test shared fixtures.

This module provides shared fixtures for Python acceptance tests:
- env_config: Environment configuration from environment variables
- ensure_services_running: Service availability verification
- async_client: Shared async HTTP client
- requires_api_key: Skip decorator for tests requiring API keys

Hierarchy:
- Inherits from L0 (tests/conftest.py): project_root, markers
- Provides L1 fixtures to L2 (platform/, agent/, e2e/)
"""

import os
from collections.abc import AsyncGenerator, Generator
from functools import wraps
from typing import Any, Callable, TypeVar

import httpx
import pytest
import pytest_asyncio

# Type variable for generic function wrapping
F = TypeVar("F", bound=Callable[..., Any])


@pytest.fixture(scope="session")
def env_config() -> dict[str, str | None]:
    """Load configuration from environment variables.

    Returns:
        dict: Environment configuration with service URLs and API keys.
    """
    return {
        "MYVAULT_URL": os.getenv("MYVAULT_URL", "http://localhost:8003"),
        "JOBQUEUE_URL": os.getenv("JOBQUEUE_URL", "http://localhost:8002"),
        "MYSCHEDULER_URL": os.getenv("MYSCHEDULER_URL", "http://localhost:8004"),
        "EXPERTAGENT_URL": os.getenv("EXPERTAGENT_URL", "http://localhost:8001"),
        "GRAPHAISERVER_URL": os.getenv("GRAPHAISERVER_URL", "http://localhost:8005"),
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
    }


@pytest.fixture(scope="session")
def service_urls(env_config: dict[str, str | None]) -> dict[str, str]:
    """Provide service URLs for acceptance tests.

    Args:
        env_config: Environment configuration dictionary.

    Returns:
        dict[str, str]: Mapping of service names to base URLs.
    """
    return {
        "myvault": env_config["MYVAULT_URL"] or "http://localhost:8003",
        "jobqueue": env_config["JOBQUEUE_URL"] or "http://localhost:8002",
        "myscheduler": env_config["MYSCHEDULER_URL"] or "http://localhost:8004",
        "expertagent": env_config["EXPERTAGENT_URL"] or "http://localhost:8001",
        "graphaiserver": env_config["GRAPHAISERVER_URL"] or "http://localhost:8005",
    }


def is_service_available(url: str, timeout: float = 5.0) -> bool:
    """Check if a service is available at the given URL.

    Args:
        url: The base URL of the service.
        timeout: Request timeout in seconds.

    Returns:
        bool: True if the service responds, False otherwise.
    """
    try:
        response = httpx.get(f"{url}/health", timeout=timeout)
        return response.status_code == 200
    except (httpx.RequestError, httpx.HTTPStatusError):
        return False


@pytest.fixture(scope="session")
def ensure_services_running(
    service_urls: dict[str, str],
) -> Generator[dict[str, str], None, None]:
    """Ensure required services are running for acceptance tests.

    This fixture verifies that all required services are available.
    It does not start services - services should be started externally.

    Args:
        service_urls: Dictionary of service URLs.

    Yields:
        dict[str, str]: The service URLs if all services are available.

    Raises:
        pytest.skip: If any required service is unavailable.
    """
    unavailable = []
    for name, url in service_urls.items():
        if not is_service_available(url):
            unavailable.append(f"{name} ({url})")

    if unavailable:
        pytest.skip(
            f"Required services not available: {', '.join(unavailable)}. "
            "Please start services with 'make dev-all' or appropriate command."
        )

    yield service_urls


def requires_api_key(key_name: str) -> Callable[[F], F]:
    """Decorator to skip tests if required API key is not set.

    Usage:
        @requires_api_key("GOOGLE_API_KEY")
        def test_llm_integration():
            ...

    Args:
        key_name: Name of the environment variable containing the API key.

    Returns:
        Callable: Decorated function that skips if key is missing.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not os.getenv(key_name):
                pytest.skip(f"{key_name} not set in environment")
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


@pytest_asyncio.fixture(scope="function")
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an async HTTP client for acceptance tests.

    Yields:
        httpx.AsyncClient: Configured async HTTP client with extended timeout.
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        yield client


@pytest.fixture(scope="session")
def test_timeout() -> int:
    """Get the test timeout value from environment.

    Returns:
        int: Timeout in seconds (default: 30).
    """
    return int(os.getenv("TEST_TIMEOUT", "30"))


@pytest.fixture(scope="session")
def test_retry_count() -> int:
    """Get the test retry count from environment.

    Returns:
        int: Number of retries (default: 3).
    """
    return int(os.getenv("TEST_RETRY_COUNT", "3"))
