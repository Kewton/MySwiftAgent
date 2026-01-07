"""Few-shot examples for Workflow Generator V2.

This package provides few-shot examples for LLM workflow generation.

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.few_shot.loader import (
    FewShotExample,
    get_example_by_api,
    load_all_examples,
    load_example,
    select_few_shot_examples,
)

__all__ = [
    "FewShotExample",
    "load_example",
    "load_all_examples",
    "select_few_shot_examples",
    "get_example_by_api",
]
