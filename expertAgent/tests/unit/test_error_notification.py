"""Unit tests for ErrorNotification model.

Issue #353: Tests for error notification structure for API responses.
"""

from datetime import datetime

import pytest

from aiagent.langgraph.jobGeneratorV2.types import Phase
from aiagent.langgraph.jobGeneratorV2.validators.pending_workflow import (
    ErrorNotification,
    NotificationLevel,
)


class TestNotificationLevel:
    """Tests for NotificationLevel enum."""

    def test_info_level(self) -> None:
        """INFO level should exist."""
        assert NotificationLevel.INFO.value == "info"

    def test_warning_level(self) -> None:
        """WARNING level should exist."""
        assert NotificationLevel.WARNING.value == "warning"

    def test_error_level(self) -> None:
        """ERROR level should exist."""
        assert NotificationLevel.ERROR.value == "error"

    def test_critical_level(self) -> None:
        """CRITICAL level should exist."""
        assert NotificationLevel.CRITICAL.value == "critical"


class TestErrorNotification:
    """Tests for ErrorNotification dataclass."""

    def test_basic_creation(self) -> None:
        """ErrorNotification should be created with required fields."""
        notification = ErrorNotification(
            job_id="job-123",
            phase=Phase.WORKFLOW_GEN,
            timestamp=datetime.now(),
            level=NotificationLevel.ERROR,
            title="Workflow generation incomplete",
            message="2 tasks still have __PENDING__ workflow_name",
            details={"pending_count": 2, "total_tasks": 3},
            suggested_actions=["Check GraphAiServer connectivity"],
            can_retry=True,
            requires_user_action=False,
        )
        assert notification.job_id == "job-123"
        assert notification.phase == Phase.WORKFLOW_GEN
        assert notification.level == NotificationLevel.ERROR
        assert notification.can_retry is True
        assert notification.requires_user_action is False

    def test_optional_langfuse_trace_id(self) -> None:
        """langfuse_trace_id should be optional."""
        notification = ErrorNotification(
            job_id="job-123",
            phase=Phase.WORKFLOW_GEN,
            timestamp=datetime.now(),
            level=NotificationLevel.INFO,
            title="Retrying",
            message="Automatic retry in progress",
            details={},
            suggested_actions=[],
            can_retry=True,
            requires_user_action=False,
        )
        assert notification.langfuse_trace_id is None

        notification_with_trace = ErrorNotification(
            job_id="job-123",
            phase=Phase.WORKFLOW_GEN,
            timestamp=datetime.now(),
            level=NotificationLevel.INFO,
            title="Retrying",
            message="Automatic retry in progress",
            details={},
            suggested_actions=[],
            can_retry=True,
            requires_user_action=False,
            langfuse_trace_id="trace_abc123",
        )
        assert notification_with_trace.langfuse_trace_id == "trace_abc123"

    def test_to_dict(self) -> None:
        """to_dict should return serializable dictionary."""
        timestamp = datetime(2026, 1, 12, 10, 0, 0)
        notification = ErrorNotification(
            job_id="job-123",
            phase=Phase.WORKFLOW_GEN,
            timestamp=timestamp,
            level=NotificationLevel.ERROR,
            title="Test Title",
            message="Test message",
            details={"key": "value"},
            suggested_actions=["Action 1", "Action 2"],
            can_retry=True,
            requires_user_action=False,
            langfuse_trace_id="trace_123",
        )
        result = notification.to_dict()

        assert result["job_id"] == "job-123"
        assert result["phase"] == "workflow_gen"
        assert result["level"] == "error"
        assert result["title"] == "Test Title"
        assert result["message"] == "Test message"
        assert result["details"] == {"key": "value"}
        assert result["suggested_actions"] == ["Action 1", "Action 2"]
        assert result["can_retry"] is True
        assert result["requires_user_action"] is False
        assert result["langfuse_trace_id"] == "trace_123"


class TestErrorNotificationForPendingWorkflows:
    """Tests for ErrorNotification creation from pending workflow detection."""

    def test_create_from_pending_result(self) -> None:
        """Should create notification from PendingWorkflowValidationResult."""
        from aiagent.langgraph.jobGeneratorV2.validators.pending_workflow import (
            PendingWorkflowValidationResult,
            create_notification_from_pending_result,
        )

        result = PendingWorkflowValidationResult(
            has_pending=True,
            pending_task_master_ids=["tm_001", "tm_002"],
            task_details=[
                {"id": "tm_001", "name": "Task 1", "workflow_name": "__PENDING__"},
                {"id": "tm_002", "name": "Task 2", "workflow_name": "__PENDING__"},
            ],
        )

        notification = create_notification_from_pending_result(
            result=result,
            job_id="job-456",
            langfuse_trace_id="trace_xyz",
        )

        assert notification.job_id == "job-456"
        assert notification.phase == Phase.WORKFLOW_GEN
        assert notification.level == NotificationLevel.ERROR
        assert "2" in notification.message or "__PENDING__" in notification.message
        assert notification.can_retry is True
        assert notification.langfuse_trace_id == "trace_xyz"
