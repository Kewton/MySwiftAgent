"""ValidationObserver for monitoring validation results.

Issue #342 Task 4.2: Observability implementation.

This module provides:
- StructuredLogFormatter: JSON-formatted log output
- ValidationObserver: Langfuse integration for validation metrics
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from aiagent.langgraph.jobGeneratorV2.validators import ValidationError


class StructuredLogFormatter(logging.Formatter):
    """Formatter that outputs structured JSON logs.

    This formatter produces JSON log entries with:
    - Timestamp
    - Level
    - Logger name
    - Message
    - Extra fields (workflow_id, errors, etc.)
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON string representation
        """
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "workflow_id"):
            log_entry["workflow_id"] = record.workflow_id

        if hasattr(record, "errors"):
            log_entry["errors"] = record.errors

        if hasattr(record, "validator"):
            log_entry["validator"] = record.validator

        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms

        if hasattr(record, "error_count"):
            log_entry["error_count"] = record.error_count

        return json.dumps(log_entry, ensure_ascii=False)


class ValidationObserver:
    """Observer that records validation results to Langfuse.

    This observer:
    - Records validation scores (pass/fail)
    - Records validation errors as events
    - Tracks validation duration
    """

    def __init__(self):
        """Initialize observer.

        Lazily initializes Langfuse client when first observation is made.
        """
        self._langfuse = None
        self._enabled = True

    @property
    def langfuse(self):
        """Lazy-load Langfuse client."""
        if self._langfuse is None and self._enabled:
            try:
                from langfuse import Langfuse

                self._langfuse = Langfuse()
            except ImportError:
                self._enabled = False
                self._langfuse = None
            except Exception:
                self._enabled = False
                self._langfuse = None

        return self._langfuse

    def observe_validation(
        self,
        workflow_id: str,
        errors: list[ValidationError],
        duration_ms: float,
        trace_id: str | None = None,
    ) -> None:
        """Record validation result to Langfuse.

        Args:
            workflow_id: Unique workflow identifier
            errors: List of validation errors (empty if valid)
            duration_ms: Validation duration in milliseconds
            trace_id: Optional existing trace ID
        """
        if not self._enabled or self.langfuse is None:
            return

        try:
            # Create or use existing trace
            tid = trace_id or workflow_id

            # Record validation score
            self.langfuse.score(
                trace_id=tid,
                name="workflow_validation",
                value=1.0 if len(errors) == 0 else 0.0,
                comment=f"Errors: {len(errors)}, Duration: {duration_ms:.2f}ms",
            )

            # Record errors as event
            if errors:
                self.langfuse.event(
                    trace_id=tid,
                    name="validation_errors",
                    metadata={
                        "error_count": len(errors),
                        "errors": [e.to_dict() for e in errors],
                        "duration_ms": duration_ms,
                    },
                )

        except Exception as e:
            # Don't let observation failures affect validation
            logging.getLogger(__name__).debug(
                f"Failed to record validation to Langfuse: {e}"
            )

    def observe_error_distribution(
        self,
        workflow_id: str,
        errors: list[ValidationError],
        trace_id: str | None = None,
    ) -> None:
        """Record error distribution to Langfuse.

        Args:
            workflow_id: Unique workflow identifier
            errors: List of validation errors
            trace_id: Optional existing trace ID
        """
        if not self._enabled or self.langfuse is None:
            return

        if not errors:
            return

        try:
            tid = trace_id or workflow_id

            # Count errors by code
            error_counts: dict[str, int] = {}
            for error in errors:
                code = error.code.value
                error_counts[code] = error_counts.get(code, 0) + 1

            # Count errors by severity
            severity_counts: dict[str, int] = {}
            for error in errors:
                sev = error.severity
                severity_counts[sev] = severity_counts.get(sev, 0) + 1

            self.langfuse.event(
                trace_id=tid,
                name="validation_error_distribution",
                metadata={
                    "by_code": error_counts,
                    "by_severity": severity_counts,
                    "total": len(errors),
                },
            )

        except Exception as e:
            logging.getLogger(__name__).debug(
                f"Failed to record error distribution to Langfuse: {e}"
            )


# Export
__all__ = ["StructuredLogFormatter", "ValidationObserver"]
