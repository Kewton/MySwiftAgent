"""Unit tests for workflow_generator schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.workflow_generator import (
    WorkflowGeneratorRequest,
    WorkflowGeneratorResponse,
    WorkflowResult,
)


class TestWorkflowGeneratorRequest:
    """Test WorkflowGeneratorRequest schema."""

    def test_valid_job_master_id_only(self):
        """Test valid request with job_master_id only."""
        request = WorkflowGeneratorRequest(job_master_id=123)
        assert request.job_master_id == 123
        assert request.task_master_id is None

    def test_valid_task_master_id_only(self):
        """Test valid request with task_master_id only."""
        request = WorkflowGeneratorRequest(task_master_id=456)
        assert request.job_master_id is None
        assert request.task_master_id == 456

    def test_invalid_both_none(self):
        """Test invalid request with both job_master_id and task_master_id as None."""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowGeneratorRequest()
        assert (
            "Exactly one of 'job_master_id' or 'task_master_id' must be provided"
            in str(exc_info.value)
        )

    def test_invalid_both_provided(self):
        """Test invalid request with both job_master_id and task_master_id provided."""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowGeneratorRequest(job_master_id=123, task_master_id=456)
        assert (
            "Exactly one of 'job_master_id' or 'task_master_id' must be provided"
            in str(exc_info.value)
        )


class TestWorkflowResult:
    """Test WorkflowResult schema."""

    def test_valid_success_workflow_result(self):
        """Test valid successful workflow result."""
        result = WorkflowResult(
            task_master_id=456,
            task_name="Send email notification",
            workflow_name="send_email_notification",
            yaml_content="version: 0.5\nnodes: {}",
            status="success",
            retry_count=0,
        )
        assert result.task_master_id == 456
        assert result.task_name == "Send email notification"
        assert result.workflow_name == "send_email_notification"
        assert result.status == "success"
        assert result.error_message is None
        assert result.retry_count == 0

    def test_valid_failed_workflow_result(self):
        """Test valid failed workflow result."""
        result = WorkflowResult(
            task_master_id=456,
            task_name="Send email notification",
            workflow_name="send_email_notification",
            yaml_content="",
            status="failed",
            error_message="LLM API timeout",
            retry_count=3,
        )
        assert result.status == "failed"
        assert result.error_message == "LLM API timeout"
        assert result.retry_count == 3

    def test_workflow_result_with_validation_result(self):
        """Test workflow result with validation result."""
        result = WorkflowResult(
            task_master_id=456,
            task_name="Send email notification",
            workflow_name="send_email_notification",
            yaml_content="version: 0.5\nnodes: {}",
            status="success",
            validation_result={
                "is_valid": True,
                "errors": [],
                "http_status": 200,
            },
            retry_count=1,
        )
        assert result.validation_result is not None
        assert result.validation_result["is_valid"] is True
        assert result.retry_count == 1


class TestWorkflowGeneratorResponse:
    """Test WorkflowGeneratorResponse schema."""

    def test_valid_success_response_single_task(self):
        """Test valid success response with single task."""
        response = WorkflowGeneratorResponse(
            status="success",
            workflows=[
                WorkflowResult(
                    task_master_id=456,
                    task_name="Send email notification",
                    workflow_name="send_email_notification",
                    yaml_content="version: 0.5\nnodes: {}",
                    status="success",
                    retry_count=0,
                )
            ],
            total_tasks=1,
            successful_tasks=1,
            failed_tasks=0,
            generation_time_ms=1234.5,
        )
        assert response.status == "success"
        assert len(response.workflows) == 1
        assert response.total_tasks == 1
        assert response.successful_tasks == 1
        assert response.failed_tasks == 0
        assert response.generation_time_ms == 1234.5

    def test_valid_success_response_multiple_tasks(self):
        """Test valid success response with multiple tasks."""
        response = WorkflowGeneratorResponse(
            status="success",
            workflows=[
                WorkflowResult(
                    task_master_id=1,
                    task_name="Task 1",
                    workflow_name="task_1",
                    yaml_content="version: 0.5\nnodes: {}",
                    status="success",
                    retry_count=0,
                ),
                WorkflowResult(
                    task_master_id=2,
                    task_name="Task 2",
                    workflow_name="task_2",
                    yaml_content="version: 0.5\nnodes: {}",
                    status="success",
                    retry_count=0,
                ),
                WorkflowResult(
                    task_master_id=3,
                    task_name="Task 3",
                    workflow_name="task_3",
                    yaml_content="version: 0.5\nnodes: {}",
                    status="success",
                    retry_count=0,
                ),
            ],
            total_tasks=3,
            successful_tasks=3,
            failed_tasks=0,
            generation_time_ms=5432.1,
        )
        assert response.status == "success"
        assert len(response.workflows) == 3
        assert response.total_tasks == 3
        assert response.successful_tasks == 3
        assert response.failed_tasks == 0

    def test_valid_partial_success_response(self):
        """Test valid partial success response."""
        response = WorkflowGeneratorResponse(
            status="partial_success",
            workflows=[
                WorkflowResult(
                    task_master_id=1,
                    task_name="Task 1",
                    workflow_name="task_1",
                    yaml_content="version: 0.5\nnodes: {}",
                    status="success",
                    retry_count=0,
                ),
                WorkflowResult(
                    task_master_id=2,
                    task_name="Task 2",
                    workflow_name="task_2",
                    yaml_content="",
                    status="failed",
                    error_message="LLM API timeout",
                    retry_count=3,
                ),
            ],
            total_tasks=2,
            successful_tasks=1,
            failed_tasks=1,
            generation_time_ms=3456.7,
        )
        assert response.status == "partial_success"
        assert len(response.workflows) == 2
        assert response.total_tasks == 2
        assert response.successful_tasks == 1
        assert response.failed_tasks == 1

    def test_valid_failed_response(self):
        """Test valid failed response."""
        response = WorkflowGeneratorResponse(
            status="failed",
            workflows=[],
            total_tasks=0,
            successful_tasks=0,
            failed_tasks=0,
            generation_time_ms=0.0,
            error_message="JobqueueClient connection error",
        )
        assert response.status == "failed"
        assert len(response.workflows) == 0
        assert response.error_message == "JobqueueClient connection error"
