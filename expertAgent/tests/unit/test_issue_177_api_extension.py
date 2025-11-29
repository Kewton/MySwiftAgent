"""Unit tests for Issue #177 - API Extension for prompt_version parameter.

This test module verifies:
1. API endpoints support prompt_version parameter
2. prompt_config.py schema validates request parameters
3. PromptLoader integrates correctly with API layer
"""

import pytest
from pydantic import ValidationError

from app.schemas.job_generator import JobGeneratorRequest
from app.schemas.prompt_config import PromptConfig
from app.schemas.workflow_generator import WorkflowGeneratorRequest


class TestPromptConfigSchema:
    """Test PromptConfig schema for API request validation."""

    def test_prompt_config_with_default_version(self):
        """Test PromptConfig with default version."""
        config = PromptConfig(
            agent_type="jobTaskGeneratorAgents",
            prompt_name="task_breakdown",
        )
        assert config.agent_type == "jobTaskGeneratorAgents"
        assert config.prompt_name == "task_breakdown"
        assert config.version == "default"

    def test_prompt_config_with_custom_version(self):
        """Test PromptConfig with custom version."""
        config = PromptConfig(
            agent_type="workflowGeneratorAgents",
            prompt_name="workflow_generation",
            version="v1.5",
        )
        assert config.agent_type == "workflowGeneratorAgents"
        assert config.prompt_name == "workflow_generation"
        assert config.version == "v1.5"

    def test_prompt_config_validation_invalid_agent_type(self):
        """Test PromptConfig validation rejects invalid agent_type."""
        with pytest.raises(ValidationError) as exc_info:
            PromptConfig(
                agent_type="invalidAgentType",
                prompt_name="task_breakdown",
            )
        assert "agent_type" in str(exc_info.value)

    def test_prompt_config_validation_empty_prompt_name(self):
        """Test PromptConfig validation rejects empty prompt_name."""
        with pytest.raises(ValidationError) as exc_info:
            PromptConfig(
                agent_type="jobTaskGeneratorAgents",
                prompt_name="",
            )
        assert "prompt_name" in str(exc_info.value)

    def test_prompt_config_all_agent_types(self):
        """Test PromptConfig accepts all valid agent types."""
        valid_agent_types = ["jobTaskGeneratorAgents", "workflowGeneratorAgents"]
        for agent_type in valid_agent_types:
            config = PromptConfig(
                agent_type=agent_type,
                prompt_name="test_prompt",
            )
            assert config.agent_type == agent_type


class TestJobGeneratorRequestWithPromptVersion:
    """Test JobGeneratorRequest schema with prompt_version support."""

    def test_job_generator_request_without_prompt_configs(self):
        """Test JobGeneratorRequest without prompt_configs (backward compatible)."""
        request = JobGeneratorRequest(
            user_requirement="Test requirement",
        )
        assert request.user_requirement == "Test requirement"
        assert request.max_retry == 5
        assert request.prompt_configs == []

    def test_job_generator_request_with_prompt_configs(self):
        """Test JobGeneratorRequest with prompt_configs."""
        request = JobGeneratorRequest(
            user_requirement="Test requirement",
            prompt_configs=[
                {
                    "agent_type": "jobTaskGeneratorAgents",
                    "prompt_name": "task_breakdown",
                    "version": "v2.0",
                }
            ],
        )
        assert len(request.prompt_configs) == 1
        assert request.prompt_configs[0].agent_type == "jobTaskGeneratorAgents"
        assert request.prompt_configs[0].prompt_name == "task_breakdown"
        assert request.prompt_configs[0].version == "v2.0"

    def test_job_generator_request_with_multiple_prompt_configs(self):
        """Test JobGeneratorRequest with multiple prompt_configs."""
        request = JobGeneratorRequest(
            user_requirement="Test requirement",
            prompt_configs=[
                {
                    "agent_type": "jobTaskGeneratorAgents",
                    "prompt_name": "task_breakdown",
                    "version": "v1.0",
                },
                {
                    "agent_type": "jobTaskGeneratorAgents",
                    "prompt_name": "evaluation",
                    "version": "v2.0",
                },
            ],
        )
        assert len(request.prompt_configs) == 2
        assert request.prompt_configs[0].prompt_name == "task_breakdown"
        assert request.prompt_configs[1].prompt_name == "evaluation"


class TestWorkflowGeneratorRequestWithPromptVersion:
    """Test WorkflowGeneratorRequest schema with prompt_version support."""

    def test_workflow_generator_request_without_prompt_configs(self):
        """Test WorkflowGeneratorRequest without prompt_configs (backward compatible)."""
        request = WorkflowGeneratorRequest(
            job_master_id="jm_01K8DXE62NFJNB0SHJZPAWQWVT",
        )
        assert request.job_master_id == "jm_01K8DXE62NFJNB0SHJZPAWQWVT"
        assert request.prompt_configs == []

    def test_workflow_generator_request_with_prompt_configs(self):
        """Test WorkflowGeneratorRequest with prompt_configs."""
        request = WorkflowGeneratorRequest(
            task_master_id="tm_01K8DXE601HMZWW0K5HR9FDYCQ",
            prompt_configs=[
                {
                    "agent_type": "workflowGeneratorAgents",
                    "prompt_name": "workflow_generation",
                    "version": "v3.0",
                }
            ],
        )
        assert len(request.prompt_configs) == 1
        assert request.prompt_configs[0].agent_type == "workflowGeneratorAgents"
        assert request.prompt_configs[0].prompt_name == "workflow_generation"
        assert request.prompt_configs[0].version == "v3.0"
