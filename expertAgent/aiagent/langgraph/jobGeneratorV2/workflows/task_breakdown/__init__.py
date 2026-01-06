"""TaskBreakdownWorkflow package for Job Generator V2.

This package implements Phase B of Issue #342:
- TaskDecomposerSubWorkflow: Parse and decompose user requirements
- FeasibilitySubWorkflow: Check task feasibility against capabilities
- AlternativeSubWorkflow: Generate alternatives for infeasible tasks
- TaskBreakdownWorkflow: Main workflow orchestrating sub-workflows

The workflow follows the pattern:
1. Decompose requirements into tasks
2. Check feasibility of each task
3. Generate alternatives for infeasible tasks
4. Return TaskBreakdownOutput with appropriate status
"""

from .alternative import AlternativeSubWorkflow
from .decomposer import TaskDecomposerSubWorkflow
from .feasibility import FeasibilitySubWorkflow, load_capabilities_from_yaml
from .workflow import TaskBreakdownWorkflow

__all__ = [
    "TaskDecomposerSubWorkflow",
    "FeasibilitySubWorkflow",
    "AlternativeSubWorkflow",
    "TaskBreakdownWorkflow",
    "load_capabilities_from_yaml",
]
