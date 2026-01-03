"""GraphAI Workflow Generator Agent using LangGraph.

This module provides the main LangGraph agent that orchestrates the workflow
for automatically generating and validating GraphAI workflow YAML files.

Updated Workflow (Issue #340):
1. generator -> Generate YAML from TaskMaster metadata using LLM
2. schema_validator -> Validate API type and field name compatibility (Issue #333)
3. sample_input_generator -> Generate sample input from Input Interface
4. sample_input_router -> Route based on object array detection (Issue #340)
5. workflow_tester -> Register and execute workflow on graphAiServer
6. validator -> Validate execution results (non-LLM)
7. llm_evaluator -> LLM-based semantic evaluation
8. Conditional routing:
   - test_data_regenerator -> Regenerate test data if quality is low
   - self_repair -> Fix workflow issues and retry
   - result_summary_generator -> Generate summary and END

The agent uses conditional routing to handle:
- Schema validation failure (-> self_repair -> generator) (Issue #333)
- Object array detection (-> test_data_regenerator) (Issue #340)
- Test data quality issues (-> test_data_regenerator -> workflow_tester)
- Validation failure with retries left (-> self_repair -> generator)
- Validation success (-> result_summary_generator -> END)
- Max retries exceeded (-> END)
"""

import logging
from typing import Any, Literal

from langgraph.graph import END, StateGraph

from .nodes import (
    generator_node,
    llm_evaluator_node,
    result_summary_generator_node,
    sample_input_generator_node,
    self_repair_node,
    test_data_regenerator_node,
    validator_node,
    workflow_schema_validator_node,
    workflow_tester_node,
)
from .routers.sample_input_router import sample_input_router
from .state import WorkflowGeneratorState

logger = logging.getLogger(__name__)


def schema_validator_router(
    state: WorkflowGeneratorState,
) -> Literal["sample_input_generator", "self_repair"]:
    """Route after schema_validator node based on validation results.

    Issue #333: Added schema validation step after generator.

    Args:
        state: Current workflow generator state

    Returns:
        "self_repair" if schema validation failed
        "sample_input_generator" if validation passed
    """
    has_schema_errors = state.get("has_schema_errors", False)

    if has_schema_errors:
        schema_issues = state.get("schema_validation_issues", [])
        error_count = len([i for i in schema_issues if i.get("severity") == "error"])
        logger.info(
            f"Schema validation failed with {error_count} errors, "
            "routing to self_repair"
        )
        return "self_repair"

    logger.info("Schema validation passed, routing to sample_input_generator")
    return "sample_input_generator"


def validator_router(
    state: WorkflowGeneratorState,
) -> Literal["llm_evaluator", "result_summary_generator"]:
    """Route after validator node based on fast_mode and validation results.

    Updated for Issue #305: Skip LLM evaluation in fast_mode when rule-based
    validation passes and workflow execution succeeded.

    Args:
        state: Current workflow generator state

    Returns:
        "result_summary_generator" if fast_mode and validation passed
        "llm_evaluator" otherwise
    """
    fast_mode = state.get("fast_mode", False)
    is_valid = state.get("is_valid", False)
    test_http_status = state.get("test_http_status")

    # Issue #305: Skip LLM evaluation in fast_mode when:
    # 1. Rule-based validation passed
    # 2. Workflow execution succeeded (HTTP 200)
    if fast_mode and is_valid and test_http_status == 200:
        logger.info(
            "Validator router: fast_mode enabled and validation passed, "
            "skipping LLM evaluation -> result_summary_generator"
        )
        return "result_summary_generator"

    logger.info("Validator router: routing to llm_evaluator")
    return "llm_evaluator"


def llm_evaluator_router(
    state: WorkflowGeneratorState,
) -> Literal["test_data_regenerator", "result_summary_generator", "self_repair"]:
    """Route after llm_evaluator node based on evaluation results.

    Routing logic:
    1. Test data regeneration needed & count < max -> test_data_regenerator
    2. Workflow quality issue (rule-based or LLM) -> self_repair
    3. Success -> result_summary_generator

    Args:
        state: Current workflow generator state

    Returns:
        Next node name
    """
    logger.info("LLM evaluator router: determining next node")

    needs_test_data_regeneration = state.get("needs_test_data_regeneration", False)
    test_data_regen_count = state.get("test_data_regeneration_count", 0)
    max_test_data_regen = state.get("max_test_data_regeneration", 2)

    # Check if test data regeneration is needed and possible
    if needs_test_data_regeneration and test_data_regen_count < max_test_data_regen:
        logger.info("Test data quality insufficient, routing to test_data_regenerator")
        return "test_data_regenerator"

    # Check rule-based validation
    is_rule_valid = state.get("is_valid", False)
    if not is_rule_valid:
        logger.info("Rule-based validation failed, routing to self_repair")
        return "self_repair"

    # Check LLM evaluation score
    evaluation_result = state.get("llm_evaluation_result") or {}
    failure_reason = evaluation_result.get("failure_reason", "none")

    if failure_reason in ("workflow_quality", "both"):
        logger.info("Workflow quality insufficient, routing to self_repair")
        return "self_repair"

    evaluation_score = state.get("evaluation_score") or 0
    if evaluation_score < 70:
        logger.info(
            f"LLM evaluation score ({evaluation_score}) below threshold, routing to self_repair"
        )
        return "self_repair"

    logger.info("Evaluation passed, routing to result_summary_generator")
    return "result_summary_generator"


def test_data_regenerator_router(
    state: WorkflowGeneratorState,
) -> Literal["workflow_tester"]:
    """Route after test_data_regenerator node.

    Always routes back to workflow_tester to re-test with new data.

    Args:
        state: Current workflow generator state

    Returns:
        Always returns "workflow_tester"
    """
    logger.info(
        "Test data regenerator router: routing to workflow_tester for re-testing"
    )
    return "workflow_tester"


def self_repair_router(
    state: WorkflowGeneratorState,
) -> Literal["generator", "END"]:
    """Route after self_repair node based on retry count.

    Routing logic:
    1. If retry_count < max_retry -> generator (regenerate)
    2. If retry_count >= max_retry -> END (max retries exceeded)

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
        logger.info(f"Retry {retry_count + 1}/{max_retry} -> generator")
        return "generator"
    else:
        logger.warning(f"Max retries exceeded ({max_retry}) -> END")
        return "END"


def create_workflow_generator_graph() -> Any:
    """Create LangGraph workflow for GraphAI workflow generation.

    Returns:
        Compiled LangGraph StateGraph
    """
    # Create graph
    workflow = StateGraph(WorkflowGeneratorState)

    # Add nodes
    workflow.add_node("generator", generator_node)
    # Issue #333: Add schema validator after generator
    workflow.add_node("schema_validator", workflow_schema_validator_node)
    workflow.add_node("sample_input_generator", sample_input_generator_node)
    workflow.add_node("workflow_tester", workflow_tester_node)
    workflow.add_node("validator", validator_node)
    workflow.add_node("llm_evaluator", llm_evaluator_node)
    workflow.add_node("test_data_regenerator", test_data_regenerator_node)
    workflow.add_node("result_summary_generator", result_summary_generator_node)
    workflow.add_node("self_repair", self_repair_node)

    # Add edges
    # Entry point -> generator
    workflow.set_entry_point("generator")

    # generator -> schema_validator (Issue #333)
    workflow.add_edge("generator", "schema_validator")

    # schema_validator -> (conditional) -> sample_input_generator or self_repair
    # Issue #333: Route based on schema validation results
    workflow.add_conditional_edges(
        "schema_validator",
        schema_validator_router,
        {
            "sample_input_generator": "sample_input_generator",
            "self_repair": "self_repair",
        },
    )

    # Issue #340: sample_input_generator -> (conditional) -> workflow_tester or test_data_regenerator
    # Route based on object array detection results
    workflow.add_conditional_edges(
        "sample_input_generator",
        sample_input_router,
        {
            "workflow_tester": "workflow_tester",
            "test_data_regenerator": "test_data_regenerator",
        },
    )

    # workflow_tester -> validator
    workflow.add_edge("workflow_tester", "validator")

    # validator -> (conditional) -> llm_evaluator or result_summary_generator
    # Issue #305: Skip LLM evaluation in fast_mode when validation passes
    workflow.add_conditional_edges(
        "validator",
        validator_router,
        {
            "llm_evaluator": "llm_evaluator",
            "result_summary_generator": "result_summary_generator",
        },
    )

    # llm_evaluator -> (conditional) -> test_data_regenerator or self_repair or result_summary_generator
    workflow.add_conditional_edges(
        "llm_evaluator",
        llm_evaluator_router,
        {
            "test_data_regenerator": "test_data_regenerator",
            "result_summary_generator": "result_summary_generator",
            "self_repair": "self_repair",
        },
    )

    # test_data_regenerator -> workflow_tester (re-test with new data)
    workflow.add_edge("test_data_regenerator", "workflow_tester")

    # result_summary_generator -> END
    workflow.add_edge("result_summary_generator", END)

    # self_repair -> (conditional) -> generator or END
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
    task_master_id: str | int,
    task_data: dict,
    max_retry: int = 3,
    callback_handler: Any | None = None,
    fast_mode: bool = False,
) -> WorkflowGeneratorState:
    """Generate GraphAI workflow YAML from TaskMaster metadata.

    Issue #278: Added callback_handler parameter for Langfuse tracing integration.
    Issue #305: Added LLM Evaluator, Test Data Regenerator, and Result Summary Generator.
    Issue #305: Added fast_mode parameter for performance optimization.
    Changed to False by default for quality-first approach.

    Args:
        task_master_id: TaskMaster ID (ULID string or int)
        task_data: TaskMaster metadata with interfaces
        max_retry: Maximum retry count for self-repair (default: 3)
        callback_handler: Optional Langfuse CallbackHandler for tracing
        fast_mode: Skip LLM evaluation when rule-based validation passes (default: False)

    Returns:
        Final state with generated workflow or error information
    """
    from .state import create_initial_state

    logger.info(f"Starting workflow generation for TaskMaster {task_master_id}")

    # Create initial state
    initial_state = create_initial_state(
        task_master_id, task_data, max_retry, fast_mode=fast_mode
    )

    # Create and run workflow graph
    graph = create_workflow_generator_graph()

    # Issue #278: Build config with callbacks if handler is provided
    config: dict[str, Any] = {}
    if callback_handler is not None:
        config["callbacks"] = [callback_handler]

    final_state_raw = await graph.ainvoke(
        initial_state, config=config if config else None
    )
    final_state: WorkflowGeneratorState = final_state_raw  # type: ignore[assignment]

    logger.info(f"Workflow generation completed: status={final_state['status']}")

    return final_state
