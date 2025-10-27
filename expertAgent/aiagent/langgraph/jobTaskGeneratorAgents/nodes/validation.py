"""Validation node for job task generator.

This module provides the validation node that validates workflow interface
compatibility using jobqueue's WorkflowValidator, and generates fix proposals
if validation errors are detected.
"""

import logging
from typing import Any

from ..prompts.validation_fix import (
    VALIDATION_FIX_SYSTEM_PROMPT,
    ValidationFixResponse,
    create_validation_fix_prompt,
)
from ..state import JobTaskGeneratorState
from ..utils.jobqueue_client import JobqueueClient
from ..utils.llm_invocation import StructuredLLMError, invoke_structured_llm

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

        interface_definitions_obj = state.get("interface_definitions", {})
        if not isinstance(interface_definitions_obj, dict):
            logger.warning(
                "interface_definitions state expected dict but got %s",
                type(interface_definitions_obj).__name__,
            )
            interface_definitions_obj = {}

        interface_list: list[dict[str, Any]] = list(interface_definitions_obj.values())

        user_prompt = create_validation_fix_prompt(errors, interface_list)
        messages = [
            {"role": "system", "content": VALIDATION_FIX_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        try:
            call_result = await invoke_structured_llm(
                messages=messages,
                response_model=ValidationFixResponse,
                context_label="validation_fix",
                model_env_var="JOB_GENERATOR_VALIDATION_MODEL",
                default_model="claude-haiku-4-5",
            )
        except StructuredLLMError as exc:
            logger.error("Validation fix proposal generation failed: %s", exc)
            new_retry = state.get("retry_count", 0) + 1
            return {
                **state,
                "error_message": str(exc),
                "retry_count": new_retry,
            }

        fix_response = call_result.result
        logger.info(
            "Fix proposals generated (model=%s can_fix=%s)",
            call_result.model_name,
            fix_response.can_fix,
        )
        if call_result.recovered_via_json:
            logger.info("Validation fix proposals succeeded via JSON fallback")

        if fix_response.fix_summary:
            logger.debug("Fix summary: %s", fix_response.fix_summary)

        if fix_response.interface_fixes:
            logger.info(
                "Interface fixes suggested: %s",
                len(fix_response.interface_fixes),
            )
            for fix in fix_response.interface_fixes:
                logger.info(
                    "Interface fix %s (%s): %s",
                    fix.task_id,
                    fix.error_type,
                    fix.fix_explanation,
                )

        if fix_response.manual_action_required:
            logger.warning(
                "Manual action required: %s",
                fix_response.manual_action_required,
            )

        new_retry = state.get("retry_count", 0) + 1
        return {
            **state,
            "validation_result": {
                "is_valid": False,
                "errors": errors,
                "warnings": warnings,
                "fix_proposals": fix_response.model_dump(),
            },
            "retry_count": new_retry,
        }

    except Exception as e:
        logger.error(f"Failed to validate workflow: {e}", exc_info=True)
        new_retry = state.get("retry_count", 0) + 1
        return {
            **state,
            "error_message": f"Validation failed: {str(e)}",
            "retry_count": new_retry,
        }
