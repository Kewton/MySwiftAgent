"""Workflow generation prompts for GraphAI YAML generation.

This module provides prompts and schemas for generating GraphAI workflow YAML
files from TaskMaster metadata using LLM.
"""

import re
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

CRITICAL REQUIREMENT:
- When LLM prompts contain :source.field references in multi-line strings,
  you MUST use stringTemplateAgent to build the prompt first
- NEVER embed :source.field directly in fetchAgent user_input multi-line strings
- This is a GraphAI technical limitation and MANDATORY
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

    # Extract recommended APIs from description
    recommended_apis_match = re.search(r"\*\*推奨API\*\*:\s*([^\n]+)", task_description)
    recommended_apis = ""
    if recommended_apis_match:
        recommended_apis = (
            f"\n\n**Recommended APIs (PRIORITY)**: {recommended_apis_match.group(1)}"
        )

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
    # Extract both utility_apis and ai_agent_apis from capabilities
    utility_apis = expert_agent_capabilities.get("utility_apis", [])
    ai_agent_apis = expert_agent_capabilities.get("ai_agent_apis", [])
    expert_apis = utility_apis + ai_agent_apis

    # Include endpoint information and output schema for better API selection
    def format_api(api: dict[str, Any]) -> str:
        """Format API information including output schema if available."""
        lines = [
            f"  - {api['name']}: {api.get('description', 'No description')}",
            f"    Endpoint: {api.get('endpoint', 'N/A')}",
        ]

        # Add output schema if available
        output_schema = api.get("output_schema")
        if output_schema:
            lines.append("    Output Schema:")
            for field_name, field_info in output_schema.items():
                field_type = field_info.get("type", "unknown")
                field_desc = field_info.get("description", "")
                required = " (required)" if field_info.get("required", False) else " (optional)"
                lines.append(f"      - {field_name}: {field_type}{required} - {field_desc}")

        return "\n".join(lines)

    api_list = "\n".join(format_api(api) for api in expert_apis)

    prompt = f"""Generate a GraphAI workflow YAML file for the following task:

## Task Metadata

**Task Name**: {task_name}
**Description**: {task_description}{recommended_apis}

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
   - source: {{}} - MUST be empty object; receives user_input from API request
   - output: Final result node with isResult: true

3. **sourceNode and user_input Reference** (CRITICAL):
   - ALWAYS define source node as: source: {{}}
   - user_input from API request is injected into source node as-is
   - For object-type user_input (RECOMMENDED):
     API request: {{"user_input": {{"test": "value1", "test2": "value2"}}}}
     Access properties with :source.property_name
     Example: :source.test, :source.test2, :source.email_address, :source.query
   - For string-type user_input (NOT RECOMMENDED):
     API request: {{"user_input": "simple string"}}
     Access directly with :source
   - IMPORTANT: Never use jsonParserAgent to parse user_input object

   **Variable Reference in Multi-line Strings** (CRITICAL):
   - When using :source.property in multi-line user_input for LLM prompts,
     the reference will NOT be substituted automatically
   - MUST use stringTemplateAgent to build the prompt first
   - stringTemplateAgent syntax:
     * inputs: Pass specific fields (e.g., keyword: :source.keyword)
     * params.template: Use ${{variable}} syntax (e.g., ${{keyword}})
     * DO NOT use nested access in template (e.g., ${{data.keyword}} does NOT work)

   Example - WRONG (variable not substituted):
   ```yaml
   llm_node:
     agent: fetchAgent
     inputs:
       body:
         user_input: |
           Keyword: :source.keyword  # ❌ Sent as literal string
   ```

   Example - CORRECT (using stringTemplateAgent):
   ```yaml
   build_prompt:
     agent: stringTemplateAgent
     inputs:
       keyword: :source.keyword  # ✅ Pass specific field
     params:
       template: |-
         Keyword: ${{keyword}}  # ✅ Use template variable

   llm_node:
     agent: fetchAgent
     inputs:
       body:
         user_input: :build_prompt  # ✅ Use constructed prompt
   ```

4. **Data Flow**:
   - Use :node_id to reference previous node output
   - Use :node_id.property for nested properties
   - **CRITICAL**: When referencing API response fields, use EXACT field names from Output Schema
     * If API has "web_view_link" in Output Schema, use :node.web_view_link (NOT :node.public_url)
     * If API has "file_id" in Output Schema, use :node.file_id (NOT :node.drive_file_id)
     * Check "Output Schema" in API list for correct field names
   - Ensure output matches output_interface schema

5. **Agent Selection** (CRITICAL):
   - **PRIORITY**: If "Recommended APIs" are specified in task description, use them first
   - **IMPORTANT**: NEVER use GraphAI standard LLM agents (geminiAgent, openAIAgent, anthropicAgent, groqAgent, replicateAgent)
   - For LLM processing:
     * ALWAYS use fetchAgent to call expertAgent jsonoutput API
     * URL: http://localhost:8104/aiagent-api/v1/aiagent/utility/jsonoutput
     * Default model: gemini-2.5-flash (recommended)
     * Fallback model: gpt-4o-mini
     * High-quality model: claude-3-5-sonnet
     * **MANDATORY**: When building LLM prompts with multiple source fields, use stringTemplateAgent FIRST
   - For HTTP API calls:
     * fetchAgent: For external API calls and expertAgent jsonoutput API
     * **CRITICAL fetchAgent structure**: url, method, and body MUST be in inputs (NOT params)
     * expertAgent APIs: Use Direct API endpoints (e.g., /api/v1/search)
   - For data formatting:
     * copyAgent: For final output formatting and data transformation
     * stringTemplateAgent: **MANDATORY** for building prompts with :source.field references

   **CRITICAL RULE - fetchAgent Structure**:
   - ❌ WRONG: url/method in params
   - ✅ CORRECT: url/method/body in inputs

   **CRITICAL RULE - Multi-line LLM Prompts**:
   - ❌ NEVER embed :source.field directly in multi-line user_input strings
   - ✅ ALWAYS use stringTemplateAgent to build prompts with variables
   - This is a GraphAI limitation, not optional

   **CRITICAL RULE - Project Field in expertAgent API Calls**:
   - ❌ DO NOT specify "project" field in body unless explicitly instructed by user
   - ✅ When project is omitted, expertAgent uses default project from environment (.env file)
   - ✅ Only add "project: <name>" if user explicitly specifies a project name in task description
   - Rationale: Hardcoding project names causes myVault secret retrieval failures

6. **Error Handling**:
   - Always validate required inputs
   - Add comments for each node's purpose

7. **Naming Convention**:
   - workflow_name: snake_case (e.g., send_email_notification)
   - node_id: descriptive snake_case (e.g., fetch_user_data)

8. **Example Workflow Structure**:

**Example 1 - Using expertAgent jsonoutput API with Gemini (RECOMMENDED with stringTemplateAgent)**:
```yaml
version: 0.5
nodes:
  source: {{}}  # REQUIRED: empty object

  # Step 1: Build prompt using stringTemplateAgent
  build_prompt:
    agent: stringTemplateAgent
    inputs:
      keyword: :source.keyword
      target_audience: :source.target_audience
    params:
      template: |-
        Analyze the following keyword: ${{keyword}}
        Target audience: ${{target_audience}}

        Provide a JSON response with analysis results.

  # Step 2: LLM processing with expertAgent jsonoutput API (Gemini 2.5 Flash)
  llm_analysis:
    agent: fetchAgent
    inputs:
      url: http://localhost:8104/aiagent-api/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :build_prompt
        model_name: gemini-2.5-flash
    timeout: 30000

  # Step 3: Extract result from expertAgent response
  extract_analysis:
    agent: copyAgent
    params:
      namedKey: analysis
    inputs:
      analysis: :llm_analysis.result
    timeout: 5000

  # Step 4: Final output
  output:
    agent: copyAgent
    params:
      namedKey: result
    inputs:
      result: :extract_analysis.analysis
    isResult: true
```

**Example 2 - Simple case without stringTemplateAgent (when user_input is single field)**:
```yaml
version: 0.5
nodes:
  source: {{}}

  # LLM processing (simple case: pass single field directly)
  llm:
    agent: fetchAgent
    inputs:
      url: http://localhost:8104/aiagent-api/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :source.query  # ✅ OK: single field reference
        model_name: gpt-4o-mini
    timeout: 30000

  # Final output
  output:
    agent: copyAgent
    params:
      namedKey: text
    inputs:
      text: :llm.result
    isResult: true
```

**Example 3 - Complex prompt with stringTemplateAgent and Claude (High-quality)**:
```yaml
version: 0.5
nodes:
  source: {{}}

  # Step 1: Build complex prompt with multiple variables
  build_prompt:
    agent: stringTemplateAgent
    inputs:
      data: :source.data
      context: :source.context
    params:
      template: |-
        Process the following data: ${{data}}

        Context: ${{context}}

        Generate high-quality analysis in JSON format.

  # Step 2: LLM processing with expertAgent jsonoutput API (Claude 3.5 Sonnet)
  llm_process:
    agent: fetchAgent
    inputs:
      url: http://localhost:8104/aiagent-api/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :build_prompt
        model_name: claude-3-5-sonnet
    timeout: 30000

  # Step 3: Final output
  output:
    agent: copyAgent
    params:
      namedKey: result
    inputs:
      result: :llm_process.result
    isResult: true
```

## Best Practices from Tutorial Patterns

**CRITICAL RULE - Node Simplification** (MANDATORY):
- ❌ DO NOT create "extract_*" nodes for simple field extraction from LLM results
- ❌ DO NOT create "format_*" nodes that only copy data without transformation
- ❌ DO NOT create "validate_*" nodes that only copy data without actual validation
- ✅ Use direct reference pattern in output node: `:node.result.field`
- ✅ Keep node count to minimum (3-4 nodes for most workflows)

**Recommended Node Structure**:
1. source: {{}} - Input node (REQUIRED)
2. build_prompt: stringTemplateAgent - Prompt construction
3. generate_content: fetchAgent - LLM call via expertAgent jsonoutput API
4. output: copyAgent with direct references - Final output (REQUIRED with isResult: true)

**Examples of GOOD direct reference patterns**:
```yaml
# ✅ GOOD: Direct reference in output node
output:
  agent: copyAgent
  inputs:
    result:
      success: true
      field1: :generate_content.result.field1
      field2: :generate_content.result.field2
      error_message: ""
  isResult: true
```

**Examples of BAD unnecessary extraction**:
```yaml
# ❌ BAD: Unnecessary extract node
extract_result:
  agent: copyAgent
  params:
    namedKey: extracted
  inputs:
    extracted: :generate_content.result.field1

output:
  inputs:
    result: :extract_result.extracted
  isResult: true
```

**CRITICAL RULE - Prompt Template Format** (MANDATORY):
- ✅ ALWAYS use Japanese prompts when output is expected in Japanese
- ✅ ALWAYS include RESPONSE_FORMAT section explicitly
- ❌ DO NOT use English prompts unless explicitly required by task
- ✅ Include clear constraints section
- ✅ Specify "返却は JSON 形式で行い、コメントやマークダウンは含めないこと"

**Standard Prompt Template Structure** (tutorialパターン):
```yaml
build_prompt:
  agent: stringTemplateAgent
  inputs:
    variable1: :source.variable1
    variable2: :source.variable2
  params:
    template: |-
      あなたは[role description]です。
      以下の情報を基に、[task description]を実行してください。

      [Input variables]: ${{variable1}}
      [Additional info]: ${{variable2}}

      # 制約条件
      - [constraint 1]
      - [constraint 2]
      - 日本語で出力すること
      - 出力は RESPONSE_FORMAT に従うこと。返却は JSON 形式で行い、コメントやマークダウンは含めないこと

      # RESPONSE_FORMAT:
      {{
        "field1": "description1",
        "field2": "description2"
      }}
```

**CRITICAL RULE - Mock Approach for Non-LLM Tasks** (MANDATORY):
- ❌ DO NOT attempt TTS audio generation via LLM
- ❌ DO NOT attempt file upload/download via LLM
- ❌ DO NOT attempt email sending via LLM
- ❌ DO NOT attempt cloud storage operations via LLM
- ✅ Use LLM to generate MOCK RESULTS for these tasks
- ✅ Include implementation notes for future API integration

**Non-LLM Task Pattern Examples**:
```yaml
# Example 1: Mock TTS audio generation
build_tts_prompt:
  agent: stringTemplateAgent
  inputs:
    script: :source.script
  params:
    template: |-
      あなたは音声ファイル生成結果を模擬するシステムです。
      以下の台本を基に、TTS音声生成の結果を模擬的に生成してください。

      台本: ${{script}}

      # 制約条件
      - 実際のTTS音声生成は行わないこと（モックデータを返す）
      - 音声データはダミーのBase64文字列とすること
      - ファイル名は現在日時を含む形式にすること

      # RESPONSE_FORMAT:
      {{
        "success": true,
        "audio_data_base64": "ダミー音声データ（Base64）",
        "file_name": "audio_YYYYMMDD_HHMMSS.mp3",
        "duration_seconds": 180
      }}

# Example 2: Mock file upload
build_upload_prompt:
  agent: stringTemplateAgent
  inputs:
    file_name: :source.file_name
  params:
    template: |-
      あなたはファイルアップロード処理を模擬するシステムです。
      以下の情報を基に、ファイルアップロード結果を生成してください。

      ファイル名: ${{file_name}}

      # 制約条件
      - 実際のファイルアップロードは行わないこと（モックデータを返す）
      - ストレージパスは架空のGCS/S3パスにすること

      # RESPONSE_FORMAT:
      {{
        "success": true,
        "storage_path": "gs://bucket/path/file.ext",
        "file_size_bytes": 1048576
      }}
```

**CRITICAL RULE - Timeout Settings** (MANDATORY):
- ✅ fetchAgent (LLM calls): 60000ms (60 seconds) - ALWAYS use 60 seconds
- ✅ stringTemplateAgent: No timeout needed (fast operation)
- ✅ copyAgent: No timeout needed (fast operation)
- ❌ DO NOT use 30000ms for LLM calls (too short, causes frequent timeouts)

**Example with correct timeout**:
```yaml
generate_content:
  agent: fetchAgent
  inputs:
    url: http://localhost:8104/aiagent-api/v1/aiagent/utility/jsonoutput
    method: POST
    body:
      user_input: :build_prompt
      model_name: gemini-2.5-flash
  timeout: 60000  # ✅ MANDATORY: 60 seconds for all LLM calls
```

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
