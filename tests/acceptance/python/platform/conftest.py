"""L2 Platform conftest.py - Platform layer acceptance test fixtures.

This module provides fixtures specific to Platform layer acceptance tests:
- myvault_client: Client configured for MyVault service
- jobqueue_client: Client configured for JobQueue service
- myscheduler_client: Client configured for MyScheduler service
- Platform service health check utilities

Hierarchy:
- Inherits from L0 (tests/conftest.py): project_root, markers
- Inherits from L1 (tests/acceptance/python/conftest.py): env_config, service_urls
"""

from collections.abc import AsyncGenerator
from typing import Any

import httpx
import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def myvault_client(
    service_urls: dict[str, str],
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an async client configured for MyVault service.

    Args:
        service_urls: Dictionary of service URLs.

    Yields:
        httpx.AsyncClient: Client configured for MyVault.
    """
    base_url = service_urls["myvault"]
    async with httpx.AsyncClient(
        base_url=base_url,
        timeout=30.0,
    ) as client:
        yield client


@pytest_asyncio.fixture
async def jobqueue_client(
    service_urls: dict[str, str],
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an async client configured for JobQueue service.

    Args:
        service_urls: Dictionary of service URLs.

    Yields:
        httpx.AsyncClient: Client configured for JobQueue.
    """
    base_url = service_urls["jobqueue"]
    async with httpx.AsyncClient(
        base_url=base_url,
        timeout=30.0,
    ) as client:
        yield client


@pytest_asyncio.fixture
async def myscheduler_client(
    service_urls: dict[str, str],
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an async client configured for MyScheduler service.

    Args:
        service_urls: Dictionary of service URLs.

    Yields:
        httpx.AsyncClient: Client configured for MyScheduler.
    """
    base_url = service_urls["myscheduler"]
    async with httpx.AsyncClient(
        base_url=base_url,
        timeout=30.0,
    ) as client:
        yield client


@pytest.fixture
def platform_services() -> list[str]:
    """List of Platform layer services.

    Returns:
        list[str]: Names of Platform layer services.
    """
    return ["myvault", "jobqueue", "myscheduler", "valkey", "langfuse"]


@pytest.fixture
def check_platform_health(
    service_urls: dict[str, str],
) -> dict[str, Any]:
    """Check health status of all Platform services.

    Args:
        service_urls: Dictionary of service URLs.

    Returns:
        dict: Health status of each Platform service.
    """
    results: dict[str, Any] = {}
    platform_services = ["myvault", "jobqueue", "myscheduler"]

    for service in platform_services:
        url = service_urls.get(service)
        if url:
            try:
                response = httpx.get(f"{url}/health", timeout=5.0)
                results[service] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "status_code": response.status_code,
                }
            except httpx.RequestError as e:
                results[service] = {
                    "status": "unavailable",
                    "error": str(e),
                }
        else:
            results[service] = {"status": "not_configured"}

    return results
