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
    messages: list[dict[str, str]] | None = None,
    response_model: type[TModel] | None = None,
    *,
    system_prompt: str | None = None,
    user_prompt: str | None = None,
    model_name: str = "claude-haiku-4-5",
    temperature: float = 0.7,
    context_label: str = "llm_call",
    model_env_var: str | None = None,
    default_model: str | None = None,
    validator: Any = None,
    **kwargs: Any,
) -> StructuredCallResult[TModel]:
    """Invoke LLM with structured output.

    Supports two calling conventions:
    1. messages=[{"role": "system", "content": ...}, {"role": "user", "content": ...}]
    2. system_prompt="...", user_prompt="..."

    Args:
        messages: List of message dicts with role and content
        response_model: Pydantic model class for the response
        system_prompt: System prompt for the LLM (alternative to messages)
        user_prompt: User prompt with the request (alternative to messages)
        model_name: Name of the model to use
        temperature: Sampling temperature
        context_label: Label for logging/tracing
        model_env_var: Environment variable for model override
        default_model: Default model if env var not set
        validator: Optional validator function for response
        **kwargs: Additional arguments

    Returns:
        StructuredCallResult with the parsed response

    Raises:
        StructuredLLMError: If LLM invocation fails
    """
    import os
    from langchain_core.messages import HumanMessage, SystemMessage

    # Handle different calling conventions
    if messages is not None:
        # Extract system and user prompts from messages
        sys_prompt = ""
        usr_prompt = ""
        for msg in messages:
            if msg.get("role") == "system":
                sys_prompt = msg.get("content", "")
            elif msg.get("role") == "user":
                usr_prompt = msg.get("content", "")
    elif system_prompt is not None and user_prompt is not None:
        sys_prompt = system_prompt
        usr_prompt = user_prompt
    else:
        raise StructuredLLMError("Either 'messages' or both 'system_prompt' and 'user_prompt' must be provided")

    if response_model is None:
        raise StructuredLLMError("response_model is required")

    # Determine model to use
    actual_model = model_name
    if model_env_var:
        actual_model = os.environ.get(model_env_var, default_model or model_name)
    elif default_model:
        actual_model = default_model

    try:
        # Select appropriate LLM client based on model name
        if actual_model.startswith("gemini"):
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(model=actual_model, temperature=temperature)
        elif actual_model.startswith("claude"):
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(model=actual_model, temperature=temperature)
        elif actual_model.startswith("gpt"):
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model=actual_model, temperature=temperature)
        else:
            # Default to Anthropic for unknown models
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(model=actual_model, temperature=temperature)

        structured_llm = llm.with_structured_output(response_model)

        # Build messages
        lc_messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=usr_prompt),
        ]

        # Invoke
        result = await structured_llm.ainvoke(lc_messages)

        # Validate if validator provided
        if validator is not None:
            result = validator(result)

        return StructuredCallResult(
            result=result,
            model_name=actual_model,
        )
    except Exception as exc:
        raise StructuredLLMError(f"LLM invocation failed: {exc}") from exc
