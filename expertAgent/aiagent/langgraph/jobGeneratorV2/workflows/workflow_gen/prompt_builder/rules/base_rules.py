"""Base rules for GraphAI workflow generation.

This module defines fundamental rules for GraphAI workflows:
- Version requirement (0.5)
- Source node requirement
- isResult requirement

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

BASE_RULES = """## GraphAI Base Rules

### Version
- ALWAYS use `version: "0.5"` (current GraphAI version)
- Do NOT use version 0.6 or other versions

### Source Node
- ALWAYS include `source: {}` as the first node
- This is the entry point for user input
- Reference source data with `:source` or `:source.property`

### Result Node
- At least ONE node MUST have `isResult: true`
- This marks the final output of the workflow
- Only one isResult node is recommended

### Node Order
- Define nodes in execution order for readability
- Source should be first
- Output/result node should be last
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
