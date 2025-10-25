"""GraphAI Workflow Generator Agent using LangGraph.

This module provides the main LangGraph agent that orchestrates the workflow
for automatically generating and validating GraphAI workflow YAML files.

Workflow:
1. generator → Generate YAML from TaskMaster metadata using LLM
2. sample_input_generator → Generate sample input from Input Interface
3. workflow_tester → Register and execute workflow on graphAiServer
4. validator → Validate execution results (non-LLM)
5. self_repair → Analyze errors and prepare retry (max 3 retries)

The agent uses conditional routing to handle:
- Validation success (→ END)
- Validation failure with retries left (→ generator)
- Max retries exceeded (→ END)
"""

import logging
from typing import Literal

from langgraph.graph import END, StateGraph

from .nodes import (
    generator_node,
    sample_input_generator_node,
    self_repair_node,
    validator_node,
    workflow_tester_node,
)
from .state import WorkflowGeneratorState

logger = logging.getLogger(__name__)


def validator_router(
    state: WorkflowGeneratorState,
) -> Literal["self_repair", "END"]:
    """Route after validator node based on validation result.

    Routing logic:
    1. If is_valid = True → END (success)
    2. If is_valid = False → self_repair (retry)

    Args:
        state: Current workflow generator state

    Returns:
        Next node name or END
    """
    logger.info("Validator router: determining next node")

    is_valid = state.get("is_valid", False)
    validation_errors = state.get("validation_errors", [])

    logger.info(
        f"Validation result: is_valid={is_valid}, errors_count={len(validation_errors)}"
    )

    if is_valid:
        logger.info("Validation passed → END")
        return "END"
    else:
        logger.info("Validation failed → self_repair")
        return "self_repair"


def self_repair_router(
    state: WorkflowGeneratorState,
) -> Literal["generator", "END"]:
    """Route after self_repair node based on retry count.

    Routing logic:
    1. If retry_count < max_retry → generator (regenerate)
    2. If retry_count >= max_retry → END (max retries exceeded)

    Args:
        state: Current workflow generator state

    Returns:
        Next node name or END
    """
    logger.info("Self-repair router: determining next node")

    retry_count = state.get("retry_count", 0)
    max_retry = state.get("max_retry", 3)

    logger.info(f"Retry count: {retry_count}/{max_retry}")

    if retry_count < max_retry:
        logger.info(f"Retry {retry_count + 1}/{max_retry} → generator")
        return "generator"
    else:
        logger.warning(f"Max retries exceeded ({max_retry}) → END")
        return "END"


def create_workflow_generator_graph() -> StateGraph:
    """Create LangGraph workflow for GraphAI workflow generation.

    Returns:
        Compiled LangGraph StateGraph
    """
    # Create graph
    workflow = StateGraph(WorkflowGeneratorState)

    # Add nodes
    workflow.add_node("generator", generator_node)
    workflow.add_node("sample_input_generator", sample_input_generator_node)
    workflow.add_node("workflow_tester", workflow_tester_node)
    workflow.add_node("validator", validator_node)
    workflow.add_node("self_repair", self_repair_node)

    # Add edges
    # Entry point → generator
    workflow.set_entry_point("generator")

    # generator → sample_input_generator
    workflow.add_edge("generator", "sample_input_generator")

    # sample_input_generator → workflow_tester
    workflow.add_edge("sample_input_generator", "workflow_tester")

    # workflow_tester → validator
    workflow.add_edge("workflow_tester", "validator")

    # validator → (conditional) → self_repair or END
    workflow.add_conditional_edges(
        "validator",
        validator_router,
        {
            "self_repair": "self_repair",
            "END": END,
        },
    )

    # self_repair → (conditional) → generator or END
    workflow.add_conditional_edges(
        "self_repair",
        self_repair_router,
        {
            "generator": "generator",
            "END": END,
        },
    )

    # Compile graph
    return workflow.compile()


async def generate_workflow(
    task_master_id: int,
    task_data: dict,
    max_retry: int = 3,
) -> WorkflowGeneratorState:
    """Generate GraphAI workflow YAML from TaskMaster metadata.

    Args:
        task_master_id: TaskMaster ID
        task_data: TaskMaster metadata with interfaces
        max_retry: Maximum retry count for self-repair (default: 3)

    Returns:
        Final state with generated workflow or error information
    """
    from .state import create_initial_state

    logger.info(f"Starting workflow generation for TaskMaster {task_master_id}")

    # Create initial state
    initial_state = create_initial_state(task_master_id, task_data, max_retry)

    # Create and run workflow graph
    graph = create_workflow_generator_graph()
    final_state = await graph.ainvoke(initial_state)

    logger.info(f"Workflow generation completed: status={final_state['status']}")

    return final_state
