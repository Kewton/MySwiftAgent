"""Job/Task Auto-Generation Agent using LangGraph.

This module provides the main LangGraph agent that orchestrates the workflow
for automatically generating Jobs and Tasks from user requirements.

Workflow:
1. requirement_analysis → Decompose user requirements into tasks
2. evaluator → Evaluate task quality and feasibility
3. interface_definition → Define JSON Schema interfaces
4. schema_enrichment → Enrich interfaces with OpenAPI schemas
5. master_creation → Create TaskMasters, JobMaster, JobMasterTask
6. validation → Validate workflow interfaces
7. job_registration → Create executable Job

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
    schema_enrichment_node,
    validation_node,
)
from .state import JobTaskGeneratorState

logger = logging.getLogger(__name__)

# Maximum retry count for evaluation and validation
MAX_RETRY_COUNT = 5


def evaluator_router(
    state: JobTaskGeneratorState,
) -> Literal[
    "interface_definition",
    "requirement_analysis",
    "master_creation",
    "END",
]:
    """Determine the next node after the evaluator step."""

    evaluation_result = state.get("evaluation_result")
    evaluator_stage = state.get("evaluator_stage", "after_task_breakdown")
    retry_count = state.get("retry_count", 0)
    error_message = state.get("error_message")

    logger.info(
        "Evaluator router invoked: stage=%s retry=%s error_present=%s",
        evaluator_stage,
        retry_count,
        bool(error_message),
    )

    if error_message:
        logger.error(
            "Stopping workflow after evaluator error: %s",
            error_message,
        )
        return "END"

    if not evaluation_result:
        logger.error("Stopping workflow: evaluation result missing")
        return "END"

    is_valid = evaluation_result.get("is_valid", False)
    all_tasks_feasible = evaluation_result.get("all_tasks_feasible", True)

    logger.debug(
        "Evaluation summary: is_valid=%s all_tasks_feasible=%s",
        is_valid,
        all_tasks_feasible,
    )

    if evaluator_stage == "after_task_breakdown":
        task_breakdown = state.get("task_breakdown", [])
        if not task_breakdown:
            logger.error("Task breakdown produced no tasks; aborting")
            return "END"
    elif evaluator_stage == "after_interface_definition":
        interface_definitions = state.get("interface_definitions", {})
        if not interface_definitions:
            logger.error(
                "Interface definition produced no interfaces; aborting",
            )
            return "END"
    else:
        logger.error("Unknown evaluator stage: %s", evaluator_stage)
        return "END"

    infeasible_tasks = evaluation_result.get("infeasible_tasks", [])
    if infeasible_tasks:
        logger.warning(
            "Detected %d infeasible tasks from evaluator",
            len(infeasible_tasks),
        )
        for task in infeasible_tasks:
            logger.warning(
                "Infeasible task: %s (%s)",
                task.get("task_name"),
                task.get("reason"),
            )

    if evaluator_stage == "after_task_breakdown":
        if is_valid:
            return "interface_definition"
        if retry_count < MAX_RETRY_COUNT:
            return "requirement_analysis"
        logger.error("Max retries reached for requirement analysis")
        return "END"

    if evaluator_stage == "after_interface_definition":
        if is_valid:
            return "master_creation"
        if retry_count < MAX_RETRY_COUNT:
            return "interface_definition"
        logger.error("Max retries reached for interface definition")
        return "END"

    return "END"


def validation_router(
    state: JobTaskGeneratorState,
) -> Literal["job_registration", "interface_definition", "END"]:
    """Determine the next node after workflow validation."""

    validation_result = state.get("validation_result")
    retry_count = state.get("retry_count", 0)
    error_message = state.get("error_message")

    logger.info(
        "Validation router invoked: retry=%s error_present=%s",
        retry_count,
        bool(error_message),
    )

    if error_message:
        logger.error("Stopping workflow during validation: %s", error_message)
        return "END"

    if not validation_result:
        logger.error("Stopping workflow: validation result missing")
        return "END"

    is_valid = validation_result.get("is_valid", False)
    errors = validation_result.get("errors", [])

    if errors:
        logger.warning("Validation errors detected: %s", errors)

    if is_valid:
        return "job_registration"

    if retry_count < MAX_RETRY_COUNT:
        return "interface_definition"

    logger.error("Validation retries exhausted; ending workflow")
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
        interface_definition → schema_enrichment (enrich with OpenAPI schemas)
        schema_enrichment → evaluator (re-evaluate interfaces)
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
    workflow.add_node("schema_enrichment", schema_enrichment_node)
    workflow.add_node("master_creation", master_creation_node)
    workflow.add_node("validation", validation_node)
    workflow.add_node("job_registration", job_registration_node)

    # Set entry point
    workflow.set_entry_point("requirement_analysis")

    # Add edges
    # requirement_analysis → evaluator
    workflow.add_edge("requirement_analysis", "evaluator")

    # evaluator → conditional routing for interface_definition /
    # requirement_analysis / master_creation / END
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

    # interface_definition → schema_enrichment
    workflow.add_edge("interface_definition", "schema_enrichment")

    # schema_enrichment → evaluator (re-evaluate)
    workflow.add_edge("schema_enrichment", "evaluator")

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

    # Compile graph (recursion_limit is set via RunnableConfig at runtime)
    graph = workflow.compile()

    logger.info("Job/Task Generator Agent created successfully")

    return graph
