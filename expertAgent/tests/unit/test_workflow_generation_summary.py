"""Unit tests for WorkflowGenerationSummary models.

Issue #305 Extension: Task Workflow Traces Summary feature.

These tests verify the new Pydantic models for workflow generation summary
that will be used to display detailed information in the UI.
"""

from app.services.job_creation_state import (
    EvaluationSummary,
    FailureDetails,
    RetryInfo,
    TestExecutionSummary,
    WorkflowGenerationSummary,
    WorkflowStatusItem,
)


class TestTestExecutionSummary:
    """Tests for TestExecutionSummary model."""

    def test_default_values(self) -> None:
        """Test default field values."""
        summary = TestExecutionSummary()

        assert summary.http_status is None
        assert summary.is_valid is False
        assert summary.validation_errors == []
        assert summary.execution_time_ms is None

    def test_with_all_fields(self) -> None:
        """Test with all fields populated."""
        summary = TestExecutionSummary(
            http_status=200,
            is_valid=True,
            validation_errors=[],
            execution_time_ms=150,
        )

        assert summary.http_status == 200
        assert summary.is_valid is True
        assert summary.validation_errors == []
        assert summary.execution_time_ms == 150

    def test_with_validation_errors(self) -> None:
        """Test with validation errors."""
        errors = [
            "[input] Missing required field: title",
            "[output] Type mismatch: expected string, got number",
        ]
        summary = TestExecutionSummary(
            http_status=400,
            is_valid=False,
            validation_errors=errors,
            execution_time_ms=50,
        )

        assert summary.http_status == 400
        assert summary.is_valid is False
        assert len(summary.validation_errors) == 2
        assert "[input]" in summary.validation_errors[0]

    def test_serialization(self) -> None:
        """Test model serialization to dict."""
        summary = TestExecutionSummary(
            http_status=200,
            is_valid=True,
            validation_errors=[],
            execution_time_ms=100,
        )
        data = summary.model_dump()

        assert data["http_status"] == 200
        assert data["is_valid"] is True
        assert data["validation_errors"] == []
        assert data["execution_time_ms"] == 100


class TestEvaluationSummary:
    """Tests for EvaluationSummary model."""

    def test_default_values(self) -> None:
        """Test default field values."""
        evaluation = EvaluationSummary()

        assert evaluation.score is None
        assert evaluation.structural_score is None
        assert evaluation.requirement_score is None
        assert evaluation.output_quality_score is None
        assert evaluation.error_handling_score is None
        assert evaluation.test_data_quality_score is None
        assert evaluation.strengths == []
        assert evaluation.weaknesses == []
        assert evaluation.suggestions == []
        assert evaluation.confidence is None

    def test_with_all_scores(self) -> None:
        """Test with all evaluation scores."""
        evaluation = EvaluationSummary(
            score=85,
            structural_score=90,
            requirement_score=85,
            output_quality_score=80,
            error_handling_score=75,
            test_data_quality_score=88,
            strengths=["Good API usage", "Clean structure"],
            weaknesses=["Missing timeout handling"],
            suggestions=["Add retry logic"],
            confidence=0.92,
        )

        assert evaluation.score == 85
        assert evaluation.structural_score == 90
        assert evaluation.requirement_score == 85
        assert evaluation.output_quality_score == 80
        assert evaluation.error_handling_score == 75
        assert evaluation.test_data_quality_score == 88
        assert len(evaluation.strengths) == 2
        assert len(evaluation.weaknesses) == 1
        assert len(evaluation.suggestions) == 1
        assert evaluation.confidence == 0.92

    def test_partial_scores(self) -> None:
        """Test with partial scores only."""
        evaluation = EvaluationSummary(
            score=70,
            structural_score=75,
            suggestions=["Improve error handling"],
        )

        assert evaluation.score == 70
        assert evaluation.structural_score == 75
        assert evaluation.requirement_score is None
        assert evaluation.suggestions == ["Improve error handling"]

    def test_serialization(self) -> None:
        """Test model serialization to dict."""
        evaluation = EvaluationSummary(
            score=85,
            strengths=["Good design"],
            confidence=0.9,
        )
        data = evaluation.model_dump()

        assert data["score"] == 85
        assert data["strengths"] == ["Good design"]
        assert data["confidence"] == 0.9


class TestRetryInfo:
    """Tests for RetryInfo model."""

    def test_default_values(self) -> None:
        """Test default field values."""
        retry_info = RetryInfo()

        assert retry_info.retry_count == 0
        assert retry_info.max_retry == 3
        assert retry_info.generation_model is None

    def test_with_all_fields(self) -> None:
        """Test with all fields populated."""
        retry_info = RetryInfo(
            retry_count=2,
            max_retry=5,
            generation_model="gpt-4o-mini",
        )

        assert retry_info.retry_count == 2
        assert retry_info.max_retry == 5
        assert retry_info.generation_model == "gpt-4o-mini"

    def test_serialization(self) -> None:
        """Test model serialization to dict."""
        retry_info = RetryInfo(
            retry_count=1,
            max_retry=3,
            generation_model="gemini-2.5-flash",
        )
        data = retry_info.model_dump()

        assert data["retry_count"] == 1
        assert data["max_retry"] == 3
        assert data["generation_model"] == "gemini-2.5-flash"


class TestFailureDetails:
    """Tests for FailureDetails model."""

    def test_minimal_fields(self) -> None:
        """Test with minimal required fields."""
        failure = FailureDetails(failure_stage="yaml_generation")

        assert failure.failure_stage == "yaml_generation"
        assert failure.error_summary == {}
        assert failure.cause_analysis is None
        assert failure.recommendations == []
        assert failure.retry_history == []

    def test_with_all_fields(self) -> None:
        """Test with all fields populated."""
        failure = FailureDetails(
            failure_stage="workflow_execution",
            error_summary={
                "http_status": 400,
                "error_code": "INVALID_PARAMETER",
                "error_message": "Invalid voice parameter",
                "error_detail": "'ja-JP-Standard-A' is not valid",
            },
            cause_analysis={
                "category": "API parameter",
                "problem_location": 'node "tts_drive_upload"',
                "problem_field": "body.voice",
                "actual_value": "ja-JP-Standard-A",
                "expected_value": "alloy, echo, fable, onyx, nova, shimmer",
            },
            recommendations=[
                "Add voice enum constraint in Interface definition",
                "Regenerate workflow with correct voice options",
            ],
            retry_history=[
                {
                    "attempt": 1,
                    "error_message": "HTTP 400 - Invalid voice parameter",
                    "model_used": "gemini-2.5-flash",
                    "timestamp": "2025-12-24T10:00:00Z",
                },
                {
                    "attempt": 2,
                    "error_message": "HTTP 400 - Invalid voice parameter",
                    "model_used": "gpt-4o-mini",
                    "timestamp": "2025-12-24T10:01:00Z",
                },
            ],
        )

        assert failure.failure_stage == "workflow_execution"
        assert failure.error_summary["http_status"] == 400
        assert failure.cause_analysis is not None
        assert failure.cause_analysis["category"] == "API parameter"
        assert len(failure.recommendations) == 2
        assert len(failure.retry_history) == 2

    def test_valid_failure_stages(self) -> None:
        """Test all valid failure stage values."""
        valid_stages = [
            "yaml_generation",
            "schema_validation",
            "workflow_registration",
            "workflow_execution",
            "node_error",
            "output_validation",
            "quality_evaluation",
        ]

        for stage in valid_stages:
            failure = FailureDetails(failure_stage=stage)
            assert failure.failure_stage == stage

    def test_serialization(self) -> None:
        """Test model serialization to dict."""
        failure = FailureDetails(
            failure_stage="schema_validation",
            error_summary={"error_message": "Schema mismatch"},
            recommendations=["Fix schema"],
        )
        data = failure.model_dump()

        assert data["failure_stage"] == "schema_validation"
        assert data["error_summary"]["error_message"] == "Schema mismatch"
        assert data["recommendations"] == ["Fix schema"]


class TestWorkflowGenerationSummary:
    """Tests for WorkflowGenerationSummary model."""

    def test_default_values(self) -> None:
        """Test default field values."""
        summary = WorkflowGenerationSummary()

        assert summary.yaml_preview is None
        assert summary.sample_input is None
        assert summary.test_result is None
        assert summary.evaluation is None
        assert summary.retry_info is None
        assert summary.failure_details is None

    def test_success_scenario(self) -> None:
        """Test success scenario with all positive fields."""
        summary = WorkflowGenerationSummary(
            yaml_preview="version: 0.5\nnodes:\n  source: {}\n  build_prompt:...",
            sample_input={
                "title": "Sample Title",
                "sections": ["section1", "section2"],
                "script_style": "monologue",
            },
            test_result=TestExecutionSummary(
                http_status=200,
                is_valid=True,
                validation_errors=[],
                execution_time_ms=150,
            ),
            evaluation=EvaluationSummary(
                score=85,
                structural_score=90,
                requirement_score=85,
                output_quality_score=80,
                error_handling_score=75,
                test_data_quality_score=88,
                strengths=["Good API usage"],
                weaknesses=[],
                suggestions=["Add timeout handling"],
                confidence=0.92,
            ),
            retry_info=RetryInfo(
                retry_count=0,
                max_retry=3,
                generation_model="gpt-4o-mini",
            ),
            failure_details=None,
        )

        assert summary.yaml_preview is not None
        assert "version: 0.5" in summary.yaml_preview
        assert summary.sample_input is not None
        assert summary.sample_input["title"] == "Sample Title"
        assert summary.test_result is not None
        assert summary.test_result.http_status == 200
        assert summary.evaluation is not None
        assert summary.evaluation.score == 85
        assert summary.retry_info is not None
        assert summary.failure_details is None

    def test_failure_scenario(self) -> None:
        """Test failure scenario with failure details."""
        summary = WorkflowGenerationSummary(
            yaml_preview="version: 0.5\nnodes:\n  tts_drive_upload:...",
            sample_input={"voice_id": "ja-JP-Standard-A"},
            test_result=TestExecutionSummary(
                http_status=400,
                is_valid=False,
                validation_errors=["[output] Invalid response format"],
                execution_time_ms=50,
            ),
            evaluation=None,
            retry_info=RetryInfo(
                retry_count=3,
                max_retry=3,
                generation_model="gpt-4o-mini",
            ),
            failure_details=FailureDetails(
                failure_stage="workflow_execution",
                error_summary={
                    "http_status": 400,
                    "error_message": "Invalid voice parameter",
                },
                recommendations=["Fix voice parameter"],
            ),
        )

        assert summary.test_result is not None
        assert summary.test_result.http_status == 400
        assert summary.failure_details is not None
        assert summary.failure_details.failure_stage == "workflow_execution"
        assert summary.retry_info is not None
        assert summary.retry_info.retry_count == 3

    def test_yaml_preview_truncation(self) -> None:
        """Test that yaml_preview can hold truncated content."""
        long_yaml = "version: 0.5\n" + "  node_" + "a" * 1000 + ": {}\n"
        truncated = long_yaml[:500]

        summary = WorkflowGenerationSummary(yaml_preview=truncated)

        assert summary.yaml_preview is not None
        assert len(summary.yaml_preview) == 500

    def test_serialization(self) -> None:
        """Test model serialization to dict and JSON."""
        summary = WorkflowGenerationSummary(
            yaml_preview="version: 0.5",
            sample_input={"key": "value"},
            test_result=TestExecutionSummary(http_status=200, is_valid=True),
            evaluation=EvaluationSummary(score=85),
            retry_info=RetryInfo(retry_count=1),
        )

        data = summary.model_dump()

        assert data["yaml_preview"] == "version: 0.5"
        assert data["sample_input"] == {"key": "value"}
        assert data["test_result"]["http_status"] == 200
        assert data["evaluation"]["score"] == 85
        assert data["retry_info"]["retry_count"] == 1

    def test_json_serialization(self) -> None:
        """Test JSON serialization."""
        summary = WorkflowGenerationSummary(
            yaml_preview="version: 0.5",
            sample_input={"key": "value"},
        )

        json_str = summary.model_dump_json()

        assert "version: 0.5" in json_str
        # JSON may have no spaces (compact) or spaces (pretty)
        assert '"key":"value"' in json_str or '"key": "value"' in json_str


class TestWorkflowStatusItemWithSummary:
    """Tests for WorkflowStatusItem with summary field."""

    def test_without_summary(self) -> None:
        """Test backward compatibility without summary field."""
        item = WorkflowStatusItem(
            task_id="task_01",
            task_name="Generate Script",
            status="success",
            workflow_name="workflow_generate_script",
            generation_time_ms=1200,
            error_message=None,
            langfuse_trace_id="trace_abc123",
        )

        assert item.task_id == "task_01"
        assert item.status == "success"
        assert item.summary is None

    def test_with_summary(self) -> None:
        """Test with summary field populated."""
        summary = WorkflowGenerationSummary(
            yaml_preview="version: 0.5",
            sample_input={"title": "Test"},
            test_result=TestExecutionSummary(http_status=200, is_valid=True),
            evaluation=EvaluationSummary(score=85),
        )

        item = WorkflowStatusItem(
            task_id="task_01",
            task_name="Generate Script",
            status="success",
            workflow_name="workflow_generate_script",
            generation_time_ms=1200,
            summary=summary,
        )

        assert item.summary is not None
        assert item.summary.yaml_preview == "version: 0.5"
        assert item.summary.evaluation is not None
        assert item.summary.evaluation.score == 85

    def test_serialization_with_summary(self) -> None:
        """Test serialization including summary."""
        summary = WorkflowGenerationSummary(
            yaml_preview="version: 0.5",
            evaluation=EvaluationSummary(score=85),
        )

        item = WorkflowStatusItem(
            task_id="task_01",
            status="success",
            summary=summary,
        )

        data = item.model_dump()

        assert data["task_id"] == "task_01"
        assert data["summary"] is not None
        assert data["summary"]["yaml_preview"] == "version: 0.5"
        assert data["summary"]["evaluation"]["score"] == 85

    def test_failed_status_with_failure_details(self) -> None:
        """Test failed status with failure details in summary."""
        failure_details = FailureDetails(
            failure_stage="workflow_execution",
            error_summary={"http_status": 400, "error_message": "API error"},
            recommendations=["Check API parameters"],
        )

        summary = WorkflowGenerationSummary(
            yaml_preview="version: 0.5",
            failure_details=failure_details,
        )

        item = WorkflowStatusItem(
            task_id="task_01",
            status="failed",
            error_message="HTTP 400 - API error",
            summary=summary,
        )

        assert item.status == "failed"
        assert item.error_message == "HTTP 400 - API error"
        assert item.summary is not None
        assert item.summary.failure_details is not None
        assert item.summary.failure_details.failure_stage == "workflow_execution"
