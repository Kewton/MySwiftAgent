"""Workflow implementations for Job Generator V2.

This package contains workflow implementations for each phase:
- task_breakdown: TaskBreakdownWorkflow (Phase B)
- interface_design: InterfaceDesignWorkflow (Phase C)
- registration: RegistrationWorkflow (Phase D)
- workflow_gen: WorkflowGenWorkflow (Phase D)

Issue #342: Architecture refactoring for better testability and maintainability.
"""

from aiagent.langgraph.jobGeneratorV2.workflows.interface_design import (
    CompatibilityCheckerSubWorkflow,
    InterfaceDesignWorkflow,
    SchemaEnricherSubWorkflow,
    SchemaGeneratorSubWorkflow,
)
from aiagent.langgraph.jobGeneratorV2.workflows.registration import (
    JobRegistrarSubWorkflow,
    MasterManagerSubWorkflow,
    RegistrationWorkflow,
)
from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown import (
    TaskBreakdownWorkflow,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen import (
    TestRunnerSubWorkflow,
    WorkflowGenWorkflow,
    YamlGeneratorSubWorkflow,
)

__all__ = [
    # Phase B: Task Breakdown
    "TaskBreakdownWorkflow",
    # Phase C: Interface Design
    "InterfaceDesignWorkflow",
    "SchemaGeneratorSubWorkflow",
    "CompatibilityCheckerSubWorkflow",
    "SchemaEnricherSubWorkflow",
    # Phase D: Registration
    "RegistrationWorkflow",
    "MasterManagerSubWorkflow",
    "JobRegistrarSubWorkflow",
    # Phase D: Workflow Generation
    "WorkflowGenWorkflow",
    "YamlGeneratorSubWorkflow",
    "TestRunnerSubWorkflow",
]
