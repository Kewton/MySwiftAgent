"""Backward compatibility alias for types module.

This module provides V3 aliases for types used in tests.
Re-exports all types from types.py with V3 naming convention.
"""

from .types import (
    ErrorType,
    ParallelExecutionResult,
    Phase,
    PhaseError,
    PhaseStatus,
    RecoveryAction,
    RecoveryStrategy,
    TaskExecutionError,
    TaskResult,
    UnifiedTaskIdentifier,
)

# Alias for V3 naming convention used in tests
PhaseV3 = Phase

__all__ = [
    "ErrorType",
    "ParallelExecutionResult",
    "Phase",
    "PhaseError",
    "PhaseStatus",
    "PhaseV3",  # Alias
    "RecoveryAction",
    "RecoveryStrategy",
    "TaskExecutionError",
    "TaskResult",
    "UnifiedTaskIdentifier",
]
