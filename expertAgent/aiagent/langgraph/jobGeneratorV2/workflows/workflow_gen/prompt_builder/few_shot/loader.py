"""Few-shot example loader for Workflow Generator V2.

This module provides functions to load and select appropriate
few-shot examples based on task characteristics.

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Directory containing few-shot examples
FEW_SHOT_DIR = Path(__file__).parent


@dataclass
class FewShotExample:
    """Few-shot example data.

    Attributes:
        name: Pattern name
        description: Pattern description
        applicable_apis: List of applicable API names
        task_example: Example task definition
        workflow_yaml: Example workflow YAML string
    """

    name: str
    description: str
    applicable_apis: list[str]
    task_example: dict[str, Any]
    workflow_yaml: str


def load_example(pattern_name: str) -> FewShotExample | None:
    """Load a single few-shot example by pattern name.

    Args:
        pattern_name: Name of the pattern (e.g., 'search_pattern')

    Returns:
        FewShotExample if found, None otherwise
    """
    yaml_file = FEW_SHOT_DIR / f"{pattern_name}.yaml"

    if not yaml_file.exists():
        logger.warning("Few-shot example not found: %s", pattern_name)
        return None

    try:
        with open(yaml_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return FewShotExample(
            name=data.get("name", pattern_name),
            description=data.get("description", ""),
            applicable_apis=data.get("applicable_apis", []),
            task_example=data.get("task_example", {}),
            workflow_yaml=data.get("workflow_yaml", ""),
        )
    except Exception as e:
        logger.error("Error loading few-shot example %s: %s", pattern_name, e)
        return None


def load_all_examples() -> list[FewShotExample]:
    """Load all available few-shot examples.

    Returns:
        List of FewShotExample objects
    """
    examples = []
    pattern_files = FEW_SHOT_DIR.glob("*_pattern.yaml")

    for yaml_file in pattern_files:
        pattern_name = yaml_file.stem
        example = load_example(pattern_name)
        if example:
            examples.append(example)

    return examples


def _has_array_output(schema: dict[str, Any] | None) -> bool:
    """Check if output schema contains array type.

    Args:
        schema: JSON Schema dictionary

    Returns:
        True if schema has array output
    """
    if not schema:
        return False
    if schema.get("type") == "array":
        return True
    properties = schema.get("properties", {})
    return any(prop.get("type") == "array" for prop in properties.values())


def _has_nested_object_output(schema: dict[str, Any] | None) -> bool:
    """Check if output schema contains nested objects.

    Args:
        schema: JSON Schema dictionary

    Returns:
        True if schema has nested object output
    """
    if not schema:
        return False
    properties = schema.get("properties", {})
    for prop in properties.values():
        if prop.get("type") == "object":
            return True
        if (
            prop.get("type") == "array"
            and prop.get("items", {}).get("type") == "object"
        ):
            return True
    return False


def _has_array_input(schema: dict[str, Any] | None) -> bool:
    """Check if input schema contains array type.

    Args:
        schema: JSON Schema dictionary

    Returns:
        True if schema has array input
    """
    if not schema:
        return False
    if schema.get("type") == "array":
        return True
    properties = schema.get("properties", {})
    return any(prop.get("type") == "array" for prop in properties.values())


def select_few_shot_examples(
    recommended_apis: list[str] | None = None,
    input_schema: dict[str, Any] | None = None,
    output_schema: dict[str, Any] | None = None,
    dependencies: list[str] | None = None,
    max_examples: int = 2,
) -> list[FewShotExample]:
    """Select appropriate few-shot examples based on task characteristics.

    Uses a scoring algorithm to select the most relevant examples:
    1. API type matching (base score)
    2. Output schema characteristics (array, nested)
    3. Dependency complexity
    4. Input schema characteristics

    Args:
        recommended_apis: List of recommended API names
        input_schema: Task input JSON Schema
        output_schema: Task output JSON Schema
        dependencies: List of dependent task IDs
        max_examples: Maximum number of examples to return

    Returns:
        List of most relevant FewShotExample objects
    """
    scored_patterns: dict[str, float] = {}

    # 1. API type scoring
    for api in recommended_apis or []:
        api_lower = api.lower()
        if "search" in api_lower or "google_search" in api_lower:
            scored_patterns["search_pattern"] = (
                scored_patterns.get("search_pattern", 0) + 1.0
            )
        if "gmail" in api_lower and "send" in api_lower:
            # Issue #342: Prefer gmail_send_pattern for gmail send APIs
            scored_patterns["gmail_send_pattern"] = (
                scored_patterns.get("gmail_send_pattern", 0) + 1.5
            )
            scored_patterns["api_call_pattern"] = (
                scored_patterns.get("api_call_pattern", 0) + 1.0
            )
        if "slack" in api_lower:
            # Issue #342: Prefer slack_notify_pattern for slack APIs
            scored_patterns["slack_notify_pattern"] = (
                scored_patterns.get("slack_notify_pattern", 0) + 1.5
            )
            scored_patterns["api_call_pattern"] = (
                scored_patterns.get("api_call_pattern", 0) + 0.8
            )
        if "drive" in api_lower or "upload" in api_lower:
            scored_patterns["api_call_pattern"] = (
                scored_patterns.get("api_call_pattern", 0) + 0.8
            )
        if "tts" in api_lower or "speech" in api_lower:
            scored_patterns["api_call_pattern"] = (
                scored_patterns.get("api_call_pattern", 0) + 0.8
            )
        if "explorer" in api_lower or "llm" in api_lower or "gemini" in api_lower:
            scored_patterns["llm_chain_pattern"] = (
                scored_patterns.get("llm_chain_pattern", 0) + 1.0
            )
        if "jsonoutput" in api_lower:
            scored_patterns["llm_chain_pattern"] = (
                scored_patterns.get("llm_chain_pattern", 0) + 1.2
            )

    # 2. Output schema scoring
    if _has_array_output(output_schema):
        scored_patterns["map_pattern"] = scored_patterns.get("map_pattern", 0) + 1.5

    if _has_nested_object_output(output_schema):
        scored_patterns["llm_chain_pattern"] = (
            scored_patterns.get("llm_chain_pattern", 0) + 1.0
        )

    # 3. Dependency complexity scoring
    dependency_count = len(dependencies or [])
    if dependency_count > 2:
        scored_patterns["llm_chain_pattern"] = (
            scored_patterns.get("llm_chain_pattern", 0) + 1.2
        )
    elif dependency_count > 0:
        scored_patterns["api_call_pattern"] = (
            scored_patterns.get("api_call_pattern", 0) + 0.5
        )

    # 4. Input schema scoring
    if _has_array_input(input_schema):
        scored_patterns["map_pattern"] = scored_patterns.get("map_pattern", 0) + 1.0

    # Sort by score and select top patterns
    sorted_patterns = sorted(scored_patterns.items(), key=lambda x: x[1], reverse=True)

    selected_names = [pattern for pattern, _ in sorted_patterns[:max_examples]]

    # Ensure at least one default pattern
    if not selected_names:
        selected_names = ["api_call_pattern"]

    # Load selected examples
    examples = []
    for name in selected_names:
        example = load_example(name)
        if example:
            examples.append(example)

    return examples


def get_example_by_api(api_name: str) -> FewShotExample | None:
    """Get the best few-shot example for a specific API.

    Args:
        api_name: API name to match

    Returns:
        Best matching FewShotExample or None
    """
    all_examples = load_all_examples()

    for example in all_examples:
        if api_name.lower() in [a.lower() for a in example.applicable_apis]:
            return example

    # Return default api_call_pattern
    return load_example("api_call_pattern")
