"""Validation node for job task generator.

This module provides the validation node that validates workflow interface
compatibility using jobqueue's WorkflowValidator, and generates fix proposals
if validation errors are detected.
"""

import logging

from langchain_anthropic import ChatAnthropic

from ..prompts.validation_fix import (
    VALIDATION_FIX_SYSTEM_PROMPT,
    ValidationFixResponse,
    create_validation_fix_prompt,
)
from ..state import JobTaskGeneratorState
from ..utils.jobqueue_client import JobqueueClient

logger = logging.getLogger(__name__)


async def validation_node(
    state: JobTaskGeneratorState,
) -> JobTaskGeneratorState:
    """Validate workflow and propose fixes for validation errors.

    This node:
    1. Calls jobqueue Validation API
    2. Analyzes validation results
    3. Generates fix proposals using LLM if errors exist
    4. Returns validation results to state

    Args:
        state: Current job task generator state

    Returns:
        Updated state with validation results
    """
    logger.info("Starting validation node")

    job_master_id = state.get("job_master_id")
    if not job_master_id:
        logger.error("JobMaster ID is missing")
        return {
            **state,
            "error_message": "JobMaster ID is required for validation",
        }

    logger.debug(f"Validating JobMaster: {job_master_id}")

    try:
        # Initialize jobqueue client
        client = JobqueueClient()

        # Call validation API
        logger.info(f"Calling validation API for JobMaster {job_master_id}")
        validation_result = await client.validate_workflow(job_master_id)

        is_valid = validation_result.get("is_valid", False)
        errors = validation_result.get("errors", [])
        warnings = validation_result.get("warnings", [])

        logger.info(f"Validation result: is_valid={is_valid}")
        logger.info(f"Errors: {len(errors)}, Warnings: {len(warnings)}")

        if errors:
            logger.warning("Validation errors detected:")
            for error in errors:
                logger.warning(f"  - {error}")

        if warnings:
            logger.info("Validation warnings:")
            for warning in warnings:
                logger.info(f"  - {warning}")

        # If validation passed, return success
        if is_valid:
            return {
                **state,
                "validation_result": {
                    "is_valid": True,
                    "errors": [],
                    "warnings": warnings,
                },
                "retry_count": 0,
            }

        # If validation failed, generate fix proposals using LLM
        logger.info("Generating fix proposals for validation errors")

        interface_definitions = state.get("interface_definitions", {})
        interface_list = list(interface_definitions.values())

        # Initialize LLM (claude-haiku-4-5)
        model = ChatAnthropic(
            model="claude-haiku-4-5",
            temperature=0.0,
        )

        # Create structured output model
        structured_model = model.with_structured_output(ValidationFixResponse)

        # Create prompt
        user_prompt = create_validation_fix_prompt(errors, interface_list)
        logger.debug(f"Created validation fix prompt (length: {len(user_prompt)})")

        # Invoke LLM
        messages = [
            {"role": "system", "content": VALIDATION_FIX_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        logger.info("Invoking LLM for validation fix proposals")
        fix_response = await structured_model.ainvoke(messages)

        logger.info(f"Fix proposals generated: can_fix={fix_response.can_fix}")
        logger.info(f"Fix summary: {fix_response.fix_summary}")

        if fix_response.interface_fixes:
            logger.info(f"Found {len(fix_response.interface_fixes)} interface fixes")
            for fix in fix_response.interface_fixes:
                logger.info(
                    f"  - {fix.task_id}: {fix.error_type} - {fix.fix_explanation}"
                )

        if fix_response.manual_action_required:
            logger.warning(
                f"Manual action required: {fix_response.manual_action_required}"
            )

        # Return validation result with fix proposals
        return {
            **state,
            "validation_result": {
                "is_valid": False,
                "errors": errors,
                "warnings": warnings,
                "fix_proposals": fix_response.model_dump(),
            },
            "retry_count": state.get("retry_count", 0),
        }

    except Exception as e:
        logger.error(f"Failed to validate workflow: {e}", exc_info=True)
        return {
            **state,
            "error_message": f"Validation failed: {str(e)}",
        }
