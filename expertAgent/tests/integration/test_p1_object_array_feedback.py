"""Integration tests for P1 Object Array Feedback handling.

Issue #340: Tests for P1-5, P1-6, P1-7 - ensuring object_array_issues
are properly propagated through the workflow.
"""

from typing import Any

import pytest


class TestTestDataRegeneratorObjectArrayMerge:
    """Tests for P1-5: test_data_regenerator merges object_array_issues."""

    @pytest.mark.asyncio
    async def test_test_data_issues_includes_object_array_issues(self) -> None:
        """P1-5: test_data_regenerator should merge object_array_issues into feedback."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.test_data_regenerator import (
            _build_regenerator_input,
        )

        # Setup state with both test_data_issues and object_array_issues
        state: dict[str, Any] = {
            "task_data": {
                "name": "Test Task",
                "description": "Test description",
                "input_interface": {"schema": {"type": "object"}},
                "recommended_apis": [],
            },
            "sample_input": {"field1": "value1"},
            "test_data_issues": ["Issue 1", "Issue 2"],
            "object_array_issues": [
                {
                    "node_id": "sample_input",
                    "issue_type": "object_in_array",
                    "message": "Array field 'focus_points' contains object at index 0",
                    "severity": "error",
                    "field_name": "focus_points",
                    "suggestion": "Use primitive types",
                }
            ],
            "suggested_test_data": None,
        }

        # Build the regenerator input
        prompt = _build_regenerator_input(state)

        # The prompt should contain the object_array_issues message
        assert "focus_points" in prompt or "object" in prompt.lower()

    @pytest.mark.asyncio
    async def test_regeneration_count_incremented(self) -> None:
        """P1-5: object_array_regeneration_count should be incremented."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.test_data_regenerator import (
            test_data_regenerator_node,
        )

        state: dict[str, Any] = {
            "task_data": {
                "name": "Test Task",
                "description": "Test description",
                "input_interface": {"schema": {"type": "object"}},
                "recommended_apis": [],
            },
            "sample_input": {"field1": "value1"},
            "test_data_issues": [],
            "object_array_issues": [],
            "suggested_test_data": {"field1": "new_value"},
            "test_data_regeneration_count": 0,
            "max_test_data_regeneration": 2,
            "object_array_regeneration_count": 0,
        }

        result = await test_data_regenerator_node(state)

        # Verify regeneration count is incremented
        assert result["object_array_regeneration_count"] == 1


class TestLLMEvaluatorObjectArrayDetection:
    """Tests for P1-6: llm_evaluator detects object_array_errors."""

    @pytest.mark.asyncio
    async def test_llm_evaluator_triggers_regeneration_on_object_array_errors(
        self,
    ) -> None:
        """P1-6: llm_evaluator should trigger test data regeneration when object_array_errors exist."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            llm_evaluator_node,
        )

        state: dict[str, Any] = {
            "task_data": {
                "name": "Test Task",
                "description": "Test description",
                "input_interface": {"schema": {"type": "object"}},
                "output_interface": {"schema": {"type": "object"}},
                "recommended_apis": [],
            },
            "yaml_content": "version: 0.5\nnodes: {}",
            "sample_input": {"field1": "value1"},
            "test_execution_result": {"status": "success"},
            "validation_result": {"issues": []},
            "is_valid": True,
            "test_data_regeneration_count": 0,
            "max_test_data_regeneration": 2,
            # Issue #340: Object array errors detected
            "has_object_array_errors": True,
            "object_array_issues": [
                {
                    "node_id": "sample_input",
                    "issue_type": "object_in_array",
                    "message": "Array field 'focus_points' contains object",
                    "severity": "error",
                    "field_name": "focus_points",
                    "suggestion": "Use primitive types",
                }
            ],
        }

        result = await llm_evaluator_node(state)

        # Verify that regeneration is triggered
        assert result.get("needs_test_data_regeneration") is True
        # Verify failure reason is set
        assert (
            result.get("llm_evaluation_result", {}).get("failure_reason")
            == "test_data_quality"
        )


class TestSelfRepairObjectArrayFeedback:
    """Tests for P1-7: self_repair includes object_array_issues in feedback."""

    @pytest.mark.asyncio
    async def test_self_repair_includes_object_array_issues_in_feedback(self) -> None:
        """P1-7: self_repair should include object_array_issues in error_feedback."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.self_repair import (
            self_repair_node,
        )

        state: dict[str, Any] = {
            "workflow_name": "test_workflow",
            "validation_errors": [],
            "validation_result": {"issues": []},
            "schema_validation_issues": [],
            "has_schema_errors": False,
            # Issue #340: Object array issues
            "object_array_issues": [
                {
                    "node_id": "sample_input",
                    "issue_type": "object_in_array",
                    "message": "Array field 'focus_points' contains object at index 0",
                    "severity": "error",
                    "field_name": "focus_points",
                    "suggestion": "Use primitive types instead of objects",
                }
            ],
            "retry_count": 0,
            "max_retry": 3,
            "repair_history": [],
            "generation_model": None,
        }

        result = await self_repair_node(state)

        # Verify object array issues are in error feedback
        error_feedback = result.get("error_feedback", "")
        assert "object_array" in error_feedback or "Object Array" in error_feedback
        assert "focus_points" in error_feedback

    @pytest.mark.asyncio
    async def test_self_repair_includes_issue_340_guidance(self) -> None:
        """P1-7: self_repair should include Issue #340 specific guidance."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.self_repair import (
            self_repair_node,
        )

        state: dict[str, Any] = {
            "workflow_name": "test_workflow",
            "validation_errors": [],
            "validation_result": {"issues": []},
            "schema_validation_issues": [],
            "has_schema_errors": False,
            "object_array_issues": [
                {
                    "node_id": "sample_input",
                    "issue_type": "object_in_array",
                    "message": "Array field 'test_field' contains object",
                    "severity": "error",
                    "field_name": "test_field",
                    "suggestion": "Use primitive types",
                }
            ],
            "retry_count": 0,
            "max_retry": 3,
            "repair_history": [],
            "generation_model": None,
        }

        result = await self_repair_node(state)

        error_feedback = result.get("error_feedback", "")
        # Should contain Issue #340 specific guidance
        assert "Issue #340" in error_feedback or "stringTemplateAgent" in error_feedback

    @pytest.mark.asyncio
    async def test_self_repair_resets_object_array_state(self) -> None:
        """P1-7: self_repair should reset object_array_issues and related state."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.self_repair import (
            self_repair_node,
        )

        state: dict[str, Any] = {
            "workflow_name": "test_workflow",
            "validation_errors": [],
            "validation_result": {"issues": []},
            "schema_validation_issues": [],
            "has_schema_errors": False,
            "object_array_issues": [
                {
                    "node_id": "sample_input",
                    "issue_type": "object_in_array",
                    "message": "Array field 'test_field' contains object",
                    "severity": "error",
                    "field_name": "test_field",
                    "suggestion": "Use primitive types",
                }
            ],
            "has_object_array_errors": True,
            "object_array_regeneration_count": 2,
            "retry_count": 0,
            "max_retry": 3,
            "repair_history": [],
            "generation_model": None,
        }

        result = await self_repair_node(state)

        # Verify state is reset for next iteration
        assert result.get("object_array_issues") == []
        assert result.get("has_object_array_errors") is False
        assert result.get("object_array_regeneration_count") == 0


class TestLLMEvaluationPromptArrayConstraints:
    """Tests for P1-6: LLM evaluation prompt contains array constraints."""

    def test_llm_evaluation_prompt_contains_array_validation_criteria(self) -> None:
        """P1-6: LLM_EVALUATION_SYSTEM_PROMPT should contain array validation criteria."""
        from aiagent.langgraph.workflowGeneratorAgents.prompts.llm_evaluation import (
            LLM_EVALUATION_SYSTEM_PROMPT,
        )

        # Check for array validation related content
        prompt_lower = LLM_EVALUATION_SYSTEM_PROMPT.lower()
        # Should mention array type validation or object Object pattern
        assert any(
            keyword in prompt_lower
            for keyword in ["array", "object object", "[object object]", "primitive"]
        )

    def test_llm_evaluation_prompt_contains_issue_340_reference(self) -> None:
        """P1-6: LLM_EVALUATION_SYSTEM_PROMPT should reference Issue #340."""
        from aiagent.langgraph.workflowGeneratorAgents.prompts.llm_evaluation import (
            LLM_EVALUATION_SYSTEM_PROMPT,
        )

        # Should contain Issue #340 reference
        assert "Issue #340" in LLM_EVALUATION_SYSTEM_PROMPT
