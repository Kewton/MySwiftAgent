"""Unit tests for JobMaster model."""

from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import new as ulid_new

from app.models.job import BackoffStrategy
from app.models.job_master import JobMaster


@pytest.mark.asyncio
async def test_job_master_creation(db_session: AsyncSession) -> None:
    """Test basic JobMaster instance creation."""
    master_id = f"jm_{ulid_new()}"

    master = JobMaster(
        id=master_id,
        name="Test Master",
        description="Test description",
        method="POST",
        url="https://example.com/api",
        headers={"Authorization": "Bearer token"},
        params={"key": "value"},
        body={"data": "test"},
        timeout_sec=60,
        max_attempts=3,
        backoff_strategy=BackoffStrategy.EXPONENTIAL,
        backoff_seconds=10.0,
        ttl_seconds=86400,
        tags=["test", "api"],
    )

    db_session.add(master)
    await db_session.commit()
    await db_session.refresh(master)

    assert master.id == master_id
    assert master.name == "Test Master"
    assert master.description == "Test description"
    assert master.method == "POST"
    assert master.url == "https://example.com/api"
    assert master.headers == {"Authorization": "Bearer token"}
    assert master.params == {"key": "value"}
    assert master.body == {"data": "test"}
    assert master.timeout_sec == 60
    assert master.max_attempts == 3
    assert master.backoff_strategy == BackoffStrategy.EXPONENTIAL
    assert master.backoff_seconds == 10.0
    assert master.ttl_seconds == 86400
    assert master.tags == ["test", "api"]
    assert master.is_active == 1  # SQLite stores bool as int
    assert isinstance(master.created_at, datetime)
    assert isinstance(master.updated_at, datetime)


@pytest.mark.asyncio
async def test_job_master_defaults(db_session: AsyncSession) -> None:
    """Test JobMaster default values."""
    master_id = f"jm_{ulid_new()}"

    master = JobMaster(
        id=master_id,
        name="Minimal Master",
        method="GET",
        url="https://example.com",
    )

    db_session.add(master)
    await db_session.commit()
    await db_session.refresh(master)

    # Check defaults
    assert master.description is None
    assert master.headers is None
    assert master.params is None
    assert master.body is None
    assert master.timeout_sec == 30
    assert master.max_attempts == 1
    assert master.backoff_strategy == BackoffStrategy.EXPONENTIAL
    assert master.backoff_seconds == 5.0
    assert master.ttl_seconds == 604800  # 7 days
    assert master.tags is None
    assert master.is_active == 1  # SQLite stores bool as int
    assert master.created_by is None
    assert master.updated_by is None


@pytest.mark.asyncio
async def test_job_master_is_active_flag(db_session: AsyncSession) -> None:
    """Test is_active flag for logical deletion."""
    master_id = f"jm_{ulid_new()}"

    master = JobMaster(
        id=master_id,
        name="Deletable Master",
        method="DELETE",
        url="https://example.com/resource",
        is_active=False,
    )

    db_session.add(master)
    await db_session.commit()
    await db_session.refresh(master)

    assert master.is_active == 0  # SQLite stores bool as int

    # Logical delete
    master.is_active = False
    await db_session.commit()
    await db_session.refresh(master)

    assert master.is_active == 0  # SQLite stores bool as int


@pytest.mark.asyncio
async def test_job_master_query_by_active(db_session: AsyncSession) -> None:
    """Test querying active masters."""
    # Create active master
    active_master = JobMaster(
        id=f"jm_{ulid_new()}",
        name="Active Master",
        method="GET",
        url="https://example.com/active",
        is_active=True,
    )

    # Create inactive master
    inactive_master = JobMaster(
        id=f"jm_{ulid_new()}",
        name="Inactive Master",
        method="GET",
        url="https://example.com/inactive",
        is_active=False,
    )

    db_session.add(active_master)
    db_session.add(inactive_master)
    await db_session.commit()

    # Query only active masters
    result = await db_session.execute(
        select(JobMaster).where(JobMaster.is_active == True)  # noqa: E712
    )
    active_masters = result.scalars().all()

    assert len(active_masters) == 1
    assert active_masters[0].name == "Active Master"


@pytest.mark.asyncio
async def test_job_master_audit_fields(db_session: AsyncSession) -> None:
    """Test audit fields (created_by, updated_by)."""
    master_id = f"jm_{ulid_new()}"

    master = JobMaster(
        id=master_id,
        name="Audited Master",
        method="POST",
        url="https://example.com/audit",
        created_by="user123",
        updated_by="user123",
    )

    db_session.add(master)
    await db_session.commit()
    await db_session.refresh(master)

    assert master.created_by == "user123"
    assert master.updated_by == "user123"

    # Update audit
    master.updated_by = "user456"
    await db_session.commit()
    await db_session.refresh(master)

    assert master.created_by == "user123"
    assert master.updated_by == "user456"


@pytest.mark.asyncio
async def test_job_master_complex_json_fields(db_session: AsyncSession) -> None:
    """Test complex nested JSON in headers, params, and body."""
    master_id = f"jm_{ulid_new()}"

    complex_body = {
        "user": {"name": "Alice", "age": 30, "settings": {"theme": "dark"}},
        "data": [1, 2, 3],
        "metadata": {"version": "1.0"},
    }

    master = JobMaster(
        id=master_id,
        name="Complex JSON Master",
        method="POST",
        url="https://example.com/complex",
        headers={"X-Custom": "value", "X-Nested": "data"},
        params={"filter": "active", "sort": "desc"},
        body=complex_body,
    )

    db_session.add(master)
    await db_session.commit()
    await db_session.refresh(master)

    assert master.headers == {"X-Custom": "value", "X-Nested": "data"}
    assert master.params == {"filter": "active", "sort": "desc"}
    assert master.body == complex_body
    assert master.body["user"]["settings"]["theme"] == "dark"  # type: ignore[index]
    assert master.body["data"] == [1, 2, 3]  # type: ignore[index]
