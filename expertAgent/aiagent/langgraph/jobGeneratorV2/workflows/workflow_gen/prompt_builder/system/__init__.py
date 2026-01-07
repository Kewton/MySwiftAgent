"""System prompts for Workflow Generator V2.

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.system.workflow_generator import (
    WORKFLOW_GENERATOR_SYSTEM_PROMPT,
    WORKFLOW_GENERATOR_SYSTEM_PROMPT_SHORT,
    get_system_prompt,
)

__all__ = [
    "WORKFLOW_GENERATOR_SYSTEM_PROMPT",
    "WORKFLOW_GENERATOR_SYSTEM_PROMPT_SHORT",
    "get_system_prompt",
]
