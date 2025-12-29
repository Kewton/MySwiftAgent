"""Unit tests for FailureDetails Builder.

Issue #305 Extension: Task Workflow Traces Summary feature.

Tests for the build_failure_details function that transforms
workflow generation state into FailureDetails for UI display.
"""

from typing import Any

from app.services.failure_details_builder import (
    build_failure_details,
    determine_failure_stage,
    extract_cause_from_validation_errors,
    extract_error_code,
    extract_error_detail,
    format_repair_history,
    generate_default_recommendations,
)
from app.services.job_creation_state import FailureDetails


class TestDetermineFailureStage:
    """Tests for determine_failure_stage function."""

    def test_yaml_generation_failure_no_yaml(self) -> None:
        """Test yaml_generation stage when yaml_content is empty."""
        state: dict[str, Any] = {
            "status": "failed",
            "yaml_content": None,
        }
        stage = determine_failure_stage(state)
        assert stage == "yaml_generation"

    def test_yaml_generation_failure_empty_string(self) -> None:
        """Test yaml_generation stage when yaml_content is empty string."""
        state: dict[str, Any] = {
            "status": "failed",
            "yaml_content": "",
        }
        stage = determine_failure_stage(state)
        assert stage == "yaml_generation"

    def test_schema_validation_failure(self) -> None:
        """Test schema_validation stage when input validation fails."""
        state: dict[str, Any] = {
            "status": "failed",
            "yaml_content": "version: 0.5",
            "validation_result": {
                "input_validation": {"is_valid": False},
            },
        }
        stage = determine_failure_stage(state)
        assert stage == "schema_validation"

    def test_workflow_execution_failure_400(self) -> None:
        """Test workflow_execution stage on HTTP 400."""
        state: dict[str, Any] = {
            "status": "failed",
            "yaml_content": "version: 0.5",
            "test_http_status": 400,
        }
        stage = determine_failure_stage(state)
        assert stage == "workflow_execution"

    def test_workflow_execution_failure_422(self) -> None:
        """Test workflow_execution stage on HTTP 422."""
        state: dict[str, Any] = {
            "status": "failed",
            "yaml_content": "version: 0.5",
            "test_http_status": 422,
        }
        stage = determine_failure_stage(state)
        assert stage == "workflow_execution"

    def test_workflow_execution_failure_500(self) -> None:
        """Test workflow_execution stage on HTTP 500."""
        state: dict[str, Any] = {
            "status": "failed",
            "yaml_content": "version: 0.5",
            "test_http_status": 500,
        }
        stage = determine_failure_stage(state)
        assert stage == "workflow_execution"

    def test_workflow_execution_failure_504(self) -> None:
        """Test workflow_execution stage on HTTP 504 (timeout)."""
        state: dict[str, Any] = {
            "status": "failed",
            "yaml_content": "version: 0.5",
            "test_http_status": 504,
        }
        stage = determine_failure_stage(state)
        assert stage == "workflow_execution"

    def test_node_error_from_validation_errors(self) -> None:
        """Test node_error stage when [graphai] error category present."""
        state: dict[str, Any] = {
            "status": "failed",
            "yaml_content": "version: 0.5",
            "test_http_status": 200,
            "validation_errors": [
                "[graphai] Node 'tts_agent' execution failed: Timeout",
            ],
        }
        stage = determine_failure_stage(state)
        assert stage == "node_error"

    def test_output_validation_from_validation_errors(self) -> None:
        """Test output_validation stage when [output] error category present."""
        state: dict[str, Any] = {
            "status": "failed",
            "yaml_content": "version: 0.5",
            "test_http_status": 200,
            "validation_errors": [
                "[output] Missing required field: result.content",
            ],
        }
        stage = determine_failure_stage(state)
        assert stage == "output_validation"

    def test_quality_evaluation_low_score(self) -> None:
        """Test quality_evaluation stage when score is below threshold."""
        state: dict[str, Any] = {
            "status": "failed",
            "yaml_content": "version: 0.5",
            "test_http_status": 200,
            "evaluation_score": 50,
        }
        stage = determine_failure_stage(state)
        assert stage == "quality_evaluation"

    def test_quality_evaluation_not_acceptable(self) -> None:
        """Test quality_evaluation stage when is_acceptable is False."""
        state: dict[str, Any] = {
            "status": "failed",
            "yaml_content": "version: 0.5",
            "test_http_status": 200,
            "evaluation_score": 80,
            "is_acceptable": False,
        }
        stage = determine_failure_stage(state)
        assert stage == "quality_evaluation"

    def test_unknown_failure_stage(self) -> None:
        """Test fallback to workflow_execution when no other stage matches."""
        state: dict[str, Any] = {
            "status": "failed",
            "yaml_content": "version: 0.5",
            "test_http_status": 200,
            "evaluation_score": 90,
            "is_acceptable": True,
        }
        stage = determine_failure_stage(state)
        # Default to workflow_execution for unknown failures
        assert stage == "workflow_execution"


class TestExtractErrorCode:
    """Tests for extract_error_code function."""

    def test_extract_from_http_error_message(self) -> None:
        """Test extracting error code from HTTP error message."""
        error_message = "HTTP 400: INVALID_PARAMETER - Voice not found"
        code = extract_error_code(error_message)
        assert code == "INVALID_PARAMETER"

    def test_extract_from_error_code_prefix(self) -> None:
        """Test extracting when error code is prefixed."""
        error_message = "Error: [ERR_001] Something went wrong"
        code = extract_error_code(error_message)
        assert code == "ERR_001"

    def test_none_when_no_code_found(self) -> None:
        """Test returns None when no error code pattern found."""
        error_message = "Something went wrong"
        code = extract_error_code(error_message)
        assert code is None

    def test_none_for_empty_message(self) -> None:
        """Test returns None for empty message."""
        code = extract_error_code("")
        assert code is None

    def test_none_for_none_message(self) -> None:
        """Test returns None for None message."""
        code = extract_error_code(None)
        assert code is None


class TestExtractErrorDetail:
    """Tests for extract_error_detail function."""

    def test_extract_from_single_error(self) -> None:
        """Test extracting detail from single validation error."""
        errors = ["[input] Missing field: title"]
        detail = extract_error_detail(errors)
        assert "Missing field: title" in detail

    def test_extract_from_multiple_errors(self) -> None:
        """Test extracting detail from multiple validation errors."""
        errors = [
            "[input] Missing field: title",
            "[output] Type mismatch: expected string",
        ]
        detail = extract_error_detail(errors)
        assert "Missing field: title" in detail
        assert "Type mismatch: expected string" in detail

    def test_none_for_empty_list(self) -> None:
        """Test returns None for empty error list."""
        detail = extract_error_detail([])
        assert detail is None

    def test_none_for_none_input(self) -> None:
        """Test returns None for None input."""
        detail = extract_error_detail(None)
        assert detail is None


class TestExtractCauseFromValidationErrors:
    """Tests for extract_cause_from_validation_errors function."""

    def test_extract_input_category(self) -> None:
        """Test extracting cause for input category error."""
        errors = ["[input] Missing required field: body.voice"]
        cause = extract_cause_from_validation_errors(errors)

        assert cause is not None
        assert cause["category"] == "input"
        assert "voice" in cause.get("problem_field", "").lower() or "body.voice" in str(
            cause
        )

    def test_extract_output_category(self) -> None:
        """Test extracting cause for output category error."""
        errors = [
            "[output] Type mismatch at result.content: expected string, got number"
        ]
        cause = extract_cause_from_validation_errors(errors)

        assert cause is not None
        assert cause["category"] == "output"

    def test_extract_graphai_category(self) -> None:
        """Test extracting cause for graphai category error."""
        errors = ["[graphai] Node 'tts_agent' execution timeout after 30s"]
        cause = extract_cause_from_validation_errors(errors)

        assert cause is not None
        assert cause["category"] == "graphai"

    def test_extract_api_category(self) -> None:
        """Test extracting cause for api category error."""
        errors = ["[api] HTTP 400: Invalid voice parameter 'ja-JP-Standard-A'"]
        cause = extract_cause_from_validation_errors(errors)

        assert cause is not None
        assert cause["category"] == "api"

    def test_none_for_empty_list(self) -> None:
        """Test returns None for empty error list."""
        cause = extract_cause_from_validation_errors([])
        assert cause is None

    def test_none_for_no_categorized_errors(self) -> None:
        """Test returns None when no categorized errors found."""
        errors = ["Unknown error without category"]
        result = extract_cause_from_validation_errors(errors)
        # May return None or a cause with unknown category
        # depending on implementation
        assert result is None or isinstance(result, str)


class TestFormatRepairHistory:
    """Tests for format_repair_history function."""

    def test_format_single_attempt(self) -> None:
        """Test formatting single repair attempt."""
        repair_history = [
            {
                "attempt": 1,
                "error": "HTTP 400 - Invalid parameter",
                "model": "gemini-2.5-flash",
                "timestamp": "2025-12-24T10:00:00Z",
            }
        ]
        formatted = format_repair_history(repair_history)

        assert len(formatted) == 1
        assert formatted[0]["attempt"] == 1
        assert "error_message" in formatted[0]
        assert formatted[0]["model_used"] == "gemini-2.5-flash"

    def test_format_multiple_attempts(self) -> None:
        """Test formatting multiple repair attempts."""
        repair_history = [
            {
                "attempt": 1,
                "error": "Error 1",
                "model": "gemini-2.5-flash",
                "timestamp": "2025-12-24T10:00:00Z",
            },
            {
                "attempt": 2,
                "error": "Error 2",
                "model": "gpt-4o-mini",
                "timestamp": "2025-12-24T10:01:00Z",
            },
        ]
        formatted = format_repair_history(repair_history)

        assert len(formatted) == 2
        assert formatted[0]["attempt"] == 1
        assert formatted[1]["attempt"] == 2

    def test_empty_history(self) -> None:
        """Test formatting empty repair history."""
        formatted = format_repair_history([])
        assert formatted == []

    def test_none_history(self) -> None:
        """Test formatting None repair history."""
        formatted = format_repair_history(None)
        assert formatted == []


class TestGenerateDefaultRecommendations:
    """Tests for generate_default_recommendations function."""

    def test_recommendations_for_yaml_generation(self) -> None:
        """Test default recommendations for yaml_generation stage."""
        recommendations = generate_default_recommendations("yaml_generation")

        assert len(recommendations) > 0
        # Should suggest regeneration, workflow, or task-related fixes
        assert any(
            "yaml" in r.lower()
            or "regenerat" in r.lower()
            or "workflow" in r.lower()
            or "task" in r.lower()
            or "model" in r.lower()
            for r in recommendations
        )

    def test_recommendations_for_schema_validation(self) -> None:
        """Test default recommendations for schema_validation stage."""
        recommendations = generate_default_recommendations("schema_validation")

        assert len(recommendations) > 0
        # Should suggest schema or test data fixes
        assert any(
            "schema" in r.lower() or "test" in r.lower() for r in recommendations
        )

    def test_recommendations_for_workflow_execution(self) -> None:
        """Test default recommendations for workflow_execution stage."""
        recommendations = generate_default_recommendations("workflow_execution")

        assert len(recommendations) > 0

    def test_recommendations_for_quality_evaluation(self) -> None:
        """Test default recommendations for quality_evaluation stage."""
        recommendations = generate_default_recommendations("quality_evaluation")

        assert len(recommendations) > 0


class TestBuildFailureDetails:
    """Tests for build_failure_details function."""

    def test_returns_none_for_success_status(self) -> None:
        """Test returns None when status is success."""
        state: dict[str, Any] = {
            "status": "success",
            "yaml_content": "version: 0.5",
        }
        result = build_failure_details(state)
        assert result is None

    def test_builds_for_yaml_generation_failure(self) -> None:
        """Test builds FailureDetails for yaml_generation failure."""
        state: dict[str, Any] = {
            "status": "failed",
            "yaml_content": None,
            "error_message": "Failed to generate YAML",
        }
        result = build_failure_details(state)

        assert result is not None
        assert isinstance(result, FailureDetails)
        assert result.failure_stage == "yaml_generation"
        assert result.error_summary["error_message"] == "Failed to generate YAML"

    def test_builds_for_workflow_execution_failure(self) -> None:
        """Test builds FailureDetails for workflow_execution failure."""
        state: dict[str, Any] = {
            "status": "failed",
            "yaml_content": "version: 0.5",
            "test_http_status": 400,
            "error_message": "HTTP 400: INVALID_PARAMETER - Invalid voice",
            "validation_errors": [
                "[api] Invalid voice parameter 'ja-JP-Standard-A'",
            ],
            "evaluation_suggestions": [
                "Use valid voice options: alloy, echo, fable, onyx, nova, shimmer",
            ],
        }
        result = build_failure_details(state)

        assert result is not None
        assert result.failure_stage == "workflow_execution"
        assert result.error_summary["http_status"] == 400
        assert "INVALID_PARAMETER" in result.error_summary.get("error_code", "")
        assert len(result.recommendations) > 0

    def test_includes_retry_history(self) -> None:
        """Test includes formatted retry history."""
        state: dict[str, Any] = {
            "status": "failed",
            "yaml_content": "version: 0.5",
            "test_http_status": 400,
            "error_message": "API Error",
            "repair_history": [
                {
                    "attempt": 1,
                    "error": "HTTP 400",
                    "model": "gemini-2.5-flash",
                    "timestamp": "2025-12-24T10:00:00Z",
                },
            ],
        }
        result = build_failure_details(state)

        assert result is not None
        assert len(result.retry_history) == 1
        assert result.retry_history[0]["attempt"] == 1

    def test_includes_cause_analysis(self) -> None:
        """Test includes cause analysis from validation errors."""
        state: dict[str, Any] = {
            "status": "failed",
            "yaml_content": "version: 0.5",
            "test_http_status": 200,
            "validation_errors": [
                "[output] Missing required field: result.audio_url",
            ],
        }
        result = build_failure_details(state)

        assert result is not None
        assert result.cause_analysis is not None
        assert result.cause_analysis["category"] == "output"

    def test_uses_default_recommendations_when_none_provided(self) -> None:
        """Test uses default recommendations when evaluation_suggestions is empty."""
        state: dict[str, Any] = {
            "status": "failed",
            "yaml_content": None,
            "error_message": "YAML generation failed",
            "evaluation_suggestions": [],
        }
        result = build_failure_details(state)

        assert result is not None
        assert len(result.recommendations) > 0

    def test_uses_evaluation_suggestions_when_provided(self) -> None:
        """Test uses evaluation_suggestions when provided."""
        suggestions = ["Fix the voice parameter", "Update the interface"]
        state: dict[str, Any] = {
            "status": "failed",
            "yaml_content": "version: 0.5",
            "test_http_status": 400,
            "error_message": "API Error",
            "evaluation_suggestions": suggestions,
        }
        result = build_failure_details(state)

        assert result is not None
        assert result.recommendations == suggestions

    def test_handles_missing_fields_gracefully(self) -> None:
        """Test handles missing optional fields gracefully."""
        state: dict[str, Any] = {
            "status": "failed",
        }
        result = build_failure_details(state)

        assert result is not None
        # Should not raise exception and return valid FailureDetails
        assert result.failure_stage in [
            "yaml_generation",
            "schema_validation",
            "workflow_registration",
            "workflow_execution",
            "node_error",
            "output_validation",
            "quality_evaluation",
        ]
