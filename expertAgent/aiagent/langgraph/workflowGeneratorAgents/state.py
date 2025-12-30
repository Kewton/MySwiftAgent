"""State definition for GraphAI Workflow Generator Agent.

This module defines the state structure for the LangGraph-based agent that
automatically generates GraphAI workflow YAML files from TaskMaster metadata.

Updated Workflow (Issue #305):
1. Generator Node -> Generate YAML from task metadata using LLM
2. Sample Input Generator Node -> Generate sample input from Input Interface
3. Workflow Tester Node -> Test YAML execution on graphAiServer
4. Validator Node -> Validate execution results (non-LLM)
5. LLM Evaluator Node -> LLM-based semantic evaluation (NEW)
6. Test Data Regenerator Node -> Regenerate low-quality test data (NEW)
7. Result Summary Generator Node -> Generate validation summary (NEW)
8. Self-Repair Node -> Fix errors and regenerate (max 3 retries)
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
        fast_mode: Skip LLM evaluation when rule-based validation passes (Issue #305)

        # Generator fields
        yaml_content: Generated GraphAI workflow YAML
        workflow_name: Generated workflow name (snake_case)
        generation_retry_count: Current generation retry count
        generation_model: Model name used for latest generation attempt

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

        # LLM Evaluator fields (Issue #305)
        llm_evaluation_result: LLM evaluation result dictionary
        evaluation_score: Overall evaluation score (0-100)
        evaluation_feedback: Human-readable feedback from LLM
        evaluation_suggestions: List of improvement suggestions

        # Test Data Quality fields (Issue #305)
        test_data_quality_score: Test data quality score (0-100)
        test_data_issues: List of test data quality issues
        needs_test_data_regeneration: Whether test data needs regeneration
        test_data_regeneration_count: Current test data regeneration count
        max_test_data_regeneration: Maximum test data regeneration count
        regenerated_sample_input: LLM-regenerated sample input
        suggested_test_data: LLM-suggested test data for regeneration

        # Result Summary fields (Issue #305)
        validation_summary: Complete validation summary dictionary
        summary_markdown: Markdown-formatted summary

        # Self-Repair fields
        retry_count: Current self-repair retry count
        error_feedback: Error feedback for LLM to fix issues
        repair_history: List of repair attempts with errors and metadata

        # Output fields
        status: Workflow status (success, failed, max_retries_exceeded)
        error_message: Error message if workflow failed
    """

    # ===== Input =====
    task_master_id: (
        str | int
    )  # ULID string (e.g., 'tm_01K8K13NC8PRJ3V4R35C1AP2JP') or legacy int
    task_data: dict[str, Any]
    max_retry: int
    fast_mode: bool  # Issue #305: Skip LLM evaluation when rule-based validation passes

    # ===== Generator =====
    yaml_content: str
    workflow_name: str
    generation_retry_count: int
    generation_model: str | None

    # ===== Workflow Testing =====
    workflow_registered: bool
    workflow_file_path: str | None
    sample_input: dict[str, Any] | str | int | float | bool | list[Any] | None
    test_execution_result: dict[str, Any] | None
    test_http_status: int | None

    # ===== Validation =====
    validation_result: dict[str, Any] | None
    validation_errors: list[str]
    is_valid: bool

    # ===== LLM Evaluator (Issue #305) =====
    llm_evaluation_result: dict[str, Any] | None
    evaluation_score: int | None
    evaluation_feedback: str | None
    evaluation_suggestions: list[str]

    # ===== Test Data Quality (Issue #305) =====
    test_data_quality_score: int | None
    test_data_issues: list[str]
    needs_test_data_regeneration: bool
    test_data_regeneration_count: int
    max_test_data_regeneration: int
    regenerated_sample_input: dict[str, Any] | None
    suggested_test_data: dict[str, Any] | None

    # ===== Result Summary (Issue #305) =====
    validation_summary: dict[str, Any] | None
    summary_markdown: str | None

    # ===== Schema Validation (Issue #333) =====
    schema_validation_result: dict[str, Any] | None
    schema_validation_issues: list[dict[str, Any]]
    has_schema_errors: bool

    # ===== Self-Repair =====
    retry_count: int
    error_feedback: str | None
    repair_history: list[dict[str, Any]]

    # ===== Output =====
    status: str
    error_message: str | None


def create_initial_state(
    task_master_id: str | int,
    task_data: dict[str, Any],
    max_retry: int = 3,
    max_test_data_regeneration: int = 2,
    fast_mode: bool = False,
) -> WorkflowGeneratorState:
    """Create initial state with default values.

    Args:
        task_master_id: TaskMaster ID (ULID string or int) to generate
            workflow for
        task_data: TaskMaster metadata from jobqueue API
        max_retry: Maximum retry count for self-repair (default: 3)
        max_test_data_regeneration: Maximum test data regeneration count (default: 2)
        fast_mode: Skip LLM evaluation when rule-based validation passes (default: False)
            Issue #305: When enabled, skips LLM evaluation for successfully
            validated workflows to reduce processing time.
            Changed to False by default for quality-first approach.

    Returns:
        WorkflowGeneratorState: Initial state with default values
    """
    # Issue #305: In fast_mode, reduce retry counts for faster processing
    effective_max_retry = 2 if fast_mode else max_retry
    effective_max_test_data_regen = 1 if fast_mode else max_test_data_regeneration

    return {
        # Input
        "task_master_id": task_master_id,
        "task_data": task_data,
        "max_retry": effective_max_retry,
        "fast_mode": fast_mode,
        # Generator
        "yaml_content": "",
        "workflow_name": "",
        "generation_retry_count": 0,
        "generation_model": None,
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
        # LLM Evaluator (Issue #305)
        "llm_evaluation_result": None,
        "evaluation_score": None,
        "evaluation_feedback": None,
        "evaluation_suggestions": [],
        # Test Data Quality (Issue #305)
        "test_data_quality_score": None,
        "test_data_issues": [],
        "needs_test_data_regeneration": False,
        "test_data_regeneration_count": 0,
        "max_test_data_regeneration": effective_max_test_data_regen,
        "regenerated_sample_input": None,
        "suggested_test_data": None,
        # Result Summary (Issue #305)
        "validation_summary": None,
        "summary_markdown": None,
        # Schema Validation (Issue #333)
        "schema_validation_result": None,
        "schema_validation_issues": [],
        "has_schema_errors": False,
        # Self-Repair
        "retry_count": 0,
        "error_feedback": None,
        "repair_history": [],
        # Output
        "status": "initialized",
        "error_message": None,
    }
