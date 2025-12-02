"""L1 conftest.py - Python integration test shared fixtures.

This module provides shared fixtures for Python integration tests:
- service_urls: Dictionary of service base URLs
- docker_compose_up: Fixture for starting services via docker-compose
- async_client: Shared async HTTP client
- Service availability checking with skip on unavailable
"""

import os
from typing import Any

import httpx
import pytest
import pytest_asyncio

# Default service URLs - can be overridden by environment variables
DEFAULT_SERVICE_URLS: dict[str, str] = {
    "myvault": os.getenv("MYVAULT_URL", "http://localhost:8003"),
    "jobqueue": os.getenv("JOBQUEUE_URL", "http://localhost:8002"),
    "myscheduler": os.getenv("MYSCHEDULER_URL", "http://localhost:8004"),
    "expertagent": os.getenv("EXPERTAGENT_URL", "http://localhost:8001"),
    "graphaiserver": os.getenv("GRAPHAISERVER_URL", "http://localhost:8005"),
}


@pytest.fixture(scope="session")
def service_urls() -> dict[str, str]:
    """Provide service URLs for integration tests.

    URLs can be overridden via environment variables:
    - MYVAULT_URL
    - JOBQUEUE_URL
    - MYSCHEDULER_URL
    - EXPERTAGENT_URL
    - GRAPHAISERVER_URL

    Returns:
        dict[str, str]: Mapping of service names to base URLs.
    """
    return DEFAULT_SERVICE_URLS.copy()


def is_service_available(url: str, timeout: float = 2.0) -> bool:
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
def check_service_availability(service_urls: dict[str, str]) -> dict[str, bool]:
    """Check availability of all services.

    Returns:
        dict[str, bool]: Mapping of service names to availability status.
    """
    return {name: is_service_available(url) for name, url in service_urls.items()}


def skip_if_service_unavailable(service_name: str) -> Any:
    """Create a pytest skip marker if service is unavailable.

    Usage:
        @pytest.mark.skipif(**skip_if_service_unavailable("myvault"))
        def test_myvault_api():
            ...

    Args:
        service_name: Name of the service to check.

    Returns:
        dict: Arguments for pytest.mark.skipif
    """
    url = DEFAULT_SERVICE_URLS.get(service_name, "")
    return {
        "condition": not is_service_available(url),
        "reason": f"{service_name} service is not available at {url}",
    }


@pytest_asyncio.fixture(scope="function")
async def async_client() -> httpx.AsyncClient:
    """Provide an async HTTP client for integration tests.

    Yields:
        httpx.AsyncClient: Configured async HTTP client.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest.fixture(scope="session")
def docker_compose_up(project_root: Any) -> None:
    """Placeholder fixture for docker-compose service management.

    In CI/CD environments, services should already be running.
    This fixture can be extended to start services locally if needed.

    Args:
        project_root: The repository root path.
    """
    # Services should be started externally (docker-compose up)
    # This fixture is a placeholder for future enhancements
    pass
