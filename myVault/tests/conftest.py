"""Pytest configuration and fixtures."""

import os
import shutil
from pathlib import Path

# Copy test config to expected location BEFORE importing app modules
test_config_src = Path(__file__).parent.parent / "config.test.yaml"
test_config_dst = Path(__file__).parent.parent / "config.yaml"
test_config_backup = Path(__file__).parent.parent / "config.yaml.backup"

# Backup existing config if it exists
if test_config_dst.exists() and not test_config_backup.exists():
    shutil.copy(test_config_dst, test_config_backup)

# Copy test config
shutil.copy(test_config_src, test_config_dst)

# Set test environment variables BEFORE importing app modules
os.environ["MSA_MASTER_KEY"] = "base64:jFi1bkzTyKQ5BLtw2dBDo1RItDXlKo8A5z2JbC6TExE="
os.environ["TOKEN_test-service"] = "test-token-123"
os.environ["TOKEN_other-service"] = "other-token-456"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app

# Test database URL
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def db_session():
    """Create a fresh database session for each test."""
    # Create test engine
    engine = create_engine(
        TEST_DATABASE_URL, connect_args={"check_same_thread": False}
    )

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    """Create a test client with test database."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Get authentication headers for test service."""
    return {"X-Service": "test-service", "X-Token": "test-token-123"}


def pytest_sessionfinish(session, exitstatus):
    """Restore original config after all tests complete."""
    test_config_dst = Path(__file__).parent.parent / "config.yaml"
    test_config_backup = Path(__file__).parent.parent / "config.yaml.backup"

    # Restore backup if it exists
    if test_config_backup.exists():
        shutil.copy(test_config_backup, test_config_dst)
        test_config_backup.unlink()  # Remove backup
