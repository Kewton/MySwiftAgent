"""Base rules for GraphAI workflow generation.

This module defines fundamental rules for GraphAI workflows:
- Version requirement (0.5)
- Source node requirement
- isResult requirement
- Output node naming (Issue #342 Phase 1)

Issue #342 Phase F: WorkflowGen V2 LLM Integration
Issue #342 Phase 1: Added OUTPUT_NODE_RULE for Worker compatibility
"""

OUTPUT_NODE_RULE = """### Output Node Naming (CRITICAL)
- The final output node MUST be named `output` (exactly)
- DO NOT use names like `format_output`, `result`, `final_result`, etc.
- The Worker expects the result at node named `output`
- This is REQUIRED for proper task chain execution

Correct:
```yaml
output:
  agent: copyAgent
  inputs:
    result: :previous_node.data
  isResult: true
```

Incorrect (DO NOT USE):
```yaml
format_output:  # WRONG - must be named 'output'
  agent: copyAgent
  ...

result:  # WRONG - must be named 'output'
  agent: copyAgent
  ...
```
"""

BASE_RULES = f"""## GraphAI Base Rules

### Version
- ALWAYS use `version: "0.5"` (current GraphAI version)
- Do NOT use version 0.6 or other versions

### Source Node
- ALWAYS include `source: {{}}` as the first node
- This is the entry point for user input
- Reference source data with `:source` or `:source.property`

### Result Node
- At least ONE node MUST have `isResult: true`
- This marks the final output of the workflow
- Only one isResult node is recommended

{OUTPUT_NODE_RULE}

### Node Order
- Define nodes in execution order for readability
- Source should be first
- Output node (named `output`) should be last
"""


def get_base_rules() -> str:
    """Get base rules for workflow generation.

    Returns:
        Base rules string
    """
    return BASE_RULES


VERSION_RULE = 'version: "0.5"'
SOURCE_RULE = "source: {}"
RESULT_RULE = "isResult: true"
