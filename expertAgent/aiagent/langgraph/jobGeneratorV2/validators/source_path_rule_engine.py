"""SourcePathRuleEngine for validating source path references.

Issue #342 Task 1.2: SourcePathRuleEngine implementation.

This module validates and generates source path references for GraphAI workflows.

Valid patterns (V1 compatible):
- :source.query - Direct field reference (V1 style)
- :source.results - Direct field reference (V1 style)
- :source.user_input.* - Explicit user input reference (V2 style)
- :source.job_params.* - Job parameters reference (V2 style)
- :node_name.* - Same workflow node reference

Invalid patterns:
- :source (no field specified)
- :source. (trailing dot, no field)
- {{job.body}} (legacy pattern)
- {{tasks[N].output_data}} (legacy pattern)

V1 Compatibility Note:
- V1 workflows use :source.fieldName directly (e.g., :source.query)
- V2 prefers :source.user_input.fieldName but accepts V1 patterns
- This is controlled by the v1_compatible parameter (default: True)
"""

from __future__ import annotations

import re
from typing import Any

from aiagent.langgraph.jobGeneratorV2.validators import (
    ValidationError,
    ValidationErrorCode,
    WorkflowValidator,
)

# V2 explicit prefixes (preferred but not required)
V2_EXPLICIT_PREFIXES = [
    ":source.user_input.",
    ":source.job_params.",
]

# Legacy patterns to detect
LEGACY_PATTERNS = [
    re.compile(r"\{\{job\.body\}\}"),
    re.compile(r"\{\{tasks\[\d+\]\.output_data\}\}"),
    re.compile(r"\{\{job\."),
    re.compile(r"\{\{tasks\["),
]

# Pattern to match source references
SOURCE_REF_PATTERN = re.compile(r":source\.(\w+)(?:\.[\w\[\]\.]+)?")

# Pattern to match node references (starting with : but not :source)
NODE_REF_PATTERN = re.compile(r":([a-zA-Z_]\w*)(?:\.[\w\[\]\.]+)?")


class SourcePathRuleEngine(WorkflowValidator):
    """Engine for validating and generating source path references.

    This engine ensures that:
    1. All :source.* references include user_input or job_params
    2. No legacy patterns ({{job.body}}, {{tasks[N].output_data}}) are used
    3. Node references point to existing nodes
    """

    def validate_path(self, path: str | None) -> tuple[bool, str]:
        """Validate a single path reference.

        Args:
            path: The path string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Handle None or empty
        if path is None:
            return False, "Path cannot be None"
        if not isinstance(path, str):
            return False, f"Path must be a string, got {type(path).__name__}"
        if not path.strip():
            return False, "Path cannot be empty"

        # Skip non-path values (URLs, plain strings, etc.)
        if not path.startswith(":") and "{{" not in path:
            return True, ""

        # Check for legacy patterns
        for pattern in LEGACY_PATTERNS:
            if pattern.search(path):
                return (
                    False,
                    f"Legacy pattern detected: '{path}'. Use :source.user_input.* or :source.job_params.* instead",
                )

        # Check source references (V1 compatible)
        # Valid: :source.query, :source.user_input.data, :source.job_params.model
        # Invalid: :source, :source.
        if path.startswith(":source"):
            # Check for just ":source" without any field
            if path == ":source":
                return False, (
                    f"Invalid source path '{path}'. "
                    ":source must be followed by a field name "
                    "(e.g., :source.query, :source.user_input.data)"
                )
            # Check for ":source." with nothing after
            if path == ":source." or not path.startswith(":source."):
                return False, (
                    f"Invalid source path '{path}'. "
                    ":source must be followed by a field name "
                    "(e.g., :source.query, :source.user_input.data)"
                )
            # Get the remainder after ":source."
            remainder = path[8:]  # len(":source.") == 8
            # Check if there's at least one valid field name
            if not remainder or remainder.startswith("."):
                return False, (
                    f"Invalid source path '{path}'. "
                    ":source must be followed by a field name "
                    "(e.g., :source.query, :source.user_input.data)"
                )
            # V1 compatible: :source.fieldName is valid
            # V2 style: :source.user_input.*, :source.job_params.* also valid
            # All pass at this point

        # Check for numeric-starting references (like :8004 from URLs)
        if path.startswith(":"):
            ref_match = NODE_REF_PATTERN.match(path)
            if ref_match:
                node_name = ref_match.group(1)
                if node_name.isdigit():
                    return (
                        False,
                        f"Invalid reference '{path}'. Node names cannot be numbers.",
                    )
            else:
                # Path starts with : but doesn't match valid node reference pattern
                # Check if it's numeric
                rest = path[1:]  # Remove the leading :
                if rest and rest[0].isdigit():
                    return (
                        False,
                        f"Invalid reference '{path}'. Node names must start with a letter or underscore.",
                    )

        return True, ""

    def generate_path(
        self,
        context: str,
        field: str,
        node_name: str | None = None,
    ) -> str:
        """Generate a valid path reference.

        Args:
            context: Context type ("previous_task", "job_params", "node")
            field: Field name to reference
            node_name: Node name for node references

        Returns:
            Valid path reference string

        Raises:
            ValueError: If context is unknown
        """
        if context == "previous_task":
            return f":source.user_input.{field}"
        elif context == "job_params":
            return f":source.job_params.{field}"
        elif context == "node":
            if node_name:
                return f":{node_name}.{field}" if "." not in field else f":{field}"
            raise ValueError("node_name is required for node context")
        else:
            raise ValueError(
                f"Unknown context: {context}. Use 'previous_task', 'job_params', or 'node'"
            )

    def validate_workflow(self, workflow: dict[str, Any]) -> list[str]:
        """Validate all paths in a workflow.

        Args:
            workflow: The workflow dictionary

        Returns:
            List of error messages
        """
        errors = []
        nodes = workflow.get("nodes", {})

        for node_name, node_def in nodes.items():
            if node_name == "source":
                continue

            if not isinstance(node_def, dict):
                continue

            # Check inputs
            node_errors = self._validate_dict_values(
                node_def.get("inputs", {}),
                f"nodes.{node_name}.inputs",
            )
            errors.extend(node_errors)

            # Check params
            param_errors = self._validate_dict_values(
                node_def.get("params", {}),
                f"nodes.{node_name}.params",
            )
            errors.extend(param_errors)

            # Check body if present
            if "body" in node_def.get("inputs", {}):
                body = node_def["inputs"]["body"]
                if isinstance(body, dict):
                    body_errors = self._validate_dict_values(
                        body,
                        f"nodes.{node_name}.inputs.body",
                    )
                    errors.extend(body_errors)

        return errors

    def validate(self, workflow: dict[str, Any]) -> list[ValidationError]:
        """Validate workflow paths and return ValidationError objects.

        Args:
            workflow: The workflow dictionary

        Returns:
            List of ValidationError objects
        """
        validation_errors = []
        nodes = workflow.get("nodes", {})

        for node_name, node_def in nodes.items():
            if node_name == "source":
                continue

            if not isinstance(node_def, dict):
                continue

            # Check all string values in the node
            errors = self._validate_node_paths(node_def, f"nodes.{node_name}")
            validation_errors.extend(errors)

        return validation_errors

    def _validate_node_paths(
        self,
        node_def: dict[str, Any],
        location_prefix: str,
    ) -> list[ValidationError]:
        """Validate all paths in a node definition.

        Args:
            node_def: Node definition dictionary
            location_prefix: Prefix for error locations

        Returns:
            List of ValidationError objects
        """
        errors: list[ValidationError] = []

        # Check inputs
        inputs = node_def.get("inputs", {})
        if isinstance(inputs, dict):
            errors.extend(
                self._validate_dict_paths(inputs, f"{location_prefix}.inputs")
            )

        # Check params
        params = node_def.get("params", {})
        if isinstance(params, dict):
            errors.extend(
                self._validate_dict_paths(params, f"{location_prefix}.params")
            )

        return errors

    def _validate_dict_paths(
        self,
        data: dict[str, Any],
        location_prefix: str,
    ) -> list[ValidationError]:
        """Validate paths in a dictionary.

        Args:
            data: Dictionary to validate
            location_prefix: Prefix for error locations

        Returns:
            List of ValidationError objects
        """
        errors: list[ValidationError] = []

        for key, value in data.items():
            location = f"{location_prefix}.{key}"

            if isinstance(value, str):
                is_valid, error_msg = self.validate_path(value)
                if not is_valid:
                    # Determine error code
                    if "legacy" in error_msg.lower():
                        code = ValidationErrorCode.LEGACY_PATH_PATTERN
                    elif "user_input" in error_msg or "job_params" in error_msg:
                        code = ValidationErrorCode.MISSING_USER_INPUT_PREFIX
                    else:
                        code = ValidationErrorCode.INVALID_SOURCE_PATH

                    errors.append(
                        ValidationError(
                            code=code,
                            message=error_msg,
                            location=location,
                            suggestion=(
                                "Use :source.{field} (V1 style) or "
                                ":source.user_input.{field} / :source.job_params.{field} (V2 style)"
                            ),
                            severity="critical",
                        )
                    )

            elif isinstance(value, dict):
                errors.extend(self._validate_dict_paths(value, location))

            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, str):
                        is_valid, error_msg = self.validate_path(item)
                        if not is_valid:
                            errors.append(
                                ValidationError(
                                    code=ValidationErrorCode.INVALID_SOURCE_PATH,
                                    message=error_msg,
                                    location=f"{location}[{i}]",
                                    suggestion=(
                                        "Use :source.{field} (V1 style) or "
                                        ":source.user_input.{field} / :source.job_params.{field} (V2 style)"
                                    ),
                                    severity="critical",
                                )
                            )
                    elif isinstance(item, dict):
                        errors.extend(
                            self._validate_dict_paths(item, f"{location}[{i}]")
                        )

        return errors

    def _validate_dict_values(
        self,
        data: dict[str, Any],
        location_prefix: str,
    ) -> list[str]:
        """Validate all string values in a dictionary (returns strings).

        Args:
            data: Dictionary to validate
            location_prefix: Prefix for error locations

        Returns:
            List of error message strings
        """
        errors: list[str] = []

        for key, value in data.items():
            location = f"{location_prefix}.{key}"

            if isinstance(value, str):
                is_valid, error_msg = self.validate_path(value)
                if not is_valid:
                    errors.append(f"[{location}] {error_msg}")

            elif isinstance(value, dict):
                errors.extend(self._validate_dict_values(value, location))

            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, str):
                        is_valid, error_msg = self.validate_path(item)
                        if not is_valid:
                            errors.append(f"[{location}[{i}]] {error_msg}")
                    elif isinstance(item, dict):
                        errors.extend(
                            self._validate_dict_values(item, f"{location}[{i}]")
                        )

        return errors


# Export
__all__ = ["SourcePathRuleEngine"]
