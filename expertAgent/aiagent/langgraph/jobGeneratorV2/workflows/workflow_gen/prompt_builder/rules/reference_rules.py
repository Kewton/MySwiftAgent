"""Reference rules for GraphAI workflow generation.

This module defines rules for node references (:node.path format).

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

REFERENCE_RULES = """## Reference Rules

### Reference Syntax
References use the `:node.path` format to access data from other nodes.

### Source Node Structure
The source node contains two namespaces:
- `user_input` - Dynamic data (job input parameters or previous task output)
- `job_params` - Static job parameters

**IMPORTANT**: Always use `:source.user_input.*` to access input data!

- `:source.user_input` - Reference user input data container
- `:source.user_input.property` - Access a property of user input (REQUIRED format)
- `:source.job_params.property` - Access static job parameters
- `:node_name` - Reference output of another node
- `:node_name.property` - Access specific property

**CRITICAL**: DO NOT use `:source.property` directly - it will NOT work!
The correct format is always `:source.user_input.property`

### fetchAgent Response Access
fetchAgent returns HTTP response body directly:
```yaml
# API returns: { "data": "value" }
# Access with: :api_node.data
```

### Source Input Access Examples
```yaml
# Job Input: { "query": "検索キーワード" }
# graphAiServer injects: source = { user_input: { query: "検索キーワード" }, job_params: {...} }

# CORRECT:
query: :source.user_input.query  # "検索キーワード"

# WRONG (will be undefined):
query: :source.query  # undefined - DO NOT USE!
```

### Nested Access
```yaml
# source.user_input = { "user": { "name": "John" } }
name: :source.user_input.user.name  # "John"
```

### Array Access
```yaml
# data = ["a", "b", "c"]
first: :node.items[0]  # "a"
```

### Common Mistakes
- DON'T reference undefined nodes
- DON'T create circular references
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
