"""Test configuration and fixtures."""

import asyncio
import os
import tempfile

import httpx
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import create_app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_db():
    """Create test database."""
    # Create temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        test_db_path = f.name

    # Set test database URL
    test_db_url = f"sqlite+aiosqlite:///{test_db_path}"
    os.environ["JOBQUEUE_DB_URL"] = test_db_url

    # Create engine and tables
    engine = create_async_engine(test_db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    TestSessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async def get_test_db():
        async with TestSessionLocal() as session:
            yield session

    yield get_test_db

    # Cleanup
    await engine.dispose()
    os.unlink(test_db_path)


@pytest_asyncio.fixture
async def client(test_db):
    """Create test client."""
    app = create_app()
    app.dependency_overrides[get_db] = test_db

    transport = httpx.ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sync_client(test_db):
    """Create synchronous test client."""
    app = create_app()
    app.dependency_overrides[get_db] = test_db

    with TestClient(app) as client:
        yield client
