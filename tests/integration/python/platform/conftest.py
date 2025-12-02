"""L2 Platform conftest.py - Platform service integration test fixtures.

This module provides fixtures specific to platform services:
- myvault_client: Client for MyVault service
- jobqueue_client: Client for JobQueue service
- myscheduler_client: Client for MyScheduler service
- Service-specific authentication and configuration
"""

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import Generator

import httpx
import pytest
import pytest_asyncio

# Optional imports - may not be available in all environments
try:
    from fastapi.testclient import TestClient

    FASTAPI_AVAILABLE = True
except ImportError:
    TestClient = None  # type: ignore
    FASTAPI_AVAILABLE = False

try:
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
    from sqlalchemy.orm import sessionmaker

    SQLALCHEMY_AVAILABLE = True
except ImportError:
    AsyncSession = None  # type: ignore
    async_sessionmaker = None  # type: ignore
    create_async_engine = None  # type: ignore
    sessionmaker = None  # type: ignore
    SQLALCHEMY_AVAILABLE = False


# ============================================================================
# MyVault Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def myvault_test_config(project_root: Path) -> Generator[None, None, None]:
    """Setup test configuration for MyVault.

    Copies test config and sets environment variables.
    """
    test_config_src = project_root / "myVault" / "config.test.yaml"
    test_config_dst = project_root / "myVault" / "config.yaml"
    test_config_backup = project_root / "myVault" / "config.yaml.backup"

    # Backup existing config if it exists
    if test_config_dst.exists() and not test_config_backup.exists():
        shutil.copy(test_config_dst, test_config_backup)

    # Copy test config if source exists
    if test_config_src.exists():
        shutil.copy(test_config_src, test_config_dst)

    # Set test environment variables
    os.environ["MSA_MASTER_KEY"] = "base64:jFi1bkzTyKQ5BLtw2dBDo1RItDXlKo8A5z2JbC6TExE="
    os.environ["TOKEN_test-service"] = "test-token-123"
    os.environ["TOKEN_other-service"] = "other-token-456"

    yield

    # Restore backup if it exists
    if test_config_backup.exists():
        shutil.copy(test_config_backup, test_config_dst)
        test_config_backup.unlink()


@pytest.fixture
def myvault_auth_headers() -> dict[str, str]:
    """Get authentication headers for MyVault test service.

    Returns:
        dict[str, str]: Headers with X-Service and X-Token.
    """
    return {"X-Service": "test-service", "X-Token": "test-token-123"}


@pytest_asyncio.fixture
async def myvault_client(
    service_urls: dict[str, str],
    myvault_auth_headers: dict[str, str],
) -> httpx.AsyncClient:
    """Provide an async client configured for MyVault service.

    Args:
        service_urls: Dictionary of service URLs.
        myvault_auth_headers: Authentication headers.

    Yields:
        httpx.AsyncClient: Client configured for MyVault.
    """
    base_url = service_urls["myvault"]
    async with httpx.AsyncClient(
        base_url=base_url,
        headers=myvault_auth_headers,
        timeout=30.0,
    ) as client:
        yield client


# ============================================================================
# JobQueue Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def jobqueue_test_db() -> Generator[str, None, None]:
    """Create a temporary test database for JobQueue.

    Creates an in-memory SQLite database with the JobQueue schema.
    """
    # Create temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        test_db_path = f.name

    # Set test database URL
    test_db_url = f"sqlite+aiosqlite:///{test_db_path}"
    os.environ["JOBQUEUE_DB_URL"] = test_db_url

    yield test_db_url

    # Cleanup
    if os.path.exists(test_db_path):
        os.unlink(test_db_path)


@pytest_asyncio.fixture
async def jobqueue_client(
    service_urls: dict[str, str],
) -> httpx.AsyncClient:
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


# ============================================================================
# MyScheduler Fixtures
# ============================================================================


@pytest.fixture
def myscheduler_temp_db() -> Generator[str, None, None]:
    """Create a temporary database for MyScheduler tests.

    Yields:
        str: Path to the temporary database file.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_db_path = f.name

    yield temp_db_path

    # Cleanup
    if os.path.exists(temp_db_path):
        os.unlink(temp_db_path)


@pytest_asyncio.fixture
async def myscheduler_client(
    service_urls: dict[str, str],
) -> httpx.AsyncClient:
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


# ============================================================================
# Shared Platform Fixtures
# ============================================================================


@pytest.fixture
def scripts_dir(project_root: Path) -> Path:
    """Get the scripts directory path.

    Args:
        project_root: Repository root path.

    Returns:
        Path: Path to the scripts directory.
    """
    return project_root / "scripts"


@pytest.fixture
def dev_start_script(scripts_dir: Path) -> Path:
    """Get the dev-start.sh script path.

    Args:
        scripts_dir: Scripts directory path.

    Returns:
        Path: Path to dev-start.sh.
    """
    return scripts_dir / "dev-start.sh"


@pytest.fixture
def docker_utils_script(scripts_dir: Path) -> Path:
    """Get the docker-utils.sh script path.

    Args:
        scripts_dir: Scripts directory path.

    Returns:
        Path: Path to docker-utils.sh.
    """
    return scripts_dir / "lib" / "docker-utils.sh"
