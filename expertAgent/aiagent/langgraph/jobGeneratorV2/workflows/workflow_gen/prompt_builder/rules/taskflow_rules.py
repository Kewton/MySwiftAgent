"""TaskFlow V2 Prompt Rules.

Issue #350 Task 2.2: TaskFlow-specific LLM prompt rules.
Issue #350 Fix: Added API capability rules for expertAgent internal APIs.

This module provides prompt rules for generating TaskFlow V2 JSON workflows.
"""

from __future__ import annotations

from core.config import settings


def get_taskflow_rules() -> list[str]:
    """Get TaskFlow V2 generation rules.

    Returns:
        List of rule sections for LLM prompts
    """
    return [
        get_taskflow_structure_rules(),
        get_taskflow_step_types(),
        get_taskflow_variable_reference_rules(),
        get_taskflow_security_rules(),
        get_taskflow_api_rules(),
    ]


def get_taskflow_structure_rules() -> str:
    """Get TaskFlow V2 structure rules."""
    return """## TaskFlow V2 Workflow Structure

A TaskFlow V2 workflow is a JSON document with the following structure:

```json
{
  "workflow_name": "string (required, pattern: ^[a-zA-Z_][a-zA-Z0-9_-]*$)",
  "description": "string (optional)",
  "input_schema": {"field_name": "type"},
  "output_schema": {"field_name": "type"},
  "steps": [/* step definitions */],
  "output": {"field_name": "${step_id.output}"}
}
```

### Field Types
- string, number, boolean, array, object, null

### Step ID Pattern
Step IDs must match: `^[a-zA-Z_][a-zA-Z0-9_-]*$`
- Valid: `fetch_data`, `step_001`, `process_result`
- Invalid: `123step`, `step@name`, `step name`
"""


def get_taskflow_step_types() -> str:
    """Get TaskFlow V2 step type descriptions."""
    return """## TaskFlow V2 Step Types

### 1. api_rest - REST API Call
```json
{
  "id": "fetch_user",
  "type": "api_rest",
  "config": {
    "step_type": "api_rest",
    "method": "GET|POST|PUT|DELETE|PATCH",
    "url": "https://api.example.com/endpoint",
    "headers": {"Authorization": "Bearer ${secrets.TOKEN}"},
    "body": "{\"key\": \"${inputs.value}\"}",
    "timeout_ms": 30000
  }
}
```
**IMPORTANT**:
- URL must use HTTPS. HTTP is not allowed.
- config must include "step_type" matching the step type.
- **body must be a JSON string**, not a dict object. Use escaped quotes.

### 2. transform - Data Transformation

**CRITICAL**: Each transform mode requires SPECIFIC config fields. DO NOT use fields not listed for each mode.

#### Mode: template (most common)
Use `template` field with ${} variable references:
```json
{
  "id": "format_output",
  "type": "transform",
  "config": {
    "step_type": "transform",
    "mode": "template",
    "template": "Result: ${fetch_user.output.data.name}"
  }
}
```

**CRITICAL**: The `template` field MUST be a STRING, not a dict/object!
- ✅ CORRECT: `"template": "Result: ${step.output.data}"`
- ✅ CORRECT: `"template": "${step.output.data.name}"`
- ❌ WRONG: `"template": {"result": "${step.output.data}"}`  ← This is INVALID!
- ❌ WRONG: `"template": {"search_results": "${api.output.data.items}"}`  ← This is INVALID!

If you need structured output, use a simple string template and let the output mapping handle it:
```json
{
  "id": "format_output",
  "type": "transform",
  "config": {
    "step_type": "transform",
    "mode": "template",
    "template": "${api_call.output.data}"
  }
}
```
Then use the workflow output field to structure the results:
```json
"output": {
  "result": "${format_output.output}",
  "status": "${api_call.output.status}"
}
```

#### Mode: concat
Use `separator` field to join array elements:
```json
{
  "id": "join_items",
  "type": "transform",
  "config": {
    "step_type": "transform",
    "mode": "concat",
    "separator": ", "
  }
}
```

#### Mode: map
Use `fields` field (array of field names to extract):
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
**WARNING**: DO NOT use `map: {...}` - this is WRONG. Use `fields: [...]` instead.

#### Mode: merge
Use `fields` field (array of field names to merge):
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

**RECOMMENDATION**: For most data transformation needs, use `mode: "template"` with ${} references.

### 3. code_js - JavaScript Function (Limited)
```json
{
  "id": "parse_data",
  "type": "code_js",
  "config": {
    "step_type": "code_js",
    "path": "/scripts/utils.js",
    "function_name": "parseJson"
  }
}
```

**IMPORTANT**: Only pre-approved functions are allowed:
- formatDate
- parseJson
- stringConcat
- arrayFilter
- objectMerge
"""


def get_taskflow_variable_reference_rules() -> str:
    """Get variable reference rules for TaskFlow V2."""
    return """## Variable Reference Syntax

TaskFlow V2 uses `${}` syntax for variable references:

### Input References
- `${inputs.field_name}` - Reference input field

### Step Output References
- `${step_id.output}` - Reference entire step output
- `${step_id.output.data}` - Reference 'data' field from step output
- `${step_id.output.data.nested}` - Reference nested field

### Secret References
- `${secrets.API_KEY}` - Reference secret from vault

### Examples
```json
{
  "url": "https://api.example.com/users/${inputs.user_id}",
  "template": "Hello, ${fetch_user.output.data.name}!",
  "headers": {"Authorization": "Bearer ${secrets.API_TOKEN}"}
}
```

### Common Mistakes to Avoid
- DON'T use `:source.` prefix (that's GraphAI syntax)
- DON'T use `{{}}` (that's Jinja2 syntax)
- DO use `${}` for all variable references
"""


def get_taskflow_security_rules() -> str:
    """Get security rules for TaskFlow V2."""
    return """## Security Requirements

### 1. HTTPS Only
All URLs MUST use HTTPS protocol. HTTP is not allowed.
- Valid: `https://api.example.com/endpoint`
- Invalid: `http://api.example.com/endpoint`

### 2. No Private IP Addresses
The following are blocked for SSRF protection:
- 127.x.x.x (localhost)
- 10.x.x.x (private)
- 192.168.x.x (private)
- 169.254.x.x (link-local)
- localhost

### 3. code_js Restrictions
Only these pre-approved functions are allowed:
- formatDate: Date formatting
- parseJson: JSON parsing
- stringConcat: String concatenation
- arrayFilter: Array filtering
- objectMerge: Object merging

If you need custom logic, use `transform` step with template mode.

### 4. Path Traversal Prevention
Paths in code_js config must not contain:
- `../` (parent directory)
- `..\\` (Windows parent directory)
"""


def get_taskflow_api_rules() -> str:
    """Get available expertAgent API information for TaskFlow generation.

    Issue #350 Fix: TaskFlow workflows MUST use internal expertAgent APIs
    instead of external APIs (like api.openai.com directly).
    """
    expertagent_base = settings.EXPERTAGENT_BASE_URL or "http://localhost:8004"

    return f"""## Available ExpertAgent APIs

**CRITICAL**: You MUST use ONLY these internal APIs. DO NOT use external APIs directly.
- ❌ DO NOT use: api.openai.com, api.anthropic.com, or any external LLM API
- ✅ DO use: expertAgent internal APIs listed below

### Base URL
All API endpoints use this base URL: `{expertagent_base}`
You can use the full URL or `${{secrets.EXPERTAGENT_BASE_URL}}` for dynamic resolution.

---

### 1. Direct LLM Call (MOST IMPORTANT - Use this for all LLM tasks)
**Endpoint**: `{expertagent_base}/v1/mylllm`
**Method**: POST
**Use for**: Text generation, summarization, translation, analysis, question answering

```json
{{
  "id": "llm_process",
  "type": "api_rest",
  "config": {{
    "step_type": "api_rest",
    "method": "POST",
    "url": "{expertagent_base}/v1/mylllm",
    "headers": {{"Content-Type": "application/json"}},
    "body": "{{\"user_input\": \"${{inputs.query}}\", \"system_prompt\": \"You are a helpful assistant.\", \"model\": \"gpt-4o-mini\"}}"
  }}
}}
```

**Available models**: gpt-4o-mini, gpt-4o, gemini-1.5-flash, gemini-1.5-pro, claude-3-5-sonnet
**Response**: `{{"result": "LLM response text"}}`

---

### 2. JSON Output Agent (For structured JSON output)
**Endpoint**: `{expertagent_base}/v1/aiagent/utility/jsonoutput`
**Method**: POST
**Use for**: Structured data extraction, classification, JSON formatting

```json
{{
  "id": "json_extract",
  "type": "api_rest",
  "config": {{
    "step_type": "api_rest",
    "method": "POST",
    "url": "{expertagent_base}/v1/aiagent/utility/jsonoutput",
    "headers": {{"Content-Type": "application/json"}},
    "body": "{{\"user_input\": \"${{inputs.text}}\", \"system_prompt\": \"Extract key information and return as JSON.\"}}"
  }}
}}
```

**Response**: `{{"result": {{...}}}}` (always valid JSON)

---

### 3. Gmail APIs
**Search**: `{expertagent_base}/v1/utility/gmail/search`
```json
{{"query": "is:unread", "max_results": 10}}
```
**Response**: `{{"messages": [...], "result_count": N}}`

**Send**: `{expertagent_base}/v1/utility/gmail/send`
```json
{{"to": "email@example.com", "subject": "Subject", "body": "Message body"}}
```
**Response**: `{{"result": "...", "message_id": "..."}}`

---

### 4. Google Search APIs
**Search**: `{expertagent_base}/v1/utility/google_search`
```json
{{"queries": ["search term"], "num": 10}}
```
**Response**: `{{"search_results": [...], "status": "ok"}}`

**Search Overview**: `{expertagent_base}/v1/utility/google_search_overview`
```json
{{"queries": ["search term"], "num": 10}}
```
**Response**: `{{"result": {{"text": "ok", "result": [...]}}}}`

---

### 5. Google Drive APIs
**Upload**: `{expertagent_base}/v1/utility/drive/upload`
```json
{{"file_path": "/path/to/file", "drive_folder_url": "https://drive.google.com/..."}}
```
**Response**: `{{"status": "success", "file_id": "...", "web_view_link": "..."}}`

---

### 6. Text-to-Speech APIs
**TTS + Drive**: `{expertagent_base}/v1/utility/text_to_speech_drive`
```json
{{"text": "Text to speak", "drive_folder_url": "...", "voice": "alloy"}}
```
**Response**: `{{"file_id": "...", "web_view_link": "..."}}`
**Voices**: alloy, echo, fable, onyx, nova, shimmer

---

### Summary of API Selection
| Task Type | Use This API |
|-----------|--------------|
| LLM text generation | /v1/mylllm |
| Structured JSON output | /v1/aiagent/utility/jsonoutput |
| Email search | /v1/utility/gmail/search |
| Email send | /v1/utility/gmail/send |
| Web search | /v1/utility/google_search |
| File upload | /v1/utility/drive/upload |
| Text-to-speech | /v1/utility/text_to_speech_drive |

**REMINDER**: Never use external APIs like api.openai.com. Always use the expertAgent internal APIs listed above.
"""


# Combine all rules for convenience
TASKFLOW_RULES_FULL = "\n\n".join(get_taskflow_rules())


__all__ = [
    "get_taskflow_rules",
    "get_taskflow_structure_rules",
    "get_taskflow_step_types",
    "get_taskflow_variable_reference_rules",
    "get_taskflow_security_rules",
    "get_taskflow_api_rules",
    "TASKFLOW_RULES_FULL",
]
