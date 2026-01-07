"""Reference rules for GraphAI workflow generation.

This module defines rules for node references (:node.path format).

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

REFERENCE_RULES = """## Reference Rules

### Reference Syntax
References use the `:node.path` format to access data from other nodes.

- `:source` - Reference the source node (user input)
- `:source.property` - Access a property of source
- `:node_name` - Reference output of another node
- `:node_name.property` - Access specific property
- `:node_name.result.field` - For fetchAgent API responses

### fetchAgent Response Access
When using fetchAgent, the API response is wrapped in `.result`:
```yaml
# API returns: { "data": "value" }
# Access with: :api_node.result.data
```

### Nested Access
```yaml
# source = { "user": { "name": "John" } }
name: :source.user.name  # "John"
```

### Array Access
```yaml
# data = ["a", "b", "c"]
first: :node.items[0]  # "a"
```

### Common Mistakes
- DON'T reference undefined nodes
- DON'T create circular references
- DON'T forget `.result` for fetchAgent responses
- DO ensure referenced node is defined before use
"""


def get_reference_rules() -> str:
    """Get reference rules for workflow generation.

    Returns:
        Reference rules string
    """
    return REFERENCE_RULES


# Reference pattern regex
REFERENCE_PATTERN = r":[\w]+(?:\.[\w\[\]]+)*"
