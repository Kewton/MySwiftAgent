"""YAML Validator Sub-Workflow for Workflow Generator V2.

This module provides validation of generated GraphAI YAML workflows.

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .errors import ValidationError, ValidationResult
from .validators import (
    check_circular_references,
    validate_agents,
    validate_node_structure,
    validate_references,
    validate_structure,
    validate_yaml_syntax,
)

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext

logger = logging.getLogger(__name__)


@dataclass
class YamlValidationResult:
    """Result of YAML validation.

    Attributes:
        is_valid: Whether the YAML is valid
        errors: List of validation errors
        parsed_yaml: Parsed YAML dictionary (None if syntax error)
        node_count: Number of nodes in the workflow
    """

    is_valid: bool
    errors: list[ValidationError]
    parsed_yaml: dict | None = None
    node_count: int = 0

    def to_validation_result(self) -> ValidationResult:
        """Convert to ValidationResult for prompt feedback."""
        return ValidationResult(
            is_valid=self.is_valid,
            errors=self.errors,
        )


class YamlValidatorSubWorkflow:
    """Sub-workflow for validating generated YAML.

    Performs multi-layer validation:
    1. YAML syntax validation
    2. Structure validation (version, source, isResult)
    3. Agent validation (known agents only)
    4. Reference validation (valid node references)
    5. Circular reference check
    """

    def __init__(
        self,
        validate_syntax: bool = True,
        validate_struct: bool = True,
        validate_agents_flag: bool = True,
        validate_refs: bool = True,
        check_cycles: bool = True,
    ):
        """Initialize YamlValidatorSubWorkflow.

        Args:
            validate_syntax: Enable YAML syntax validation
            validate_struct: Enable structure validation
            validate_agents_flag: Enable agent existence validation
            validate_refs: Enable reference validation
            check_cycles: Enable circular reference check
        """
        self._validate_syntax = validate_syntax
        self._validate_struct = validate_struct
        self._validate_agents = validate_agents_flag
        self._validate_refs = validate_refs
        self._check_cycles = check_cycles

    def validate(
        self,
        yaml_content: str,
        context: "ExecutionContext | None" = None,
    ) -> YamlValidationResult:
        """Validate YAML workflow content.

        Args:
            yaml_content: YAML string to validate
            context: Execution context for logging

        Returns:
            YamlValidationResult with validation details
        """
        job_id = context.job_id if context else "unknown"
        logger.info("Validating YAML workflow (job=%s)", job_id)

        all_errors: list[ValidationError] = []
        parsed_yaml = None
        node_count = 0

        # 1. Syntax validation
        if self._validate_syntax:
            parsed_yaml, syntax_errors = validate_yaml_syntax(yaml_content)
            all_errors.extend(syntax_errors)

            if syntax_errors:
                logger.warning(
                    "YAML syntax validation failed: %d errors",
                    len(syntax_errors),
                )
                return YamlValidationResult(
                    is_valid=False,
                    errors=all_errors,
                    parsed_yaml=None,
                    node_count=0,
                )

        # 2. Structure validation
        if self._validate_struct and parsed_yaml:
            structure_errors = validate_structure(parsed_yaml)
            all_errors.extend(structure_errors)

            # Get node count
            nodes = parsed_yaml.get("nodes", {})
            node_count = len(nodes)

            # Validate individual node structures
            for node_name, node_def in nodes.items():
                if node_name != "source" and isinstance(node_def, dict):
                    node_errors = validate_node_structure(node_name, node_def)
                    all_errors.extend(node_errors)

        # 3. Agent validation
        if self._validate_agents and parsed_yaml:
            nodes = parsed_yaml.get("nodes", {})
            agent_errors = validate_agents(nodes)
            all_errors.extend(agent_errors)

        # 4. Reference validation
        if self._validate_refs and parsed_yaml:
            nodes = parsed_yaml.get("nodes", {})
            ref_errors = validate_references(nodes)
            all_errors.extend(ref_errors)

        # 5. Circular reference check
        if self._check_cycles and parsed_yaml:
            nodes = parsed_yaml.get("nodes", {})
            cycle_errors = check_circular_references(nodes)
            all_errors.extend(cycle_errors)

        is_valid = len(all_errors) == 0

        if is_valid:
            logger.info("YAML validation passed (%d nodes)", node_count)
        else:
            logger.warning(
                "YAML validation failed: %d errors",
                len(all_errors),
            )

        return YamlValidationResult(
            is_valid=is_valid,
            errors=all_errors,
            parsed_yaml=parsed_yaml,
            node_count=node_count,
        )

    def quick_validate(
        self,
        yaml_content: str,
    ) -> tuple[bool, list[str]]:
        """Quick validation returning simple boolean and error messages.

        Args:
            yaml_content: YAML string to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        result = self.validate(yaml_content)
        error_messages = [e.message for e in result.errors]
        return result.is_valid, error_messages
