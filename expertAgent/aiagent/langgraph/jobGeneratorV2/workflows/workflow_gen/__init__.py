"""WorkflowGen workflow for Job Generator V2.

This package contains the WorkflowGenWorkflow and its sub-workflows:
- WorkflowGenWorkflow: Main workflow orchestrating YAML generation and testing
- YamlGeneratorSubWorkflow: Generates GraphAI YAML workflows (template-based)
- TestRunnerSubWorkflow: Runs workflow tests (optional)
- PromptBuilderSubWorkflow: Builds LLM prompts for workflow generation
- LLMGeneratorSubWorkflow: LLM-based workflow generation
- YamlValidatorSubWorkflow: Validates generated YAML

Issue #342 Phase D.2: WorkflowGen workflow implementation.
Issue #342 Phase F: WorkflowGen V2 LLM Integration.
Issue #350: Added Strategy Pattern for engine switching (GraphAI/TaskFlow V2).
"""

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.errors import (
    ErrorCode,
    ValidationError,
    ValidationResult,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.llm_generator import (
    LLMGenerationResult,
    LLMGeneratorSubWorkflow,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder import (
    PromptBuilderSubWorkflow,
    WorkflowPrompt,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.schemas import (
    AVAILABLE_AGENTS,
    GraphAIWorkflowSchema,
    NodeDefinition,
    is_valid_agent,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
    TestRunnerSubWorkflow,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow import (
    WorkflowGenWorkflow,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
    YamlGeneratorSubWorkflow,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_validator import (
    YamlValidationResult,
    YamlValidatorSubWorkflow,
)

# Issue #350: Strategy Pattern exports
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.engine_strategy import (
    EngineType,
    GraphAIGeneratorStrategy,
    TaskFlowGeneratorStrategy,
    WorkflowGeneratorStrategy,
    WorkflowOutput,
    create_strategy,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.taskflow_generator import (
    TaskFlowGenerationResult,
    TaskFlowLLMGenerator,
)

__all__ = [
    # Main workflow
    "WorkflowGenWorkflow",
    # Sub-workflows
    "YamlGeneratorSubWorkflow",
    "TestRunnerSubWorkflow",
    "PromptBuilderSubWorkflow",
    "LLMGeneratorSubWorkflow",
    "YamlValidatorSubWorkflow",
    # Schemas
    "GraphAIWorkflowSchema",
    "NodeDefinition",
    "AVAILABLE_AGENTS",
    "is_valid_agent",
    # Errors
    "ErrorCode",
    "ValidationError",
    "ValidationResult",
    # Results
    "LLMGenerationResult",
    "YamlValidationResult",
    "WorkflowPrompt",
    # Issue #350: Strategy Pattern
    "EngineType",
    "WorkflowOutput",
    "WorkflowGeneratorStrategy",
    "GraphAIGeneratorStrategy",
    "TaskFlowGeneratorStrategy",
    "create_strategy",
    # Issue #350: TaskFlow generator
    "TaskFlowLLMGenerator",
    "TaskFlowGenerationResult",
]
