"""Backward compatibility alias for orchestrator module.

This module provides V3 aliases for orchestrator components.
Re-exports all components from orchestrator.py with V3 naming.
"""

from .orchestrator import (
    JobGenerationOrchestrator,
    JobGenerationRequest,
    JobGenerationResult,
    OrchestratorError,
)

# Aliases for V3 naming convention used in tests
JobGenerationOrchestratorV3 = JobGenerationOrchestrator
JobGenerationResultV3 = JobGenerationResult

__all__ = [
    "JobGenerationOrchestrator",
    "JobGenerationOrchestratorV3",  # Alias
    "JobGenerationRequest",
    "JobGenerationResult",
    "JobGenerationResultV3",  # Alias
    "OrchestratorError",
]
