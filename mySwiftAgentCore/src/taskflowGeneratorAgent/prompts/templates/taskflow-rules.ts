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
    "type": "object",
    "properties": { ... },
    "required": [ ... ]
  },
  "output_schema": {
    "type": "object",
    "properties": { ... }
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
    "result_key": "$steps.step_id.output_key"
  }
}
\`\`\`

## Step Types

### 1. api_rest
REST API call step for external service integration.

Config:
- \`method\`: HTTP method (GET, POST, PUT, DELETE, PATCH)
- \`url\`: API endpoint URL (can use variables)
- \`headers\`: Request headers object
- \`timeout\`: Request timeout in milliseconds

Params:
- \`body\`: Request body (for POST/PUT/PATCH)
- Any dynamic values using variable references

### 2. transform
Data transformation step using template or mapping.

**IMPORTANT**: Use either \`template\` OR \`mapping\` in config. DO NOT use \`expression\`.

Config (use ONE of the following):
- \`template\`: Handlebars-like template string for transformation. Use \`{{path}}\` for variable interpolation.
  Example: \`"{\\"result\\": \\"{{input.value}}\\"}"\`
- \`mapping\`: Key-value mapping from output fields to input paths using JSONPath expressions.
  Example: \`{ "output_field": "$.input.value" }\`

**WARNING**: \`expression\` is NOT supported for security reasons. Workflows using \`expression\` will fail validation.

Params:
- Input data references using \`$input\` or \`$steps\`

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

Use the following patterns for variable references:

- \`$input.field_name\`: Reference workflow input
- \`$steps.step_id.field_name\`: Reference output from previous step
- \`$env.VARIABLE_NAME\`: Reference environment variable (use sparingly)

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
      "config": { "method": "GET", "url": "https://api.example.com/data/$input.id" },
      "params": {}
    },
    {
      "id": "transform_response",
      "type": "transform",
      "config": { "template": "{\\"result\\": \\"{{steps.fetch_data.data}}\\"}" },
      "params": {}
    }
  ]
}
\`\`\`

### Transform with Mapping
\`\`\`json
{
  "steps": [
    {
      "id": "map_data",
      "type": "transform",
      "config": {
        "mapping": {
          "result": "$.steps.previous_step.output",
          "count": "$.steps.previous_step.count"
        }
      },
      "params": {}
    }
  ]
}
\`\`\`

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

### Internal Capability (use capability_id)
For registered capabilities, use \`capability_id\` instead of \`url\`:
\`\`\`json
{
  "id": "search_google",
  "type": "api_rest",
  "config": {
    "capability_id": "google_search",
    "method": "POST"
  },
  "params": {
    "body": { "query": "$input.search_term" }
  }
}
\`\`\`

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
- Use \`capability_id\` when referencing a registered capability
- Use \`url\` only for external APIs with full URLs
- Never use both \`capability_id\` and \`url\` in the same step
- Prefer \`capability_id\` when the capability is available
`;

/**
 * JSON Schema for TaskFlow validation
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
    input_schema: {
      type: 'object',
      required: ['type'],
      properties: {
        type: { type: 'string' },
        properties: { type: 'object' },
        required: { type: 'array', items: { type: 'string' } },
      },
    },
    output_schema: {
      type: 'object',
      required: ['type'],
      properties: {
        type: { type: 'string' },
        properties: { type: 'object' },
        required: { type: 'array', items: { type: 'string' } },
      },
    },
    steps: {
      type: 'array',
      items: {
        type: 'object',
        required: ['id', 'type', 'config', 'params'],
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
