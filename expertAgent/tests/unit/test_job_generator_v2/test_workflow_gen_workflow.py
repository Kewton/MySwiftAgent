"""Tests for WorkflowGenWorkflow.

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aiagent.langgraph.jobGeneratorV2.types import (
    InterfaceSchema,
    PhaseStatus,
    WorkflowGenInput,
    WorkflowGenOutput,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen import (
    WorkflowGenWorkflow,
    YamlGeneratorSubWorkflow,
)


class TestWorkflowGenWorkflow:
    """Tests for WorkflowGenWorkflow class."""

    def test_create_workflow(self):
        """Test creating WorkflowGenWorkflow."""
        workflow = WorkflowGenWorkflow()
        assert workflow is not None

    def test_create_workflow_with_testing(self):
        """Test creating workflow with testing enabled."""
        workflow = WorkflowGenWorkflow(enable_testing=True)
        assert workflow._enable_testing is True

    def test_create_workflow_with_version(self):
        """Test creating workflow with custom version."""
        workflow = WorkflowGenWorkflow(graphai_version="0.5")
        assert workflow._graphai_version == "0.5"

    def test_get_retry_policy(self):
        """Test getting retry policy."""
        workflow = WorkflowGenWorkflow()
        policy = workflow.get_retry_policy()
        assert policy is not None
        assert policy.max_retries > 0

    @pytest.mark.asyncio
    async def test_execute_no_task_masters(self):
        """Test execute with no task masters."""
        workflow = WorkflowGenWorkflow()

        input_data = WorkflowGenInput(
            task_master_ids=[],
            job_master_id="job_1",
            interfaces={},
        )

        mock_context = MagicMock()
        mock_context.job_id = "test_job"

        result = await workflow.execute(input_data, mock_context)

        assert isinstance(result, WorkflowGenOutput)
        assert result.status == PhaseStatus.FAILED
        assert result.workflow_yaml is None

    @pytest.mark.asyncio
    async def test_execute_no_job_master(self):
        """Test execute with no job master."""
        workflow = WorkflowGenWorkflow()

        input_data = WorkflowGenInput(
            task_master_ids=["tm_1"],
            job_master_id="",
            interfaces={},
        )

        mock_context = MagicMock()
        mock_context.job_id = "test_job"

        result = await workflow.execute(input_data, mock_context)

        assert isinstance(result, WorkflowGenOutput)
        assert result.status == PhaseStatus.FAILED

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test execute generates workflow successfully."""
        workflow = WorkflowGenWorkflow()

        input_data = WorkflowGenInput(
            task_master_ids=["tm_task_1", "tm_task_2"],
            job_master_id="job_master_1",
            interfaces={
                "task_1": InterfaceSchema(
                    task_id="task_1",
                    input_schema={"type": "object"},
                    output_schema={"type": "object"},
                ),
            },
        )

        mock_context = MagicMock()
        mock_context.job_id = "test_job"

        result = await workflow.execute(input_data, mock_context)

        assert isinstance(result, WorkflowGenOutput)
        assert result.status == PhaseStatus.SUCCESS
        assert result.workflow_yaml is not None
        assert "version" in result.workflow_yaml


class TestYamlGeneratorSubWorkflow:
    """Tests for YamlGeneratorSubWorkflow class."""

    def test_create_generator(self):
        """Test creating YamlGeneratorSubWorkflow."""
        generator = YamlGeneratorSubWorkflow()
        assert generator is not None

    def test_create_generator_with_version(self):
        """Test creating generator with custom version."""
        generator = YamlGeneratorSubWorkflow(graphai_version="0.5")
        assert generator._graphai_version == "0.5"

    @pytest.mark.asyncio
    async def test_generate_single_task(self):
        """Test generating workflow for single task."""
        generator = YamlGeneratorSubWorkflow()

        mock_context = MagicMock()
        mock_context.job_id = "test_job"

        result = await generator.generate(
            task_master_ids=["tm_task_1"],
            job_master_id="job_1",
            interfaces={},
            context=mock_context,
        )

        assert result.yaml_content
        assert result.node_count >= 1
        assert "version" in result.yaml_content

    @pytest.mark.asyncio
    async def test_generate_multiple_tasks(self):
        """Test generating workflow for multiple tasks."""
        generator = YamlGeneratorSubWorkflow()

        mock_context = MagicMock()
        mock_context.job_id = "test_job"

        result = await generator.generate(
            task_master_ids=["tm_task_1", "tm_task_2", "tm_task_3"],
            job_master_id="job_1",
            interfaces={},
            context=mock_context,
        )

        assert result.yaml_content
        assert result.node_count == 3  # 3 tasks
        assert "task_1" in result.yaml_content
        assert "task_2" in result.yaml_content
        assert "task_3" in result.yaml_content

    @pytest.mark.asyncio
    async def test_generate_workflow_name(self):
        """Test generated workflow has correct name."""
        generator = YamlGeneratorSubWorkflow()

        mock_context = MagicMock()
        mock_context.job_id = "test_job"

        result = await generator.generate(
            task_master_ids=["tm_1"],
            job_master_id="job_master_123",
            interfaces={},
            context=mock_context,
        )

        assert "job_master_123" in result.workflow_name

    @pytest.mark.asyncio
    async def test_generate_first_node_references_source(self):
        """Test first node references source."""
        generator = YamlGeneratorSubWorkflow()

        mock_context = MagicMock()
        mock_context.job_id = "test_job"

        result = await generator.generate(
            task_master_ids=["tm_task_1"],
            job_master_id="job_1",
            interfaces={},
            context=mock_context,
        )

        assert ":source" in result.yaml_content

    @pytest.mark.asyncio
    async def test_generate_last_node_is_result(self):
        """Test last node has isResult."""
        generator = YamlGeneratorSubWorkflow()

        mock_context = MagicMock()
        mock_context.job_id = "test_job"

        result = await generator.generate(
            task_master_ids=["tm_task_1"],
            job_master_id="job_1",
            interfaces={},
            context=mock_context,
        )

        assert "isResult: true" in result.yaml_content


class TestWorkflowGenIntegration:
    """Integration tests for workflow generation."""

    @pytest.mark.asyncio
    async def test_workflow_complete_flow(self):
        """Test complete workflow generation flow."""
        workflow = WorkflowGenWorkflow(enable_testing=False)

        input_data = WorkflowGenInput(
            task_master_ids=["tm_search", "tm_format", "tm_send"],
            job_master_id="job_email_workflow",
            interfaces={
                "search": InterfaceSchema(
                    task_id="search",
                    input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                    output_schema={"type": "object", "properties": {"results": {"type": "array"}}},
                ),
            },
        )

        mock_context = MagicMock()
        mock_context.job_id = "integration_test"

        result = await workflow.execute(input_data, mock_context)

        assert result.status == PhaseStatus.SUCCESS
        assert result.workflow_yaml is not None

        # Verify YAML structure
        yaml_content = result.workflow_yaml
        assert "version:" in yaml_content
        assert "nodes:" in yaml_content
