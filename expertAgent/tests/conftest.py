"""Pytest configuration and fixtures."""

import os
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from core.secrets import secrets_manager


@pytest.fixture(scope="session", autouse=True)
def enable_myvault_for_ci():
    """
    Enable MyVault for CI environments by providing a mock client.

    This fixture runs automatically for all tests and ensures that
    integration tests don't get skipped in CI due to MyVault being unavailable.
    """
    # Only mock if MyVault is not already enabled (CI environment)
    if not secrets_manager.myvault_enabled:
        # Create a mock MyVault client
        mock_client = MagicMock()

        # Configure mock responses
        mock_client.get_secret.return_value = "mock-secret-value"
        mock_client.get_secrets.return_value = {
            "OPENAI_API_KEY": "mock-openai-key",
            "GOOGLE_API_KEY": "mock-google-key",
            "ANTHROPIC_API_KEY": "mock-anthropic-key",
        }
        mock_client.update_secret.return_value = None
        mock_client.health_check.return_value = True

        # Set the mock client
        secrets_manager.myvault_client = mock_client
        secrets_manager.myvault_enabled = True

        # Also set environment variable for consistency
        os.environ["MYVAULT_ENABLED"] = "true"


@pytest.fixture
def client() -> TestClient:
    """Test client fixture."""
    return TestClient(app)


# ========================================
# Gmail Utility API Mock Fixtures
# ========================================


@pytest.fixture
def mock_gmail_service(monkeypatch):
    """Mock Gmail service with basic response."""
    mock_result = {
        "total_count": 5,
        "returned_count": 5,
        "emails": [],
    }

    def mock_get_emails(*args, **kwargs):
        return mock_result

    monkeypatch.setattr(
        "app.api.v1.gmail_utility_endpoints.get_emails_by_keyword", mock_get_emails
    )
    return mock_result


@pytest.fixture
def mock_gmail_service_with_data(monkeypatch):
    """Mock Gmail service with sample email data."""
    mock_result = {
        "total_count": 2,
        "returned_count": 2,
        "emails": [
            {
                "id": "abc123",
                "subject": "Test Email 1",
                "from": "sender1@example.com",
                "date": "Mon, 14 Oct 2025 07:10:00 +0900",
                "body_text": "This is test email 1",
                "snippet": "This is test email 1",
                "is_unread": True,
                "has_attachments": False,
                "labels": ["INBOX"],
                "to": ["recipient@example.com"],
                "cc": [],
                "thread_id": "thread123",
            },
            {
                "id": "def456",
                "subject": "Test Email 2",
                "from": "sender2@example.com",
                "date": "Tue, 15 Oct 2025 08:00:00 +0900",
                "body_text": "This is test email 2",
                "snippet": "This is test email 2",
                "is_unread": False,
                "has_attachments": True,
                "labels": ["INBOX", "IMPORTANT"],
                "to": ["recipient@example.com"],
                "cc": ["cc@example.com"],
                "thread_id": "thread456",
                "attachments": [{"filename": "test.pdf"}],
            },
        ],
    }

    def mock_get_emails(*args, **kwargs):
        return mock_result

    monkeypatch.setattr(
        "app.api.v1.gmail_utility_endpoints.get_emails_by_keyword", mock_get_emails
    )
    return mock_result


@pytest.fixture
def mock_gmail_service_empty(monkeypatch):
    """Mock Gmail service with empty result."""
    mock_result = {
        "total_count": 0,
        "returned_count": 0,
        "emails": [],
    }

    def mock_get_emails(*args, **kwargs):
        return mock_result

    monkeypatch.setattr(
        "app.api.v1.gmail_utility_endpoints.get_emails_by_keyword", mock_get_emails
    )
    return mock_result


@pytest.fixture
def mock_gmail_service_with_attachments(monkeypatch):
    """Mock Gmail service with attachment data."""
    mock_result = {
        "total_count": 1,
        "returned_count": 1,
        "emails": [
            {
                "id": "attach123",
                "subject": "Email with Attachments",
                "from": "sender@example.com",
                "date": "Mon, 14 Oct 2025 07:10:00 +0900",
                "body_text": "This email has attachments",
                "snippet": "This email has attachments",
                "is_unread": False,
                "has_attachments": True,
                "labels": ["INBOX"],
                "to": ["recipient@example.com"],
                "cc": [],
                "thread_id": "thread789",
                "attachments": [
                    {"filename": "report.pdf", "size": 1024},
                    {"filename": "image.png", "size": 2048},
                ],
            }
        ],
    }

    def mock_get_emails(*args, **kwargs):
        return mock_result

    monkeypatch.setattr(
        "app.api.v1.gmail_utility_endpoints.get_emails_by_keyword", mock_get_emails
    )
    return mock_result


@pytest.fixture
def mock_gmail_service_with_unread(monkeypatch):
    """Mock Gmail service with unread emails only."""
    mock_result = {
        "total_count": 2,
        "returned_count": 2,
        "emails": [
            {
                "id": "unread1",
                "subject": "Unread Email 1",
                "from": "sender@example.com",
                "date": "Mon, 14 Oct 2025 07:10:00 +0900",
                "body_text": "Unread email content",
                "snippet": "Unread email content",
                "is_unread": True,
                "has_attachments": False,
                "labels": ["INBOX", "UNREAD"],
                "to": ["recipient@example.com"],
                "cc": [],
                "thread_id": "thread111",
            },
            {
                "id": "unread2",
                "subject": "Unread Email 2",
                "from": "sender2@example.com",
                "date": "Tue, 15 Oct 2025 08:00:00 +0900",
                "body_text": "Another unread email",
                "snippet": "Another unread email",
                "is_unread": True,
                "has_attachments": False,
                "labels": ["INBOX", "UNREAD"],
                "to": ["recipient@example.com"],
                "cc": [],
                "thread_id": "thread222",
            },
        ],
    }

    def mock_get_emails(*args, **kwargs):
        return mock_result

    monkeypatch.setattr(
        "app.api.v1.gmail_utility_endpoints.get_emails_by_keyword", mock_get_emails
    )
    return mock_result
