"""Prompt assembler for Workflow Generator V2.

This module assembles the final prompt from components.

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

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

        # Add few-shot examples
        if self.examples:
            sections.append("\n## Examples\n")
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

    lines.extend([
        "",
        "## Instructions",
        "Generate a GraphAI workflow YAML that:",
        "1. Accepts input matching the input schema via the source node",
        "2. Produces output matching the output schema",
        "3. Uses appropriate agents for the task",
        "4. Includes proper error handling (timeouts, console logging)",
        "",
        "Return ONLY the YAML content, no explanations.",
    ])

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

    Returns:
        WorkflowPrompt with all components assembled
    """
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
