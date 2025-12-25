"""Utility functions for Job/Task Auto-Generation Agent.

This package contains utility modules:
- jobqueue_client: API client for jobqueue CRUD operations
- schema_matcher: Matching logic for existing schemas
- graphai_capabilities: GraphAI and expertAgent capability lists
- workflow_helper: Issue #305 - Workflow generation helper
"""

from .workflow_helper import generate_workflow_for_task

__all__: list[str] = ["generate_workflow_for_task"]
