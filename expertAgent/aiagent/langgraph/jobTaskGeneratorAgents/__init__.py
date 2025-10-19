"""Job/Task Auto-Generation Agent.

This package provides a LangGraph-based agent that automatically generates
jobqueue Jobs and Tasks from natural language requirements.

The agent implements a 6-node workflow:
1. requirement_analysis_node: Decompose requirements into tasks
2. evaluator_node: Evaluate task quality and feasibility
3. interface_definition_node: Define interface schemas
4. master_creation_node: Register TaskMasters and JobMaster
5. validation_node: Validate workflow interfaces
6. job_registration_node: Create executable Job

The agent follows 4 principles for task decomposition:
- Hierarchical decomposition
- Clear dependencies
- Specificity and executability
- Modularity and reusability

Plus feasibility evaluation against GraphAI + expertAgent Direct API capabilities.
"""

from aiagent.langgraph.jobTaskGeneratorAgents.state import (
    JobTaskGeneratorState,
    create_initial_state,
)

__all__ = [
    "JobTaskGeneratorState",
    "create_initial_state",
]
