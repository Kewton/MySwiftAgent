"""Backward compatibility alias for job_analyzer module.

This module provides V3 aliases for job_analyzer components.
Re-exports all components from job_analyzer.py with V3 naming.
"""

from .job_analyzer import (
    AnalyzedTask,
    InterfaceDefinition,
    JobAnalysisInput,
    JobAnalysisResponse,
    JobParameter,
    analyze_job,
)

__all__ = [
    "AnalyzedTask",
    "InterfaceDefinition",
    "JobAnalysisInput",
    "JobAnalysisResponse",
    "JobParameter",
    "analyze_job",
]
