"""Integration tests for Workflow Generator API."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from aiagent.langgraph.workflowGeneratorAgents.prompts.workflow_generation import (
    WorkflowGenerationResponse,
)
from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_task_data_fetcher():
    """Create mock TaskDataFetcher."""
    fetcher = MagicMock()
    fetcher.fetch_task_master_by_id = AsyncMock()
    fetcher.fetch_task_masters_by_job_master_id = AsyncMock()
    return fetcher


class TestWorkflowGeneratorAPI:
    """Test Workflow Generator API endpoints."""

    def test_workflow_generator_with_task_master_id(
        self, client, mock_task_data_fetcher
    ):
        """Test /v1/workflow-generator with task_master_id."""
        # Setup mock
        mock_task_data_fetcher.fetch_task_master_by_id.return_value = {
            "task_master_id": "456",
            "name": "Send email notification",
            "description": "Send email notification with report",
            "method": "POST",
            "url": "http://localhost:8104/api/v1/utility/gmail_send",
            "input_interface": {
                "id": "input_123",
                "name": "EmailInput",
                "description": "Email input schema",
                "schema": {"type": "object", "properties": {}},
            },
            "output_interface": {
                "id": "output_123",
                "name": "EmailOutput",
                "description": "Email output schema",
                "schema": {"type": "object", "properties": {}},
            },
        }

        with (
            patch(
                "app.api.v1.workflow_generator_endpoints.TaskDataFetcher",
                return_value=mock_task_data_fetcher,
            ),
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.nodes.generator.create_llm"
            ) as mock_create_llm,
            patch("httpx.AsyncClient") as mock_httpx,
        ):
            # Setup LLM mock (create_llm returns a model instance)
            mock_response = MagicMock()
            mock_response.workflow_name = "send_email_notification"
            # Define actual workflow with email_sender node
            mock_response.yaml_content = """version: 0.5
nodes:
  email_sender:
    agent: fetchAgent
    params:
      url: http://localhost:8104/api/v1/utility/gmail_send
      method: POST
    isResult: true
"""
            mock_response.reasoning = "Test"

            mock_structured_model = MagicMock()
            mock_structured_model.ainvoke = AsyncMock(return_value=mock_response)

            mock_llm_instance = MagicMock()
            mock_llm_instance.with_structured_output.return_value = (
                mock_structured_model
            )
            mock_create_llm.return_value = mock_llm_instance

            # Setup httpx mock
            mock_client = AsyncMock()

            def mock_post_responses(*args, **kwargs):
                """Return different responses based on URL."""
                # Registration endpoint
                if "register" in str(args):
                    mock_reg = MagicMock()
                    mock_reg.status_code = 200
                    mock_reg.json.return_value = {"file_path": "/workflows/test.yaml"}
                    return mock_reg

                # Execution endpoint
                mock_exec = MagicMock()
                mock_exec.status_code = 200
                # Return results with actual node name from workflow YAML
                mock_exec.json.return_value = {
                    "results": {
                        "email_sender": {  # Matches node name in YAML
                            "message_id": "msg_123",
                            "status": "sent"
                        }
                    },
                    "errors": {},
                    "logs": [],
                }
                return mock_exec

            mock_client.post = AsyncMock(side_effect=mock_post_responses)
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_client
            mock_context.__aexit__.return_value = None
            mock_httpx.return_value = mock_context

            # Execute
            response = client.post(
                "/aiagent-api/v1/workflow-generator",
                json={"task_master_id": 456},
            )

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["total_tasks"] == 1
            assert data["successful_tasks"] == 1
            assert data["failed_tasks"] == 0
            assert len(data["workflows"]) == 1
            assert data["workflows"][0]["task_master_id"] == 456
            assert data["workflows"][0]["task_name"] == "Send email notification"
            assert data["workflows"][0]["status"] == "success"  # Endpoint maps validated → success
            assert "yaml_content" in data["workflows"][0]

    def test_workflow_generator_with_job_master_id(
        self, client, mock_task_data_fetcher
    ):
        """Test /v1/workflow-generator with job_master_id."""
        # Setup mock
        mock_task_data_fetcher.fetch_task_masters_by_job_master_id.return_value = [
            {
                "task_master_id": "task_1",
                "name": "Generate report",
                "description": "Generate PDF report",
                "method": "POST",
                "url": "http://localhost:8104/api/v1/report/generate",
                "order": 0,
                "input_interface": {
                    "id": "input_1",
                    "name": "ReportInput",
                    "description": "Report input",
                    "schema": {"type": "object"},
                },
                "output_interface": {
                    "id": "output_1",
                    "name": "ReportOutput",
                    "description": "Report output",
                    "schema": {"type": "object"},
                },
            },
            {
                "task_master_id": "task_2",
                "name": "Send email",
                "description": "Send email with report",
                "method": "POST",
                "url": "http://localhost:8104/api/v1/utility/gmail_send",
                "order": 1,
                "input_interface": {
                    "id": "input_2",
                    "name": "EmailInput",
                    "description": "Email input",
                    "schema": {"type": "object"},
                },
                "output_interface": {
                    "id": "output_2",
                    "name": "EmailOutput",
                    "description": "Email output",
                    "schema": {"type": "object"},
                },
            },
        ]

        with (
            patch(
                "app.api.v1.workflow_generator_endpoints.TaskDataFetcher",
                return_value=mock_task_data_fetcher,
            ),
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.nodes.generator.create_llm"
            ) as mock_create_llm,
            patch("httpx.AsyncClient") as mock_httpx,
        ):
            # Setup LLM mock (create_llm returns a model instance)
            mock_response = MagicMock()
            mock_response.workflow_name = "test_workflow"
            # Define actual workflow with task_executor node
            mock_response.yaml_content = """version: 0.5
nodes:
  task_executor:
    agent: fetchAgent
    params:
      url: http://localhost:8104/api/v1/test
      method: POST
    isResult: true
"""
            mock_response.reasoning = "Test"

            mock_structured_model = MagicMock()
            mock_structured_model.ainvoke = AsyncMock(return_value=mock_response)

            mock_llm_instance = MagicMock()
            mock_llm_instance.with_structured_output.return_value = (
                mock_structured_model
            )
            mock_create_llm.return_value = mock_llm_instance

            # Setup httpx mock (handles multiple retries)
            mock_client = AsyncMock()

            def mock_post_responses(*args, **kwargs):
                """Return different responses based on URL."""
                # Registration endpoint
                if "register" in str(args):
                    mock_reg = MagicMock()
                    mock_reg.status_code = 200
                    mock_reg.json.return_value = {"file_path": "/workflows/test.yaml"}
                    return mock_reg

                # Execution endpoint
                mock_exec = MagicMock()
                mock_exec.status_code = 200
                # Return results with actual node name
                mock_exec.json.return_value = {
                    "results": {
                        "task_executor": {  # Matches node name in YAML
                            "result": "success"
                        }
                    },
                    "errors": {},
                    "logs": [],
                }
                return mock_exec

            mock_client.post = AsyncMock(side_effect=mock_post_responses)
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_client
            mock_context.__aexit__.return_value = None
            mock_httpx.return_value = mock_context

            # Execute
            response = client.post(
                "/aiagent-api/v1/workflow-generator",
                json={"job_master_id": 123},
            )

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["total_tasks"] == 2
            assert data["successful_tasks"] == 2
            assert data["failed_tasks"] == 0
            assert len(data["workflows"]) == 2
            assert data["workflows"][0]["task_name"] == "Generate report"
            assert data["workflows"][1]["task_name"] == "Send email"

    def test_workflow_generator_missing_both_ids(self, client):
        """Test /v1/workflow-generator with both IDs missing (422 error)."""
        # Execute
        response = client.post(
            "/aiagent-api/v1/workflow-generator",
            json={},
        )

        # Verify
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_workflow_generator_both_ids_provided(self, client):
        """Test /v1/workflow-generator with both IDs provided (422 error)."""
        # Execute
        response = client.post(
            "/aiagent-api/v1/workflow-generator",
            json={"job_master_id": 123, "task_master_id": 456},
        )

        # Verify
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_workflow_generator_task_not_found(self, client, mock_task_data_fetcher):
        """Test /v1/workflow-generator with non-existent task (404 error)."""
        # Setup mock to raise JobqueueAPIError
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.jobqueue_client import (
            JobqueueAPIError,
        )

        mock_task_data_fetcher.fetch_task_master_by_id.side_effect = JobqueueAPIError(
            status_code=404,
            message="TaskMaster not found",
        )

        with patch(
            "app.api.v1.workflow_generator_endpoints.TaskDataFetcher",
            return_value=mock_task_data_fetcher,
        ):
            # Execute
            response = client.post(
                "/aiagent-api/v1/workflow-generator",
                json={"task_master_id": 999},
            )

            # Verify
            assert response.status_code == 404
            data = response.json()
            assert "detail" in data
            assert "not found" in data["detail"].lower()

    def test_workflow_generator_jobqueue_api_error(
        self, client, mock_task_data_fetcher
    ):
        """Test /v1/workflow-generator with Jobqueue API error (500 error)."""
        # Setup mock to raise JobqueueAPIError
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.jobqueue_client import (
            JobqueueAPIError,
        )

        mock_task_data_fetcher.fetch_task_master_by_id.side_effect = JobqueueAPIError(
            status_code=500,
            message="Internal server error",
        )

        with patch(
            "app.api.v1.workflow_generator_endpoints.TaskDataFetcher",
            return_value=mock_task_data_fetcher,
        ):
            # Execute
            response = client.post(
                "/aiagent-api/v1/workflow-generator",
                json={"task_master_id": 456},
            )

            # Verify
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Jobqueue API error" in data["detail"]


class TestWorkflowGeneratorLangGraphIntegration:
    """Integration tests for LangGraph Agent workflow generation."""

    @pytest.mark.asyncio
    async def test_workflow_generation_with_valid_workflow(
        self, client, mock_task_data_fetcher
    ):
        """Test successful workflow generation with LangGraph Agent."""
        # Setup mock task data
        mock_task_data_fetcher.fetch_task_master_by_id.return_value = {
            "task_master_id": "789",
            "name": "Send notification email",
            "description": "Send email notification to users",
            "method": "POST",
            "url": "http://localhost:8104/api/v1/utility/gmail_send",
            "input_interface": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "example": "user@example.com"},
                        "subject": {"type": "string", "example": "Test Subject"},
                        "body": {"type": "string", "example": "Test Body"},
                    },
                    "required": ["to", "subject", "body"],
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
                },
            },
        }

        # Mock LangGraph Agent nodes to simulate successful workflow
        with (
            patch(
                "app.api.v1.workflow_generator_endpoints.TaskDataFetcher",
                return_value=mock_task_data_fetcher,
            ),
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.nodes.generator.create_llm"
            ) as mock_create_llm,
            patch("httpx.AsyncClient") as mock_httpx_client,
        ):
            # Setup LLM mock (create_llm returns a model instance)
            mock_response = WorkflowGenerationResponse(
                workflow_name="send_notification_email",
                yaml_content="""version: 0.5
nodes:
  email_sender:
    agent: fetchAgent
    params:
      url: http://localhost:8104/api/v1/utility/gmail_send
      method: POST
    isResult: true
""",
                reasoning="Using fetchAgent for Gmail API"
            )

            mock_structured_model = MagicMock()
            mock_structured_model.ainvoke = AsyncMock(return_value=mock_response)

            mock_llm_instance = MagicMock()
            mock_llm_instance.with_structured_output.return_value = (
                mock_structured_model
            )
            mock_create_llm.return_value = mock_llm_instance

            # Setup httpx mock for graphAiServer (handles multiple retries)
            mock_client = AsyncMock()

            # Pre-create mock responses for proper scoping
            mock_register_response = MagicMock()
            mock_register_response.status_code = 200
            mock_register_response.json = MagicMock(return_value={
                "file_path": "/workflows/send_notification_email.yaml"
            })

            mock_execute_response = MagicMock()
            mock_execute_response.status_code = 200
            mock_execute_response.json = MagicMock(return_value={
                "results": {
                    "email_sender": {"message_id": "msg_123", "status": "sent"}
                },
                "errors": {},
                "logs": [],
            })

            def mock_post_responses(*args, **kwargs):
                """Return different responses based on URL."""
                # Registration endpoint
                if "register" in str(args):
                    return mock_register_response
                # Execution endpoint
                return mock_execute_response

            mock_client.post = AsyncMock(side_effect=mock_post_responses)

            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_client
            mock_context_manager.__aexit__.return_value = None
            mock_httpx_client.return_value = mock_context_manager

            # Execute
            response = client.post(
                "/aiagent-api/v1/workflow-generator",
                json={"task_master_id": 789},
            )

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["total_tasks"] == 1
            assert data["successful_tasks"] == 1
            assert data["failed_tasks"] == 0

            workflow = data["workflows"][0]
            assert workflow["task_master_id"] == 789
            assert workflow["task_name"] == "Send notification email"
            assert workflow["workflow_name"] == "send_notification_email"
            assert workflow["status"] == "success"  # Endpoint maps validated → success
            assert workflow["retry_count"] == 0
            assert "version: 0.5" in workflow["yaml_content"]
            assert "email_sender" in workflow["yaml_content"]

    @pytest.mark.asyncio
    async def test_workflow_generation_with_retry(self, client, mock_task_data_fetcher):
        """Test workflow generation with validation failure and retry."""
        # Setup mock task data
        mock_task_data_fetcher.fetch_task_master_by_id.return_value = {
            "task_master_id": "890",
            "name": "Process data",
            "description": "Process data with API",
            "method": "POST",
            "url": "http://localhost:8104/api/v1/data/process",
            "input_interface": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {"data": {"type": "string"}},
                },
            },
            "output_interface": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {"result": {"type": "string"}},
                },
            },
        }

        validation_attempt = 0

        with (
            patch(
                "app.api.v1.workflow_generator_endpoints.TaskDataFetcher",
                return_value=mock_task_data_fetcher,
            ),
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.nodes.generator.create_llm"
            ) as mock_create_llm,
            patch("httpx.AsyncClient") as mock_httpx_client,
        ):
            # Setup LLM mock (create_llm returns a model instance)
            mock_response = MagicMock()
            mock_response.workflow_name = "process_data"
            mock_response.yaml_content = (
                "version: 0.5\nnodes:\n  processor:\n    agent: fetchAgent\n"
            )
            mock_response.reasoning = "Using fetchAgent"

            mock_structured_model = MagicMock()
            mock_structured_model.ainvoke = AsyncMock(return_value=mock_response)

            mock_llm_instance = MagicMock()
            mock_llm_instance.with_structured_output.return_value = (
                mock_structured_model
            )
            mock_create_llm.return_value = mock_llm_instance

            # Setup httpx mock with first attempt failing, second succeeding
            mock_client = AsyncMock()

            def mock_post_side_effect(*args, **kwargs):
                nonlocal validation_attempt
                validation_attempt += 1

                # Registration always succeeds
                if "register" in str(args):
                    mock_reg = MagicMock()
                    mock_reg.status_code = 200
                    mock_reg.json.return_value = {
                        "file_path": "/workflows/process_data.yaml"
                    }
                    return mock_reg

                # First execution fails, second succeeds
                if validation_attempt <= 2:
                    # First attempt: validation error
                    mock_exec = MagicMock()
                    mock_exec.status_code = 200
                    mock_exec.json.return_value = {
                        "results": {},
                        "errors": {"processor": {"message": "Node error"}},
                        "logs": [],
                    }
                    return mock_exec
                else:
                    # Second attempt: success
                    mock_exec = MagicMock()
                    mock_exec.status_code = 200
                    mock_exec.json.return_value = {
                        "results": {"processor": {"result": "processed"}},
                        "errors": {},
                        "logs": [],
                    }
                    return mock_exec

            mock_client.post = AsyncMock(side_effect=mock_post_side_effect)

            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_client
            mock_context_manager.__aexit__.return_value = None
            mock_httpx_client.return_value = mock_context_manager

            # Execute
            response = client.post(
                "/aiagent-api/v1/workflow-generator",
                json={"task_master_id": 890},
            )

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

            workflow = data["workflows"][0]
            assert workflow["status"] == "success"  # Endpoint maps validated → success
            assert workflow["retry_count"] == 1  # One retry was performed

    @pytest.mark.asyncio
    async def test_workflow_generation_max_retries_exceeded(
        self, client, mock_task_data_fetcher
    ):
        """Test workflow generation failing after max retries."""
        # Setup mock task data
        mock_task_data_fetcher.fetch_task_master_by_id.return_value = {
            "task_master_id": "901",
            "name": "Invalid task",
            "description": "Task that always fails",
            "method": "POST",
            "url": "http://localhost:8104/api/v1/invalid",
            "input_interface": {
                "type": "json_schema",
                "schema": {"type": "object"},
            },
            "output_interface": {
                "type": "json_schema",
                "schema": {"type": "object"},
            },
        }

        with (
            patch(
                "app.api.v1.workflow_generator_endpoints.TaskDataFetcher",
                return_value=mock_task_data_fetcher,
            ),
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.nodes.generator.create_llm"
            ) as mock_create_llm,
            patch("httpx.AsyncClient") as mock_httpx_client,
        ):
            # Setup LLM mock (create_llm returns a model instance)
            mock_response = MagicMock()
            mock_response.workflow_name = "invalid_task"
            mock_response.yaml_content = "version: 0.5\nnodes: {}\n"
            mock_response.reasoning = "Basic workflow"

            mock_structured_model = MagicMock()
            mock_structured_model.ainvoke = AsyncMock(return_value=mock_response)

            mock_llm_instance = MagicMock()
            mock_llm_instance.with_structured_output.return_value = (
                mock_structured_model
            )
            mock_create_llm.return_value = mock_llm_instance

            # Setup httpx mock to always fail
            mock_client = AsyncMock()

            def mock_post_always_fail(*args, **kwargs):
                # Registration succeeds
                if "register" in str(args):
                    mock_reg = MagicMock()
                    mock_reg.status_code = 200
                    mock_reg.json.return_value = {
                        "file_path": "/workflows/invalid_task.yaml"
                    }
                    return mock_reg

                # Execution always fails with no results
                mock_exec = MagicMock()
                mock_exec.status_code = 200
                mock_exec.json.return_value = {
                    "results": {},
                    "errors": {},
                    "logs": [],
                }
                return mock_exec

            mock_client.post = AsyncMock(side_effect=mock_post_always_fail)

            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_client
            mock_context_manager.__aexit__.return_value = None
            mock_httpx_client.return_value = mock_context_manager

            # Execute
            response = client.post(
                "/aiagent-api/v1/workflow-generator",
                json={"task_master_id": 901},
            )

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "failed"  # All tasks failed
            assert data["total_tasks"] == 1
            assert data["successful_tasks"] == 0
            assert data["failed_tasks"] == 1

            workflow = data["workflows"][0]
            assert workflow["status"] == "failed"
            assert workflow["retry_count"] == 3  # Max retries reached
            assert workflow["error_message"] is not None
            assert "Max retries exceeded" in workflow["error_message"]

    @pytest.mark.asyncio
    async def test_workflow_generation_multiple_tasks_partial_success(
        self, client, mock_task_data_fetcher
    ):
        """Test workflow generation with multiple tasks - some succeed, some fail."""
        # Setup mock task data
        mock_task_data_fetcher.fetch_task_masters_by_job_master_id.return_value = [
            {
                "task_master_id": "task_success",
                "name": "Successful task",
                "description": "This task succeeds",
                "method": "POST",
                "url": "http://localhost:8104/api/v1/success",
                "order": 0,
                "input_interface": {
                    "type": "json_schema",
                    "schema": {"type": "object"},
                },
                "output_interface": {
                    "type": "json_schema",
                    "schema": {"type": "object"},
                },
            },
            {
                "task_master_id": "task_fail",
                "name": "Failing task",
                "description": "This task fails",
                "method": "POST",
                "url": "http://localhost:8104/api/v1/fail",
                "order": 1,
                "input_interface": {
                    "type": "json_schema",
                    "schema": {"type": "object"},
                },
                "output_interface": {
                    "type": "json_schema",
                    "schema": {"type": "object"},
                },
            },
        ]

        current_task = 0

        with (
            patch(
                "app.api.v1.workflow_generator_endpoints.TaskDataFetcher",
                return_value=mock_task_data_fetcher,
            ),
            patch(
                "aiagent.langgraph.workflowGeneratorAgents.nodes.generator.create_llm"
            ) as mock_create_llm,
            patch("httpx.AsyncClient") as mock_httpx_client,
        ):
            # Setup LLM mock (create_llm returns a model instance)
            mock_response = WorkflowGenerationResponse(
                workflow_name="test_workflow",
                yaml_content="version: 0.5\nnodes:\n  node1:\n    agent: fetchAgent\n",
                reasoning="Test"
            )

            mock_structured_model = MagicMock()
            mock_structured_model.ainvoke = AsyncMock(return_value=mock_response)

            mock_llm_instance = MagicMock()
            mock_llm_instance.with_structured_output.return_value = (
                mock_structured_model
            )
            mock_create_llm.return_value = mock_llm_instance

            # Setup httpx mock
            mock_client = AsyncMock()

            def mock_post_mixed_results(*args, **kwargs):
                nonlocal current_task

                # Registration always succeeds
                if "register" in str(args):
                    mock_reg = MagicMock()
                    mock_reg.status_code = 200
                    mock_reg.json.return_value = {"file_path": "/workflows/test.yaml"}
                    return mock_reg

                # First task succeeds, second task fails
                if current_task == 0:
                    current_task += 1
                    mock_exec = MagicMock()
                    mock_exec.status_code = 200
                    mock_exec.json.return_value = {
                        "results": {"node1": {"result": "ok"}},
                        "errors": {},
                        "logs": [],
                    }
                    return mock_exec
                else:
                    # Second task always fails (no results)
                    mock_exec = MagicMock()
                    mock_exec.status_code = 200
                    mock_exec.json.return_value = {
                        "results": {},
                        "errors": {},
                        "logs": [],
                    }
                    return mock_exec

            mock_client.post = AsyncMock(side_effect=mock_post_mixed_results)

            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_client
            mock_context_manager.__aexit__.return_value = None
            mock_httpx_client.return_value = mock_context_manager

            # Execute
            response = client.post(
                "/aiagent-api/v1/workflow-generator",
                json={"job_master_id": 456},
            )

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "partial_success"
            assert data["total_tasks"] == 2
            assert data["successful_tasks"] == 1
            assert data["failed_tasks"] == 1

            # First workflow succeeds
            assert data["workflows"][0]["status"] == "success"  # Endpoint maps validated → success
            assert data["workflows"][0]["task_name"] == "Successful task"

            # Second workflow fails
            assert data["workflows"][1]["status"] == "failed"
            assert data["workflows"][1]["task_name"] == "Failing task"
