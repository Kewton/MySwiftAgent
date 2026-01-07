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
- Set timeout for long-running APIs (default: 30s)

Correct:
```yaml
api_call:
  agent: fetchAgent
  inputs:
    url: http://api.example.com/endpoint
    method: POST
    body:
      query: :source.query
  timeout: 30
```

Incorrect:
```yaml
# DON'T put url/method/body in params
api_call:
  agent: fetchAgent
  params:  # WRONG!
    url: http://api.example.com
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
