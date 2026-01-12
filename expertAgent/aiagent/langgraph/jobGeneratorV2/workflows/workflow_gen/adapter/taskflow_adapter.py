"""TaskFlow Adapter for converting ExpertAgent output to GraphAiServer format.

Issue #355: TaskFlow Adapter Layer implementation.

This module provides the TaskFlowAdapter class that implements the Adapter Pattern
to convert ExpertAgent workflow definitions (which may contain JSON strings)
to GraphAiServer format (which expects objects).

Design reference: dev-reports/investigation/issue-353-pending-workflow/schema-unification-proposal.md
"""

from __future__ import annotations

import copy
import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ConversionResult:
    """Result of workflow conversion.

    Attributes:
        success: Whether conversion succeeded
        data: Converted workflow data (None if failed)
        errors: List of error messages
        warnings: List of warning messages
    """

    success: bool
    data: dict[str, Any] | None
    errors: list[str]
    warnings: list[str]


class TaskFlowAdapter:
    """Adapter for converting ExpertAgent output to GraphAiServer format.

    Implements the Adapter Pattern to absorb schema differences between
    ExpertAgent (which may output JSON strings for dict fields) and
    GraphAiServer (which expects proper objects).

    Responsibilities:
    1. Convert JSON string fields to objects
    2. Preserve existing object fields unchanged
    3. Report detailed errors for invalid conversions

    Usage:
        adapter = TaskFlowAdapter()
        result = adapter.convert(workflow_from_llm)
        if result.success:
            await register_workflow(result.data)
        else:
            handle_errors(result.errors)

    Attributes:
        WORKFLOW_JSON_STRING_FIELDS: Fields at workflow level that may be JSON strings
        STEP_JSON_STRING_FIELDS: Fields at step config level that may be JSON strings
    """

    # Fields at workflow level that may be JSON strings
    WORKFLOW_JSON_STRING_FIELDS = ["input_schema", "output_schema", "output"]

    # Fields at step config level that may be JSON strings
    STEP_JSON_STRING_FIELDS = ["body"]

    def convert(self, workflow: dict[str, Any]) -> ConversionResult:
        """Convert workflow to GraphAiServer format.

        Args:
            workflow: ExpertAgent/LLM-generated workflow definition

        Returns:
            ConversionResult with converted data or errors
        """
        errors: list[str] = []
        warnings: list[str] = []

        try:
            # Deep copy to avoid modifying original data
            result = self._deep_copy(workflow)

            # Step 1: Convert workflow-level JSON string fields
            for field in self.WORKFLOW_JSON_STRING_FIELDS:
                if field in result:
                    converted, error = self._convert_json_string(result[field], field)
                    if error:
                        errors.append(error)
                    else:
                        result[field] = converted

            # Step 2: Convert step-level fields
            if "steps" in result and isinstance(result["steps"], list):
                for i, step in enumerate(result["steps"]):
                    step_errors = self._convert_step(step, i)
                    errors.extend(step_errors)

            # Return result based on errors
            if errors:
                return ConversionResult(
                    success=False,
                    data=None,
                    errors=errors,
                    warnings=warnings,
                )

            return ConversionResult(
                success=True,
                data=result,
                errors=[],
                warnings=warnings,
            )

        except Exception as e:
            logger.exception("Unexpected error during conversion")
            return ConversionResult(
                success=False,
                data=None,
                errors=[f"Unexpected conversion error: {e}"],
                warnings=warnings,
            )

    def _convert_json_string(
        self, value: Any, field_name: str
    ) -> tuple[Any, str | None]:
        """Convert JSON string to object if needed.

        Args:
            value: Value to convert (may be str, dict, or None)
            field_name: Name of the field for error messages

        Returns:
            Tuple of (converted value, error message or None)
        """
        if value is None:
            return None, None

        if isinstance(value, dict):
            # Already an object, return as-is
            return value, None

        if isinstance(value, str):
            try:
                return json.loads(value), None
            except json.JSONDecodeError as e:
                return None, f"{field_name}: Invalid JSON string - {e}"

        # Not a string or dict
        return (
            None,
            f"{field_name}: Expected dict or JSON string, got {type(value).__name__}",
        )

    def _convert_step(self, step: dict[str, Any], index: int) -> list[str]:
        """Convert step-level fields.

        Args:
            step: Step definition
            index: Step index for error messages

        Returns:
            List of error messages (empty if successful)
        """
        errors: list[str] = []
        step_id = step.get("id", f"step_{index}")

        if "config" not in step:
            return errors

        config = step["config"]
        if not isinstance(config, dict):
            return errors

        for field in self.STEP_JSON_STRING_FIELDS:
            if field in config:
                converted, error = self._convert_json_string(
                    config[field], f"steps[{step_id}].config.{field}"
                )
                if error:
                    # For body field, we log warning but don't fail
                    # GraphAiServer accepts both string and object for body
                    logger.warning(
                        "Step body conversion warning: %s - keeping original value",
                        error,
                    )
                elif converted is not None:
                    config[field] = converted

        return errors

    def _deep_copy(self, obj: Any) -> Any:
        """Create a deep copy of the object.

        Args:
            obj: Object to copy

        Returns:
            Deep copy of the object
        """
        return copy.deepcopy(obj)
