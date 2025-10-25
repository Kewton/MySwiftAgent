"""Unit tests for mock_helpers utility functions.

These tests verify the mock helper functions' behavior including:
- LLM mock creation (basic and structured output)
- Workflow state creation
- Task breakdown generation
- Interface schema generation
- Validation and evaluation result creation
- Edge cases and default values

Issue #111: Comprehensive test coverage for all workflow nodes.
"""

import pytest

from tests.utils.mock_helpers import (
    create_mock_evaluation_result,
    create_mock_interface_schemas,
    create_mock_llm,
    create_mock_llm_with_structured_output,
    create_mock_task_breakdown,
    create_mock_validation_result,
    create_mock_workflow_state,
)


@pytest.mark.unit
class TestMockHelpers:
    """Unit tests for mock_helpers utility functions."""

    # ========================================================================
    # LLM Mock Creation Tests (3 tests)
    # ========================================================================

    @pytest.mark.asyncio
    async def test_create_mock_llm_default(self):
        """Test create_mock_llm with default parameters.

        Priority: High
        This tests the basic LLM mock creation.
        """
        mock_llm = create_mock_llm()

        # Verify mock is created
        assert mock_llm is not None

        # Verify ainvoke returns empty dict by default
        result = await mock_llm.ainvoke("test prompt")
        assert result == {}

    @pytest.mark.asyncio
    async def test_create_mock_llm_with_response_data(self):
        """Test create_mock_llm with custom response data.

        Priority: High
        This tests LLM mock with predefined response.
        """
        response_data = {
            "task_breakdown": [{"task_id": "task_1"}],
            "reasoning": "Test reasoning",
        }

        mock_llm = create_mock_llm(response_data)

        # Verify ainvoke returns the specified data
        result = await mock_llm.ainvoke("test prompt")
        assert result == response_data
        assert result["reasoning"] == "Test reasoning"

    @pytest.mark.asyncio
    async def test_create_mock_llm_with_structured_output(self):
        """Test create_mock_llm_with_structured_output.

        Priority: High
        This tests structured output LLM mock creation.
        """
        response_data = {"field1": "value1", "field2": 42}

        mock_llm = create_mock_llm_with_structured_output(response_data)

        # Verify with_structured_output method exists
        assert hasattr(mock_llm, "with_structured_output")

        # Verify structured output returns the specified data
        structured_model = mock_llm.with_structured_output(dict)
        result = await structured_model.ainvoke("test prompt")
        assert result == response_data

    # ========================================================================
    # Workflow State Creation Tests (3 tests)
    # ========================================================================

    def test_create_mock_workflow_state_default(self):
        """Test create_mock_workflow_state with default parameters.

        Priority: High
        This tests basic workflow state creation.
        """
        state = create_mock_workflow_state()

        # Verify retry_count defaults to 0
        assert state["retry_count"] == 0

        # Verify no other fields are added by default
        assert len(state) == 1

    def test_create_mock_workflow_state_with_retry_count(self):
        """Test create_mock_workflow_state with custom retry_count.

        Priority: Medium
        This tests retry_count parameter.
        """
        state = create_mock_workflow_state(retry_count=3)

        # Verify retry_count is set correctly
        assert state["retry_count"] == 3

    def test_create_mock_workflow_state_with_additional_fields(self):
        """Test create_mock_workflow_state with additional fields.

        Priority: High
        This tests the **additional_fields mechanism.
        """
        state = create_mock_workflow_state(
            retry_count=2,
            user_requirement="Test requirement",
            task_breakdown=[{"task_id": "task_1"}],
            error_message="Test error",
        )

        # Verify retry_count
        assert state["retry_count"] == 2

        # Verify additional fields
        assert state["user_requirement"] == "Test requirement"
        assert len(state["task_breakdown"]) == 1
        assert state["error_message"] == "Test error"

        # Verify total field count
        assert len(state) == 4

    # ========================================================================
    # Task Breakdown Creation Tests (3 tests)
    # ========================================================================

    def test_create_mock_task_breakdown_default(self):
        """Test create_mock_task_breakdown with default parameters.

        Priority: High
        This tests default task breakdown creation (3 tasks).
        """
        tasks = create_mock_task_breakdown()

        # Verify 3 tasks are created by default
        assert len(tasks) == 3

        # Verify first task structure
        assert tasks[0]["task_id"] == "task_1"
        assert tasks[0]["name"] == "Task 1"
        assert tasks[0]["description"] == "Description for task 1"
        assert tasks[0]["priority"] == "high"
        assert tasks[0]["dependencies"] == []

    def test_create_mock_task_breakdown_custom_num_tasks(self):
        """Test create_mock_task_breakdown with custom number of tasks.

        Priority: Medium
        This tests task count parameter.
        """
        tasks = create_mock_task_breakdown(num_tasks=5)

        # Verify 5 tasks are created
        assert len(tasks) == 5

        # Verify task IDs are sequential
        for i in range(1, 6):
            assert tasks[i - 1]["task_id"] == f"task_{i}"

    def test_create_mock_task_breakdown_dependencies(self):
        """Test create_mock_task_breakdown dependency structure.

        Priority: Medium
        This tests dependency generation logic.
        """
        tasks = create_mock_task_breakdown(num_tasks=4)

        # Verify first task has no dependencies
        assert tasks[0]["dependencies"] == []

        # Verify subsequent tasks depend on previous task
        assert tasks[1]["dependencies"] == ["task_1"]
        assert tasks[2]["dependencies"] == ["task_2"]
        assert tasks[3]["dependencies"] == ["task_3"]

    # ========================================================================
    # Interface Schema Creation Tests (2 tests)
    # ========================================================================

    def test_create_mock_interface_schemas_default(self):
        """Test create_mock_interface_schemas with default parameters.

        Priority: Medium
        This tests default interface schema creation.
        """
        schemas = create_mock_interface_schemas()

        # Verify 3 schemas are created by default
        assert len(schemas) == 3

        # Verify first schema structure
        schema = schemas[0]
        assert schema["task_id"] == "task_1"
        assert schema["interface_name"] == "Interface_1"
        assert schema["description"] == "Interface for task 1"

        # Verify input schema
        assert schema["input_schema"]["type"] == "object"
        assert "input_1" in schema["input_schema"]["properties"]
        assert schema["input_schema"]["required"] == ["input_1"]

        # Verify output schema
        assert schema["output_schema"]["type"] == "object"
        assert "output_1" in schema["output_schema"]["properties"]
        assert schema["output_schema"]["required"] == ["output_1"]

    def test_create_mock_interface_schemas_custom_num_schemas(self):
        """Test create_mock_interface_schemas with custom number of schemas.

        Priority: Low
        This tests schema count parameter.
        """
        schemas = create_mock_interface_schemas(num_schemas=2)

        # Verify 2 schemas are created
        assert len(schemas) == 2

        # Verify schema names are sequential
        assert schemas[0]["interface_name"] == "Interface_1"
        assert schemas[1]["interface_name"] == "Interface_2"

    # ========================================================================
    # Validation Result Creation Tests (2 tests)
    # ========================================================================

    def test_create_mock_validation_result_default(self):
        """Test create_mock_validation_result with default parameters.

        Priority: Medium
        This tests default validation result creation.
        """
        result = create_mock_validation_result()

        # Verify default values
        assert result["is_valid"] is True
        assert result["errors"] == []
        assert result["warnings"] == []

    def test_create_mock_validation_result_with_errors(self):
        """Test create_mock_validation_result with errors and warnings.

        Priority: Medium
        This tests custom validation result creation.
        """
        result = create_mock_validation_result(
            is_valid=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"],
        )

        # Verify custom values
        assert result["is_valid"] is False
        assert len(result["errors"]) == 2
        assert result["errors"][0] == "Error 1"
        assert len(result["warnings"]) == 1
        assert result["warnings"][0] == "Warning 1"

    # ========================================================================
    # Evaluation Result Creation Tests (2 tests)
    # ========================================================================

    def test_create_mock_evaluation_result_default(self):
        """Test create_mock_evaluation_result with default parameters.

        Priority: Medium
        This tests default evaluation result creation.
        """
        result = create_mock_evaluation_result()

        # Verify default values
        assert result["is_valid"] is True
        assert result["quality_score"] == 0.9
        assert result["feasibility_score"] == 0.85
        assert result["evaluation_summary"] == "Test evaluation summary"

    def test_create_mock_evaluation_result_custom_scores(self):
        """Test create_mock_evaluation_result with custom scores.

        Priority: Low
        This tests custom evaluation result creation.
        """
        result = create_mock_evaluation_result(
            is_valid=False,
            quality_score=0.5,
            feasibility_score=0.6,
        )

        # Verify custom values
        assert result["is_valid"] is False
        assert result["quality_score"] == 0.5
        assert result["feasibility_score"] == 0.6
        assert result["evaluation_summary"] == "Test evaluation summary"
