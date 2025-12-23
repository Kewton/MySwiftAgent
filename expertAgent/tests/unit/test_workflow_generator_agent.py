"""Unit tests for workflowGeneratorAgents LangGraph workflow."""

from unittest.mock import patch

import pytest

from aiagent.langgraph.workflowGeneratorAgents.agent import (
    create_workflow_generator_graph,
    generate_workflow,
    self_repair_router,
    validator_router,
)
from aiagent.langgraph.workflowGeneratorAgents.state import (
    WorkflowGeneratorState,
    create_initial_state,
)


class TestValidatorRouter:
    """Test validator_router (conditional routing after validation).

    Updated for Issue #305: validator_router now always routes to llm_evaluator
    for semantic evaluation. The llm_evaluator_router handles subsequent routing.
    """

    def test_validator_router_validation_success(self):
        """Test router returns llm_evaluator when validation passes.

        Issue #305: validator now routes to llm_evaluator for semantic evaluation.
        """
        state: WorkflowGeneratorState = {
            "task_master_id": 123,
            "task_data": {"name": "test"},
            "is_valid": True,
            "validation_errors": [],
            "max_retry": 3,
            "retry_count": 0,
            "status": "validated",
        }

        next_node = validator_router(state)

        assert next_node == "llm_evaluator"

    def test_validator_router_validation_failed(self):
        """Test router returns llm_evaluator even when validation fails.

        Issue #305: validator now always routes to llm_evaluator for
        comprehensive evaluation before self_repair.
        """
        state: WorkflowGeneratorState = {
            "task_master_id": 123,
            "task_data": {"name": "test"},
            "is_valid": False,
            "validation_errors": ["YAML syntax error"],
            "max_retry": 3,
            "retry_count": 0,
            "status": "validation_failed",
        }

        next_node = validator_router(state)

        assert next_node == "llm_evaluator"


class TestSelfRepairRouter:
    """Test self_repair_router (conditional routing after self-repair)."""

    def test_self_repair_router_retry_available(self):
        """Test router returns generator when retries are available."""
        state: WorkflowGeneratorState = {
            "task_master_id": 123,
            "task_data": {"name": "test"},
            "max_retry": 3,
            "retry_count": 1,
            "status": "ready_for_retry",
        }

        next_node = self_repair_router(state)

        assert next_node == "generator"

    def test_self_repair_router_max_retries_exceeded(self):
        """Test router returns END when max retries exceeded."""
        state: WorkflowGeneratorState = {
            "task_master_id": 123,
            "task_data": {"name": "test"},
            "max_retry": 3,
            "retry_count": 3,
            "status": "max_retries_exceeded",  # Status is set by self_repair node
        }

        next_node = self_repair_router(state)

        assert next_node == "END"
        # Note: Routers cannot mutate state in LangGraph
        # Status is set by self_repair_node before router is called

    def test_self_repair_router_retry_count_at_boundary(self):
        """Test router at retry boundary (retry_count == max_retry - 1)."""
        state: WorkflowGeneratorState = {
            "task_master_id": 123,
            "task_data": {"name": "test"},
            "max_retry": 3,
            "retry_count": 2,
            "status": "ready_for_retry",
        }

        next_node = self_repair_router(state)

        # Should still allow one more retry
        assert next_node == "generator"


class TestCreateInitialState:
    """Test create_initial_state helper function."""

    def test_create_initial_state_default(self):
        """Test creating initial state with default values."""
        task_data = {
            "name": "Send email notification",
            "description": "Test task",
            "input_interface": {"type": "json_schema", "schema": {}},
            "output_interface": {"type": "json_schema", "schema": {}},
        }

        state = create_initial_state(123, task_data, max_retry=3)

        assert state["task_master_id"] == 123
        assert state["task_data"] == task_data
        assert state["max_retry"] == 3
        assert state["retry_count"] == 0
        assert state["status"] == "initialized"

    def test_create_initial_state_custom_max_retry(self):
        """Test creating initial state with custom max_retry."""
        task_data = {"name": "Test task"}

        state = create_initial_state(456, task_data, max_retry=5)

        assert state["task_master_id"] == 456
        assert state["max_retry"] == 5


class TestWorkflowGraph:
    """Test LangGraph workflow construction."""

    def test_create_workflow_generator_graph(self):
        """Test workflow graph creation."""
        graph = create_workflow_generator_graph()

        # Graph should be compiled
        assert graph is not None

        # Can't easily inspect internal structure, but can verify it's a compiled graph
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "ainvoke")


class TestGenerateWorkflow:
    """Test generate_workflow main entry point (integration tests).

    Updated for Issue #305: Tests now mock the new llm_evaluator_node
    and result_summary_generator_node.
    """

    @pytest.mark.asyncio
    async def test_generate_workflow_success_first_try(self):
        """Test successful workflow generation on first attempt."""
        task_data = {
            "name": "Send email notification",
            "description": "Test task",
            "input_interface": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string", "example": "test@example.com"}
                    },
                },
            },
            "output_interface": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {"status": {"type": "string"}},
                },
            },
        }

        # Mock all nodes to simulate successful workflow
        with (
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.agent.generator_node"
            ) as mock_generator,
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.agent.sample_input_generator_node"
            ) as mock_sample_input,
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.agent.workflow_tester_node"
            ) as mock_tester,
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.agent.validator_node"
            ) as mock_validator,
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.agent.llm_evaluator_node"
            ) as mock_llm_evaluator,
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.agent.result_summary_generator_node"
            ) as mock_result_summary,
        ):
            # Setup mock responses
            async def mock_gen(state):
                return {
                    **state,
                    "yaml_content": "version: 0.5\nnodes: {}",
                    "workflow_name": "send_email_notification",
                    "status": "yaml_generated",
                }

            async def mock_sample(state):
                return {
                    **state,
                    "sample_input": {"email": "test@example.com"},
                    "status": "sample_input_generated",
                }

            async def mock_test(state):
                return {
                    **state,
                    "workflow_registered": True,
                    "test_http_status": 200,
                    "test_execution_result": {
                        "results": {"output": {"status": "sent"}},
                        "errors": {},
                        "logs": [],
                    },
                    "status": "workflow_tested",
                }

            async def mock_validate(state):
                return {
                    **state,
                    "is_valid": True,
                    "validation_result": {"is_valid": True, "errors": []},
                    "status": "validated",
                }

            async def mock_llm_eval(state):
                return {
                    **state,
                    "llm_evaluation_result": {
                        "overall_score": 85,
                        "structural_score": 90,
                        "requirement_score": 85,
                        "output_quality_score": 80,
                        "error_handling_score": 75,
                        "test_data_quality_score": 85,
                    },
                    "evaluation_score": 85,
                    "needs_test_data_regeneration": False,
                    "is_valid": True,
                }

            async def mock_summary(state):
                return {
                    **state,
                    "validation_summary": {"overall_status": "success"},
                    "summary_markdown": "# Summary",
                    "status": "success",
                }

            mock_generator.side_effect = mock_gen
            mock_sample_input.side_effect = mock_sample
            mock_tester.side_effect = mock_test
            mock_validator.side_effect = mock_validate
            mock_llm_evaluator.side_effect = mock_llm_eval
            mock_result_summary.side_effect = mock_summary

            # Execute workflow
            final_state = await generate_workflow(
                task_master_id=123, task_data=task_data, max_retry=3
            )

            # Assertions
            assert final_state["is_valid"] is True
            assert final_state["status"] == "success"  # Updated for Issue #305
            assert final_state["retry_count"] == 0
            assert final_state["workflow_name"] == "send_email_notification"

    @pytest.mark.asyncio
    async def test_generate_workflow_success_after_retry(self):
        """Test successful workflow generation after 1 retry.

        Updated for Issue #305: Now includes llm_evaluator_node and
        result_summary_generator_node in the workflow.
        """
        task_data = {
            "name": "Send email notification",
            "description": "Test task",
            "input_interface": {"type": "json_schema", "schema": {"type": "object"}},
            "output_interface": {"type": "json_schema", "schema": {"type": "object"}},
        }

        llm_eval_attempt = 0

        with (
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.agent.generator_node"
            ) as mock_generator,
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.agent.sample_input_generator_node"
            ) as mock_sample_input,
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.agent.workflow_tester_node"
            ) as mock_tester,
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.agent.validator_node"
            ) as mock_validator,
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.agent.llm_evaluator_node"
            ) as mock_llm_evaluator,
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.agent.result_summary_generator_node"
            ) as mock_result_summary,
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.agent.self_repair_node"
            ) as mock_self_repair,
        ):

            async def mock_gen(state):
                return {
                    **state,
                    "yaml_content": "version: 0.5\nnodes: {}",
                    "workflow_name": "test_workflow",
                    "status": "yaml_generated",
                }

            async def mock_sample(state):
                return {**state, "sample_input": {}, "status": "sample_input_generated"}

            async def mock_test(state):
                return {
                    **state,
                    "workflow_registered": True,
                    "test_http_status": 200,
                    "test_execution_result": {"results": {}, "errors": {}, "logs": []},
                    "status": "workflow_tested",
                }

            async def mock_validate(state):
                return {
                    **state,
                    "is_valid": True,
                    "validation_result": {"is_valid": True, "errors": []},
                    "status": "validated",
                }

            async def mock_llm_eval(state):
                nonlocal llm_eval_attempt
                llm_eval_attempt += 1

                # First attempt: low score, second attempt: pass
                if llm_eval_attempt == 1:
                    return {
                        **state,
                        "llm_evaluation_result": {
                            "overall_score": 50,
                            "failure_reason": "workflow_quality",
                        },
                        "evaluation_score": 50,
                        "needs_test_data_regeneration": False,
                        "is_valid": False,
                    }
                else:
                    return {
                        **state,
                        "llm_evaluation_result": {
                            "overall_score": 85,
                            "failure_reason": "none",
                        },
                        "evaluation_score": 85,
                        "needs_test_data_regeneration": False,
                        "is_valid": True,
                    }

            async def mock_summary(state):
                return {
                    **state,
                    "validation_summary": {"overall_status": "partial"},
                    "summary_markdown": "# Summary",
                    "status": "success",
                }

            async def mock_repair(state):
                return {
                    **state,
                    "error_feedback": "Fix node error",
                    "retry_count": state.get("retry_count", 0) + 1,
                    "status": "ready_for_retry",
                }

            mock_generator.side_effect = mock_gen
            mock_sample_input.side_effect = mock_sample
            mock_tester.side_effect = mock_test
            mock_validator.side_effect = mock_validate
            mock_llm_evaluator.side_effect = mock_llm_eval
            mock_result_summary.side_effect = mock_summary
            mock_self_repair.side_effect = mock_repair

            final_state = await generate_workflow(
                task_master_id=123, task_data=task_data, max_retry=3
            )

            # Should succeed after 1 retry
            assert final_state["is_valid"] is True
            assert final_state["status"] == "success"  # Updated for Issue #305
            assert final_state["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_generate_workflow_max_retries_exceeded(self):
        """Test workflow generation failing after max retries."""
        task_data = {
            "name": "Send email notification",
            "description": "Test task",
            "input_interface": {"type": "json_schema", "schema": {"type": "object"}},
            "output_interface": {"type": "json_schema", "schema": {"type": "object"}},
        }

        with (
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.agent.generator_node"
            ) as mock_generator,
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.agent.sample_input_generator_node"
            ) as mock_sample_input,
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.agent.workflow_tester_node"
            ) as mock_tester,
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.agent.validator_node"
            ) as mock_validator,
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.agent.self_repair_node"
            ) as mock_self_repair,
        ):

            async def mock_gen(state):
                return {
                    **state,
                    "yaml_content": "version: 0.5\nnodes: {}",
                    "workflow_name": "test_workflow",
                    "status": "yaml_generated",
                }

            async def mock_sample(state):
                return {**state, "sample_input": {}, "status": "sample_input_generated"}

            async def mock_test(state):
                return {
                    **state,
                    "workflow_registered": True,
                    "test_http_status": 200,
                    "test_execution_result": {"results": {}, "errors": {}, "logs": []},
                    "status": "workflow_tested",
                }

            async def mock_validate(state):
                # Always fail validation
                return {
                    **state,
                    "is_valid": False,
                    "validation_errors": ["Persistent error"],
                    "status": "validation_failed",
                }

            async def mock_repair(state):
                retry_count = state.get("retry_count", 0)
                max_retry = state.get("max_retry", 3)
                new_retry_count = retry_count + 1

                # Determine status based on retry count (same logic as real node)
                if new_retry_count >= max_retry:
                    status = "max_retries_exceeded"
                else:
                    status = "ready_for_retry"

                return {
                    **state,
                    "error_feedback": "Fix persistent error",
                    "retry_count": new_retry_count,
                    "status": status,
                }

            mock_generator.side_effect = mock_gen
            mock_sample_input.side_effect = mock_sample
            mock_tester.side_effect = mock_test
            mock_validator.side_effect = mock_validate
            mock_self_repair.side_effect = mock_repair

            final_state = await generate_workflow(
                task_master_id=123, task_data=task_data, max_retry=3
            )

            # Should fail after max retries
            assert final_state["is_valid"] is False
            assert final_state["status"] == "max_retries_exceeded"
            assert final_state["retry_count"] == 3

    @pytest.mark.asyncio
    async def test_generate_workflow_with_custom_max_retry(self):
        """Test workflow generation with custom max_retry value."""
        task_data = {
            "name": "Test task",
            "input_interface": {"type": "json_schema", "schema": {"type": "object"}},
            "output_interface": {"type": "json_schema", "schema": {"type": "object"}},
        }

        with (
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.agent.generator_node"
            ) as mock_generator,
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.agent.sample_input_generator_node"
            ) as mock_sample_input,
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.agent.workflow_tester_node"
            ) as mock_tester,
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.agent.validator_node"
            ) as mock_validator,
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.agent.self_repair_node"
            ) as mock_self_repair,
        ):

            async def mock_gen(state):
                return {
                    **state,
                    "yaml_content": "",
                    "workflow_name": "test",
                    "status": "yaml_generated",
                }

            async def mock_sample(state):
                return {**state, "sample_input": {}, "status": "sample_input_generated"}

            async def mock_test(state):
                return {
                    **state,
                    "test_http_status": 200,
                    "test_execution_result": {"results": {}, "errors": {}, "logs": []},
                    "status": "workflow_tested",
                }

            async def mock_validate(state):
                return {
                    **state,
                    "is_valid": False,
                    "validation_errors": ["Error"],
                    "status": "validation_failed",
                }

            async def mock_repair(state):
                retry_count = state.get("retry_count", 0)
                max_retry = state.get("max_retry", 3)
                new_retry_count = retry_count + 1

                # Determine status based on retry count (same logic as real node)
                if new_retry_count >= max_retry:
                    status = "max_retries_exceeded"
                else:
                    status = "ready_for_retry"

                return {
                    **state,
                    "error_feedback": "Fix",
                    "retry_count": new_retry_count,
                    "status": status,
                }

            mock_generator.side_effect = mock_gen
            mock_sample_input.side_effect = mock_sample
            mock_tester.side_effect = mock_test
            mock_validator.side_effect = mock_validate
            mock_self_repair.side_effect = mock_repair

            # Custom max_retry = 2 (to avoid hitting LangGraph recursion limit of 25)
            final_state = await generate_workflow(
                task_master_id=123, task_data=task_data, max_retry=2
            )

            # Should fail after 2 retries
            assert final_state["retry_count"] == 2
            assert final_state["status"] == "max_retries_exceeded"
