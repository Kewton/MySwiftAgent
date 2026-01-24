/**
 * TaskFlow Rules - Rules and schema for TaskFlow workflow generation
 *
 * Issue #364: TaskFlow generation rules based on graphAiServer format
 */

/**
 * TaskFlow generation rules for LLM prompt
 */
export const TASKFLOW_RULES = `
# TaskFlow Workflow Generation Rules

## Overview
You are a workflow generator that creates TaskFlow JSON definitions compatible with graphAiServer.
Follow these rules strictly to generate valid workflows.

## Output Format
The workflow must be a valid JSON object with the following structure:

\`\`\`json
{
  "workflow_name": "string (required, snake_case)",
  "description": "string (optional)",
  "input_schema": {
    "field_name": "type_string"
  },
  "output_schema": {
    "field_name": "type_string"
  },
  "steps": [
    {
      "id": "string (required, unique step identifier)",
      "type": "string (required, one of: api_rest, transform, code_js, llm, parallel, action)",
      "description": "string (optional)",
      "config": { ... },
      "params": { ... }
    }
  ],
  "output": {
    "result_key": "\${step_id.field_name}"
  }
}
\`\`\`

**IMPORTANT Output Mapping Syntax:**
- Use \`\${step_id.field_name}\` to reference step outputs (NO ".output" in path)
- Example: \`"\${transform_step.keyword}"\` NOT \`"\${transform_step.output.keyword}"\`

**IMPORTANT Schema Format:**
- \`input_schema\` and \`output_schema\` use SIMPLE type mapping: \`{"field_name": "type"}\`
- Valid types: "string", "number", "boolean", "array", "object"
- Do NOT use JSON Schema format (no "type": "object", "properties", "required")
- Example: \`{"query": "string", "num_results": "number"}\`

## Step Types

### 1. api_rest
REST API call step for external service integration.

**CRITICAL: \`url\` is REQUIRED for api_rest steps. Never use \`capability_id\`.**

Config (REQUIRED fields):
- \`method\`: HTTP method (GET, POST, PUT, DELETE, PATCH) - REQUIRED
- \`url\`: Full API endpoint URL - REQUIRED (e.g., "http://localhost:8004/v1/utility/google_search")
- \`headers\`: Request headers object (default: {"Content-Type": "application/json"})
- \`body\`: Request body for POST/PUT/PATCH - include directly in config
- \`timeout_ms\`: Request timeout in milliseconds (default: 30000)

**Common Capability URLs:**
- google_search: http://localhost:8004/v1/utility/google_search (POST)
- gmail_send: http://localhost:8004/v1/utility/gmail/send (POST)
- json_output_agent: http://localhost:8004/v1/aiagent/utility/jsonoutput (POST)

**API Response Field Names (IMPORTANT for transform mapping):**
- google_search returns: \`search_results\` (array of {title, link, knowledge, original_query})
- gmail_send returns: \`message_id\`, \`status\`
- json_output_agent returns: structured JSON based on system_prompt specification

Example:
\`\`\`json
{
  "id": "search_step",
  "type": "api_rest",
  "config": {
    "method": "POST",
    "url": "http://localhost:8004/v1/utility/google_search",
    "headers": {"Content-Type": "application/json"},
    "body": {"queries": ["\${inputs.query}"], "num": 3},
    "timeout_ms": 30000
  },
  "params": {}
}
\`\`\`

Params:
- Usually empty \`{}\` - put request body in \`config.body\` instead

### 2. transform
Data transformation step using template or mapping.

**IMPORTANT**: Use either \`template\` OR \`mapping\` in config. DO NOT use \`expression\`.

Config (use ONE of the following):
- \`template\`: Handlebars-like template string for transformation. Use \`{{path}}\` for variable interpolation.
  Example: \`"{\\"result\\": \\"{{input.value}}\\"}"\`
- \`mapping\`: Key-value mapping from output fields to input paths using **dot notation**.
  - For input fields: \`"input.field_name"\` (singular "input")
  - For step outputs: \`"steps.step_id.field_name"\` (with "steps." prefix)
  Example: \`{ "keyword": "input.keyword", "results": "steps.search_step.search_results" }\`

**WARNING**: \`expression\` is NOT supported for security reasons. Workflows using \`expression\` will fail validation.

Params:
- Usually empty \`{}\` for transform steps

### 3. code_js
Custom JavaScript code execution in sandboxed environment.

Config:
- \`code\`: JavaScript code string
- \`timeout\`: Execution timeout in milliseconds

Params:
- Input parameters for the code

### 4. llm
LLM (Large Language Model) call step.

Config:
- \`prompt\`: User prompt template with variable interpolation (REQUIRED). Use \`{{path}}\` for variable references.
- \`model\`: Model identifier (optional, e.g., "gpt-4o-mini")
- \`temperature\`: Generation temperature 0.0-2.0 (optional, default: 0.7)
- \`max_tokens\`: Maximum tokens to generate (optional, default: 4096)
- \`system_prompt\`: System prompt for context setting (optional)

Params:
- Input parameters for variable substitution in prompt

### 5. parallel
Parallel execution of multiple sub-steps.

Config:
- \`max_concurrency\`: Maximum concurrent executions
- \`fail_fast\`: Stop on first failure (boolean)

Params:
- \`steps\`: Array of sub-step definitions

### 6. action
Predefined action execution (e.g., sending email, notifications).

Config:
- \`action_type\`: Type of action to execute
- Action-specific configuration

Params:
- Action-specific parameters

## Variable References

**IMPORTANT: Different syntax for different step types!**

### For transform steps (mapping mode):
Use dot notation WITHOUT \`\${}\` brackets:
- \`input.field_name\`: Reference workflow input (singular "input", not "inputs")
- \`steps.step_id.field_name\`: Reference output from previous step (use "steps." prefix)

### For api_rest steps (in config.body):
Use \`\${}\` syntax:
- \`\${inputs.field_name}\`: Reference workflow input
- \`\${step_id.field_name}\`: Reference output from previous step (NO ".output" in path)
  - **IMPORTANT (Issue #396)**: stepResults stores the output object directly, so use \`\${step_id.field}\` NOT \`\${step_id.output.field}\`

### For secrets:
- \`\${secrets.VARIABLE_NAME}\`: Reference secret from MyVault (for API keys etc.)

**CRITICAL Transform Mapping Syntax:**
- For inputs: \`input.query\` (singular, no brackets)
- For step outputs: \`steps.search_step.results\` (with "steps." prefix)

## Best Practices

1. **Step IDs**: Use descriptive, snake_case step IDs (e.g., \`fetch_user_data\`, \`transform_result\`)
2. **Dependencies**: Steps are executed in order; reference only previous steps
3. **Error Handling**: Consider adding error handling for API calls
4. **Validation**: Ensure input/output schemas match actual data
5. **Security**: Never expose sensitive data in workflow definitions

## Common Patterns

### API Call with Transform (using template)
\`\`\`json
{
  "steps": [
    {
      "id": "fetch_data",
      "type": "api_rest",
      "config": { "method": "GET", "url": "https://api.example.com/data/\${inputs.id}" },
      "params": {}
    },
    {
      "id": "transform_response",
      "type": "transform",
      "config": { "template": "{\\"result\\": \\"\${fetch_data.data}\\"}" },
      "params": {}
    }
  ]
}
\`\`\`
**Note (Issue #396)**: Use \`\${fetch_data.data}\` NOT \`\${fetch_data.output.data}\`. The stepResults stores output directly.

### Transform with Mapping
\`\`\`json
{
  "steps": [
    {
      "id": "map_data",
      "type": "transform",
      "config": {
        "mapping": {
          "result": "steps.previous_step.result",
          "count": "steps.previous_step.count"
        }
      },
      "params": {}
    }
  ]
}
\`\`\`

**IMPORTANT**: In transform mapping, use \`steps.step_id.field\` (no .output), NOT \`\${step_id.output.field}\`

### LLM Processing
\`\`\`json
{
  "steps": [
    {
      "id": "generate_summary",
      "type": "llm",
      "config": {
        "prompt": "Summarize the following text: {{input.text}}",
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "system_prompt": "You are a helpful assistant."
      },
      "params": {}
    }
  ]
}
\`\`\`

## Capability vs External API Usage

When making API calls, distinguish between:

### Internal Capability (use capability URL)
For registered capabilities, construct the URL using the capability's endpoint:
\`\`\`json
{
  "id": "search_google",
  "type": "api_rest",
  "config": {
    "method": "POST",
    "url": "http://localhost:8004/v1/utility/google_search",
    "headers": { "Content-Type": "application/json" },
    "body": { "queries": ["\${inputs.search_term}"], "num": 3 },
    "timeout_ms": 30000
  },
  "params": {}
}
\`\`\`
**google_search response**: Returns \`search_results\` array. Use \`steps.search_google.search_results\` in transform mapping.

### External API (use url)
For external APIs with full URLs:
\`\`\`json
{
  "id": "fetch_weather",
  "type": "api_rest",
  "config": {
    "url": "https://api.weather.com/v1/forecast",
    "method": "GET"
  },
  "params": {}
}
\`\`\`

**Important Rules:**
- ALWAYS use \`url\` field for api_rest steps - it is REQUIRED
- NEVER use \`capability_id\` - it is not supported
- For internal capabilities, use their full URL (e.g., http://localhost:8004/v1/utility/google_search)
- For external APIs, use HTTPS URLs
- Put request body in \`config.body\`, not in \`params\`
`;

/**
 * JSON Schema for TaskFlow validation
 * Issue #396: Updated to match graphAiServer expected format (simple type mapping)
 */
export const TASKFLOW_JSON_SCHEMA = {
  $schema: 'http://json-schema.org/draft-07/schema#',
  type: 'object',
  required: ['workflow_name', 'input_schema', 'output_schema', 'steps', 'output'],
  properties: {
    workflow_name: {
      type: 'string',
      pattern: '^[a-z][a-z0-9_]*$',
    },
    description: {
      type: 'string',
    },
    // Issue #396: Simple type mapping format {field: "type"}
    input_schema: {
      type: 'object',
      additionalProperties: {
        type: 'string',
        enum: ['string', 'number', 'boolean', 'array', 'object', 'null'],
      },
    },
    output_schema: {
      type: 'object',
      additionalProperties: {
        type: 'string',
        enum: ['string', 'number', 'boolean', 'array', 'object', 'null'],
      },
    },
    steps: {
      type: 'array',
      items: {
        type: 'object',
        required: ['id', 'type', 'config'],
        properties: {
          id: { type: 'string' },
          type: {
            type: 'string',
            enum: ['api_rest', 'transform', 'code_js', 'llm', 'parallel', 'action'],
          },
          description: { type: 'string' },
          config: { type: 'object' },
          params: { type: 'object' },
        },
      },
    },
    output: {
      type: 'object',
      additionalProperties: { type: 'string' },
    },
  },
};
