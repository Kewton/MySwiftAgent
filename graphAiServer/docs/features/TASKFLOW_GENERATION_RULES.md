# TaskFlow V2 Workflow Generation Rules

This document provides comprehensive rules for LLMs to generate valid TaskFlow V2 workflow definitions.

**Issue**: #350
**Version**: 2.0 (OpenAI Structured Output Compatible)

---

## Overview

TaskFlow V2 is a modular task execution engine that supports:
- Sequential execution of workflow steps
- REST API calls with SSRF protection
- Data transformation using template strings
- JavaScript code execution in a secure sandbox

### OpenAI Structured Output Compatibility

TaskFlow V2 schemas are designed to be compatible with OpenAI's Structured Output feature.

**Key Constraints:**
- No `oneOf`/`Union` types (use unified config model)
- No dynamic dict types (use JSON strings)
- All fields must be in `required` array with `additionalProperties: false`

---

## JSON Structure Rules

### Required Fields

Every workflow definition MUST include:

```json
{
  "workflow_name": "required_string",
  "description": "optional_string",
  "input_schema": "{\"field\": \"type\"}",
  "output_schema": "{\"field\": \"type\"}",
  "steps": [...],
  "output": "{\"field\": \"${reference}\"}"
}
```

### Field Constraints

| Field | Type | Format | Constraints |
|-------|------|--------|-------------|
| `workflow_name` | string | - | Pattern: `^[a-zA-Z_][a-zA-Z0-9_-]*$` |
| `description` | string | - | Optional |
| `input_schema` | string | JSON | Must be valid JSON object string |
| `output_schema` | string | JSON | Must be valid JSON object string |
| `steps` | array | - | At least 1 step required |
| `output` | string | JSON | Must be valid JSON object string |

### Schema Fields as JSON Strings

**CRITICAL**: `input_schema`, `output_schema`, and `output` must be **JSON strings**, not objects.

```json
// CORRECT - JSON strings
{
  "input_schema": "{\"user_id\": \"string\", \"query\": \"string\"}",
  "output_schema": "{\"result\": \"string\"}",
  "output": "{\"result\": \"${format_output.output}\"}"
}

// WRONG - Objects (not compatible with OpenAI Structured Output)
{
  "input_schema": {"user_id": "string"},
  "output_schema": {"result": "string"},
  "output": {"result": "${format_output.output}"}
}
```

### Simple Types

Use these types in schema definitions:
- `string` - Text values
- `number` - Numeric values (integer or float)
- `boolean` - true/false
- `array` - List of values
- `object` - Key-value pairs
- `null` - Null value

---

## Step Types

### Unified Step Config

All step types use a unified config model with `step_type` discriminator:

```json
{
  "id": "step_id",
  "type": "api_rest|transform|code_js",
  "config": {
    "step_type": "api_rest|transform|code_js",
    // type-specific fields...
  },
  "params": {}
}
```

**IMPORTANT**: `config.step_type` MUST match `type`.

---

### 1. api_rest - HTTP Requests

Use for external API calls.

```json
{
  "id": "fetch_user",
  "type": "api_rest",
  "config": {
    "step_type": "api_rest",
    "method": "POST",
    "url": "https://api.example.com/users",
    "headers": {
      "Content-Type": "application/json",
      "Authorization": "Bearer ${secrets.API_TOKEN}"
    },
    "body": "{\"user_id\": \"${inputs.user_id}\"}",
    "timeout_ms": 30000,
    "verify_ssl": true
  }
}
```

**Config Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `step_type` | string | Yes | Must be `"api_rest"` |
| `method` | string | Yes | GET, POST, PUT, DELETE, PATCH |
| `url` | string | Yes | HTTPS URL (variable refs allowed) |
| `headers` | object | No | HTTP headers |
| `body` | string | No | **JSON string** for request body |
| `timeout_ms` | int | No | 1000-300000 (default: 30000) |
| `verify_ssl` | bool | No | SSL verification (default: true) |

**Security Requirements:**
- URLs MUST use HTTPS (HTTP only for localhost)
- Private IPs are blocked (127.x.x.x, 10.x.x.x, 192.168.x.x)
- Cloud metadata endpoints are blocked

**Body Field Format:**

The `body` field must be a **JSON string**, not an object:

```json
// CORRECT - JSON string with escaped quotes
"body": "{\"key\": \"value\", \"data\": \"${inputs.data}\"}"

// WRONG - Object (not allowed)
"body": {"key": "value"}
```

---

### 2. transform - Data Transformation

Use for data transformation without external calls.

#### Template Mode (Most Common)

```json
{
  "id": "format_output",
  "type": "transform",
  "config": {
    "step_type": "transform",
    "mode": "template",
    "template": "${fetch_user.output.data.name}"
  }
}
```

**CRITICAL**: `template` must be a **string**, not an object!

```json
// CORRECT
"template": "${api_call.output.data}"
"template": "Result: ${step.output.name}"

// WRONG - Object is INVALID
"template": {"result": "${step.output.data}"}
```

#### Concat Mode

```json
{
  "id": "join_strings",
  "type": "transform",
  "config": {
    "step_type": "transform",
    "mode": "concat",
    "separator": ", "
  }
}
```

#### Map Mode

```json
{
  "id": "extract_fields",
  "type": "transform",
  "config": {
    "step_type": "transform",
    "mode": "map",
    "fields": ["name", "email", "id"]
  }
}
```

#### Merge Mode

```json
{
  "id": "merge_data",
  "type": "transform",
  "config": {
    "step_type": "transform",
    "mode": "merge",
    "fields": ["user", "profile"]
  }
}
```

**Config Fields by Mode:**

| Mode | Required Fields | Optional Fields |
|------|-----------------|-----------------|
| `template` | `template` (string) | - |
| `concat` | `separator` (string) | - |
| `map` | `fields` (array) | - |
| `merge` | `fields` (array) | - |

---

### 3. code_js - JavaScript Execution

Use for complex logic requiring custom code.

```json
{
  "id": "calculate",
  "type": "code_js",
  "config": {
    "step_type": "code_js",
    "path": "/scripts/utils.js",
    "function_name": "parseJson"
  }
}
```

**Config Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `step_type` | string | Yes | Must be `"code_js"` |
| `path` | string | Yes | Path to JavaScript file |
| `function_name` | string | Yes | Function to execute |

**Allowed Functions (Whitelist):**
- `formatDate` - Date formatting
- `parseJson` - JSON parsing
- `stringConcat` - String concatenation
- `arrayFilter` - Array filtering
- `objectMerge` - Object merging

**Constraints:**
- Maximum execution time: 5 seconds
- Maximum memory: 128MB
- No access to Node.js APIs (fs, http, etc.)
- No external module imports
- Path must not contain `../` (path traversal blocked)

---

## Variable Reference Syntax

### Reference Types

| Syntax | Source | Example |
|--------|--------|---------|
| `${inputs.field}` | Workflow inputs | `${inputs.user_id}` |
| `${step_id.output}` | Step output | `${fetch_user.output}` |
| `${step_id.output.field}` | Step output field | `${fetch_user.output.name}` |
| `${secrets.KEY}` | Secret from MyVault | `${secrets.API_TOKEN}` |

### Nested Access

Access nested fields with dot notation:

```
${inputs.user.profile.name}
${fetch_data.output.response.items[0].id}
```

---

## Decision Guidelines

### Step Type Selection

```
Need to call external API?
    YES -> api_rest
    NO -> Transform or process data?
        YES -> transform (use appropriate mode)
        NO -> Need complex logic?
            YES -> code_js (whitelist only)
```

### Mode Selection for Transform

```
What transformation is needed?

1. Extract/format data from previous step -> mode: "template"
   Example: Get specific field from API response

2. Join array elements -> mode: "concat"
   Example: Combine multiple strings with separator

3. Extract specific fields from objects -> mode: "map"
   Example: Get only name and email from user objects

4. Merge multiple objects -> mode: "merge"
   Example: Combine user and profile data
```

---

## Anti-Patterns (Avoid These)

### 1. Missing step_type in config

```json
// WRONG - Missing step_type
{
  "type": "api_rest",
  "config": {
    "method": "GET",
    "url": "https://api.example.com"
  }
}

// CORRECT - Include step_type
{
  "type": "api_rest",
  "config": {
    "step_type": "api_rest",
    "method": "GET",
    "url": "https://api.example.com"
  }
}
```

### 2. Object instead of JSON string

```json
// WRONG - input_schema as object
"input_schema": {"query": "string"}

// CORRECT - input_schema as JSON string
"input_schema": "{\"query\": \"string\"}"
```

### 3. Template as object

```json
// WRONG - template as object
"template": {"result": "${step.output}"}

// CORRECT - template as string
"template": "${step.output}"
```

### 4. HTTP Instead of HTTPS

```json
// WRONG
"url": "http://api.example.com/data"

// CORRECT
"url": "https://api.example.com/data"
```

### 5. Body as object

```json
// WRONG - body as object
"body": {"key": "value"}

// CORRECT - body as JSON string
"body": "{\"key\": \"value\"}"
```

---

## Validation Checklist

Before submitting a workflow, verify:

- [ ] `workflow_name` follows naming rules (`^[a-zA-Z_][a-zA-Z0-9_-]*$`)
- [ ] `input_schema` is a valid JSON string
- [ ] `output_schema` is a valid JSON string
- [ ] `output` is a valid JSON string
- [ ] All step IDs are unique
- [ ] All step IDs follow naming rules
- [ ] All `config.step_type` matches `type`
- [ ] All URLs use HTTPS
- [ ] All `body` fields are JSON strings (not objects)
- [ ] All `template` fields are strings (not objects)
- [ ] Variable references match actual step IDs

---

## Example: Complete Workflow

```json
{
  "workflow_name": "llm_answer_generation",
  "description": "Generate an answer using LLM",
  "input_schema": "{\"query\": \"string\"}",
  "output_schema": "{\"answer\": \"string\"}",
  "steps": [
    {
      "id": "call_llm",
      "type": "api_rest",
      "config": {
        "step_type": "api_rest",
        "method": "POST",
        "url": "http://localhost:8004/v1/mylllm",
        "headers": {
          "Content-Type": "application/json"
        },
        "body": "{\"user_input\": \"${inputs.query}\", \"system_prompt\": \"You are a helpful assistant.\", \"model\": \"gpt-4o-mini\"}",
        "timeout_ms": 60000
      }
    },
    {
      "id": "format_output",
      "type": "transform",
      "config": {
        "step_type": "transform",
        "mode": "template",
        "template": "${call_llm.output.result}"
      }
    }
  ],
  "output": "{\"answer\": \"${format_output.output}\"}"
}
```

---

## Model Selection Guide

TaskFlow V2 generation uses LLMs with Structured Output. Model performance varies:

| Model | Structured Output | Processing Time | Recommendation |
|-------|------------------|-----------------|----------------|
| `gpt-5-mini` | Excellent | 1-5 min (complex schemas) | Production |
| `gpt-4o-mini` | Good | 10-30 sec | Fast iteration |
| `gemini-3-flash-preview` | Good | 5-20 sec | Default |
| `claude-haiku-4-5` | Limited | N/A | Not recommended |

**Environment Variables:**
- `WORKFLOW_GENERATOR_V2_MODEL`: Model name (default: `gemini-3-flash-preview`)
- `WORKFLOW_GENERATOR_V2_TEMPERATURE`: Temperature (default: `0.3`)

---

## Error Codes Reference

| Code | Category | Retryable | Action |
|------|----------|-----------|--------|
| SCHEMA_INVALID_TYPE | Schema | Yes | Fix field type (string vs object) |
| SCHEMA_INVALID_UNION | Schema | No | Use unified config model |
| SEC_001 | Security | No | Change to HTTPS |
| SEC_002 | Security | No | Use public API endpoint |
| API_001 | API | Maybe | Check URL and credentials |
| TIMEOUT_001 | Timeout | Yes | Increase timeout_ms |

---

*Document Version: 2.0 - Issue #350 (OpenAI Structured Output Compatible)*
