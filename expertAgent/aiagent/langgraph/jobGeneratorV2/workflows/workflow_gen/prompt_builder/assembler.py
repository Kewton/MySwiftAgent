"""Prompt assembler for Workflow Generator V2.

This module assembles the final prompt from components.

Issue #342 Phase F: WorkflowGen V2 LLM Integration
Issue #342 Iteration 2: Dead code integration
- INT-3: APISchemaInjector integration for API spec injection
- INT-4: WorkflowPatternLibrary integration for pattern suggestions

Issue #343: API info deduplication warning
"""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from typing import Any

from aiagent.langgraph.jobGeneratorV2.injectors import APISchemaInjector
from aiagent.langgraph.jobGeneratorV2.patterns import WorkflowPatternLibrary

from .constraints import format_multiple_api_constraints
from .few_shot import FewShotExample, select_few_shot_examples
from .rules import (
    get_agent_rules,
    get_api_rules,
    get_base_rules,
    get_reference_rules,
)
from .system import get_system_prompt


@dataclass
class WorkflowPrompt:
    """Assembled workflow generation prompt.

    Attributes:
        system: System prompt defining the role
        rules: GraphAI rules section
        api_constraints: API-specific constraints
        examples: Few-shot examples
        task_context: Task-specific context
        error_feedback: Previous error feedback (for retries)
    """

    system: str
    rules: str
    api_constraints: str
    examples: list[FewShotExample]
    task_context: str
    error_feedback: str = ""

    def render(self) -> str:
        """Render the complete user prompt.

        Returns:
            Formatted user prompt string
        """
        sections = [
            self.rules,
            self.api_constraints,
        ]

        # Add few-shot examples with URL warning
        if self.examples:
            sections.append("\n## Examples\n")
            # Issue #342 V2: Add warning to prevent LLM from copying example URLs
            sections.append(
                "⚠️ **CRITICAL**: The examples below use PLACEHOLDER URLs.\n"
                "⚠️ **DO NOT** copy URLs from these examples.\n"
                "⚠️ **ALWAYS** use the EXACT URLs from the "
                "'API Endpoint Mappings' section above.\n"
            )
            for i, example in enumerate(self.examples, 1):
                sections.append(f"### Example {i}: {example.name}")
                sections.append(f"Description: {example.description}")
                sections.append("```yaml")
                sections.append(example.workflow_yaml)
                sections.append("```\n")

        # Add task context
        sections.append(self.task_context)

        # Add error feedback (for retries)
        if self.error_feedback:
            sections.append(self.error_feedback)

        return "\n".join(sections)


def build_task_context(
    task_name: str,
    task_description: str,
    input_schema: dict[str, Any],
    output_schema: dict[str, Any],
    dependencies: list[str] | None = None,
) -> str:
    """Build task context section.

    Args:
        task_name: Name of the task
        task_description: Task description
        input_schema: Task input JSON Schema
        output_schema: Task output JSON Schema
        dependencies: List of dependent task IDs

    Returns:
        Formatted task context string
    """
    lines = [
        "\n## Task to Generate Workflow For\n",
        f"### Task Name: {task_name}",
        f"### Description: {task_description}",
        "",
        "### Input Schema:",
        "```json",
        json.dumps(input_schema, indent=2, ensure_ascii=False),
        "```",
        "",
        "### Output Schema:",
        "```json",
        json.dumps(output_schema, indent=2, ensure_ascii=False),
        "```",
    ]

    if dependencies:
        lines.append("")
        lines.append(f"### Dependencies: {', '.join(dependencies)}")

    lines.extend(
        [
            "",
            "## Instructions",
            "Generate a GraphAI workflow YAML that:",
            "1. Accepts input matching the input schema via the source node",
            "2. Produces output matching the output schema",
            "3. Uses appropriate agents for the task",
            "4. Includes proper error handling (timeouts, console logging)",
            "",
            "Return ONLY the YAML content, no explanations.",
        ]
    )

    return "\n".join(lines)


def _format_api_mappings(api_mappings: list[dict[str, Any]] | None) -> str:
    """Format API mappings for prompt inclusion.

    Issue #342 V2: Provides explicit API endpoint and method info.

    Args:
        api_mappings: List of API mapping dictionaries

    Returns:
        Formatted API mapping section string
    """
    if not api_mappings:
        return ""

    lines = [
        "\n## API Endpoint Mappings (MUST USE EXACTLY)",
        "",
        "Use these EXACT URLs and methods in your inputs block:",
        "",
    ]

    for mapping in api_mappings:
        lines.append(f"### {mapping['api_name']}")
        lines.append(f"- URL: `{mapping['endpoint_url']}`")
        lines.append(f"- Method: `{mapping['http_method']}`")
        lines.append(f"- Agent: `{mapping['agent_type']}`")
        if mapping.get("description"):
            lines.append(f"- Description: {mapping['description']}")
        lines.append("")

    return "\n".join(lines)


def assemble_prompt(
    task_name: str,
    task_description: str,
    input_schema: dict[str, Any],
    output_schema: dict[str, Any],
    recommended_apis: list[str] | None = None,
    dependencies: list[str] | None = None,
    error_feedback: str = "",
    verbose: bool = True,
    api_mappings: list[dict[str, Any]] | None = None,
    api_injector: APISchemaInjector | None = None,
    pattern_library: WorkflowPatternLibrary | None = None,
) -> WorkflowPrompt:
    """Assemble the complete workflow generation prompt.

    Args:
        task_name: Name of the task
        task_description: Task description
        input_schema: Task input JSON Schema
        output_schema: Task output JSON Schema
        recommended_apis: List of recommended API names
        dependencies: List of dependent task IDs
        error_feedback: Previous error feedback (for retries)
        verbose: Use verbose prompts
        api_mappings: Issue #342 V2 - API mapping info from AgentSelector
        api_injector: Issue #342 INT-3 - APISchemaInjector for API spec injection
        pattern_library: Issue #342 INT-4 - WorkflowPatternLibrary for pattern suggestions

    Returns:
        WorkflowPrompt with all components assembled
    """
    # Issue #343: Warn about potential API info duplication
    if recommended_apis and api_mappings:
        warnings.warn(
            "Both recommended_apis and api_mappings provided. "
            "API information may be duplicated in prompt. "
            "Consider using APISchemaInjector only.",
            DeprecationWarning,
            stacklevel=2,
        )

    # Get system prompt
    system = get_system_prompt(verbose=verbose)

    # Assemble rules
    rules_sections = [
        get_base_rules(),
        get_agent_rules(),
        get_reference_rules(),
        get_api_rules(),
    ]
    rules = "\n".join(rules_sections)

    # Get API constraints
    api_constraints = ""
    if recommended_apis:
        api_constraints = format_multiple_api_constraints(recommended_apis)

    # Issue #342 V2: Add API mappings section if provided
    api_mappings_section = _format_api_mappings(api_mappings)
    if api_mappings_section:
        api_constraints = api_constraints + "\n" + api_mappings_section

    # Issue #342 INT-3: Inject API schema specs using APISchemaInjector
    if api_injector is None:
        api_injector = APISchemaInjector()

    if recommended_apis:
        api_constraints = api_injector.inject(api_constraints, recommended_apis)

    # Issue #342 INT-4: Add pattern suggestion using WorkflowPatternLibrary
    if pattern_library is None:
        pattern_library = WorkflowPatternLibrary()

    suggested_pattern_name = pattern_library.suggest_pattern(task_description)
    pattern = pattern_library.get_pattern(suggested_pattern_name)
    if pattern:
        pattern_section = "\n## Recommended Workflow Pattern\n"
        pattern_section += "Based on the task description, consider using the "
        pattern_section += f"'{suggested_pattern_name}' pattern:\n"
        pattern_section += f"- Description: {pattern.get('description', 'N/A')}\n"
        pattern_section += f"- Common nodes: {', '.join(pattern.get('nodes', []))}\n"
        api_constraints = api_constraints + "\n" + pattern_section

    # Select few-shot examples
    examples = select_few_shot_examples(
        recommended_apis=recommended_apis,
        input_schema=input_schema,
        output_schema=output_schema,
        dependencies=dependencies,
    )

    # Build task context
    task_context = build_task_context(
        task_name=task_name,
        task_description=task_description,
        input_schema=input_schema,
        output_schema=output_schema,
        dependencies=dependencies,
    )

    return WorkflowPrompt(
        system=system,
        rules=rules,
        api_constraints=api_constraints,
        examples=examples,
        task_context=task_context,
        error_feedback=error_feedback,
    )
