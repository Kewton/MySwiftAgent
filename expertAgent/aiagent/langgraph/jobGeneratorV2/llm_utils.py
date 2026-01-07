"""LLM utilities for Job Generator V2.

This module provides LLM invocation utilities that don't depend on langchain.
During Phase E integration, these will be connected to the actual LLM services.

Issue #342: These utilities support the new architecture.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

TModel = TypeVar("TModel", bound=BaseModel)


class StructuredLLMError(RuntimeError):
    """Raised when structured model calls fail."""


@dataclass(slots=True)
class StructuredCallResult(Generic[TModel]):
    """Result from structured LLM invocation.

    Attributes:
        result: The parsed Pydantic model
        recovered_via_json: Whether JSON parsing fallback was used
        raw_text: Raw response text for debugging
        model_name: Name of the model used
        trace_id: Optional trace ID for observability
    """

    result: TModel
    recovered_via_json: bool = False
    raw_text: str | None = None
    model_name: str = "unknown"
    trace_id: str | None = None


# ----- Prompt Constants -----

INTERFACE_SCHEMA_SYSTEM_PROMPT = """You are an expert API interface designer.
Your task is to define JSON Schema specifications for task input/output interfaces.

## Requirements
1. Follow JSON Schema Draft 7 specification
2. Include clear descriptions for all properties
3. Define appropriate required fields
4. Use consistent naming conventions (snake_case)
5. Include examples where helpful

## Output Format
Return a structured response with interface definitions for each task.
Each interface should have:
- task_id: The ID of the task
- interface_name: A descriptive name for the interface
- description: What this interface does
- input_schema: JSON Schema for task input
- output_schema: JSON Schema for task output
- derived_fields: Optional pre-processed output fields
"""


TASK_BREAKDOWN_SYSTEM_PROMPT = """You are an expert task decomposition assistant.
Your task is to decompose user requirements into executable workflow tasks.

## Principles
1. Hierarchical decomposition - Break complex tasks into smaller units
2. Clear dependencies - Define which tasks depend on others
3. Specificity and executability - Each task should be specific and actionable
4. Modularity and reusability - Design tasks that can be reused

## Output Format
Return a structured response with:
- tasks: List of TaskBreakdownItem with task_id, name, description, dependencies
- overall_summary: Summary of the entire workflow
- job_body_parameters: Parameters extracted from the requirements
"""


def create_task_breakdown_prompt(
    user_requirement: str,
    available_capabilities: list[dict[str, Any]] | None = None,
    max_tasks: int = 10,
) -> str:
    """Create the prompt for task breakdown.

    Args:
        user_requirement: The user's requirement to decompose
        available_capabilities: Optional list of available APIs/capabilities
        max_tasks: Maximum number of tasks to generate

    Returns:
        Formatted prompt string
    """
    capabilities_section = ""
    if available_capabilities:
        cap_list = []
        for cap in available_capabilities:
            cap_list.append(f"- {cap.get('name', 'Unknown')}: {cap.get('description', '')}")
        capabilities_section = f"""
## Available Capabilities
{chr(10).join(cap_list)}
"""

    return f"""## User Requirement
{user_requirement}

{capabilities_section}

Please decompose this requirement into a maximum of {max_tasks} executable tasks.
Each task should have a unique task_id (e.g., 'task_001'), a clear name, and a detailed description.
Define dependencies between tasks where necessary.
"""


def _build_task_breakdown_system_prompt() -> str:
    """Build the system prompt for task breakdown.

    Returns:
        System prompt string
    """
    return TASK_BREAKDOWN_SYSTEM_PROMPT


def create_interface_schema_prompt(
    tasks: list[dict[str, Any]],
    user_requirement: str,
) -> str:
    """Create the prompt for interface schema generation.

    Args:
        tasks: List of task definitions as dicts
        user_requirement: The original user requirement

    Returns:
        Formatted prompt string
    """
    task_descriptions = []
    for task in tasks:
        task_desc = f"""
Task ID: {task.get('id', 'unknown')}
Name: {task.get('name', 'Unknown Task')}
Description: {task.get('description', 'No description')}
Type: {task.get('task_type', 'unknown')}
Recommended API: {task.get('recommended_api', 'N/A')}
Dependencies: {', '.join(task.get('dependencies', [])) or 'None'}
"""
        task_descriptions.append(task_desc)

    return f"""## User Requirement
{user_requirement}

## Tasks to Define Interfaces For
{chr(10).join(task_descriptions)}

Please generate JSON Schema definitions for each task's input and output.
Consider the data flow between dependent tasks.
"""


async def invoke_structured_llm(
    system_prompt: str,
    user_prompt: str,
    response_model: type[TModel],
    model_name: str = "claude-haiku-4-5",
    temperature: float = 0.7,
    **kwargs: Any,
) -> StructuredCallResult[TModel]:
    """Invoke LLM with structured output.

    This is a placeholder implementation for Phase C testing.
    During Phase E, this will be connected to actual LLM services.

    Args:
        system_prompt: System prompt for the LLM
        user_prompt: User prompt with the request
        response_model: Pydantic model class for the response
        model_name: Name of the model to use
        temperature: Sampling temperature
        **kwargs: Additional arguments

    Returns:
        StructuredCallResult with the parsed response

    Raises:
        StructuredLLMError: If LLM invocation fails
    """
    # This is a placeholder - actual implementation will be in Phase E
    # For now, raise an error if actually called (tests should mock this)
    raise StructuredLLMError(
        "LLM invocation not implemented in Phase C. "
        "Use mocks for testing or wait for Phase E integration."
    )
