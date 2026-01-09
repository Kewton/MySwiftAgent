"""Tests for ValidationObserver and StructuredLogFormatter.

Issue #342 Task 4.2: Observability implementation tests.
"""

import json
import logging
import pytest


class TestStructuredLogFormatter:
    """Tests for StructuredLogFormatter."""

    @pytest.fixture
    def formatter(self):
        """Create formatter instance."""
        from aiagent.langgraph.jobGeneratorV2.observability.validation_observer import (
            StructuredLogFormatter,
        )

        return StructuredLogFormatter()

    def test_basic_log_format(self, formatter):
        """Basic log format includes required fields."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)

        assert "timestamp" in data
        assert data["level"] == "INFO"
        assert data["logger"] == "test.logger"
        assert data["message"] == "Test message"

    def test_log_with_workflow_id(self, formatter):
        """Log with workflow_id extra field."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="Validation failed",
            args=(),
            exc_info=None,
        )
        record.workflow_id = "wf-123"
        output = formatter.format(record)
        data = json.loads(output)

        assert data["workflow_id"] == "wf-123"

    def test_log_with_errors(self, formatter):
        """Log with errors extra field."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Errors found",
            args=(),
            exc_info=None,
        )
        record.errors = [{"code": "TEST", "message": "test error"}]
        output = formatter.format(record)
        data = json.loads(output)

        assert "errors" in data
        assert len(data["errors"]) == 1

    def test_log_with_validator(self, formatter):
        """Log with validator extra field."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=1,
            msg="Running validator",
            args=(),
            exc_info=None,
        )
        record.validator = "SourcePathRuleEngine"
        output = formatter.format(record)
        data = json.loads(output)

        assert data["validator"] == "SourcePathRuleEngine"

    def test_log_with_duration(self, formatter):
        """Log with duration_ms extra field."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Validation complete",
            args=(),
            exc_info=None,
        )
        record.duration_ms = 123.45
        output = formatter.format(record)
        data = json.loads(output)

        assert data["duration_ms"] == 123.45


class TestValidationObserver:
    """Tests for ValidationObserver."""

    @pytest.fixture
    def observer(self):
        """Create observer instance."""
        from aiagent.langgraph.jobGeneratorV2.observability.validation_observer import (
            ValidationObserver,
        )

        return ValidationObserver()

    def test_observer_initialization(self, observer):
        """Observer initializes without Langfuse."""
        assert observer._enabled is True
        assert observer._langfuse is None

    def test_observe_validation_no_langfuse(self, observer):
        """observe_validation works without Langfuse."""
        from aiagent.langgraph.jobGeneratorV2.validators import (
            ValidationError,
            ValidationErrorCode,
        )

        errors = [
            ValidationError(
                code=ValidationErrorCode.INVALID_TIMEOUT,
                message="Timeout too small",
                location="nodes.test",
            )
        ]
        # Should not raise even without Langfuse
        observer.observe_validation(
            workflow_id="test-123",
            errors=errors,
            duration_ms=50.0,
        )

    def test_observe_validation_empty_errors(self, observer):
        """observe_validation with empty errors."""
        observer.observe_validation(
            workflow_id="test-123",
            errors=[],
            duration_ms=10.0,
        )

    def test_observe_error_distribution_no_langfuse(self, observer):
        """observe_error_distribution works without Langfuse."""
        from aiagent.langgraph.jobGeneratorV2.validators import (
            ValidationError,
            ValidationErrorCode,
        )

        errors = [
            ValidationError(
                code=ValidationErrorCode.INVALID_TIMEOUT,
                message="Timeout 1",
                location="nodes.a",
                severity="critical",
            ),
            ValidationError(
                code=ValidationErrorCode.INVALID_TIMEOUT,
                message="Timeout 2",
                location="nodes.b",
                severity="major",
            ),
            ValidationError(
                code=ValidationErrorCode.ENV_VAR_IN_URL,
                message="Env var",
                location="nodes.c",
                severity="critical",
            ),
        ]
        observer.observe_error_distribution(
            workflow_id="test-123",
            errors=errors,
        )

    def test_observe_error_distribution_empty(self, observer):
        """observe_error_distribution with empty errors."""
        observer.observe_error_distribution(
            workflow_id="test-123",
            errors=[],
        )


class TestValidationObserverDisabled:
    """Tests for ValidationObserver when disabled."""

    def test_disabled_observer(self):
        """Observer can be disabled."""
        from aiagent.langgraph.jobGeneratorV2.observability.validation_observer import (
            ValidationObserver,
        )

        observer = ValidationObserver()
        observer._enabled = False

        # Should not raise
        observer.observe_validation(
            workflow_id="test",
            errors=[],
            duration_ms=1.0,
        )
        observer.observe_error_distribution(
            workflow_id="test",
            errors=[],
        )
