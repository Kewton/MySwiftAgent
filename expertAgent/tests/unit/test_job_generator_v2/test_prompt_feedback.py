"""Tests for ValidationResult.to_prompt_feedback() improvements.

Issue #343 Task 2.3: Test to_prompt_feedback() with max_errors and max_total_length.

The improved method should:
1. Accept max_errors parameter to limit number of errors
2. Accept max_total_length parameter to limit total feedback length
3. Sort errors by severity (critical > major > minor)
4. Sanitize error messages for security
"""


from aiagent.langgraph.jobGeneratorV2.validators import (
    ValidationError,
    ValidationErrorCode,
    ValidationResult,
)


class TestToPromptFeedbackParameters:
    """Test to_prompt_feedback() method parameters."""

    def test_accepts_max_errors_parameter(self) -> None:
        """Test that to_prompt_feedback accepts max_errors parameter."""
        errors = [
            ValidationError(
                code=ValidationErrorCode.INVALID_TIMEOUT,
                message=f"Timeout issue {i}",
                location=f"nodes.node{i}",
                severity="major",
            )
            for i in range(10)
        ]
        result = ValidationResult.failure(errors)

        # Should accept max_errors parameter
        feedback = result.to_prompt_feedback(max_errors=3)

        # Should only include 3 "Timeout issue" messages (not counting header)
        timeout_count = sum(1 for i in range(10) if f"Timeout issue {i}" in feedback)
        assert timeout_count == 3

    def test_accepts_max_total_length_parameter(self) -> None:
        """Test that to_prompt_feedback accepts max_total_length parameter."""
        errors = [
            ValidationError(
                code=ValidationErrorCode.INVALID_TIMEOUT,
                message="This is a very long error message. " * 20,  # Long message (~700 chars)
                location="nodes.test",
                severity="major",
            )
            for _ in range(5)
        ]
        result = ValidationResult.failure(errors)

        # Should accept max_total_length parameter
        feedback = result.to_prompt_feedback(max_total_length=1000)

        # Should be truncated (within limit + truncation message)
        assert len(feedback) <= 1050  # Allow margin for truncation message

    def test_default_max_errors_is_5(self) -> None:
        """Test that default max_errors is 5."""
        errors = [
            ValidationError(
                code=ValidationErrorCode.INVALID_TIMEOUT,
                message=f"Unique error message {i}",
                location=f"nodes.node{i}",
                severity="major",
            )
            for i in range(10)
        ]
        result = ValidationResult.failure(errors)

        feedback = result.to_prompt_feedback()

        # Count unique error messages in feedback
        # Should have at most 5 "Unique error message" instances
        unique_count = sum(1 for i in range(10) if f"Unique error message {i}" in feedback)
        assert unique_count <= 5

    def test_default_max_total_length_is_2000(self) -> None:
        """Test that default max_total_length is 2000."""
        errors = [
            ValidationError(
                code=ValidationErrorCode.INVALID_TIMEOUT,
                message="Very long error message content. " * 30,  # ~990 chars per msg
                location="nodes.test",
                severity="major",
            )
            for _ in range(10)
        ]
        result = ValidationResult.failure(errors)

        feedback = result.to_prompt_feedback()

        # Should be at most ~2000 characters (with some margin for truncation msg)
        assert len(feedback) <= 2100


class TestSeveritySorting:
    """Test error sorting by severity."""

    def test_critical_errors_first(self) -> None:
        """Test that critical errors appear before major and minor."""
        errors = [
            ValidationError(
                code=ValidationErrorCode.INVALID_TIMEOUT,
                message="Minor error",
                location="nodes.test",
                severity="minor",
            ),
            ValidationError(
                code=ValidationErrorCode.INVALID_TIMEOUT,
                message="Critical error",
                location="nodes.test",
                severity="critical",
            ),
            ValidationError(
                code=ValidationErrorCode.INVALID_TIMEOUT,
                message="Major error",
                location="nodes.test",
                severity="major",
            ),
        ]
        result = ValidationResult.failure(errors)

        feedback = result.to_prompt_feedback()

        # Critical should appear before Major which should appear before Minor
        critical_pos = feedback.find("Critical error")
        major_pos = feedback.find("Major error")
        minor_pos = feedback.find("Minor error")

        assert critical_pos < major_pos, "Critical should appear before Major"
        assert major_pos < minor_pos, "Major should appear before Minor"

    def test_max_errors_respects_severity(self) -> None:
        """Test that max_errors keeps highest severity errors."""
        errors = [
            ValidationError(
                code=ValidationErrorCode.INVALID_TIMEOUT,
                message="Minor 1",
                location="nodes.test",
                severity="minor",
            ),
            ValidationError(
                code=ValidationErrorCode.INVALID_TIMEOUT,
                message="Critical 1",
                location="nodes.test",
                severity="critical",
            ),
            ValidationError(
                code=ValidationErrorCode.INVALID_TIMEOUT,
                message="Minor 2",
                location="nodes.test",
                severity="minor",
            ),
            ValidationError(
                code=ValidationErrorCode.INVALID_TIMEOUT,
                message="Major 1",
                location="nodes.test",
                severity="major",
            ),
        ]
        result = ValidationResult.failure(errors)

        feedback = result.to_prompt_feedback(max_errors=2)

        # Should include critical and major, not minor
        assert "Critical 1" in feedback
        assert "Major 1" in feedback


class TestSanitization:
    """Test that error messages are sanitized."""

    def test_sanitizes_user_paths(self) -> None:
        """Test that user paths in errors are sanitized."""
        errors = [
            ValidationError(
                code=ValidationErrorCode.INVALID_TIMEOUT,
                message="Error at /Users/john/secret/file.py",
                location="nodes.test",
                severity="major",
            ),
        ]
        result = ValidationResult.failure(errors)

        feedback = result.to_prompt_feedback()

        # User path should be masked
        assert "/Users/john" not in feedback
        assert "[USER_PATH]" in feedback

    def test_sanitizes_suggestion(self) -> None:
        """Test that suggestion field is also sanitized."""
        errors = [
            ValidationError(
                code=ValidationErrorCode.INVALID_TIMEOUT,
                message="Error occurred",
                location="nodes.test",
                suggestion="Check /Users/admin/config.yaml",
                severity="major",
            ),
        ]
        result = ValidationResult.failure(errors)

        feedback = result.to_prompt_feedback()

        # Suggestion path should be masked
        assert "/Users/admin" not in feedback


class TestEmptyAndValidResults:
    """Test edge cases."""

    def test_empty_feedback_for_valid_result(self) -> None:
        """Test that valid results return empty feedback."""
        result = ValidationResult.success()

        feedback = result.to_prompt_feedback()

        assert feedback == ""

    def test_empty_feedback_for_no_errors(self) -> None:
        """Test that empty error list returns empty feedback."""
        result = ValidationResult(is_valid=False, errors=[])

        feedback = result.to_prompt_feedback()

        assert feedback == ""

    def test_includes_fix_instruction(self) -> None:
        """Test that feedback includes instruction to fix errors."""
        errors = [
            ValidationError(
                code=ValidationErrorCode.INVALID_TIMEOUT,
                message="Test error",
                location="nodes.test",
                severity="major",
            ),
        ]
        result = ValidationResult.failure(errors)

        feedback = result.to_prompt_feedback()

        assert "Please generate corrected YAML" in feedback or "fix" in feedback.lower()

    def test_includes_header(self) -> None:
        """Test that feedback includes header section."""
        errors = [
            ValidationError(
                code=ValidationErrorCode.INVALID_TIMEOUT,
                message="Test error",
                location="nodes.test",
                severity="major",
            ),
        ]
        result = ValidationResult.failure(errors)

        feedback = result.to_prompt_feedback()

        assert "Previous Generation Errors" in feedback or "MUST FIX" in feedback


class TestTruncationBehavior:
    """Test truncation behavior."""

    def test_truncation_adds_indicator(self) -> None:
        """Test that truncation adds an indicator message."""
        errors = [
            ValidationError(
                code=ValidationErrorCode.INVALID_TIMEOUT,
                message="This is a long error description. " * 20,  # ~700 chars per msg
                location="nodes.test",
                severity="major",
            )
            for _ in range(10)
        ]
        result = ValidationResult.failure(errors)

        feedback = result.to_prompt_feedback(max_total_length=500)

        # Should indicate that content was truncated
        assert "truncated" in feedback.lower() or "..." in feedback
