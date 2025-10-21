"""Workflow generation prompts for GraphAI YAML generation.

This module provides prompts and schemas for generating GraphAI workflow YAML
files from TaskMaster metadata using LLM.
"""

from typing import Any

from pydantic import BaseModel, Field

# System prompt for workflow generation
WORKFLOW_GENERATION_SYSTEM_PROMPT = """You are an expert GraphAI workflow YAML generator.

Your role is to generate executable GraphAI workflow YAML files from TaskMaster metadata.

Key responsibilities:
1. Analyze TaskMaster metadata (name, description, input/output interfaces)
2. Select appropriate GraphAI agents and expertAgent APIs
3. Generate syntactically correct YAML with proper data flow
4. Ensure input/output interface compatibility
5. Add clear comments and documentation

Quality criteria:
- YAML syntax must be 100% correct
- All agent names must exist in available_agents list
- Data flow must match input/output schemas
- Error handling must be included
- Comments must explain each node's purpose
"""


class WorkflowGenerationResponse(BaseModel):
    """Response schema for workflow generation."""

    workflow_name: str = Field(
        description="Workflow name in snake_case (e.g., send_email_notification)"
    )
    yaml_content: str = Field(
        description="Complete GraphAI workflow YAML content with proper indentation"
    )
    reasoning: str = Field(
        description="Explanation of design decisions and agent choices"
    )


def create_workflow_generation_prompt(
    task_data: dict[str, Any],
    graphai_capabilities: dict[str, Any],
    expert_agent_capabilities: dict[str, Any],
) -> str:
    """Create workflow generation prompt from task metadata and capabilities.

    Args:
        task_data: TaskMaster metadata with interfaces
        graphai_capabilities: Available GraphAI agents and their descriptions
        expert_agent_capabilities: Available expertAgent APIs

    Returns:
        Formatted prompt string
    """
    task_name = task_data.get("name", "Unknown Task")
    task_description = task_data.get("description", "No description")
    input_interface = task_data.get("input_interface", {})
    output_interface = task_data.get("output_interface", {})

    # Extract interface schemas
    input_schema = input_interface.get("schema", {})
    output_schema = output_interface.get("schema", {})

    # Format available agents
    graphai_agents = graphai_capabilities.get("agents", [])
    agent_list = "\n".join(
        f"  - {agent['name']}: {agent.get('description', 'No description')}"
        for agent in graphai_agents
    )

    # Format available APIs
    expert_apis = expert_agent_capabilities.get("apis", [])
    api_list = "\n".join(
        f"  - {api['name']}: {api.get('description', 'No description')}"
        for api in expert_apis
    )

    prompt = f"""Generate a GraphAI workflow YAML file for the following task:

## Task Metadata

**Task Name**: {task_name}
**Description**: {task_description}

**Input Interface**:
```json
{input_schema}
```

**Output Interface**:
```json
{output_schema}
```

## Available GraphAI Agents

{agent_list}

## Available ExpertAgent APIs

{api_list}

## YAML Generation Rules

1. **Basic Structure**:
   - version: 0.5
   - nodes: Dictionary of node definitions
   - At least one node with isResult: true

2. **Required Nodes**:
   - source: Entry point (receives user_input as object)
   - output: Final result node with isResult: true

3. **Input Schema Usage**:
   - Use :source.property_name to access input properties
   - Example: :source.email_address, :source.query

4. **Data Flow**:
   - Use :node_id to reference previous node output
   - Use :node_id.property for nested properties
   - Ensure output matches output_interface schema

5. **Agent Selection**:
   - Prefer fetchAgent for HTTP API calls
   - Use LLM agents (geminiAgent, openAIAgent) for text processing
   - Use copyAgent for final output formatting

6. **Error Handling**:
   - Always validate required inputs
   - Add comments for each node's purpose

7. **Naming Convention**:
   - workflow_name: snake_case (e.g., send_email_notification)
   - node_id: descriptive snake_case (e.g., fetch_user_data)

## Output Requirements

Generate a complete, executable GraphAI workflow YAML that:
- Accepts inputs matching the input_interface schema
- Produces outputs matching the output_interface schema
- Uses only available agents
- Includes clear comments
- Is syntactically correct

Provide your response in the structured format with workflow_name, yaml_content, and reasoning.
"""

    return prompt


def create_workflow_generation_prompt_with_feedback(
    task_data: dict[str, Any],
    graphai_capabilities: dict[str, Any],
    expert_agent_capabilities: dict[str, Any],
    error_feedback: str,
) -> str:
    """Create workflow generation prompt with error feedback for self-repair.

    Args:
        task_data: TaskMaster metadata with interfaces
        graphai_capabilities: Available GraphAI agents
        expert_agent_capabilities: Available expertAgent APIs
        error_feedback: Error messages and validation failures

    Returns:
        Formatted prompt string with error feedback
    """
    base_prompt = create_workflow_generation_prompt(
        task_data, graphai_capabilities, expert_agent_capabilities
    )

    feedback_section = f"""

## Previous Generation Errors

The previously generated workflow had the following errors:

```
{error_feedback}
```

## Required Fixes

Please regenerate the workflow addressing ALL of the above errors:
1. Fix YAML syntax errors if any
2. Correct agent names (use only available agents)
3. Fix data flow issues (ensure :references are correct)
4. Validate input/output schema compatibility
5. Add missing error handling

Generate a corrected version of the workflow.
"""

    return base_prompt + feedback_section
