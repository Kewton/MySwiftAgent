"""Client modules for external service communication.

Issue #361: HTTP client abstractions for mySwiftAgentCore integration.
Issue #385: Capability fetch error and log sanitization utilities.
"""

from .workflow_generator_client import (
    CapabilityFetchError,
    WorkflowGeneratorClient,
    WorkflowGeneratorError,
    WorkflowGeneratorHTTPError,
    WorkflowGeneratorTimeoutError,
    WorkflowGeneratorValidationError,
)

__all__ = [
    "CapabilityFetchError",
    "WorkflowGeneratorClient",
    "WorkflowGeneratorError",
    "WorkflowGeneratorHTTPError",
    "WorkflowGeneratorTimeoutError",
    "WorkflowGeneratorValidationError",
]
