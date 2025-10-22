"""Job/Task Auto-Generation Agent using LangGraph.

This module provides the main LangGraph agent that orchestrates the workflow
for automatically generating Jobs and Tasks from user requirements.

Workflow:
1. requirement_analysis → Decompose user requirements into tasks
2. evaluator → Evaluate task quality and feasibility
3. interface_definition → Define JSON Schema interfaces
4. master_creation → Create TaskMasters, JobMaster, JobMasterTask
5. validation → Validate workflow interfaces
6. job_registration → Create executable Job

The agent uses conditional routing to handle:
- Evaluation failures (retry or exit)
- Infeasible tasks (propose alternatives or API extensions)
- Validation failures (retry with fixes or exit)
"""

import logging
from typing import Any, Literal

from langgraph.graph import END, StateGraph

from .nodes import (
    evaluator_node,
    interface_definition_node,
    job_registration_node,
    master_creation_node,
    requirement_analysis_node,
    validation_node,
)
from .state import JobTaskGeneratorState

logger = logging.getLogger(__name__)

# Maximum retry count for evaluation and validation
MAX_RETRY_COUNT = 5


def evaluator_router(
    state: JobTaskGeneratorState,
) -> Literal["interface_definition", "requirement_analysis", "master_creation", "END"]:
    """Route after evaluator node based on evaluation result.

    Routing logic:
    1. If evaluation result is missing or error occurred → END
    2. If evaluator_stage is "after_task_breakdown":
       - If valid → interface_definition
       - If invalid and retry < max → requirement_analysis (retry)
       - If invalid and retry >= max → END
    3. If evaluator_stage is "after_interface_definition":
       - If valid → master_creation
       - If invalid and retry < max → interface_definition (retry)
       - If invalid and retry >= max → END

    Args:
        state: Current job task generator state

    Returns:
        Next node name or END
    """
    logger.info("Evaluator router: determining next node")

    evaluation_result = state.get("evaluation_result")
    evaluator_stage = state.get("evaluator_stage", "after_task_breakdown")
    retry_count = state.get("retry_count", 0)
    error_message = state.get("error_message")

    # If error occurred, end workflow
    if error_message:
        logger.error(f"Error detected in state: {error_message}")
        return "END"

    # If evaluation result is missing, end workflow
    if not evaluation_result:
        logger.error("Evaluation result is missing")
        return "END"

    is_valid = evaluation_result.get("is_valid", False)
    all_tasks_feasible = evaluation_result.get("all_tasks_feasible", True)

    logger.info(
        f"Evaluation result: is_valid={is_valid}, "
        f"all_tasks_feasible={all_tasks_feasible}, "
        f"stage={evaluator_stage}, retry_count={retry_count}"
    )

    # Phase 8: Check for empty results (tasks=[] or interfaces=[])
    if evaluator_stage == "after_task_breakdown":
        task_breakdown = state.get("task_breakdown", [])
        logger.debug(
            f"task_breakdown state check: type={type(task_breakdown)}, "
            f"count={len(task_breakdown) if task_breakdown else 0}"
        )
        if not task_breakdown:
            logger.error("Task breakdown returned empty tasks list → END")
            return "END"
    elif evaluator_stage == "after_interface_definition":
        interface_definitions: dict | list = state.get("interface_definitions", {})
        logger.debug(
            f"interface_definitions state check: type={type(interface_definitions)}, "
            f"count={len(interface_definitions) if interface_definitions else 0}"
        )
        if not interface_definitions:
            logger.error("Interface definition returned empty interfaces → END")
            return "END"

    # Log infeasible tasks if any
    infeasible_tasks = evaluation_result.get("infeasible_tasks", [])
    if infeasible_tasks:
        logger.warning(f"Found {len(infeasible_tasks)} infeasible tasks")
        for task in infeasible_tasks:
            logger.warning(f"  - {task.get('task_name')}: {task.get('reason')}")

    # Route based on evaluator stage
    if evaluator_stage == "after_task_breakdown":
        if is_valid:
            print("[DEBUG] Task breakdown valid → interface_definition", flush=True)
            logger.info("Task breakdown valid → interface_definition")
            return "interface_definition"
        else:
            if retry_count < MAX_RETRY_COUNT:
                print(f"[DEBUG] Task breakdown invalid, retry {retry_count + 1}/{MAX_RETRY_COUNT} → requirement_analysis", flush=True)
                logger.warning(
                    f"Task breakdown invalid, retry {retry_count + 1}/{MAX_RETRY_COUNT} → requirement_analysis"
                )
                return "requirement_analysis"
            else:
                print("[DEBUG] Task breakdown invalid, max retries reached → END", flush=True)
                logger.error("Task breakdown invalid, max retries reached → END")
                return "END"

    elif evaluator_stage == "after_interface_definition":
        if is_valid:
            print("[DEBUG] Interface definition valid → master_creation", flush=True)
            logger.info("Interface definition valid → master_creation")
            return "master_creation"
        else:
            if retry_count < MAX_RETRY_COUNT:
                print(f"[DEBUG] Interface definition invalid, retry {retry_count + 1}/{MAX_RETRY_COUNT} → interface_definition", flush=True)
                logger.warning(
                    f"Interface definition invalid, retry {retry_count + 1}/{MAX_RETRY_COUNT} → interface_definition"
                )
                return "interface_definition"
            else:
                print("[DEBUG] Interface definition invalid, max retries reached → END", flush=True)
                logger.error("Interface definition invalid, max retries reached → END")
                return "END"

    else:
        logger.error(f"Unknown evaluator stage: {evaluator_stage}")
        return "END"


def validation_router(
    state: JobTaskGeneratorState,
) -> Literal["job_registration", "interface_definition", "END"]:
    """Route after validation node based on validation result.

    Routing logic:
    1. If validation result is missing or error occurred → END
    2. If validation is successful → job_registration
    3. If validation failed:
       - If retry < max → interface_definition (retry with fixes)
       - If retry >= max → END

    Args:
        state: Current job task generator state

    Returns:
        Next node name or END
    """
    logger.info("Validation router: determining next node")

    validation_result = state.get("validation_result")
    retry_count = state.get("retry_count", 0)
    error_message = state.get("error_message")

    # If error occurred, end workflow
    if error_message:
        logger.error(f"Error detected in state: {error_message}")
        return "END"

    # If validation result is missing, end workflow
    if not validation_result:
        logger.error("Validation result is missing")
        return "END"

    is_valid = validation_result.get("is_valid", False)
    errors = validation_result.get("errors", [])

    logger.info(
        f"Validation result: is_valid={is_valid}, "
        f"errors={len(errors)}, retry_count={retry_count}"
    )

    if errors:
        logger.warning("Validation errors:")
        for error in errors:
            logger.warning(f"  - {error}")

    # Route based on validation result
    if is_valid:
        logger.info("Validation successful → job_registration")
        return "job_registration"
    else:
        if retry_count < MAX_RETRY_COUNT:
            logger.warning(
                f"Validation failed, retry {retry_count + 1}/{MAX_RETRY_COUNT} → interface_definition"
            )
            return "interface_definition"
        else:
            logger.error("Validation failed, max retries reached → END")
            return "END"


def create_job_task_generator_agent() -> Any:
    """Create Job/Task Auto-Generation Agent using LangGraph.

    This function creates a LangGraph StateGraph with the following workflow:

    Flow:
        START → requirement_analysis → evaluator
        evaluator → (conditional)
            - interface_definition (if task breakdown valid)
            - requirement_analysis (if invalid, retry)
            - END (if max retries)
        interface_definition → evaluator (re-evaluate interfaces)
        evaluator → (conditional)
            - master_creation (if interfaces valid)
            - interface_definition (if invalid, retry)
            - END (if max retries)
        master_creation → validation
        validation → (conditional)
            - job_registration (if validation successful)
            - interface_definition (if failed, retry with fixes)
            - END (if max retries)
        job_registration → END

    Returns:
        Compiled LangGraph StateGraph
    """
    logger.info("Creating Job/Task Generator Agent")

    # Create StateGraph
    workflow = StateGraph(JobTaskGeneratorState)

    # Add nodes
    workflow.add_node("requirement_analysis", requirement_analysis_node)
    workflow.add_node("evaluator", evaluator_node)
    workflow.add_node("interface_definition", interface_definition_node)
    workflow.add_node("master_creation", master_creation_node)
    workflow.add_node("validation", validation_node)
    workflow.add_node("job_registration", job_registration_node)

    # Set entry point
    workflow.set_entry_point("requirement_analysis")

    # Add edges
    # requirement_analysis → evaluator
    workflow.add_edge("requirement_analysis", "evaluator")

    # evaluator → (conditional) interface_definition / requirement_analysis / master_creation / END
    workflow.add_conditional_edges(
        "evaluator",
        evaluator_router,
        {
            "interface_definition": "interface_definition",
            "requirement_analysis": "requirement_analysis",
            "master_creation": "master_creation",
            "END": END,
        },
    )

    # interface_definition → evaluator (re-evaluate)
    workflow.add_edge("interface_definition", "evaluator")

    # master_creation → validation
    workflow.add_edge("master_creation", "validation")

    # validation → (conditional) job_registration / interface_definition / END
    workflow.add_conditional_edges(
        "validation",
        validation_router,
        {
            "job_registration": "job_registration",
            "interface_definition": "interface_definition",
            "END": END,
        },
    )

    # job_registration → END
    workflow.add_edge("job_registration", END)

    # Compile graph (Phase 8: recursion_limit is set via RunnableConfig at runtime)
    graph = workflow.compile()

    logger.info("Job/Task Generator Agent created successfully")

    return graph
