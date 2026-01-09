"""Agent-specific rules for GraphAI workflow generation.

This module defines constraints and best practices for specific agents:
- fetchAgent: HTTP API calls
- stringTemplateAgent: Template strings
- mapAgent: Array processing
- copyAgent: Data transformation

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

FETCH_AGENT_RULES = """### fetchAgent Rules
- Place url, method, body ALL in `inputs` block (NOT params)
- Use method: POST for API calls
- Reference body values with `:node.property`
- Access response data with `:node_name.result.field`
- Set timeout for long-running APIs in **milliseconds** (default: 30000ms = 30 seconds)
- IMPORTANT: Use correct API parameter names (e.g., 'queries' not 'query' for google_search)

Correct:
```yaml
# Google Search example - note 'queries' is an array
google_search:
  agent: fetchAgent
  inputs:
    url: ${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search
    method: POST
    body:
      queries: [':source.user_input.search_term']  # Array format required
      num: 3
  timeout: 180000  # 3 minutes for search

# Generic API call
api_call:
  agent: fetchAgent
  inputs:
    url: http://api.example.com/endpoint
    method: POST
    body:
      data: :source.user_input.data
  timeout: 30000
```

Incorrect:
```yaml
# DON'T put url/method/body in params
api_call:
  agent: fetchAgent
  params:  # WRONG!
    url: http://api.example.com

# DON'T use 'query' for google_search (use 'queries')
search:
  agent: fetchAgent
  inputs:
    url: ${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search
    body:
      query: :source.query  # WRONG! Should be 'queries: [...]'
```
"""

STRING_TEMPLATE_AGENT_RULES = """### stringTemplateAgent Rules
- Define variables in `inputs`
- Use `${variable_name}` in template
- Template goes in `params.template`
- Supports multiline strings with |

Example:
```yaml
format:
  agent: stringTemplateAgent
  inputs:
    data: :previous_node.result
    title: :source.title
  params:
    template: |
      Title: ${title}
      Data: ${data}
```
"""

MAP_AGENT_RULES = """### mapAgent Rules
- Input array goes in `inputs.rows`
- Use `compositeResult: true` to collect results
- Define nested `graph.nodes` for processing
- Access current item with `:row` or named key

Example:
```yaml
process_items:
  agent: mapAgent
  inputs:
    rows: :source.items
  params:
    compositeResult: true
  graph:
    nodes:
      item_source: {}
      process:
        agent: stringTemplateAgent
        inputs:
          item: :item_source
        params:
          template: "Processed: ${item}"
        isResult: true
```
"""

COPY_AGENT_RULES = """### copyAgent Rules
- Use for output transformation
- `inputs` contains data to copy
- `params.namedKey` sets the output key name
- Often used as the final output node

Example:
```yaml
output:
  agent: copyAgent
  inputs:
    result: :previous_node.data
  params:
    namedKey: output
  isResult: true
```
"""

ALL_AGENT_RULES = f"""## Agent-Specific Rules

{FETCH_AGENT_RULES}

{STRING_TEMPLATE_AGENT_RULES}

{MAP_AGENT_RULES}

{COPY_AGENT_RULES}
"""


def get_agent_rules(agents: list[str] | None = None) -> str:
    """Get agent-specific rules.

    Args:
        agents: List of agent names to include rules for.
                If None, returns all rules.

    Returns:
        Agent rules string
    """
    if agents is None:
        return ALL_AGENT_RULES

    rules = ["## Agent-Specific Rules\n"]

    agent_lower = [a.lower() for a in agents]

    if any("fetch" in a for a in agent_lower):
        rules.append(FETCH_AGENT_RULES)
    if any("string" in a or "template" in a for a in agent_lower):
        rules.append(STRING_TEMPLATE_AGENT_RULES)
    if any("map" in a for a in agent_lower):
        rules.append(MAP_AGENT_RULES)
    if any("copy" in a for a in agent_lower):
        rules.append(COPY_AGENT_RULES)

    return "\n".join(rules)
