"""Job Generator V2 - Refactored Job/Task Generator Agent.

This module provides a clean architecture for job generation with:
- Clear phase separation (TaskBreakdown, InterfaceDesign, Registration, WorkflowGen)
- Proper retry management (no infinite loops)
- Observable state transitions
- Testable components

Issue #342: Architecture refactoring to fix retry_count bug and improve maintainability.

The key improvement is in error recovery:
- Each phase has its own RetryState (max 3 retries per phase)
- ErrorRecoveryManager decides recovery strategy based on error type
- Prevents infinite loops by always decrementing retry budget
"""

from .context import (
    ContextBuilder,
    ExecutionContext,
    IntegrationContext,
    LLMContext,
    ObservabilityContext,
    StorageContext,
)
from .orchestrator import JobGenerationOrchestrator
from .protocols import (
    ErrorType,
    PhaseExecution,
    ProgressReporter,
    RetryPolicy,
    WorkflowError,
    WorkflowProtocol,
)
from .recovery import (
    ErrorRecoveryDecision,
    ErrorRecoveryManager,
    ErrorRecoveryStrategy,
)
from .types import (
    Capability,
    FeasibilityReport,
    InterfaceDesignInput,
    InterfaceDesignOutput,
    InterfaceSchema,
    JobGenerationRequest,
    JobGenerationResult,
    Phase,
    PhaseStatus,
    RegistrationInput,
    RegistrationOutput,
    RelaxationSuggestion,
    RetryAttempt,
    RetryState,
    TaskBreakdownInput,
    TaskBreakdownOutput,
    TaskDefinition,
    WorkflowGenInput,
    WorkflowGenOutput,
)

__all__ = [
    # Enums
    "Phase",
    "PhaseStatus",
    "ErrorType",
    "ErrorRecoveryStrategy",
    # Retry management
    "RetryState",
    "RetryAttempt",
    "RetryPolicy",
    # Core types
    "TaskDefinition",
    "JobGenerationRequest",
    "JobGenerationResult",
    "Capability",
    "InterfaceSchema",
    # Phase I/O types
    "TaskBreakdownInput",
    "TaskBreakdownOutput",
    "InterfaceDesignInput",
    "InterfaceDesignOutput",
    "RegistrationInput",
    "RegistrationOutput",
    "WorkflowGenInput",
    "WorkflowGenOutput",
    # Supporting types
    "RelaxationSuggestion",
    "FeasibilityReport",
    "PhaseExecution",
    # Protocols
    "WorkflowProtocol",
    "WorkflowError",
    "ProgressReporter",
    # Context
    "ExecutionContext",
    "LLMContext",
    "StorageContext",
    "IntegrationContext",
    "ObservabilityContext",
    "ContextBuilder",
    # Recovery
    "ErrorRecoveryDecision",
    "ErrorRecoveryManager",
    # Orchestrator
    "JobGenerationOrchestrator",
]
