"""Workflow generation prompts for GraphAI YAML generation.

This module provides prompts and schemas for generating GraphAI workflow YAML
files from TaskMaster metadata using LLM.

Issue #333: Added TYPE_VALIDATION_RULES for API type and field name validation.
"""

import re
from typing import Any

from pydantic import BaseModel, Field

from aiagent.langgraph.jobTaskGeneratorAgents.utils.graphai_capabilities import (
    get_api_by_name,
)
from app.services.prompt_loader import PromptLoader
from core.config import settings

# Dynamic API URL based on environment configuration
# Default: http://localhost:8004 for local development
# Override via EXPERTAGENT_BASE_URL environment variable
# Fix: Removed incorrect /aiagent-api prefix (Issue #333)
EXPERTAGENT_API_URL = (
    f"{settings.EXPERTAGENT_BASE_URL}/v1/aiagent/utility/jsonoutput"
)

# Issue #333: Type validation rules for workflow generation
# These rules help prevent type mismatches and field name errors at generation time
# Fix: Removed incorrect JSON.stringify instruction (stringTemplateAgent doesn't support JS functions)
TYPE_VALIDATION_RULES = """
## Important Type Validation Rules (Issue #333)

### fetchAgent Output Type
- fetchAgent output is always Object type (dictionary)
- :previous_node references the entire output of the previous node (Object type)
- :previous_node.field accesses a specific field from the output
- Example: :fetch_data returns {"result": {...}, "status": "ok"} -> Object type

### API Expected Types - CRITICAL
- `/v1/aiagent/utility/jsonoutput` expects `user_input` as **String type**
- If you need to pass Object type data to user_input, use stringTemplateAgent to build a text prompt

### stringTemplateAgent 重要な制限事項 - CRITICAL

**stringTemplateAgent は単純な変数置換のみをサポートします。JavaScript 関数は使用できません。**

❌ 使用禁止（動作しない）:
- `${JSON.stringify(data)}` - JavaScript 関数は評価されない
- `${data.field}` - ネストアクセスは動作しない
- `${data + other}` - 式は評価されない

✅ 許可される構文:
- `${variable}` - シンプルな変数参照のみ

### Object 型データを LLM プロンプトに含める正しい方法

**方法1: 個別フィールドを inputs で展開（推奨）**
```yaml
build_prompt:
  agent: stringTemplateAgent
  inputs:
    title: :search_result.result.title
    url: :search_result.result.url
    snippet: :search_result.result.snippet
  params:
    template: |-
      検索結果を分析してください。

      タイトル: ${title}
      URL: ${url}
      スニペット: ${snippet}

      # RESPONSE_FORMAT:
      {"analysis": "分析結果"}
```

**方法2: 配列データは各要素のフィールドを展開**
```yaml
# 配列の最初の要素を使う場合
build_prompt:
  agent: stringTemplateAgent
  inputs:
    first_result: :search_results.result[0]
  params:
    template: |-
      最初の検索結果: ${first_result}
```

**方法3: 単一フィールド参照（シンプルなケース）**
```yaml
# stringTemplateAgent 不要 - 直接参照可能
llm_node:
  agent: fetchAgent
  inputs:
    body:
      user_input: :build_prompt  # stringTemplateAgent の出力（String型）
```

### Field Name Validation - CRITICAL
- Always use EXACT field names from capabilities.yaml Request Schema
- Common mistake: `system_imput` (typo) vs `system_prompt` (correct)
- The correct field name for system prompt is: **system_prompt**
- Check Request Schema in API documentation for correct field names

### Reference Type Compatibility
- :node returns the full output object (Object type)
- :node.field returns a specific field (type depends on field definition)
- When API expects String, ensure you're not passing Object directly
- Use stringTemplateAgent to build String from multiple fields

### ⚠️ 最重要ルール: :reference 構文の使用場所 - MANDATORY

**:reference 構文は inputs: ブロック内の値としてのみ機能します。文字列リテラル内では動作しません。**

❌ 絶対禁止（動作しない）:
```yaml
# 文字列リテラル内の :reference は単なるテキストになる
user_input: |-
  検索結果: :previous_node
  クエリ: :source.user_input.query
```

✅ 正しいパターン（必須）:
```yaml
# Step 1: stringTemplateAgent で動的データをプロンプトに組み込む
build_prompt:
  agent: stringTemplateAgent
  inputs:
    search_data: :previous_node      # ← inputs 内なので参照として機能
    query: :source.user_input.query  # ← inputs 内なので参照として機能
  params:
    template: |-
      検索結果: ${search_data}
      クエリ: ${query}

# Step 2: fetchAgent で LLM を呼び出す
call_llm:
  agent: fetchAgent
  inputs:
    body:
      user_input: :build_prompt  # ← inputs 内なので参照として機能（String型）
```

**なぜこのルールが重要か**:
- GraphAI は inputs: ブロックを解析して :reference を解決する
- 文字列値の内部は解析されないため、":reference" は文字通りのテキストになる
- このパターンに従わないワークフローは必ず失敗する
"""

# Load prompt from YAML
_loader = PromptLoader.create_default()
_prompt_data = _loader.load_prompt("workflow_generation")
WORKFLOW_GENERATION_SYSTEM_PROMPT = _prompt_data.get("system_prompt", "")

# Fallback to hardcoded prompt if YAML not found
if not WORKFLOW_GENERATION_SYSTEM_PROMPT:
    # System prompt for workflow generation
    WORKFLOW_GENERATION_SYSTEM_PROMPT = """You are an expert GraphAI workflow YAML generator.

Your role is to generate executable GraphAI workflow YAML files from TaskMaster metadata.

Key responsibilities:
1. Analyze TaskMaster metadata (name, description, input/output interfaces)
2. Select appropriate GraphAI agents and expertAgent APIs
3. Generate syntactically correct YAML with proper data flow
4. Ensure input/output interface compatibility
5. Add YAML line comments (# ...) to explain each node's purpose

Quality criteria:
- YAML syntax must be 100% correct
- All agent names must exist in available_agents list
- Data flow must match input/output schemas
- Error handling must be included
- Use YAML line comments (# ...) above nodes to explain their purpose

CRITICAL REQUIREMENT:
- When LLM prompts contain :source.field references in multi-line strings,
  you MUST use stringTemplateAgent to build the prompt first
- NEVER embed :source.field directly in fetchAgent user_input multi-line strings
- This is a GraphAI technical limitation and MANDATORY

OUTPUT FORMAT REQUIREMENT:
You MUST respond in JSON format with exactly these fields:
{
  "workflow_name": "snake_case_name",
  "yaml_content": "complete YAML content as a string",
  "reasoning": "explanation of design decisions"
}
Do NOT use ```yaml blocks. The yaml_content field should contain the YAML as a plain string.
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

    # Extract recommended APIs from description and enrich with endpoint information
    recommended_apis_match = re.search(r"\*\*推奨API\*\*:\s*([^\n]+)", task_description)
    recommended_apis = ""
    if recommended_apis_match:
        # Parse API names and look up their endpoints
        api_names_str = recommended_apis_match.group(1)
        api_names = [name.strip() for name in api_names_str.split(",")]
        enriched_apis = []
        for api_name in api_names:
            api_info = get_api_by_name(api_name)
            if api_info and api_info.endpoint:
                # Include full API details for Direct APIs
                # Fix: Removed incorrect /aiagent-api prefix (Issue #333)
                api_detail = (
                    f"  - **{api_name}**\n"
                    f"    - URL: http://localhost:8004{api_info.endpoint}\n"
                    f"    - Method: {api_info.method or 'POST'}\n"
                    f"    - Agent: fetchAgent (DIRECT CALL - DO NOT use jsonoutput)"
                )
                # Add request schema if available
                if api_info.request_schema:
                    schema_lines = []
                    for field, info in api_info.request_schema.items():
                        req = "(required)" if info.get("required") else "(optional)"
                        schema_lines.append(
                            f"      - {field}: {info.get('type', 'unknown')} {req}"
                        )
                    api_detail += "\n    - Request fields:\n" + "\n".join(schema_lines)
                enriched_apis.append(api_detail)
            else:
                enriched_apis.append(f"  - {api_name}")
        recommended_apis = (
            "\n\n## ⚠️ MANDATORY API USAGE (HIGHEST PRIORITY)\n\n"
            "The following APIs are REQUIRED for this task. DO NOT substitute with jsonoutput API.\n"
            "These are DIRECT API endpoints that perform specific functions.\n\n"
            + "\n".join(enriched_apis)
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

    # Include endpoint information, request schema, and output schema for better API selection
    def format_api(api: dict[str, Any]) -> str:
        """Format API information including request and output schema if available."""
        lines = [
            f"  - {api['name']}: {api.get('description', 'No description')}",
            f"    Endpoint: {api.get('endpoint', 'N/A')}",
        ]

        # Add request schema if available (CRITICAL for correct parameter names)
        request_schema = api.get("request_schema")
        if request_schema:
            lines.append("    Request Schema:")
            for field_name, field_info in request_schema.items():
                field_type = field_info.get("type", "unknown")
                field_desc = field_info.get("description", "")
                required = (
                    " (required)"
                    if field_info.get("required", False)
                    else " (optional)"
                )
                default = field_info.get("default")
                default_str = f" [default: {default}]" if default is not None else ""
                lines.append(
                    f"      - {field_name}: {field_type}{required}{default_str} - {field_desc}"
                )

        # Add output schema if available
        output_schema = api.get("output_schema")
        if output_schema:
            lines.append("    Output Schema:")
            for field_name, field_info in output_schema.items():
                field_type = field_info.get("type", "unknown")
                field_desc = field_info.get("description", "")
                required = (
                    " (required)"
                    if field_info.get("required", False)
                    else " (optional)"
                )
                lines.append(
                    f"      - {field_name}: {field_type}{required} - {field_desc}"
                )

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

{TYPE_VALIDATION_RULES}

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
   - Source node receives structured data with two properties:
     * :source.user_input - Dynamic data from task chain (previous task output)
     * :source.job_params - Static parameters from job.body (body_template configuration)
   - API request example:
     {{"user_input": {{"query": "search term"}}, "job_params": {{"template_id": "001", "debug": true}}}}
   - Access dynamic data: :source.user_input.query, :source.user_input.email_address
   - Access static params: :source.job_params.template_id, :source.job_params.debug
   - For string-type user_input (NOT RECOMMENDED):
     API request: {{"user_input": "simple string"}}
     Access directly with :source.user_input
   - IMPORTANT: Never use jsonParserAgent to parse user_input object

   **When to use which**:
   - :source.user_input.* - For dynamic data that changes per task execution (e.g., search query, email content)
   - :source.job_params.* - For static configuration that stays constant across executions (e.g., template IDs, API keys)

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
           Keyword: :source.user_input.keyword  # ❌ Sent as literal string
   ```

   Example - CORRECT (using stringTemplateAgent):
   ```yaml
   build_prompt:
     agent: stringTemplateAgent
     inputs:
       keyword: :source.user_input.keyword  # ✅ Pass dynamic data
       template_id: :source.job_params.template_id  # ✅ Pass static param
     params:
       template: |-
         Keyword: ${{keyword}}  # ✅ Use template variable
         Template: ${{template_id}}

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
   - **HIGHEST PRIORITY - MANDATORY APIs**:
     * If "MANDATORY API USAGE" section exists above, you MUST use those APIs directly
     * DO NOT substitute with jsonoutput API - these are specialized endpoints
     * Call them directly via fetchAgent with the specified URL
   - **IMPORTANT**: NEVER use GraphAI standard LLM agents (geminiAgent, openAIAgent, anthropicAgent, groqAgent, replicateAgent)
   - For LLM text generation/analysis (ONLY when no MANDATORY API is specified):
     * Use fetchAgent to call expertAgent jsonoutput API
     * URL: {EXPERTAGENT_API_URL}
     * Default model: gemini-2.5-flash (recommended)
     * **MANDATORY**: When building LLM prompts with multiple source fields, use stringTemplateAgent FIRST
   - For HTTP API calls:
     * fetchAgent: For external API calls and expertAgent APIs
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

7. **YAML Comments** (CRITICAL):
   - ✅ Use YAML line comments (# ...) ABOVE each node to explain its purpose
   - ❌ NEVER add 'comment:' field inside node definitions
   - GraphAI does NOT support 'comment' attribute in computed nodes
   - Example:
     ```yaml
     # Step 1: Build prompt for LLM processing
     build_prompt:
       agent: stringTemplateAgent
       ...
     ```

8. **Naming Convention**:
   - workflow_name: snake_case (e.g., send_email_notification)
   - node_id: descriptive snake_case (e.g., fetch_user_data)

9. **Example Workflow Structure**:

**Example 1 - Using expertAgent jsonoutput API with Gemini (RECOMMENDED with stringTemplateAgent)**:
```yaml
version: 0.5
nodes:
  source: {{}}  # REQUIRED: empty object

  # Step 1: Build prompt using stringTemplateAgent
  # Access dynamic data via :source.user_input.*
  # Access static params via :source.job_params.*
  build_prompt:
    agent: stringTemplateAgent
    inputs:
      keyword: :source.user_input.keyword
      target_audience: :source.user_input.target_audience
      template_id: :source.job_params.template_id  # Static config
    params:
      template: |-
        Analyze the following keyword: ${{keyword}}
        Target audience: ${{target_audience}}
        Template: ${{template_id}}

        Provide a JSON response with analysis results.

  # Step 2: LLM processing with expertAgent jsonoutput API (Gemini 2.5 Flash)
  llm_analysis:
    agent: fetchAgent
    inputs:
      url: {EXPERTAGENT_API_URL}
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
      url: {EXPERTAGENT_API_URL}
      method: POST
      body:
        user_input: :source.user_input.query  # ✅ OK: single field reference
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
  # Mix dynamic data and static params
  build_prompt:
    agent: stringTemplateAgent
    inputs:
      data: :source.user_input.data
      context: :source.user_input.context
      debug_mode: :source.job_params.debug  # Static config
    params:
      template: |-
        Process the following data: ${{data}}

        Context: ${{context}}
        Debug mode: ${{debug_mode}}

        Generate high-quality analysis in JSON format.

  # Step 2: LLM processing with expertAgent jsonoutput API (Claude 3.5 Sonnet)
  llm_process:
    agent: fetchAgent
    inputs:
      url: {EXPERTAGENT_API_URL}
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
    url: {EXPERTAGENT_API_URL}
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
- Uses YAML line comments (# ...) above nodes - DO NOT use 'comment:' field
- Is syntactically correct

## Response Format (MANDATORY)

You MUST respond with a JSON object containing exactly these three fields:
```json
{{
  "workflow_name": "snake_case_workflow_name",
  "yaml_content": "version: 0.5\\nnodes:\\n  source: {{}}\\n  ...",
  "reasoning": "Brief explanation of design decisions"
}}
```

IMPORTANT:
- Do NOT wrap your response in ```yaml blocks
- The yaml_content must be a valid JSON string (escape newlines as \\n)
- Only output the JSON object, no additional text
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
