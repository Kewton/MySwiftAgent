"""L2 Platform conftest.py - Platform layer acceptance test fixtures.

This module provides fixtures specific to Platform layer acceptance tests:
- myvault_client: Client configured for MyVault service
- jobqueue_client: Client configured for JobQueue service
- myscheduler_client: Client configured for MyScheduler service
- Platform service health check utilities

Hierarchy:
- Inherits from L0 (tests/conftest.py): project_root, markers
- Inherits from L1 (tests/acceptance/python/conftest.py): env_config, service_urls, check_services_health
"""

from collections.abc import AsyncGenerator
from typing import Any

import httpx
import pytest
import pytest_asyncio

from tests.acceptance.python.conftest import check_services_health


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
    platform_services: list[str],
) -> dict[str, Any]:
    """Check health status of all Platform services.

    Uses the shared check_services_health helper from L1 conftest
    to avoid code duplication with agent/conftest.py.

    Args:
        service_urls: Dictionary of service URLs.
        platform_services: List of platform service names.

    Returns:
        dict[str, Any]: Health status of each Platform service.
    """
    # Filter to only HTTP services (exclude valkey, langfuse which have different health endpoints)
    http_services = [s for s in platform_services if s in service_urls]
    return check_services_health(service_urls, http_services)
