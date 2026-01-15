"""Backward compatibility alias for error_recovery module.

This module provides V3 aliases for error recovery components.
Re-exports all components from error_recovery.py.
"""

from .error_recovery import (
    ErrorContractProtocol,
    ErrorRecoveryManager,
    JobAnalysisErrorContract,
    RegistrationErrorContract,
    WorkflowGenErrorContract,
)

__all__ = [
    "ErrorContractProtocol",
    "ErrorRecoveryManager",
    "JobAnalysisErrorContract",
    "RegistrationErrorContract",
    "WorkflowGenErrorContract",
]
