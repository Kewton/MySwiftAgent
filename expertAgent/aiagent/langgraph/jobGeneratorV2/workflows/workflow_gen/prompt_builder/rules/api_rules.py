"""API rules for GraphAI workflow generation.

This module defines rules for calling expertAgent APIs.

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

API_RULES = """## API Call Rules

### expertAgent API Base URL
Use the environment variable placeholder for API URLs:
- `${EXPERTAGENT_BASE_URL}/aiagent-api/v1/...`
- This resolves to the correct URL in each environment

### Common API Endpoints

#### Utility APIs (Direct/Fast)
- Gmail Search: `/v1/utility/gmail/search`
- Gmail Send: `/v1/utility/gmail/send`
- Google Search: `/v1/utility/google_search` (timeout: 180s)
- Drive Upload: `/v1/utility/drive/upload`
- TTS + Drive: `/v1/utility/text_to_speech_drive`

#### AI Agent APIs (LLM-based)
- JSON Output: `/v1/aiagent/utility/jsonoutput`
- Explorer: `/v1/aiagent/utility/explorer`
- Direct LLM: `/v1/mylllm`

### API Call Pattern
```yaml
api_call:
  agent: fetchAgent
  inputs:
    url: ${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search
    method: POST
    body:
      queries: [':source.user_input.query']  # Note: 'queries' is array, not 'query'
      num: 3
  timeout: 180000  # Google search needs longer timeout (180s)
  console:
    after: true  # For debugging
```

### Gmail Search Pattern
```yaml
gmail_search:
  agent: fetchAgent
  inputs:
    url: ${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/gmail/search
    method: POST
    body:
      query: :source.user_input.search_query
      max_results: 10
  timeout: 30000  # 30 seconds
```

### Timeout Guidelines
| API Type | Recommended Timeout |
|----------|-------------------|
| Utility APIs | 30s |
| Google Search | 180s (LLM processing) |
| AI Agent APIs | 90s |
| TTS APIs | 60s |

### Response Access
API responses are wrapped in `.result`:
```yaml
# Response: { "messages": [...] }
# Access: :api_node.result.messages
```
"""


def get_api_rules() -> str:
    """Get API rules for workflow generation.

    Returns:
        API rules string
    """
    return API_RULES


# API timeout recommendations
API_TIMEOUTS = {
    "gmail/search": 30,
    "gmail/send": 30,
    "google_search": 180,
    "google_search_overview": 60,
    "drive/upload": 60,
    "text_to_speech": 60,
    "text_to_speech_drive": 60,
    "jsonoutput": 90,
    "explorer": 90,
    "mylllm": 60,
}


def get_recommended_timeout(endpoint: str) -> int:
    """Get recommended timeout for an API endpoint.

    Args:
        endpoint: API endpoint path

    Returns:
        Recommended timeout in seconds
    """
    for key, timeout in API_TIMEOUTS.items():
        if key in endpoint.lower():
            return timeout
    return 30  # Default timeout
