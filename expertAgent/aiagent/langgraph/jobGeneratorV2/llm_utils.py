"""LLM utilities for Job Generator V2.

This module provides LLM invocation utilities for structured LLM calls.
Supports multiple LLM providers (Anthropic, OpenAI, Google) with automatic
API key retrieval from MyVault.

Features:
- Structured output with Pydantic model validation
- Markdown JSON/YAML fallback parser for Gemini models
- Langfuse callback integration for observability
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, TypeVar, Union

from pydantic import BaseModel, SecretStr

if TYPE_CHECKING:
    from langchain_anthropic import ChatAnthropic
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_openai import ChatOpenAI

    from .context import ExecutionContext

    # Type alias for LLM clients
    LLMClient = Union[ChatAnthropic, ChatGoogleGenerativeAI, ChatOpenAI]

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


def get_callbacks_from_context(context: "ExecutionContext") -> list[Any]:
    """Extract LangChain callbacks from ExecutionContext.

    This function extracts the tracer (e.g., Langfuse callback handler) from
    the ExecutionContext's observability context and returns it as a list
    of callbacks that can be passed to LangChain's ainvoke method.

    Args:
        context: ExecutionContext with observability settings

    Returns:
        List of LangChain callbacks (may be empty if no tracer is configured)

    Example:
        callbacks = get_callbacks_from_context(context)
        result = await llm.ainvoke(messages, config={"callbacks": callbacks})
    """
    if context.observability and context.observability.tracer:
        return [context.observability.tracer]
    return []


def _extract_content_from_markdown(text: str) -> tuple[str, str]:
    """Extract content from markdown code blocks.

    Handles formats like:
    - ```json\n{...}\n```
    - ```yaml\n...\n```
    - ```\n{...}\n```
    - Raw JSON/YAML without code blocks

    Args:
        text: Raw text that may contain markdown-wrapped content

    Returns:
        Tuple of (extracted content, format hint: 'json', 'yaml', or 'unknown')
    """
    if not text:
        return "", "unknown"

    # Pattern to match ```json ... ```, ```yaml ... ```, or ``` ... ```
    pattern = r"```(json|yaml)?\s*([\s\S]*?)```"
    match = re.search(pattern, text)
    if match:
        format_hint = match.group(1) or "unknown"
        content = match.group(2).strip()
        return content, format_hint

    # If no code block found, return as-is
    return text.strip(), "unknown"


def _parse_markdown_json_response(
    raw_content: str,
    response_model: type[TModel],
) -> TModel | None:
    """Parse JSON/YAML from markdown-wrapped LLM response.

    Some LLM models (e.g., Gemini) with complex Pydantic schemas may return
    JSON/YAML as text in markdown code blocks instead of using native
    structured output. This function extracts and parses that content.

    Args:
        raw_content: Raw text content from LLM response
        response_model: Pydantic model class to parse into

    Returns:
        Parsed model instance, or None if parsing fails
    """
    import yaml

    try:
        content, format_hint = _extract_content_from_markdown(raw_content)
        if not content:
            return None

        data = None

        # Try JSON first (faster and more precise)
        if format_hint in ("json", "unknown"):
            try:
                data = json.loads(content)
                logger.debug("Successfully parsed as JSON")
            except json.JSONDecodeError:
                pass

        # Try YAML if JSON failed or format is yaml
        if data is None and format_hint in ("yaml", "unknown"):
            try:
                data = yaml.safe_load(content)
                logger.debug("Successfully parsed as YAML")
            except yaml.YAMLError as e:
                logger.debug("YAML parse error in markdown fallback: %s", e)

        if data is None:
            logger.debug("Failed to parse content as JSON or YAML")
            return None

        return response_model.model_validate(data)
    except Exception as e:
        logger.debug("Validation error in markdown fallback: %s", e)
        return None


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
            cap_list.append(
                f"- {cap.get('name', 'Unknown')}: {cap.get('description', '')}"
            )
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


def _build_task_breakdown_system_prompt(
    capabilities: list[dict[str, Any]] | None = None,
) -> str:
    """Build the system prompt for task breakdown with API info.

    Args:
        capabilities: Optional list of capability dicts from YAML.
                     If provided, API information is injected into prompt.

    Returns:
        System prompt string with optional API section
    """
    from aiagent.langgraph.shared.capability_utils import format_capabilities_for_prompt

    # Use shared formatting function
    capabilities_section = format_capabilities_for_prompt(capabilities or [])

    # Build recommended_apis instruction section
    api_instruction = ""
    if capabilities and capabilities_section:
        api_instruction = """
## recommended_apis の記述ルール

**重要**: 各タスクには必ず `recommended_apis` を指定してください。

1. タスク実行に必要なAPIを上記リストから選択
2. 各APIには `api_name`, `endpoint`, `reason` を含める
3. 1タスク1API を原則とする

### 例
```json
{
  "task_id": "task_001",
  "name": "Google検索",
  "recommended_apis": [
    {
      "api_name": "Google検索",
      "endpoint": "/v1/utility/google_search",
      "reason": "キーワードでWeb検索を実行"
    }
  ]
}
```
"""

    # Build base prompt
    base_prompt = """You are an expert task decomposition assistant.
Your task is to decompose user requirements into executable workflow tasks.

## Principles
1. Hierarchical decomposition - Break complex tasks into smaller units
2. Clear dependencies - Define which tasks depend on others
3. Specificity and executability - Each task should be specific and actionable
4. Modularity and reusability - Design tasks that can be reused"""

    # Add API selection principle if capabilities provided
    if capabilities and capabilities_section:
        base_prompt += "\n5. **API Selection** - Each task MUST specify recommended_apis from available APIs"

    # Build output format section
    output_format = """
## Output Format
Return a structured response with:
- tasks: List of TaskBreakdownItem with task_id, name, description, dependencies, recommended_apis
- overall_summary: Summary of the entire workflow
- job_body_parameters: Parameters extracted from the requirements
"""

    # Combine all sections
    if capabilities_section:
        return f"{base_prompt}\n\n{capabilities_section}\n{api_instruction}\n{output_format}"
    else:
        return f"{base_prompt}\n{output_format}"


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
Task ID: {task.get("id", "unknown")}
Name: {task.get("name", "Unknown Task")}
Description: {task.get("description", "No description")}
Type: {task.get("task_type", "unknown")}
Recommended API: {task.get("recommended_api", "N/A")}
Dependencies: {", ".join(task.get("dependencies", [])) or "None"}
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
    callbacks: list[Any] | None = None,
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
        callbacks: Optional list of LangChain callbacks (e.g., Langfuse handler)
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
        raise StructuredLLMError(
            "Either 'messages' or both 'system_prompt' and 'user_prompt' must be provided"
        )

    if response_model is None:
        raise StructuredLLMError("response_model is required")

    # Determine model to use
    actual_model = model_name
    if model_env_var:
        actual_model = os.environ.get(model_env_var, default_model or model_name)
    elif default_model:
        actual_model = default_model

    try:
        from core.secrets import secrets_manager

        # Initialize LLM client based on model prefix
        llm: Any  # Use Any to avoid complex union type issues
        if actual_model.startswith("gemini"):
            from langchain_google_genai import ChatGoogleGenerativeAI

            try:
                google_api_key = secrets_manager.get_secret(
                    "GOOGLE_API_KEY", project=None
                )
            except ValueError as e:
                raise StructuredLLMError(
                    f"Failed to get GOOGLE_API_KEY from MyVault: {e}. "
                    f"Please ensure GOOGLE_API_KEY is set in MyVault default_project."
                ) from e

            llm = ChatGoogleGenerativeAI(
                model=actual_model,
                temperature=temperature,
                google_api_key=google_api_key,
                max_output_tokens=16384,  # Issue #385: Prevent truncation
            )
        elif actual_model.startswith("claude"):
            from langchain_anthropic import ChatAnthropic

            try:
                anthropic_api_key = secrets_manager.get_secret(
                    "ANTHROPIC_API_KEY", project=None
                )
            except ValueError as e:
                raise StructuredLLMError(
                    f"Failed to get ANTHROPIC_API_KEY from MyVault: {e}. "
                    f"Please ensure ANTHROPIC_API_KEY is set in MyVault default_project."
                ) from e

            llm = ChatAnthropic(  # type: ignore[call-arg]
                model_name=actual_model,
                temperature=temperature,
                api_key=SecretStr(anthropic_api_key),
                max_tokens=16384,  # Issue #385: Prevent truncation
            )
        elif actual_model.startswith("gpt"):
            from langchain_openai import ChatOpenAI

            try:
                openai_api_key = secrets_manager.get_secret(
                    "OPENAI_API_KEY", project=None
                )
            except ValueError as e:
                raise StructuredLLMError(
                    f"Failed to get OPENAI_API_KEY from MyVault: {e}. "
                    f"Please ensure OPENAI_API_KEY is set in MyVault default_project."
                ) from e

            llm = ChatOpenAI(
                model=actual_model,
                temperature=temperature,
                api_key=SecretStr(openai_api_key),
                max_tokens=16384,  # Issue #385: Prevent truncation
            )
        else:
            from langchain_anthropic import ChatAnthropic

            try:
                anthropic_api_key = secrets_manager.get_secret(
                    "ANTHROPIC_API_KEY", project=None
                )
            except ValueError as e:
                raise StructuredLLMError(
                    f"Failed to get ANTHROPIC_API_KEY from MyVault: {e}. "
                    f"Please ensure ANTHROPIC_API_KEY is set in MyVault default_project."
                ) from e

            llm = ChatAnthropic(  # type: ignore[call-arg]
                model_name=actual_model,
                temperature=temperature,
                api_key=SecretStr(anthropic_api_key),
                max_tokens=16384,  # Issue #385: Prevent truncation
            )

        # Use include_raw=True to get both structured output and raw text
        # This allows fallback parsing for Gemini's markdown-wrapped JSON
        structured_llm = llm.with_structured_output(response_model, include_raw=True)

        # Build messages
        lc_messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=usr_prompt),
        ]

        # Build config with callbacks for Langfuse tracing
        invoke_config: dict[str, Any] = {}
        if callbacks:
            invoke_config["callbacks"] = callbacks

        # Invoke
        raw_result = await structured_llm.ainvoke(
            lc_messages,
            config=invoke_config if invoke_config else None,
        )

        # Extract parsed result and raw content
        result = (
            raw_result.get("parsed") if isinstance(raw_result, dict) else raw_result
        )
        raw_message = raw_result.get("raw") if isinstance(raw_result, dict) else None
        raw_content = (
            raw_message.content
            if raw_message and hasattr(raw_message, "content")
            else None
        )

        recovered_via_json = False

        # If structured output failed but we have raw content, try markdown fallback
        if result is None and raw_content:
            logger.info(
                "Structured output returned None, attempting markdown JSON fallback "
                "(model=%s, context=%s)",
                actual_model,
                context_label,
            )
            result = _parse_markdown_json_response(raw_content, response_model)
            if result is not None:
                recovered_via_json = True
                logger.info(
                    "Successfully recovered response via markdown JSON fallback "
                    "(model=%s, context=%s)",
                    actual_model,
                    context_label,
                )

        # If still None after fallback, raise error
        if result is None:
            raise StructuredLLMError(
                f"LLM returned None response and markdown fallback failed "
                f"(model={actual_model}, context={context_label})"
            )

        # Validate if validator provided
        if validator is not None:
            result = validator(result)

        return StructuredCallResult(
            result=result,
            recovered_via_json=recovered_via_json,
            raw_text=raw_content,
            model_name=actual_model,
        )
    except StructuredLLMError:
        raise
    except Exception as exc:
        raise StructuredLLMError(f"LLM invocation failed: {exc}") from exc
