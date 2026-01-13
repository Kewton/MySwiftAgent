"""Template variable extractor for body_template validation.

Issue #358: Extract template variables from body_template for validation.

This module provides:
- extract_template_variables(): Extract all {{...}} template references
- TemplateVariableResult: Container for extracted variables
- TaskOutputReference: Reference to tasks[N].output_data

Template patterns:
- {{job.body}} - Entire job body
- {{job.body.field}} - Specific field from job body
- {{job.project}} - Job project
- {{tasks[N].output_data}} - Previous task output
- {{tasks[N].output_data.field}} - Field from previous task output
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Template variable pattern: matches {{...}}
TEMPLATE_PATTERN = re.compile(r"\{\{([^}]+)\}\}")

# Job body reference pattern: matches job.body or job.body.field
JOB_BODY_PATTERN = re.compile(r"^job\.body(?:\.(.+))?$")

# Job reference pattern (non-body): matches job.project, job.id, etc.
JOB_REF_PATTERN = re.compile(r"^job\.(?!body)(\w+)$")

# Task output pattern: matches tasks[N].output_data or tasks[N].output_data.field
TASK_OUTPUT_PATTERN = re.compile(r"^tasks\[(\d+)\]\.output_data(?:\.(.+))?$")


@dataclass
class TaskOutputReference:
    """Reference to a task's output data.

    Attributes:
        task_index: Index of the referenced task (0-based)
        field_path: Optional field path within output_data (empty string if whole output)
        raw_reference: Original reference string
    """

    task_index: int
    field_path: str = ""
    raw_reference: str = ""


@dataclass
class TemplateVariableResult:
    """Result of template variable extraction.

    Attributes:
        job_body_refs: Set of job.body references (e.g., "job.body.user_input")
        job_refs: Set of other job references (e.g., "job.project")
        task_output_refs: List of task output references
        raw_variables: All raw variable strings found
    """

    job_body_refs: set[str] = field(default_factory=set)
    job_refs: set[str] = field(default_factory=set)
    task_output_refs: list[TaskOutputReference] = field(default_factory=list)
    raw_variables: set[str] = field(default_factory=set)

    def get_required_job_body_fields(self) -> set[str]:
        """Get the set of required job.body field names.

        Extracts field names from job.body.X references.

        Returns:
            Set of field names (e.g., {"user_input", "recipient_email"})
        """
        fields: set[str] = set()
        for ref in self.job_body_refs:
            # Match job.body.field pattern
            match = JOB_BODY_PATTERN.match(ref)
            if match and match.group(1):
                # Extract first level field name
                field_path = match.group(1)
                first_field = field_path.split(".")[0]
                fields.add(first_field)
        return fields

    def get_max_task_index(self) -> int:
        """Get the maximum task index referenced.

        Returns:
            Maximum task index, or -1 if no task references
        """
        if not self.task_output_refs:
            return -1
        return max(ref.task_index for ref in self.task_output_refs)


def extract_template_variables(body_template: dict[str, Any]) -> TemplateVariableResult:
    """Extract template variables from body_template.

    Recursively traverses the body_template dictionary and extracts all
    {{...}} template variable references.

    Args:
        body_template: Body template dictionary to analyze

    Returns:
        TemplateVariableResult with categorized references

    Example:
        >>> body_template = {
        ...     "inputs": "{{job.body}}",
        ...     "previous": "{{tasks[0].output_data}}",
        ... }
        >>> result = extract_template_variables(body_template)
        >>> "job.body" in result.job_body_refs
        True
    """
    result = TemplateVariableResult()
    _extract_from_value(body_template, result)
    return result


def _extract_from_value(value: Any, result: TemplateVariableResult) -> None:
    """Recursively extract variables from any value type.

    Args:
        value: Value to extract from (dict, list, str, etc.)
        result: Result object to populate
    """
    if isinstance(value, dict):
        for v in value.values():
            _extract_from_value(v, result)
    elif isinstance(value, list):
        for item in value:
            _extract_from_value(item, result)
    elif isinstance(value, str):
        _extract_from_string(value, result)


def _extract_from_string(text: str, result: TemplateVariableResult) -> None:
    """Extract template variables from a string.

    Args:
        text: String to extract from
        result: Result object to populate
    """
    matches = TEMPLATE_PATTERN.findall(text)

    for var in matches:
        var = var.strip()
        result.raw_variables.add(var)

        # Check for job.body reference
        job_body_match = JOB_BODY_PATTERN.match(var)
        if job_body_match:
            result.job_body_refs.add(var)
            continue

        # Check for other job reference (job.project, etc.)
        job_ref_match = JOB_REF_PATTERN.match(var)
        if job_ref_match:
            result.job_refs.add(var)
            continue

        # Check for task output reference
        task_match = TASK_OUTPUT_PATTERN.match(var)
        if task_match:
            task_index = int(task_match.group(1))
            field_path = task_match.group(2) or ""
            result.task_output_refs.append(
                TaskOutputReference(
                    task_index=task_index,
                    field_path=field_path,
                    raw_reference=var,
                )
            )
            continue

        # Unknown reference type - log warning
        logger.warning("Unknown template variable pattern: %s", var)


__all__ = [
    "extract_template_variables",
    "TemplateVariableResult",
    "TaskOutputReference",
    "TEMPLATE_PATTERN",
    "JOB_BODY_PATTERN",
    "TASK_OUTPUT_PATTERN",
]
