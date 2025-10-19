"""LangGraph nodes for Job/Task Auto-Generation Agent.

This package contains 6 nodes that form the workflow:
- requirement_analysis: Decompose requirements into tasks
- evaluator: Evaluate task quality and feasibility
- interface_definition: Define interface schemas
- master_creation: Register TaskMasters and JobMaster
- validation: Validate workflow interfaces
- job_registration: Create executable Job
"""

__all__: list[str] = []
