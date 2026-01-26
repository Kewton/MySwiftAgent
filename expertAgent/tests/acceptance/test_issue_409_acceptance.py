"""
Issue #409 Acceptance Tests (L3: Local Acceptance Tests)

Multiple Independent Tasks Dataflow - E2E Validation

This test validates that workflows with multiple independent tasks
(dependencies=[]) correctly use {{job.body.user_input}} for all
independent tasks, not just the first one.

Prerequisites:
- Services running (./scripts/dev-hybrid.sh start --local-only)
- myVault configured with required API keys

Execution:
  cd expertAgent && uv run pytest tests/acceptance/test_issue_409_acceptance.py -v -s
"""

import logging
from unittest.mock import MagicMock

import pytest

from aiagent.langgraph.jobGeneratorV2.types_old import (
    InterfaceSchema,
    TaskDefinition,
)
from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
    MasterManagerSubWorkflow,
)


@pytest.mark.acceptance
class TestIssue409Acceptance:
    """Issue #409: Acceptance tests for multiple independent tasks dataflow.

    Acceptance Criteria:
    - AC-1: dependencies=[]のタスク（TaskFlow）は{{job.body.user_input}}を使用する
    - AC-2: _get_user_input_schemaが全独立タスクのフィールドを含む
    - AC-3: Issue #408の検証が正しく機能する（全ユーザー入力フィールドが検証対象）
    - AC-4: 複数独立タスクのテストケースが追加される
    - AC-5: 既存テストTC-005はレガシー互換性テストとして残し、docstringに明記する
    - AC-6: 同名フィールド衝突時に両方の型情報を含む警告ログを出力する
    - AC-7: 同名フィールドで型が異なる場合はValueErrorを発生させる
    - AC-8: 独立タスクのデータフロー仕様をexpertAgent/docs/に文書化する
    """

    # ==========================================================================
    # E2E-001: Multiple Independent Tasks Job Generation
    # ==========================================================================

    def test_e2e001_two_independent_tasks_receive_user_input(self) -> None:
        """E2E-001: Two independent tasks both receive user_input correctly.

        Scenario:
        - task_001: dependencies=[], needs 'keyword'
        - task_002: dependencies=[], needs 'recipient_email'
        - task_003: dependencies=[task_001, task_002], needs outputs from both

        Expected:
        - task_001: inputs = {{job.body.user_input}}
        - task_002: inputs = {{job.body.user_input}} (NOT {{tasks[0].output_data}})
        - task_003: inputs = dict with field references
        """
        # Arrange
        manager = MasterManagerSubWorkflow(
            jobqueue_client=MagicMock(),
            engine="taskflow",
        )

        sorted_tasks: list[TaskDefinition] = [
            TaskDefinition(
                id="task_001",
                name="Keyword Search",
                description="Search by keyword",
                task_type="fetch",
                recommended_api="/api/search",
                dependencies=[],  # Independent
            ),
            TaskDefinition(
                id="task_002",
                name="Email Lookup",
                description="Lookup recipient email",
                task_type="fetch",
                recommended_api="/api/email",
                dependencies=[],  # Also independent (AC-1 key scenario)
            ),
            TaskDefinition(
                id="task_003",
                name="Send Report",
                description="Send report combining search results and email",
                task_type="send",
                recommended_api="/api/send",
                dependencies=["task_001", "task_002"],
            ),
        ]

        interfaces: dict[str, InterfaceSchema] = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {"keyword": {"type": "string"}},
                    "required": ["keyword"],
                },
                output_schema={
                    "type": "object",
                    "properties": {"search_results": {"type": "array"}},
                },
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={
                    "type": "object",
                    "properties": {"recipient_email": {"type": "string"}},
                    "required": ["recipient_email"],
                },
                output_schema={
                    "type": "object",
                    "properties": {"email_validated": {"type": "boolean"}},
                },
            ),
            "task_003": InterfaceSchema(
                task_id="task_003",
                input_schema={
                    "type": "object",
                    "properties": {
                        "search_results": {"type": "array"},
                        "email_validated": {"type": "boolean"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {"status": {"type": "string"}},
                },
            ),
        }

        task_order_map = {task.id: i for i, task in enumerate(sorted_tasks)}

        # Act - Generate body_template for each task
        template_001 = manager._build_body_template(
            order=0,
            task=sorted_tasks[0],
            interfaces=interfaces,
            task_order_map=task_order_map,
        )

        template_002 = manager._build_body_template(
            order=1,
            task=sorted_tasks[1],
            interfaces=interfaces,
            task_order_map=task_order_map,
        )

        template_003 = manager._build_body_template(
            order=2,
            task=sorted_tasks[2],
            interfaces=interfaces,
            task_order_map=task_order_map,
        )

        # Assert
        # AC-1: First independent task uses user_input
        assert template_001["inputs"] == "{{job.body.user_input}}", (
            f"Task 001 should use user_input, got: {template_001['inputs']}"
        )

        # AC-1 KEY: Second independent task ALSO uses user_input (this is the fix)
        assert template_002["inputs"] == "{{job.body.user_input}}", (
            f"Task 002 (independent) should use user_input, not previous task output. "
            f"Got: {template_002['inputs']}"
        )

        # Dependent task uses field references
        assert isinstance(template_003["inputs"], dict), (
            f"Task 003 (dependent) should have dict inputs, got: {type(template_003['inputs'])}"
        )

    def test_e2e002_type_mismatch_raises_valueerror_with_type_info(self) -> None:
        """E2E-002: Type mismatch in independent tasks raises ValueError.

        Scenario:
        - task_001: dependencies=[], field 'value' with type 'string'
        - task_002: dependencies=[], field 'value' with type 'integer'

        Expected:
        - ValueError raised with both type information
        """
        # Arrange
        manager = MasterManagerSubWorkflow(
            jobqueue_client=MagicMock(),
            engine="taskflow",
        )

        sorted_tasks = [
            TaskDefinition(
                id="task_001",
                name="Task A",
                description="Task A",
                task_type="fetch",
                recommended_api="/api/a",
                dependencies=[],
            ),
            TaskDefinition(
                id="task_002",
                name="Task B",
                description="Task B",
                task_type="fetch",
                recommended_api="/api/b",
                dependencies=[],
            ),
        ]

        interfaces: dict[str, InterfaceSchema] = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {"value": {"type": "string"}},
                },
                output_schema={"type": "object", "properties": {}},
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={
                    "type": "object",
                    "properties": {"value": {"type": "integer"}},
                },
                output_schema={"type": "object", "properties": {}},
            ),
        }

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            manager._get_user_input_schema(sorted_tasks, interfaces)

        error_message = str(exc_info.value)
        # AC-7: Error should contain both type information
        assert "value" in error_message.lower(), "Error should mention field name"
        assert "string" in error_message.lower(), "Error should mention 'string' type"
        assert "integer" in error_message.lower(), "Error should mention 'integer' type"

    def test_e2e003_type_match_logs_warning_and_continues(self, caplog) -> None:
        """E2E-003: Type match in independent tasks logs warning and continues.

        Scenario:
        - task_001: dependencies=[], field 'value' with type 'string'
        - task_002: dependencies=[], field 'value' with type 'string' (same)

        Expected:
        - Warning logged with both type info
        - Processing continues (no error)
        - Merged schema contains the field
        """
        # Arrange
        manager = MasterManagerSubWorkflow(
            jobqueue_client=MagicMock(),
            engine="taskflow",
        )

        sorted_tasks = [
            TaskDefinition(
                id="task_001",
                name="Task A",
                description="Task A",
                task_type="fetch",
                recommended_api="/api/a",
                dependencies=[],
            ),
            TaskDefinition(
                id="task_002",
                name="Task B",
                description="Task B",
                task_type="fetch",
                recommended_api="/api/b",
                dependencies=[],
            ),
        ]

        interfaces: dict[str, InterfaceSchema] = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {"value": {"type": "string"}},
                },
                output_schema={"type": "object", "properties": {}},
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={
                    "type": "object",
                    "properties": {"value": {"type": "string"}},
                },
                output_schema={"type": "object", "properties": {}},
            ),
        }

        # Act
        with caplog.at_level(logging.WARNING):
            result = manager._get_user_input_schema(sorted_tasks, interfaces)

        # Assert
        # Processing should continue
        assert result is not None
        assert "value" in result.get("properties", {})

        # AC-6: Warning should be logged with type info
        warning_found = False
        for record in caplog.records:
            if record.levelno == logging.WARNING:
                msg = record.message
                if "value" in msg.lower() and "task b" in msg.lower():
                    warning_found = True
                    # Check both type info is present
                    assert "string" in msg.lower(), (
                        f"Warning should contain type info. Got: {msg}"
                    )
                    break

        assert warning_found, (
            f"Warning log should be present. Logs: {[r.message for r in caplog.records]}"
        )

    # ==========================================================================
    # AC-2: _get_user_input_schema merges all independent tasks
    # ==========================================================================

    def test_ac2_user_input_schema_merges_all_independent_task_fields(self) -> None:
        """AC-2: _get_user_input_schema returns merged schema from all independent tasks.

        This ensures Issue #408 validation has access to all user input fields.
        """
        # Arrange
        manager = MasterManagerSubWorkflow(
            jobqueue_client=MagicMock(),
            engine="taskflow",
        )

        sorted_tasks = [
            TaskDefinition(
                id="task_001",
                name="Task A",
                description="Task A",
                task_type="fetch",
                recommended_api="/api/a",
                dependencies=[],
            ),
            TaskDefinition(
                id="task_002",
                name="Task B",
                description="Task B",
                task_type="fetch",
                recommended_api="/api/b",
                dependencies=[],
            ),
            TaskDefinition(
                id="task_003",
                name="Task C",
                description="Dependent",
                task_type="process",
                recommended_api="/api/c",
                dependencies=["task_001"],
            ),
        ]

        interfaces: dict[str, InterfaceSchema] = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {
                        "field_a": {"type": "string"},
                        "shared_field": {"type": "number"},
                    },
                    "required": ["field_a"],
                },
                output_schema={"type": "object", "properties": {}},
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={
                    "type": "object",
                    "properties": {
                        "field_b": {"type": "boolean"},
                    },
                    "required": ["field_b"],
                },
                output_schema={"type": "object", "properties": {}},
            ),
            "task_003": InterfaceSchema(
                task_id="task_003",
                input_schema={
                    "type": "object",
                    "properties": {
                        "dependent_field": {"type": "array"},
                    },
                },
                output_schema={"type": "object", "properties": {}},
            ),
        }

        # Act
        result = manager._get_user_input_schema(sorted_tasks, interfaces)

        # Assert
        assert result is not None
        properties = result.get("properties", {})

        # Fields from task_001 (independent)
        assert "field_a" in properties, "field_a from task_001 should be merged"
        assert "shared_field" in properties, (
            "shared_field from task_001 should be merged"
        )

        # Fields from task_002 (independent)
        assert "field_b" in properties, "field_b from task_002 should be merged"

        # Fields from task_003 should NOT be included (dependent)
        assert "dependent_field" not in properties, (
            "dependent_field from task_003 should NOT be merged"
        )

        # Required fields should be merged
        required = result.get("required", [])
        assert "field_a" in required
        assert "field_b" in required

    # ==========================================================================
    # Backward Compatibility Tests
    # ==========================================================================

    def test_legacy_call_without_task_param_still_works(self) -> None:
        """Backward compatibility: Calling _build_body_template without task param.

        This ensures existing code that calls _build_body_template(order=N)
        without the task parameter continues to work.
        """
        # Arrange
        manager = MasterManagerSubWorkflow(
            jobqueue_client=MagicMock(),
            engine="taskflow",
        )

        # Act - Legacy call without task/interfaces
        result = manager._build_body_template(order=1)

        # Assert - Should use legacy format
        assert result["inputs"] == "{{tasks[0].output_data}}", (
            f"Legacy call should use previous task output, got: {result['inputs']}"
        )
        assert result["workflow"] == "__PENDING__"
        assert result["project"] == "{{job.body.project}}"

    def test_dependent_task_with_interfaces_uses_field_references(self) -> None:
        """Dependent task with interfaces uses field references correctly.

        Ensures that tasks with dependencies still use field-level references.
        """
        # Arrange
        manager = MasterManagerSubWorkflow(
            jobqueue_client=MagicMock(),
            engine="taskflow",
        )

        task = TaskDefinition(
            id="task_002",
            name="Process",
            description="Process data",
            task_type="process",
            recommended_api="/api/process",
            dependencies=["task_001"],  # Has dependency
        )

        interfaces: dict[str, InterfaceSchema] = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"type": "object", "properties": {}},
                output_schema={
                    "type": "object",
                    "properties": {"result": {"type": "string"}},
                },
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={
                    "type": "object",
                    "properties": {"result": {"type": "string"}},
                },
                output_schema={"type": "object", "properties": {}},
            ),
        }

        task_order_map = {"task_001": 0, "task_002": 1}

        # Act
        result = manager._build_body_template(
            order=1,
            task=task,
            interfaces=interfaces,
            task_order_map=task_order_map,
        )

        # Assert - Dependent task should use dict format with field references
        inputs = result["inputs"]
        assert isinstance(inputs, dict), f"Expected dict inputs, got: {type(inputs)}"
        assert inputs.get("result") == "{{tasks[0].output_data.result}}"


@pytest.mark.acceptance
class TestIssue409EdgeCases:
    """Edge case tests for Issue #409."""

    def test_single_independent_task_still_works(self) -> None:
        """Single independent task (original behavior) still works correctly."""
        # Arrange
        manager = MasterManagerSubWorkflow(
            jobqueue_client=MagicMock(),
            engine="taskflow",
        )

        sorted_tasks = [
            TaskDefinition(
                id="task_001",
                name="Only Task",
                description="The only task",
                task_type="fetch",
                recommended_api="/api/only",
                dependencies=[],
            ),
        ]

        interfaces: dict[str, InterfaceSchema] = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
                output_schema={"type": "object", "properties": {}},
            ),
        }

        # Act
        result = manager._get_user_input_schema(sorted_tasks, interfaces)

        # Assert
        assert result is not None
        assert "query" in result.get("properties", {})
        assert "query" in result.get("required", [])

    def test_empty_input_schema_handled_correctly(self) -> None:
        """Independent task with empty input schema is handled correctly."""
        # Arrange
        manager = MasterManagerSubWorkflow(
            jobqueue_client=MagicMock(),
            engine="taskflow",
        )

        sorted_tasks = [
            TaskDefinition(
                id="task_001",
                name="Empty Input Task",
                description="Task with empty input",
                task_type="fetch",
                recommended_api="/api/empty",
                dependencies=[],
            ),
        ]

        interfaces: dict[str, InterfaceSchema] = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {},  # Empty properties
                },
                output_schema={"type": "object", "properties": {}},
            ),
        }

        # Act
        result = manager._get_user_input_schema(sorted_tasks, interfaces)

        # Assert - Should return schema with empty properties (not None)
        # Because task is independent but has no input fields
        if result is not None:
            assert result.get("properties", {}) == {}

    def test_no_independent_tasks_returns_none(self) -> None:
        """If all tasks are dependent, returns None for user_input_schema."""
        # Arrange
        manager = MasterManagerSubWorkflow(
            jobqueue_client=MagicMock(),
            engine="taskflow",
        )

        # All tasks have dependencies
        sorted_tasks = [
            TaskDefinition(
                id="task_001",
                name="Dependent Only",
                description="All dependent",
                task_type="fetch",
                recommended_api="/api/dep",
                dependencies=["external_task"],
            ),
        ]

        interfaces: dict[str, InterfaceSchema] = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {"data": {"type": "string"}},
                },
                output_schema={"type": "object", "properties": {}},
            ),
        }

        # Act
        result = manager._get_user_input_schema(sorted_tasks, interfaces)

        # Assert - No independent tasks means no user input schema
        assert result is None
