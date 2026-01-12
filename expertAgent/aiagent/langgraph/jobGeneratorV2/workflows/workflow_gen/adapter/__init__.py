"""TaskFlow Adapter module.

Issue #355: TaskFlow Adapter Layer implementation.

This module provides the TaskFlowAdapter class for converting
ExpertAgent output (JSON strings) to GraphAiServer format (objects).
"""

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.adapter.taskflow_adapter import (
    ConversionResult,
    TaskFlowAdapter,
)

__all__ = [
    "ConversionResult",
    "TaskFlowAdapter",
]
