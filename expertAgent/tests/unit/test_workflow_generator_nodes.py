"""Unit tests for workflowGeneratorAgents nodes."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from aiagent.langgraph.workflowGeneratorAgents.nodes.generator import generator_node
from aiagent.langgraph.workflowGeneratorAgents.nodes.sample_input_generator import (
    sample_input_generator_node,
)
from aiagent.langgraph.workflowGeneratorAgents.nodes.self_repair import (
    self_repair_node,
)
from aiagent.langgraph.workflowGeneratorAgents.nodes.validator import validator_node
from aiagent.langgraph.workflowGeneratorAgents.nodes.workflow_tester import (
    workflow_tester_node,
)
from aiagent.langgraph.workflowGeneratorAgents.prompts.workflow_generation import (
    WorkflowGenerationResponse,
)
from aiagent.langgraph.workflowGeneratorAgents.state import WorkflowGeneratorState


@pytest.fixture
def base_state() -> WorkflowGeneratorState:
    """Create base state for testing."""
    return {
        "task_master_id": 123,
        "task_data": {
            "name": "Send email notification",
            "description": "Send email notification to users",
            "input_interface": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "recipient_email": {
                            "type": "string",
                            "example": "user@example.com",
                        },
                        "subject": {"type": "string", "example": "Test Subject"},
                        "body": {"type": "string", "example": "Test Body"},
                    },
                    "required": ["recipient_email", "subject", "body"],
                },
            },
            "output_interface": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "string"},
                        "status": {"type": "string"},
                    },
                    "required": ["message_id", "status"],
                },
            },
        },
        "max_retry": 3,
        "retry_count": 0,
        "status": "initialized",
    }


class TestGeneratorNode:
    """Test generator_node (LLM-based YAML generation)."""

    @pytest.mark.asyncio
    async def test_generator_node_success(self, base_state):
        """Test successful YAML generation without feedback."""
        with patch(
            "aiagent.langgraph.workflowGeneratorAgents.nodes.generator.invoke_structured_llm"
        ) as mock_invoke_llm:
            # Setup mock LLM response
            mock_response = WorkflowGenerationResponse(
                workflow_name="send_email_notification",
                yaml_content="version: 0.5\nnodes:\n  node1: {}\n",
                reasoning="Generated workflow using Gmail API",
            )

            from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
                StructuredCallResult,
            )

            mock_invoke_llm.return_value = StructuredCallResult(
                result=mock_response,
                recovered_via_json=False,
                raw_text=None,
                model_name="test-model",
            )

            # Execute generator node
            result = await generator_node(base_state)

            # Assertions
            assert result["workflow_name"] == "send_email_notification"
            assert "version: 0.5" in result["yaml_content"]
            assert result["status"] == "yaml_generated"
            assert result["generation_retry_count"] == 1

    @pytest.mark.asyncio
    async def test_generator_node_with_feedback(self, base_state):
        """Test YAML regeneration with error feedback."""
        state_with_feedback = {
            **base_state,
            "error_feedback": "Node 'node1' is not defined in available agents",
            "retry_count": 1,
        }

        with patch(
            "aiagent.langgraph.workflowGeneratorAgents.nodes.generator.invoke_structured_llm"
        ) as mock_invoke_llm:
            mock_response = WorkflowGenerationResponse(
                workflow_name="send_email_notification_fixed",
                yaml_content="version: 0.5\nnodes:\n  validNode: {}\n",
                reasoning="Fixed: using valid agent node",
            )

            from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
                StructuredCallResult,
            )

            mock_invoke_llm.return_value = StructuredCallResult(
                result=mock_response,
                recovered_via_json=False,
                raw_text=None,
                model_name="test-model",
            )

            result = await generator_node(state_with_feedback)

            assert result["workflow_name"] == "send_email_notification_fixed"
            assert "validNode" in result["yaml_content"]

    @pytest.mark.asyncio
    async def test_generator_node_llm_error(self, base_state):
        """Test generator node handling LLM API error."""
        with patch(
            "aiagent.langgraph.workflowGeneratorAgents.nodes.generator.invoke_structured_llm"
        ) as mock_invoke_llm:
            from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
                StructuredLLMError,
            )

            mock_invoke_llm.side_effect = StructuredLLMError("LLM API timeout")

            result = await generator_node(base_state)

            assert result["status"] == "failed"
            assert "LLM API timeout" in result["error_message"]


class TestSampleInputGeneratorNode:
    """Test sample_input_generator_node."""

    @pytest.mark.asyncio
    async def test_sample_input_generator_success(self, base_state):
        """Test successful sample input generation from JSON Schema."""
        state_with_yaml = {
            **base_state,
            "yaml_content": "version: 0.5\nnodes: {}",
            "workflow_name": "send_email_notification",
        }

        result = await sample_input_generator_node(state_with_yaml)

        assert result["sample_input"] is not None
        assert "recipient_email" in result["sample_input"]
        assert "subject" in result["sample_input"]
        assert "body" in result["sample_input"]
        assert result["status"] == "sample_input_generated"

    @pytest.mark.asyncio
    async def test_sample_input_generator_with_example(self, base_state):
        """Test sample input generation using schema examples."""
        state_with_yaml = {
            **base_state,
            "yaml_content": "version: 0.5\nnodes: {}",
            "workflow_name": "send_email_notification",
        }

        result = await sample_input_generator_node(state_with_yaml)

        # Should use example values from schema
        assert result["sample_input"]["recipient_email"] == "user@example.com"
        assert result["sample_input"]["subject"] == "Test Subject"
        assert result["sample_input"]["body"] == "Test Body"

    @pytest.mark.asyncio
    async def test_sample_input_generator_no_schema(self, base_state):
        """Test sample input generation with missing schema."""
        state_no_schema = {
            **base_state,
            "yaml_content": "version: 0.5\nnodes: {}",
            "workflow_name": "test_workflow",
        }
        state_no_schema["task_data"]["input_interface"] = {"type": "none"}

        result = await sample_input_generator_node(state_no_schema)

        assert result["sample_input"] == {}
        assert result["status"] == "sample_input_generated"


class TestWorkflowTesterNode:
    """Test workflow_tester_node (graphAiServer integration)."""

    @pytest.mark.asyncio
    async def test_workflow_tester_success(self, base_state):
        """Test successful workflow registration and execution."""
        state_with_sample = {
            **base_state,
            "workflow_name": "send_email_notification",
            "yaml_content": "version: 0.5\nnodes:\n  node1: {}\n",
            "sample_input": {
                "recipient_email": "test@example.com",
                "subject": "Test",
                "body": "Test body",
            },
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            # Mock registration response
            mock_register_response = MagicMock()
            mock_register_response.status_code = 200
            mock_register_response.json.return_value = {
                "file_path": "/workflows/send_email_notification.yaml"
            }
            mock_register_response.text = "Registration successful"

            # Mock execution response
            mock_execute_response = MagicMock()
            mock_execute_response.status_code = 200
            mock_execute_response.json.return_value = {
                "results": {"output": {"message_id": "msg_123", "status": "sent"}},
                "errors": {},
                "logs": [],
            }
            mock_execute_response.text = "Execution successful"

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(
                side_effect=[mock_register_response, mock_execute_response]
            )

            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_client
            mock_context_manager.__aexit__.return_value = None
            mock_client_class.return_value = mock_context_manager

            result = await workflow_tester_node(state_with_sample)

            assert result["workflow_registered"] is True
            assert (
                result["workflow_file_path"]
                == "/workflows/send_email_notification.yaml"
            )
            assert result["test_http_status"] == 200
            assert result["test_execution_result"] is not None
            assert result["status"] == "workflow_tested"

    @pytest.mark.asyncio
    async def test_workflow_tester_registration_failed(self, base_state):
        """Test workflow registration failure."""
        state_with_sample = {
            **base_state,
            "workflow_name": "send_email_notification",
            "yaml_content": "invalid: yaml: content",
            "sample_input": {"recipient_email": "test@example.com"},
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_register_response = MagicMock()
            mock_register_response.status_code = 400
            mock_register_response.json.return_value = {"error": "Invalid YAML"}
            mock_register_response.text = "Invalid YAML syntax"

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_register_response)

            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_client
            mock_context_manager.__aexit__.return_value = None
            mock_client_class.return_value = mock_context_manager

            result = await workflow_tester_node(state_with_sample)

            assert result["workflow_registered"] is False
            assert result["test_http_status"] == 400
            assert result["status"] == "registration_failed"
            assert "Workflow registration failed" in result["error_message"]

    @pytest.mark.asyncio
    async def test_workflow_tester_execution_timeout(self, base_state):
        """Test workflow execution timeout."""
        state_with_sample = {
            **base_state,
            "workflow_name": "send_email_notification",
            "yaml_content": "version: 0.5\nnodes: {}",
            "sample_input": {"recipient_email": "test@example.com"},
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_register_response = MagicMock()
            mock_register_response.status_code = 200
            mock_register_response.json.return_value = {
                "file_path": "/workflows/test.yaml"
            }

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(
                side_effect=[
                    mock_register_response,
                    httpx.TimeoutException("Request timeout"),
                ]
            )

            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_client
            mock_context_manager.__aexit__.return_value = None
            mock_client_class.return_value = mock_context_manager

            result = await workflow_tester_node(state_with_sample)

            assert result["test_http_status"] == 504
            assert result["status"] == "execution_timeout"
            assert "timeout" in result["error_message"].lower()


class TestValidatorNode:
    """Test validator_node (non-LLM validation)."""

    @pytest.mark.asyncio
    async def test_validator_success(self, base_state):
        """Test successful validation (all checks pass)."""
        state_with_test_result = {
            **base_state,
            "yaml_content": "version: 0.5\nnodes:\n  node1: {}\n",
            "test_http_status": 200,
            "test_execution_result": {
                "results": {"output": {"message_id": "msg_123"}},
                "errors": {},
                "logs": [],
            },
        }

        result = await validator_node(state_with_test_result)

        assert result["is_valid"] is True
        assert result["validation_result"]["is_valid"] is True
        assert len(result["validation_result"]["errors"]) == 0
        assert result["status"] == "validated"

    @pytest.mark.asyncio
    async def test_validator_yaml_syntax_error(self, base_state):
        """Test validation failure: YAML syntax error."""
        state_with_invalid_yaml = {
            **base_state,
            "yaml_content": "invalid: yaml: : content",
            "test_http_status": 200,
            "test_execution_result": {"results": {}, "errors": {}, "logs": []},
        }

        result = await validator_node(state_with_invalid_yaml)

        assert result["is_valid"] is False
        assert len(result["validation_errors"]) > 0
        assert any("YAML syntax error" in err for err in result["validation_errors"])
        assert result["status"] == "validation_failed"

    @pytest.mark.asyncio
    async def test_validator_http_error(self, base_state):
        """Test validation failure: HTTP error (non-200)."""
        state_with_http_error = {
            **base_state,
            "yaml_content": "version: 0.5\nnodes: {}",
            "test_http_status": 500,
            "test_execution_result": {
                "error": "Internal server error",
                "errors": {},
                "logs": [],
            },
        }

        result = await validator_node(state_with_http_error)

        assert result["is_valid"] is False
        assert any("HTTP 500" in err for err in result["validation_errors"])

    @pytest.mark.asyncio
    async def test_validator_graphai_errors(self, base_state):
        """Test validation failure: GraphAI execution errors."""
        state_with_graphai_errors = {
            **base_state,
            "yaml_content": "version: 0.5\nnodes: {}",
            "test_http_status": 200,
            "test_execution_result": {
                "results": {},
                "errors": {
                    "node1": {"message": "Node execution failed: timeout"},
                },
                "logs": [],
            },
        }

        result = await validator_node(state_with_graphai_errors)

        assert result["is_valid"] is False
        assert any("node1" in err for err in result["validation_errors"])
        assert any("timeout" in err for err in result["validation_errors"])

    @pytest.mark.asyncio
    async def test_validator_graphai_timeout_logs(self, base_state):
        """Test validation failure: GraphAI timeout in logs."""
        state_with_timeout_logs = {
            **base_state,
            "yaml_content": "version: 0.5\nnodes: {}",
            "test_http_status": 200,
            "test_execution_result": {
                "results": {},
                "errors": {},
                "logs": [
                    {"nodeId": "node1", "state": "timed-out"},
                    {"nodeId": "node2", "state": "completed"},
                ],
            },
        }

        result = await validator_node(state_with_timeout_logs)

        assert result["is_valid"] is False
        assert any(
            "node1" in err and "timed out" in err for err in result["validation_errors"]
        )

    @pytest.mark.asyncio
    async def test_validator_no_results(self, base_state):
        """Test validation failure: workflow produced no results."""
        state_with_no_results = {
            **base_state,
            "yaml_content": "version: 0.5\nnodes: {}",
            "test_http_status": 200,
            "test_execution_result": {
                "results": {},  # Empty results
                "errors": {},
                "logs": [],
            },
        }

        result = await validator_node(state_with_no_results)

        assert result["is_valid"] is False
        assert any("no results" in err for err in result["validation_errors"])


class TestSelfRepairNode:
    """Test self_repair_node (error feedback generation)."""

    @pytest.mark.asyncio
    async def test_self_repair_node_first_retry(self, base_state):
        """Test self-repair node on first retry."""
        state_with_errors = {
            **base_state,
            "workflow_name": "send_email_notification",
            "yaml_content": "version: 0.5\nnodes: {}",
            "is_valid": False,
            "validation_errors": [
                "Node 'invalid_node' error: Agent not found",
                "YAML syntax error: invalid indentation",
            ],
            "retry_count": 0,
        }

        result = await self_repair_node(state_with_errors)

        assert result["retry_count"] == 1
        assert result["error_feedback"] is not None
        assert "invalid_node" in result["error_feedback"]
        assert "YAML syntax error" in result["error_feedback"]
        assert result["status"] == "ready_for_retry"

    @pytest.mark.asyncio
    async def test_self_repair_node_second_retry(self, base_state):
        """Test self-repair node on second retry."""
        state_with_errors = {
            **base_state,
            "workflow_name": "send_email_notification",
            "yaml_content": "version: 0.5\nnodes: {}",
            "is_valid": False,
            "validation_errors": ["Workflow execution failed: HTTP 500"],
            "retry_count": 1,
        }

        result = await self_repair_node(state_with_errors)

        assert result["retry_count"] == 2
        assert "HTTP 500" in result["error_feedback"]

    @pytest.mark.asyncio
    async def test_self_repair_node_multiple_errors(self, base_state):
        """Test self-repair node with multiple validation errors."""
        state_with_multiple_errors = {
            **base_state,
            "workflow_name": "test_workflow",
            "validation_errors": [
                "YAML syntax error",
                "HTTP 500 error",
                "Node 'node1' timeout",
                "Output schema validation failed",
            ],
            "retry_count": 0,
        }

        result = await self_repair_node(state_with_multiple_errors)

        assert result["retry_count"] == 1
        assert all(
            err in result["error_feedback"]
            for err in [
                "YAML syntax error",
                "HTTP 500 error",
                "node1",
                "Output schema",
            ]
        )
