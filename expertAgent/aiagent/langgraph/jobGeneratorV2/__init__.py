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

# New 3-phase adapter (Issue #359) - not yet production-ready
from .adapter import JobGeneratorAdapter

# Production adapter with full LLM integration
from .adapter_old import JobGeneratorV2Adapter
from .context import (
    ContextBuilder,
    ExecutionContext,
    IntegrationContext,
    LLMContext,
    ObservabilityContext,
    StorageContext,
)
from .orchestrator import JobGenerationOrchestrator
from .progress import JobStateProgressReporter
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
from .types_old import (
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
from .workflows.task_breakdown import (
    AlternativeSubWorkflow,
    FeasibilitySubWorkflow,
    TaskBreakdownWorkflow,
    TaskDecomposerSubWorkflow,
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
    # Workflows
    "TaskBreakdownWorkflow",
    "TaskDecomposerSubWorkflow",
    "FeasibilitySubWorkflow",
    "AlternativeSubWorkflow",
    # Adapters
    "JobGeneratorAdapter",  # New 3-phase (Issue #359) - not production-ready
    "JobGeneratorV2Adapter",  # Production adapter with full LLM integration
    # Progress reporting (Issue #342-V2-UX)
    "JobStateProgressReporter",
]
