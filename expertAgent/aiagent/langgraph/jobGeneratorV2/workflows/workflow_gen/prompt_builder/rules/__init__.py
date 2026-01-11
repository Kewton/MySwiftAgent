"""Rules for Workflow Generator V2.

This package provides rule modules for LLM workflow generation.

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.rules.agent_rules import (
    ALL_AGENT_RULES,
    ARRAY_JOIN_AGENT_RULES,
    COPY_AGENT_RULES,
    FETCH_AGENT_RULES,
    MAP_AGENT_OUTPUT_RULES,
    MAP_AGENT_RULES,
    STRING_TEMPLATE_AGENT_RULES,
    get_agent_rules,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.rules.api_rules import (
    API_RULES,
    API_TIMEOUTS,
    get_api_rules,
    get_recommended_timeout,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.rules.base_rules import (
    BASE_RULES,
    OUTPUT_NODE_RULE,
    RESULT_RULE,
    SOURCE_RULE,
    VERSION_RULE,
    get_base_rules,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.rules.reference_rules import (
    REFERENCE_PATTERN,
    REFERENCE_RULES,
    get_reference_rules,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.rules.taskflow_rules import (
    TASKFLOW_RULES_FULL,
    get_taskflow_rules,
    get_taskflow_security_rules,
    get_taskflow_step_types,
    get_taskflow_structure_rules,
    get_taskflow_variable_reference_rules,
)

__all__ = [
    # Base rules
    "BASE_RULES",
    "VERSION_RULE",
    "SOURCE_RULE",
    "RESULT_RULE",
    "OUTPUT_NODE_RULE",
    "get_base_rules",
    # Agent rules
    "ALL_AGENT_RULES",
    "FETCH_AGENT_RULES",
    "STRING_TEMPLATE_AGENT_RULES",
    "MAP_AGENT_RULES",
    "MAP_AGENT_OUTPUT_RULES",
    "COPY_AGENT_RULES",
    "ARRAY_JOIN_AGENT_RULES",
    "get_agent_rules",
    # Reference rules
    "REFERENCE_RULES",
    "REFERENCE_PATTERN",
    "get_reference_rules",
    # API rules
    "API_RULES",
    "API_TIMEOUTS",
    "get_api_rules",
    "get_recommended_timeout",
    # TaskFlow rules (Issue #350)
    "TASKFLOW_RULES_FULL",
    "get_taskflow_rules",
    "get_taskflow_structure_rules",
    "get_taskflow_step_types",
    "get_taskflow_variable_reference_rules",
    "get_taskflow_security_rules",
]
