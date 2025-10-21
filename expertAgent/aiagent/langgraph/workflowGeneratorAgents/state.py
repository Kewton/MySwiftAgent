"""State definition for GraphAI Workflow Generator Agent.

This module defines the state structure for the LangGraph-based agent that
automatically generates GraphAI workflow YAML files from TaskMaster metadata.

Workflow:
1. Generator Node → Generate YAML from task metadata using LLM
2. Workflow Tester Node → Test YAML execution on graphAiServer
3. Validator Node → Validate execution results (non-LLM)
4. Self-Repair Node → Fix errors and regenerate (max 3 retries)
"""

from typing import Any, TypedDict


class WorkflowGeneratorState(TypedDict, total=False):
    """State for GraphAI Workflow Generator workflow.

    This state tracks the complete workflow from TaskMaster metadata to
    validated GraphAI workflow YAML.

    Attributes:
        # Input fields
        task_master_id: TaskMaster ID to generate workflow for
        task_data: TaskMaster metadata (name, description, interfaces, etc.)
        max_retry: Maximum retry count for self-repair (default: 3)

        # Generator fields
        yaml_content: Generated GraphAI workflow YAML
        workflow_name: Generated workflow name (snake_case)
        generation_retry_count: Current generation retry count

        # Workflow Testing fields
        workflow_registered: Whether workflow was registered to graphAiServer
        workflow_file_path: Path to registered workflow file
        sample_input: Generated sample input for testing
        test_execution_result: graphAiServer execution result
        test_http_status: HTTP status code from graphAiServer

        # Validation fields
        validation_result: Validation result (is_valid, errors)
        validation_errors: List of validation error messages
        is_valid: Whether workflow passed all validations

        # Self-Repair fields
        retry_count: Current self-repair retry count
        error_feedback: Error feedback for LLM to fix issues
        repair_history: List of repair attempts with errors

        # Output fields
        status: Workflow status (success, failed, max_retries_exceeded)
        error_message: Error message if workflow failed
    """

    # ===== Input =====
    task_master_id: int
    task_data: dict[str, Any]
    max_retry: int

    # ===== Generator =====
    yaml_content: str
    workflow_name: str
    generation_retry_count: int

    # ===== Workflow Testing =====
    workflow_registered: bool
    workflow_file_path: str | None
    sample_input: dict[str, Any] | str
    test_execution_result: dict[str, Any] | None
    test_http_status: int | None

    # ===== Validation =====
    validation_result: dict[str, Any] | None
    validation_errors: list[str]
    is_valid: bool

    # ===== Self-Repair =====
    retry_count: int
    error_feedback: str | None
    repair_history: list[dict[str, Any]]

    # ===== Output =====
    status: str
    error_message: str | None


def create_initial_state(
    task_master_id: int,
    task_data: dict[str, Any],
    max_retry: int = 3,
) -> WorkflowGeneratorState:
    """Create initial state with default values.

    Args:
        task_master_id: TaskMaster ID to generate workflow for
        task_data: TaskMaster metadata from jobqueue API
        max_retry: Maximum retry count for self-repair (default: 3)

    Returns:
        WorkflowGeneratorState: Initial state with default values
    """
    return {
        # Input
        "task_master_id": task_master_id,
        "task_data": task_data,
        "max_retry": max_retry,
        # Generator
        "yaml_content": "",
        "workflow_name": "",
        "generation_retry_count": 0,
        # Workflow Testing
        "workflow_registered": False,
        "workflow_file_path": None,
        "sample_input": {},
        "test_execution_result": None,
        "test_http_status": None,
        # Validation
        "validation_result": None,
        "validation_errors": [],
        "is_valid": False,
        # Self-Repair
        "retry_count": 0,
        "error_feedback": None,
        "repair_history": [],
        # Output
        "status": "initialized",
        "error_message": None,
    }
