"""Pending workflow validation for Job Generator V2.

Issue #353: Validates that WORKFLOW_GEN phase completed successfully
by checking for __PENDING__ placeholders in TaskMaster workflow_names.

This module provides:
- PENDING_PLACEHOLDER: The placeholder constant
- PendingWorkflowValidationResult: Result of validation
- PendingWorkflowValidator: Validates TaskMasters for pending workflows
- NotificationLevel: Enum for notification severity
- ErrorNotification: Notification data for API responses
- create_notification_from_pending_result: Helper to create notifications
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from aiagent.langgraph.jobGeneratorV2.types import Phase

logger = logging.getLogger(__name__)

# Issue #353: Placeholder constant for pending workflows
PENDING_PLACEHOLDER = "__PENDING__"


class NotificationLevel(Enum):
    """Notification severity levels.

    Issue #353: Used to indicate the severity of error notifications
    for display in UI and log categorization.
    """

    INFO = "info"  # Information (e.g., retry in progress)
    WARNING = "warning"  # Warning (e.g., retry count increasing)
    ERROR = "error"  # Error (e.g., phase failed)
    CRITICAL = "critical"  # Critical (e.g., unrecoverable failure)


@dataclass
class PendingWorkflowValidationResult:
    """Result of pending workflow validation.

    Issue #353: Contains information about TaskMasters that still have
    __PENDING__ workflow_name after WORKFLOW_GEN phase.

    Attributes:
        has_pending: True if any TaskMaster has __PENDING__ workflow_name
        pending_task_master_ids: List of TaskMaster IDs with pending workflows
        task_details: Detailed information about each pending task
    """

    has_pending: bool
    pending_task_master_ids: list[str] = field(default_factory=list)
    task_details: list[dict[str, Any]] = field(default_factory=list)

    def get_error_message(self) -> str:
        """Generate human-readable error message.

        Returns:
            Error message describing pending workflows.
        """
        if not self.has_pending:
            return ""

        count = len(self.pending_task_master_ids)
        ids_preview = ", ".join(self.pending_task_master_ids[:3])
        if count > 3:
            ids_preview += f"... (and {count - 3} more)"

        return (
            f"WORKFLOW_GEN phase incomplete: {count} task(s) still have "
            f"__PENDING__ workflow_name. Task IDs: {ids_preview}"
        )


class PendingWorkflowValidator:
    """Validates TaskMasters for pending workflow placeholders.

    Issue #353: Checks that all TaskMasters have valid workflow_names
    (not __PENDING__) after WORKFLOW_GEN phase completion.

    Example:
        validator = PendingWorkflowValidator()
        result = validator.validate(task_masters)
        if result.has_pending:
            raise WorkflowError(result.get_error_message(), ErrorType.INCOMPLETE_WORKFLOW)
    """

    def validate(
        self, task_masters: list[dict[str, Any]]
    ) -> PendingWorkflowValidationResult:
        """Validate TaskMasters for pending workflows.

        Args:
            task_masters: List of TaskMaster dictionaries with body_template

        Returns:
            PendingWorkflowValidationResult with validation outcome
        """
        pending_ids: list[str] = []
        task_details: list[dict[str, Any]] = []

        for task_master in task_masters:
            task_id = task_master.get("id", "unknown")
            body_template = task_master.get("body_template")

            if body_template is None:
                # No body_template - skip (not considered pending)
                logger.debug(
                    "Task %s has no body_template, skipping",
                    task_id,
                )
                continue

            workflow_name = body_template.get("workflow_name")

            if workflow_name is None:
                # No workflow_name - skip (might be configured differently)
                logger.debug(
                    "Task %s has no workflow_name in body_template, skipping",
                    task_id,
                )
                continue

            if workflow_name == PENDING_PLACEHOLDER:
                pending_ids.append(task_id)
                task_details.append(
                    {
                        "id": task_id,
                        "name": task_master.get("name", ""),
                        "workflow_name": workflow_name,
                    }
                )
                logger.warning(
                    "Task %s has pending workflow: %s",
                    task_id,
                    workflow_name,
                )

        has_pending = len(pending_ids) > 0

        if has_pending:
            logger.error(
                "Pending workflow validation failed: %d task(s) have __PENDING__",
                len(pending_ids),
            )
        else:
            logger.info("Pending workflow validation passed: all workflows complete")

        return PendingWorkflowValidationResult(
            has_pending=has_pending,
            pending_task_master_ids=pending_ids,
            task_details=task_details,
        )


@dataclass
class ErrorNotification:
    """Error notification for API responses.

    Issue #353: Structured notification data for error communication
    to frontend/UI.

    Attributes:
        job_id: Job identifier
        phase: Phase where error occurred
        timestamp: When the notification was created
        level: Notification severity level
        title: Short title for the notification
        message: Detailed message
        details: Additional details as key-value pairs
        suggested_actions: List of suggested remediation actions
        can_retry: Whether the operation can be retried
        requires_user_action: Whether user intervention is needed
        langfuse_trace_id: Optional Langfuse trace ID for debugging
    """

    job_id: str
    phase: Phase
    timestamp: datetime
    level: NotificationLevel
    title: str
    message: str
    details: dict[str, Any]
    suggested_actions: list[str]
    can_retry: bool
    requires_user_action: bool
    langfuse_trace_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the notification.
        """
        return {
            "job_id": self.job_id,
            "phase": self.phase.value,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "title": self.title,
            "message": self.message,
            "details": self.details,
            "suggested_actions": self.suggested_actions,
            "can_retry": self.can_retry,
            "requires_user_action": self.requires_user_action,
            "langfuse_trace_id": self.langfuse_trace_id,
        }


def create_notification_from_pending_result(
    result: PendingWorkflowValidationResult,
    job_id: str,
    langfuse_trace_id: str | None = None,
) -> ErrorNotification:
    """Create ErrorNotification from PendingWorkflowValidationResult.

    Issue #353: Helper function to create a properly formatted notification
    from validation results.

    Args:
        result: Validation result with pending workflow info
        job_id: Job identifier
        langfuse_trace_id: Optional Langfuse trace ID

    Returns:
        ErrorNotification with appropriate fields set
    """
    pending_count = len(result.pending_task_master_ids)

    return ErrorNotification(
        job_id=job_id,
        phase=Phase.WORKFLOW_GEN,
        timestamp=datetime.now(),
        level=NotificationLevel.ERROR,
        title="WORKFLOW_GEN phase incomplete",
        message=f"{pending_count} task(s) still have __PENDING__ workflow_name",
        details={
            "pending_count": pending_count,
            "pending_task_master_ids": result.pending_task_master_ids,
            "task_details": result.task_details[:5],  # Limit to first 5
        },
        suggested_actions=[
            "Check GraphAiServer connectivity",
            "Verify LLM API key in myVault",
            "Review Langfuse trace for detailed error logs",
        ],
        can_retry=True,
        requires_user_action=False,
        langfuse_trace_id=langfuse_trace_id,
    )


__all__ = [
    "PENDING_PLACEHOLDER",
    "NotificationLevel",
    "PendingWorkflowValidationResult",
    "PendingWorkflowValidator",
    "ErrorNotification",
    "create_notification_from_pending_result",
]
