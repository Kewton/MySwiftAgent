"""Pytest configuration and fixtures."""

import os

# Set test environment variables BEFORE importing app modules
os.environ["MSA_MASTER_KEY"] = "base64:jFi1bkzTyKQ5BLtw2dBDo1RItDXlKo8A5z2JbC6TExE="
os.environ["ALLOWED_SERVICES"] = "test-service,other-service"
os.environ["TOKEN_test-service"] = "test-token-123"
os.environ["TOKEN_other-service"] = "other-token-456"
os.environ["ALLOW_test-service"] = "test:,common:"
os.environ["ALLOW_other-service"] = "other:"

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
