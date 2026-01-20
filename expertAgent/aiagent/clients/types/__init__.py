"""Type definitions for client modules.

Issue #361: Data types for mySwiftAgentCore API communication.
"""

from .workflow_generator import (
    BatchStatus,
    BatchWorkflowGenerationRequest,
    BatchWorkflowGenerationResponse,
    FailedTask,
    GenerationOptions,
    RecoverySuggestion,
    TaskInterface,
    TaskRequest,
    TraceContext,
    WorkflowResult,
    WorkflowStatus,
)

__all__ = [
    "BatchStatus",
    "BatchWorkflowGenerationRequest",
    "BatchWorkflowGenerationResponse",
    "FailedTask",
    "GenerationOptions",
    "RecoverySuggestion",
    "TaskInterface",
    "TaskRequest",
    "TraceContext",
    "WorkflowResult",
    "WorkflowStatus",
]
