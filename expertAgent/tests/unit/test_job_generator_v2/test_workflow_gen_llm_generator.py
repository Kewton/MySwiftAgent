"""Tests for LLMGeneratorSubWorkflow.

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.llm_generator import (
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    MODEL_ENV_VAR,
    TEMPERATURE_ENV_VAR,
    LLMGenerationResult,
    LLMGeneratorSubWorkflow,
    WorkflowYAMLResponse,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder import (
    WorkflowPrompt,
)


class TestLLMGenerationResult:
    """Tests for LLMGenerationResult dataclass."""

    def test_create_result(self):
        """Test creating LLMGenerationResult."""
        result = LLMGenerationResult(
            yaml_content="version: 0.5\nnodes: {}",
            workflow_name="test_workflow",
            model_name="test-model",
            node_count=1,
        )
        assert result.yaml_content == "version: 0.5\nnodes: {}"
        assert result.workflow_name == "test_workflow"
        assert result.model_name == "test-model"
        assert result.node_count == 1

    def test_result_default_node_count(self):
        """Test result default node count is 0."""
        result = LLMGenerationResult(
            yaml_content="",
            workflow_name="test",
            model_name="model",
        )
        assert result.node_count == 0


class TestWorkflowYAMLResponse:
    """Tests for WorkflowYAMLResponse Pydantic model."""

    def test_create_response(self):
        """Test creating WorkflowYAMLResponse."""
        response = WorkflowYAMLResponse(
            yaml_content="version: 0.5\nnodes: {}",
            workflow_name="test",
        )
        assert response.yaml_content == "version: 0.5\nnodes: {}"
        assert response.workflow_name == "test"

    def test_response_default_name(self):
        """Test response default workflow name."""
        response = WorkflowYAMLResponse(yaml_content="test")
        assert response.workflow_name == "generated_workflow"


class TestLLMGeneratorSubWorkflow:
    """Tests for LLMGeneratorSubWorkflow class."""

    def test_create_generator_default(self):
        """Test creating generator with defaults (env vars cleared)."""
        # Clear env vars to test true defaults
        with patch.dict("os.environ", {MODEL_ENV_VAR: "", TEMPERATURE_ENV_VAR: ""}, clear=False):
            import os
            # Remove the env vars if they exist
            os.environ.pop(MODEL_ENV_VAR, None)
            os.environ.pop(TEMPERATURE_ENV_VAR, None)
            generator = LLMGeneratorSubWorkflow()
            assert generator._model == DEFAULT_MODEL
            assert generator._temperature == DEFAULT_TEMPERATURE

    def test_create_generator_custom_model(self):
        """Test creating generator with custom model."""
        generator = LLMGeneratorSubWorkflow(model="custom-model")
        assert generator._model == "custom-model"

    def test_create_generator_custom_temperature(self):
        """Test creating generator with custom temperature."""
        generator = LLMGeneratorSubWorkflow(temperature=0.7)
        assert generator._temperature == 0.7

    def test_create_generator_structured_output_flag(self):
        """Test creating generator with structured output flag."""
        generator = LLMGeneratorSubWorkflow(use_structured_output=False)
        assert generator._use_structured_output is False

    @pytest.mark.asyncio
    async def test_generate_calls_llm(self):
        """Test generate method calls LLM."""
        generator = LLMGeneratorSubWorkflow()

        # Create mock prompt
        prompt = WorkflowPrompt(
            system="System",
            rules="Rules",
            api_constraints="",
            examples=[],
            task_context="Task",
        )

        # Mock the LLM call
        mock_result = MagicMock()
        mock_schema = MagicMock()
        mock_schema.to_yaml.return_value = "version: 0.5\nnodes:\n  source: {}"
        mock_schema.nodes = {"source": {}, "output": {}}
        mock_result.result = mock_schema
        mock_result.model_name = "test-model"

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.llm_generator.invoke_structured_llm",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await generator.generate(prompt)

            assert isinstance(result, LLMGenerationResult)
            assert result.yaml_content == "version: 0.5\nnodes:\n  source: {}"

    @pytest.mark.asyncio
    async def test_generate_raw_mode(self):
        """Test generate method in raw (non-structured) mode."""
        generator = LLMGeneratorSubWorkflow(use_structured_output=False)

        prompt = WorkflowPrompt(
            system="System",
            rules="Rules",
            api_constraints="",
            examples=[],
            task_context="Task",
        )

        # Mock the LLM call
        mock_result = MagicMock()
        mock_result.result = WorkflowYAMLResponse(
            yaml_content="version: '0.5'\nnodes:\n  source: {}\n  output:\n    agent: copyAgent\n    isResult: true",
            workflow_name="raw_workflow",
        )
        mock_result.model_name = "test-model"

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.llm_generator.invoke_structured_llm",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await generator.generate(prompt)

            assert isinstance(result, LLMGenerationResult)
            assert result.workflow_name == "raw_workflow"

    @pytest.mark.asyncio
    async def test_generate_from_task(self):
        """Test generate_from_task convenience method."""
        generator = LLMGeneratorSubWorkflow()

        # Mock the LLM call
        mock_result = MagicMock()
        mock_schema = MagicMock()
        mock_schema.to_yaml.return_value = "version: 0.5\nnodes: {}"
        mock_schema.nodes = {"source": {}}
        mock_result.result = mock_schema
        mock_result.model_name = "test-model"

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.llm_generator.invoke_structured_llm",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await generator.generate_from_task(
                task_name="Test Task",
                task_description="A test task",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            )

            assert isinstance(result, LLMGenerationResult)
