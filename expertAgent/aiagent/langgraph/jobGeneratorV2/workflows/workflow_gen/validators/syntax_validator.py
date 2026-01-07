"""YAML Syntax Validator for Workflow Generator V2.

This module validates YAML syntax.

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

from __future__ import annotations

import logging
from typing import Any

import yaml

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.errors import (
    ErrorCode,
    ValidationError,
)

logger = logging.getLogger(__name__)


def validate_yaml_syntax(yaml_content: str) -> tuple[dict[str, Any] | None, list[ValidationError]]:
    """Validate YAML syntax and parse content.

    Args:
        yaml_content: YAML string to validate

    Returns:
        Tuple of (parsed_dict, errors)
        - parsed_dict: Parsed YAML as dict (None if syntax error)
        - errors: List of validation errors (empty if valid)
    """
    errors: list[ValidationError] = []

    if not yaml_content or not yaml_content.strip():
        errors.append(
            ValidationError(
                code=ErrorCode.YAML_SYNTAX,
                message="YAML content is empty",
                location="root",
                suggestion="Provide non-empty YAML content",
            )
        )
        return None, errors

    try:
        parsed = yaml.safe_load(yaml_content)

        if parsed is None:
            errors.append(
                ValidationError(
                    code=ErrorCode.YAML_SYNTAX,
                    message="YAML parsed to None",
                    location="root",
                    suggestion="Check YAML content is not just whitespace or comments",
                )
            )
            return None, errors

        if not isinstance(parsed, dict):
            errors.append(
                ValidationError(
                    code=ErrorCode.INVALID_YAML_STRUCTURE,
                    message=f"YAML root must be a dictionary, got {type(parsed).__name__}",
                    location="root",
                    suggestion="Ensure YAML starts with 'version:' and 'nodes:'",
                )
            )
            return None, errors

        return parsed, errors

    except yaml.YAMLError as e:
        error_msg = str(e)
        # Extract line number if available
        location = "root"
        if hasattr(e, "problem_mark") and e.problem_mark:
            location = f"line {e.problem_mark.line + 1}"

        errors.append(
            ValidationError(
                code=ErrorCode.YAML_SYNTAX,
                message=f"YAML syntax error: {error_msg}",
                location=location,
                suggestion="Check indentation and YAML syntax",
            )
        )
        return None, errors

    except Exception as e:
        logger.error("Unexpected error parsing YAML: %s", e)
        errors.append(
            ValidationError(
                code=ErrorCode.YAML_SYNTAX,
                message=f"Unexpected parsing error: {e}",
                location="root",
                suggestion="Check YAML content format",
            )
        )
        return None, errors
