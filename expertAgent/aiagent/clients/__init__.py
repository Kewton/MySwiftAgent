"""Client modules for external service communication.

Issue #361: HTTP client abstractions for mySwiftAgentCore integration.
"""

from .workflow_generator_client import (
    WorkflowGeneratorClient,
    WorkflowGeneratorError,
    WorkflowGeneratorHTTPError,
    WorkflowGeneratorTimeoutError,
    WorkflowGeneratorValidationError,
)

__all__ = [
    "WorkflowGeneratorClient",
    "WorkflowGeneratorError",
    "WorkflowGeneratorHTTPError",
    "WorkflowGeneratorTimeoutError",
    "WorkflowGeneratorValidationError",
]
