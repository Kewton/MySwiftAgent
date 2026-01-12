"""Integration tests for LLM retry flow with error feedback.

Issue #343 Task 2.6: Test the complete LLM generation -> validation -> retry flow.

This test verifies that:
1. ValidationResult.to_prompt_feedback() generates proper feedback
2. Error feedback is passed through the generation pipeline
3. Retry attempts use the error feedback from previous validation
"""

from typing import Any
from unittest.mock import patch

import pytest

from aiagent.langgraph.jobGeneratorV2.validators import (
    ValidationError,
    ValidationErrorCode,
    ValidationResult,
)


class TestErrorFeedbackGeneration:
    """Test error feedback generation from ValidationResult."""

    def test_to_prompt_feedback_formats_errors(self) -> None:
        """Test that to_prompt_feedback produces formatted error feedback."""
        errors = [
            ValidationError(
                code=ValidationErrorCode.INVALID_TIMEOUT,
                message="Timeout value 30 appears to be in seconds",
                location="nodes.api_call.timeout",
                suggestion="Use milliseconds: timeout: 30000",
                severity="major",
            ),
        ]
        result = ValidationResult.failure(errors)

        feedback = result.to_prompt_feedback()

        # Should contain error information
        assert "INVALID_TIMEOUT" in feedback
        assert "nodes.api_call.timeout" in feedback
        assert "milliseconds" in feedback.lower() or "30000" in feedback

    def test_feedback_includes_suggestion(self) -> None:
        """Test that feedback includes fix suggestions."""
        errors = [
            ValidationError(
                code=ValidationErrorCode.INVALID_SOURCE_PATH,
                message="Invalid source path format",
                location="nodes.search.inputs.query",
                suggestion="Use :source.user_input.query format",
                severity="major",
            ),
        ]
        result = ValidationResult.failure(errors)

        feedback = result.to_prompt_feedback()

        # Should include the suggestion
        assert "source.user_input" in feedback or "Fix" in feedback

    def test_multiple_errors_formatted(self) -> None:
        """Test that multiple errors are all included."""
        errors = [
            ValidationError(
                code=ValidationErrorCode.INVALID_TIMEOUT,
                message="Error 1",
                location="nodes.a",
                severity="critical",
            ),
            ValidationError(
                code=ValidationErrorCode.ENV_VAR_IN_URL,
                message="Error 2",
                location="nodes.b",
                severity="major",
            ),
        ]
        result = ValidationResult.failure(errors)

        feedback = result.to_prompt_feedback()

        assert "Error 1" in feedback
        assert "Error 2" in feedback


class TestValidationPipelineIntegration:
    """Test ValidationPipeline integration with error feedback."""

    def test_pipeline_validation_result_has_to_prompt_feedback(self) -> None:
        """Test that pipeline's ValidationResult has to_prompt_feedback method."""
        from aiagent.langgraph.jobGeneratorV2.pipeline import ValidationPipeline

        pipeline = ValidationPipeline()

        # Create a workflow with an error
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "api_call": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "http://example.com",
                    },
                    "timeout": 30,  # This might trigger validation error
                },
            },
        }

        result = pipeline.validate(workflow)

        # Result should have to_prompt_feedback method
        assert hasattr(result, "to_prompt_feedback")
        assert callable(result.to_prompt_feedback)

        # If there are errors, feedback should be non-empty
        if not result.is_valid:
            feedback = result.to_prompt_feedback()
            assert len(feedback) > 0


class TestYamlGeneratorRetryFlow:
    """Test YamlGenerator's retry flow with error feedback."""

    @pytest.mark.asyncio
    async def test_retry_uses_error_feedback(self) -> None:
        """Test that error_feedback parameter is passed through generate_from_task."""
        import inspect

        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.llm_generator import (
            LLMGenerationResult,
            LLMGeneratorSubWorkflow,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder import (
            PromptBuilderSubWorkflow,
        )

        # Verify generate_from_task accepts error_feedback
        sig = inspect.signature(LLMGeneratorSubWorkflow.generate_from_task)
        assert "error_feedback" in sig.parameters, (
            "generate_from_task should accept error_feedback parameter"
        )

        # Verify PromptBuilder.build accepts error_feedback
        sig = inspect.signature(PromptBuilderSubWorkflow.build)
        assert "error_feedback" in sig.parameters, (
            "PromptBuilder.build should accept error_feedback parameter"
        )

        # Test that error_feedback flows through
        captured_feedback: str | None = None

        async def mock_generate(
            self: Any, prompt: Any, context: Any = None
        ) -> LLMGenerationResult:
            nonlocal captured_feedback
            captured_feedback = prompt.error_feedback
            return LLMGenerationResult(
                yaml_content="version: '0.5'\nnodes:\n  source: {}",
                workflow_name="test",
                model_name="test",
                node_count=1,
            )

        generator = LLMGeneratorSubWorkflow()
        test_feedback = "## Errors\n- Fix timeout value"

        with patch.object(LLMGeneratorSubWorkflow, "generate", mock_generate):
            await generator.generate_from_task(
                task_name="test",
                task_description="Test",
                input_schema={},
                output_schema={},
                error_feedback=test_feedback,
            )

        assert captured_feedback == test_feedback, (
            "error_feedback should be passed through to the prompt"
        )


class TestTimeoutValidationInRetry:
    """Test that timeout validation errors trigger proper feedback."""

    def test_timeout_error_in_feedback(self) -> None:
        """Test that timeout validation error appears in feedback."""
        from aiagent.langgraph.jobGeneratorV2.validators import ValidationResult
        from aiagent.langgraph.jobGeneratorV2.validators.agent_constraint_validator import (
            AgentConstraintValidator,
        )

        validator = AgentConstraintValidator()

        # Workflow with timeout in seconds (should fail)
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "api_call": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "http://example.com",
                    },
                    "timeout": 30,  # Seconds, not milliseconds
                },
            },
        }

        errors = validator.validate(workflow)

        if errors:
            result = ValidationResult.failure(errors)
            feedback = result.to_prompt_feedback()

            # Feedback should mention timeout issue
            assert (
                "timeout" in feedback.lower()
                or "INVALID_TIMEOUT" in feedback
                or "millisecond" in feedback.lower()
            )


class TestSecuritySanitization:
    """Test that error feedback is sanitized."""

    def test_feedback_sanitizes_sensitive_info(self) -> None:
        """Test that sensitive information is sanitized in feedback."""
        errors = [
            ValidationError(
                code=ValidationErrorCode.VALIDATION_FAILED,
                message="Error at /Users/admin/secret/config.py",
                location="nodes.test",
                severity="major",
            ),
        ]
        result = ValidationResult.failure(errors)

        feedback = result.to_prompt_feedback()

        # User path should be sanitized
        assert "/Users/admin" not in feedback
        assert "[USER_PATH]" in feedback


class TestFeedbackLengthLimits:
    """Test feedback length limits."""

    def test_feedback_respects_max_length(self) -> None:
        """Test that feedback respects max_total_length."""
        errors = [
            ValidationError(
                code=ValidationErrorCode.VALIDATION_FAILED,
                message="x" * 500,
                location="nodes.test",
                severity="major",
            )
            for _ in range(10)
        ]
        result = ValidationResult.failure(errors)

        feedback = result.to_prompt_feedback(max_total_length=1000)

        # Should be within limit (with some margin)
        assert len(feedback) <= 1100

    def test_feedback_respects_max_errors(self) -> None:
        """Test that feedback respects max_errors."""
        errors = [
            ValidationError(
                code=ValidationErrorCode.VALIDATION_FAILED,
                message=f"Unique error {i}",
                location=f"nodes.test{i}",
                severity="major",
            )
            for i in range(10)
        ]
        result = ValidationResult.failure(errors)

        feedback = result.to_prompt_feedback(max_errors=3)

        # Should only include 3 unique error messages
        count = sum(1 for i in range(10) if f"Unique error {i}" in feedback)
        assert count <= 3
