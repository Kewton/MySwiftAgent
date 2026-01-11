"""Schemas for Workflow Generation.

Issue #350: Added TaskFlow V2 schemas.
Issue #351: Added variable pattern utilities.

This module provides Pydantic schemas for:
- GraphAI YAML workflows (existing)
- TaskFlow V2 JSON workflows (new)
- Variable pattern utilities for validation (Issue #351)
"""

# GraphAI schemas (existing) - import from the schemas.py file at parent level
# Note: This import pattern is needed because we converted schemas.py to a package
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.schemas.graphai_schema import (
    AVAILABLE_AGENTS,
    GraphAIWorkflowSchema,
    NodeDefinition,
    SourceNodeDefinition,
    is_valid_agent,
)

# TaskFlow V2 schemas (new)
# Note: ParallelBlock and ConditionalBlock removed for OpenAI Structured Output compatibility
from .taskflow_schema import (
    ApiRestConfig,
    CodeJsConfig,
    IOSchemaType,
    TaskFlowStep,
    TaskFlowWorkflow,
    TransformConfig,
    UnifiedStepConfig,
)

# Variable pattern utilities (Issue #351)
from .variable_patterns import (
    TASKFLOW_VARIABLE_PATTERN,
    contains_variable_reference,
    mask_secret_references,
    replace_variables_with_placeholder,
    validate_variable_syntax,
)

__all__ = [
    # GraphAI schemas
    "GraphAIWorkflowSchema",
    "NodeDefinition",
    "SourceNodeDefinition",
    "AVAILABLE_AGENTS",
    "is_valid_agent",
    # TaskFlow V2 schemas
    "IOSchemaType",
    "UnifiedStepConfig",
    "ApiRestConfig",  # Legacy alias for UnifiedStepConfig
    "TransformConfig",  # Legacy alias for UnifiedStepConfig
    "CodeJsConfig",  # Legacy alias for UnifiedStepConfig
    "TaskFlowStep",
    "TaskFlowWorkflow",
    # Variable pattern utilities (Issue #351)
    "TASKFLOW_VARIABLE_PATTERN",
    "contains_variable_reference",
    "replace_variables_with_placeholder",
    "mask_secret_references",
    "validate_variable_syntax",
]
