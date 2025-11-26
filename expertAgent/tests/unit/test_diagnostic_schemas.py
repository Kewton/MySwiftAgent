"""Unit tests for diagnostic schemas.

Issue #171: Diagnostic Information Retrieval API Implementation.
Tests for Pydantic schema validation and serialization.
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.conversation_metadata import ConversationMetadata
from app.schemas.diagnostic import (
    DiagnosticInfo,
    DiagnosticListQuery,
    DiagnosticListResponse,
    DiagnosticSummary,
    LangfuseLink,
    MessageInfo,
    TokenUsage,
)


class TestConversationMetadata:
    """Tests for ConversationMetadata schema."""

    @pytest.mark.unit
    def test_create_minimal(self):
        """Test creating with minimal fields."""
        metadata = ConversationMetadata()

        assert metadata.trace_id is None
        assert metadata.job_id is None
        assert metadata.total_tokens == 0

    @pytest.mark.unit
    def test_create_full(self):
        """Test creating with all fields."""
        created = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        metadata = ConversationMetadata(
            trace_id="trace-123",
            prompt_version="v1.0",
            job_id="job-456",
            user_id="user-789",
            project_id="project-101",
            workflow_id="workflow-202",
            created_at=created,
            system_prompt="You are an assistant.",
            total_tokens=100,
            input_tokens=40,
            output_tokens=60,
        )

        assert metadata.trace_id == "trace-123"
        assert metadata.job_id == "job-456"
        assert metadata.total_tokens == 100

    @pytest.mark.unit
    def test_to_index_keys(self):
        """Test generating index keys."""
        metadata = ConversationMetadata(
            job_id="job-456",
            user_id="user-789",
            project_id="project-101",
        )

        keys = metadata.to_index_keys()

        assert keys["job_index"] == "job-456"
        assert keys["user_index"] == "user-789"
        assert keys["project_index"] == "project-101"
        assert "workflow_index" not in keys

    @pytest.mark.unit
    def test_to_index_keys_empty(self):
        """Test generating index keys when all are None."""
        metadata = ConversationMetadata()

        keys = metadata.to_index_keys()

        assert keys == {}

    @pytest.mark.unit
    def test_to_dict(self):
        """Test converting to dictionary."""
        created = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        metadata = ConversationMetadata(
            job_id="job-456",
            created_at=created,
            total_tokens=100,
        )

        data = metadata.to_dict()

        assert data["job_id"] == "job-456"
        assert data["total_tokens"] == 100
        assert "2025-01-15" in data["created_at"]

    @pytest.mark.unit
    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "job_id": "job-456",
            "user_id": "user-789",
            "total_tokens": 100,
        }

        metadata = ConversationMetadata.from_dict(data)

        assert metadata.job_id == "job-456"
        assert metadata.user_id == "user-789"
        assert metadata.total_tokens == 100

    @pytest.mark.unit
    def test_token_validation(self):
        """Test token fields validation."""
        with pytest.raises(ValidationError):
            ConversationMetadata(total_tokens=-1)


class TestMessageInfo:
    """Tests for MessageInfo schema."""

    @pytest.mark.unit
    def test_create_minimal(self):
        """Test creating with required fields only."""
        msg = MessageInfo(role="user", content="Hello")

        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp is None
        assert msg.tokens is None

    @pytest.mark.unit
    def test_create_full(self):
        """Test creating with all fields."""
        ts = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        msg = MessageInfo(
            role="assistant",
            content="Hi there!",
            timestamp=ts,
            tokens=50,
        )

        assert msg.role == "assistant"
        assert msg.content == "Hi there!"
        assert msg.timestamp == ts
        assert msg.tokens == 50

    @pytest.mark.unit
    def test_missing_required_fields(self):
        """Test validation error for missing required fields."""
        with pytest.raises(ValidationError):
            MessageInfo(role="user")


class TestTokenUsage:
    """Tests for TokenUsage schema."""

    @pytest.mark.unit
    def test_defaults(self):
        """Test default values."""
        usage = TokenUsage()

        assert usage.total_tokens == 0
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0

    @pytest.mark.unit
    def test_create_with_values(self):
        """Test creating with values."""
        usage = TokenUsage(
            total_tokens=100,
            input_tokens=40,
            output_tokens=60,
        )

        assert usage.total_tokens == 100
        assert usage.input_tokens == 40
        assert usage.output_tokens == 60

    @pytest.mark.unit
    def test_negative_validation(self):
        """Test that negative values are rejected."""
        with pytest.raises(ValidationError):
            TokenUsage(total_tokens=-1)


class TestLangfuseLink:
    """Tests for LangfuseLink schema."""

    @pytest.mark.unit
    def test_defaults(self):
        """Test default values."""
        link = LangfuseLink()

        assert link.trace_id is None
        assert link.trace_url is None
        assert link.session_id is None

    @pytest.mark.unit
    def test_create_with_values(self):
        """Test creating with values."""
        link = LangfuseLink(
            trace_id="trace-123",
            trace_url="http://localhost:3000/trace/trace-123",
            session_id="session-456",
        )

        assert link.trace_id == "trace-123"
        assert link.trace_url == "http://localhost:3000/trace/trace-123"
        assert link.session_id == "session-456"


class TestDiagnosticInfo:
    """Tests for DiagnosticInfo schema."""

    @pytest.mark.unit
    def test_create_minimal(self):
        """Test creating with minimal fields."""
        info = DiagnosticInfo(conversation_id="conv-123")

        assert info.conversation_id == "conv-123"
        assert info.job_id is None
        assert info.messages == []
        assert info.token_usage.total_tokens == 0

    @pytest.mark.unit
    def test_create_full(self):
        """Test creating with all fields."""
        created = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        info = DiagnosticInfo(
            conversation_id="conv-123",
            job_id="job-456",
            user_id="user-789",
            project_id="project-101",
            workflow_id="workflow-202",
            system_prompt="You are an assistant.",
            messages=[
                MessageInfo(role="user", content="Hello"),
                MessageInfo(role="assistant", content="Hi!"),
            ],
            token_usage=TokenUsage(total_tokens=100),
            langfuse_link=LangfuseLink(trace_id="trace-123"),
            prompt_version="v1.0",
            created_at=created,
            metadata={"custom": "value"},
        )

        assert info.conversation_id == "conv-123"
        assert info.job_id == "job-456"
        assert len(info.messages) == 2
        assert info.token_usage.total_tokens == 100
        assert info.metadata["custom"] == "value"


class TestDiagnosticListQuery:
    """Tests for DiagnosticListQuery schema."""

    @pytest.mark.unit
    def test_defaults(self):
        """Test default values."""
        query = DiagnosticListQuery()

        assert query.job_id is None
        assert query.user_id is None
        assert query.limit == 100
        assert query.offset == 0

    @pytest.mark.unit
    def test_create_with_filters(self):
        """Test creating with filters."""
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)
        query = DiagnosticListQuery(
            job_id="job-456",
            user_id="user-789",
            start_date=start,
            end_date=end,
            limit=50,
            offset=10,
        )

        assert query.job_id == "job-456"
        assert query.limit == 50
        assert query.offset == 10

    @pytest.mark.unit
    def test_limit_validation_min(self):
        """Test that limit minimum is 1."""
        with pytest.raises(ValidationError):
            DiagnosticListQuery(limit=0)

    @pytest.mark.unit
    def test_limit_validation_max(self):
        """Test that limit maximum is 1000."""
        with pytest.raises(ValidationError):
            DiagnosticListQuery(limit=1001)

    @pytest.mark.unit
    def test_offset_validation(self):
        """Test that offset minimum is 0."""
        with pytest.raises(ValidationError):
            DiagnosticListQuery(offset=-1)


class TestDiagnosticListResponse:
    """Tests for DiagnosticListResponse schema."""

    @pytest.mark.unit
    def test_defaults(self):
        """Test default values."""
        response = DiagnosticListResponse()

        assert response.items == []
        assert response.total == 0
        assert response.limit == 100
        assert response.offset == 0
        assert response.has_more is False

    @pytest.mark.unit
    def test_create_with_items(self):
        """Test creating with items."""
        items = [
            DiagnosticInfo(conversation_id="conv-1"),
            DiagnosticInfo(conversation_id="conv-2"),
        ]
        response = DiagnosticListResponse(
            items=items,
            total=10,
            limit=2,
            offset=0,
            has_more=True,
        )

        assert len(response.items) == 2
        assert response.total == 10
        assert response.has_more is True


class TestDiagnosticSummary:
    """Tests for DiagnosticSummary schema."""

    @pytest.mark.unit
    def test_defaults(self):
        """Test default values."""
        summary = DiagnosticSummary()

        assert summary.total_conversations == 0
        assert summary.total_tokens == 0
        assert summary.average_tokens == 0.0
        assert summary.unique_users == 0
        assert summary.unique_jobs == 0

    @pytest.mark.unit
    def test_create_with_values(self):
        """Test creating with values."""
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)
        summary = DiagnosticSummary(
            total_conversations=100,
            total_tokens=50000,
            average_tokens=500.0,
            unique_users=25,
            unique_jobs=10,
            date_range_start=start,
            date_range_end=end,
        )

        assert summary.total_conversations == 100
        assert summary.average_tokens == 500.0
        assert summary.unique_users == 25
