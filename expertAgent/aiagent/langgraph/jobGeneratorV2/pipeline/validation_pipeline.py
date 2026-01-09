"""ValidationPipeline for orchestrating workflow validation.

Issue #342 Task 4.1: ValidationPipeline implementation.
Issue #342 Iteration 2: ValidationObserver integration (INT-2).

This module orchestrates multiple validators in sequence:
1. SourcePathRuleEngine - Path validation
2. AgentConstraintValidator - Agent constraints

Results are aggregated, prioritized, and formatted for LLM feedback.
Observer pattern is used for validation monitoring and Langfuse integration.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from aiagent.langgraph.jobGeneratorV2.validators import (
    ValidationError,
    ValidationResult,
    WorkflowValidator,
)
from aiagent.langgraph.jobGeneratorV2.validators.agent_constraint_validator import (
    AgentConstraintValidator,
)
from aiagent.langgraph.jobGeneratorV2.validators.source_path_rule_engine import (
    SourcePathRuleEngine,
)

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.observability import ValidationObserver

logger = logging.getLogger(__name__)


@dataclass
class PipelineStats:
    """Statistics from pipeline execution.

    Attributes:
        total_errors: Total number of errors found
        critical_errors: Number of critical severity errors
        major_errors: Number of major severity errors
        minor_errors: Number of minor severity errors
        execution_time_ms: Total execution time in milliseconds
    """

    total_errors: int = 0
    critical_errors: int = 0
    major_errors: int = 0
    minor_errors: int = 0
    execution_time_ms: float = 0.0


class ValidationPipeline:
    """Pipeline that orchestrates multiple workflow validators.

    This pipeline:
    1. Runs validators in configured order
    2. Aggregates errors from all validators
    3. Prioritizes errors by severity
    4. Generates feedback for LLM retry
    5. Notifies observer for monitoring (Issue #342 INT-2)
    """

    def __init__(
        self,
        validators: list[WorkflowValidator] | None = None,
        observer: "ValidationObserver | None" = None,
    ):
        """Initialize pipeline with validators and optional observer.

        Args:
            validators: List of validators to run. If None, uses default validators.
            observer: Optional ValidationObserver for monitoring and Langfuse integration.
                     Issue #342 Iteration 2: INT-2 integration.
        """
        if validators is None:
            self.validators = [
                SourcePathRuleEngine(),
                AgentConstraintValidator(),
            ]
        else:
            self.validators = validators

        # Issue #342 INT-2: Add observer for validation monitoring
        self.observer = observer

    def validate(
        self,
        workflow: dict[str, Any],
        workflow_id: str = "",
    ) -> ValidationResult:
        """Validate workflow using all validators.

        Args:
            workflow: Workflow dictionary to validate
            workflow_id: Optional workflow identifier for logging and observability.
                        Issue #342 INT-2: Used for observer notification.

        Returns:
            ValidationResult with aggregated errors
        """
        start_time = time.time()
        all_errors: list[ValidationError] = []

        # Run each validator
        for validator in self.validators:
            try:
                errors = validator.validate(workflow)
                all_errors.extend(errors)
            except Exception as e:
                logger.warning(
                    f"Validator {type(validator).__name__} raised exception: {e}"
                )
                # Continue with other validators

        # Sort errors by severity (critical first)
        all_errors = self._sort_by_severity(all_errors)

        # Log stats
        execution_time = (time.time() - start_time) * 1000
        stats = self._compute_stats(all_errors, execution_time)
        self._log_stats(stats)

        # Issue #342 INT-2: Notify observer if configured
        if self.observer is not None:
            try:
                self.observer.observe_validation(
                    workflow_id=workflow_id or "unknown",
                    errors=all_errors,
                    duration_ms=execution_time,
                )
            except Exception as e:
                logger.debug(f"Observer notification failed: {e}")

        if not all_errors:
            return ValidationResult.success()

        return ValidationResult.failure(all_errors)

    def to_prompt_feedback(self, result: ValidationResult) -> str:
        """Generate prompt feedback from validation result.

        Args:
            result: ValidationResult from validate()

        Returns:
            Formatted string for LLM retry prompts
        """
        if result.is_valid:
            return ""

        return result.to_prompt_feedback()

    def _sort_by_severity(
        self,
        errors: list[ValidationError],
    ) -> list[ValidationError]:
        """Sort errors by severity (critical > major > minor).

        Args:
            errors: List of errors to sort

        Returns:
            Sorted list of errors
        """
        severity_order = {"critical": 0, "major": 1, "minor": 2}

        return sorted(
            errors,
            key=lambda e: severity_order.get(e.severity, 1),
        )

    def _compute_stats(
        self,
        errors: list[ValidationError],
        execution_time_ms: float,
    ) -> PipelineStats:
        """Compute pipeline execution statistics.

        Args:
            errors: List of validation errors
            execution_time_ms: Execution time in milliseconds

        Returns:
            PipelineStats instance
        """
        stats = PipelineStats(
            total_errors=len(errors),
            execution_time_ms=execution_time_ms,
        )

        for error in errors:
            if error.severity == "critical":
                stats.critical_errors += 1
            elif error.severity == "major":
                stats.major_errors += 1
            else:
                stats.minor_errors += 1

        return stats

    def _log_stats(self, stats: PipelineStats) -> None:
        """Log pipeline execution statistics.

        Args:
            stats: PipelineStats instance
        """
        if stats.total_errors > 0:
            logger.info(
                f"Validation completed: {stats.total_errors} errors "
                f"(critical={stats.critical_errors}, major={stats.major_errors}, "
                f"minor={stats.minor_errors}) in {stats.execution_time_ms:.2f}ms"
            )
        else:
            logger.debug(f"Validation passed in {stats.execution_time_ms:.2f}ms")

    def add_validator(self, validator: WorkflowValidator) -> None:
        """Add a validator to the pipeline.

        Args:
            validator: Validator to add
        """
        self.validators.append(validator)

    def remove_validator(self, validator_type: type) -> None:
        """Remove validators of a specific type.

        Args:
            validator_type: Type of validator to remove
        """
        self.validators = [
            v for v in self.validators if not isinstance(v, validator_type)
        ]


# Export
__all__ = ["ValidationPipeline", "PipelineStats"]
