"""Utility modules for workflow generator agents."""

from .input_conversion import convert_sample_input_to_dict_or_str
from .interface_validator import (
    InterfaceIssue,
    InterfaceValidationResult,
    format_interface_issues,
    validate_interface_compatibility,
    validate_task_chain_interfaces,
)
from .type_guards import (
    format_apis_comma_separated,
    format_apis_for_prompt,
    get_api_endpoint,
    get_api_name,
    normalize_api_item,
    normalize_recommended_apis,
)
from .workflow_validator import (
    ValidationResult,
    validate_output_node_convention,
    validate_workflow_arrays,
)

__all__ = [
    "convert_sample_input_to_dict_or_str",
    # Interface validation (Issue #338)
    "InterfaceIssue",
    "InterfaceValidationResult",
    "format_interface_issues",
    "validate_interface_compatibility",
    "validate_task_chain_interfaces",
    # Type guards (Issue #338)
    "format_apis_comma_separated",
    "format_apis_for_prompt",
    "get_api_endpoint",
    "get_api_name",
    "normalize_api_item",
    "normalize_recommended_apis",
    # Workflow validation
    "ValidationResult",
    "validate_output_node_convention",
    "validate_workflow_arrays",
]
