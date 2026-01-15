"""Unit tests for PendingWorkflowValidator.

Issue #353: Tests for __PENDING__ workflow detection and validation.
"""

from aiagent.langgraph.jobGeneratorV2.protocols import ErrorType
from aiagent.langgraph.jobGeneratorV2.validators.pending_workflow import (
    PENDING_PLACEHOLDER,
    PendingWorkflowValidationResult,
    PendingWorkflowValidator,
)


class TestPendingWorkflowValidationResult:
    """Tests for PendingWorkflowValidationResult dataclass."""

    def test_no_pending_result(self) -> None:
        """Result should indicate no pending workflows."""
        result = PendingWorkflowValidationResult(
            has_pending=False,
            pending_task_master_ids=[],
            task_details=[],
        )
        assert not result.has_pending
        assert len(result.pending_task_master_ids) == 0
        assert len(result.task_details) == 0

    def test_pending_result(self) -> None:
        """Result should indicate pending workflows."""
        result = PendingWorkflowValidationResult(
            has_pending=True,
            pending_task_master_ids=["tm_001", "tm_002"],
            task_details=[
                {"id": "tm_001", "name": "Task 1", "workflow_name": "__PENDING__"},
                {"id": "tm_002", "name": "Task 2", "workflow_name": "__PENDING__"},
            ],
        )
        assert result.has_pending
        assert len(result.pending_task_master_ids) == 2
        assert "tm_001" in result.pending_task_master_ids

    def test_get_error_message(self) -> None:
        """Error message should contain pending task details."""
        result = PendingWorkflowValidationResult(
            has_pending=True,
            pending_task_master_ids=["tm_001"],
            task_details=[
                {"id": "tm_001", "name": "Task 1", "workflow_name": "__PENDING__"},
            ],
        )
        error_msg = result.get_error_message()
        assert "tm_001" in error_msg
        assert "__PENDING__" in error_msg or "未完了" in error_msg


class TestPendingWorkflowValidator:
    """Tests for PendingWorkflowValidator."""

    def test_validator_initialization(self) -> None:
        """Validator should initialize properly."""
        validator = PendingWorkflowValidator()
        assert validator is not None

    def test_validate_no_pending(self) -> None:
        """Validate should pass when no __PENDING__ exists."""
        validator = PendingWorkflowValidator()
        task_masters = [
            {
                "id": "tm_001",
                "body_template": {"workflow_name": "workflow_task_001"},
            },
            {
                "id": "tm_002",
                "body_template": {"workflow_name": "workflow_task_002"},
            },
        ]
        result = validator.validate(task_masters)
        assert not result.has_pending
        assert len(result.pending_task_master_ids) == 0

    def test_validate_with_pending(self) -> None:
        """Validate should detect __PENDING__ workflow names."""
        validator = PendingWorkflowValidator()
        task_masters = [
            {
                "id": "tm_001",
                "body_template": {"workflow_name": "workflow_task_001"},
            },
            {
                "id": "tm_002",
                "body_template": {"workflow_name": PENDING_PLACEHOLDER},
            },
            {
                "id": "tm_003",
                "body_template": {"workflow_name": PENDING_PLACEHOLDER},
            },
        ]
        result = validator.validate(task_masters)
        assert result.has_pending
        assert len(result.pending_task_master_ids) == 2
        assert "tm_002" in result.pending_task_master_ids
        assert "tm_003" in result.pending_task_master_ids

    def test_validate_empty_list(self) -> None:
        """Validate should handle empty task list."""
        validator = PendingWorkflowValidator()
        result = validator.validate([])
        assert not result.has_pending
        assert len(result.pending_task_master_ids) == 0

    def test_validate_missing_body_template(self) -> None:
        """Validate should handle missing body_template."""
        validator = PendingWorkflowValidator()
        task_masters = [
            {"id": "tm_001"},  # No body_template
            {
                "id": "tm_002",
                "body_template": None,  # None body_template
            },
        ]
        result = validator.validate(task_masters)
        # Tasks without body_template should not be counted as pending
        assert not result.has_pending

    def test_validate_missing_workflow_name(self) -> None:
        """Validate should handle missing workflow_name."""
        validator = PendingWorkflowValidator()
        task_masters = [
            {
                "id": "tm_001",
                "body_template": {},  # No workflow_name
            },
            {
                "id": "tm_002",
                "body_template": {"workflow_name": None},  # None workflow_name
            },
        ]
        result = validator.validate(task_masters)
        # Tasks without workflow_name should not be counted as pending
        # (They might be configured differently)
        assert not result.has_pending


class TestPendingPlaceholderConstant:
    """Tests for PENDING_PLACEHOLDER constant."""

    def test_pending_placeholder_value(self) -> None:
        """PENDING_PLACEHOLDER should be __PENDING__."""
        assert PENDING_PLACEHOLDER == "__PENDING__"


class TestErrorTypeIncompleteWorkflow:
    """Tests for ErrorType.INCOMPLETE_WORKFLOW."""

    def test_incomplete_workflow_error_type_exists(self) -> None:
        """ErrorType.INCOMPLETE_WORKFLOW should exist."""
        assert hasattr(ErrorType, "INCOMPLETE_WORKFLOW")
        assert ErrorType.INCOMPLETE_WORKFLOW.value == "incomplete_workflow"
