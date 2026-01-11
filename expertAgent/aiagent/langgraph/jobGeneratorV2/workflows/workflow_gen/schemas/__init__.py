"""Schemas for Workflow Generation.

Issue #350: Added TaskFlow V2 schemas.

This module provides Pydantic schemas for:
- GraphAI YAML workflows (existing)
- TaskFlow V2 JSON workflows (new)
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
from .taskflow_schema import (
    ApiRestConfig,
    CodeJsConfig,
    ConditionalBlock,
    IOSchemaType,
    ParallelBlock,
    TaskFlowStep,
    TaskFlowWorkflow,
    TransformConfig,
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
    "ApiRestConfig",
    "TransformConfig",
    "CodeJsConfig",
    "TaskFlowStep",
    "ParallelBlock",
    "ConditionalBlock",
    "TaskFlowWorkflow",
]
