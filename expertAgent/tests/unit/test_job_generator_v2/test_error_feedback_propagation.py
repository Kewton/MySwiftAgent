"""Tests for error feedback propagation through the workflow generation pipeline.

Issue #343 Task 2.4: Test error_feedback parameter propagation.

The error_feedback parameter should flow through:
1. YamlGenerator -> LLMGenerator.generate_from_task()
2. LLMGenerator -> PromptBuilder.build()
3. PromptBuilder -> assembler.assemble_prompt()
4. assembler -> WorkflowPrompt
"""

from typing import Any
from unittest.mock import patch

import pytest


class TestLLMGeneratorErrorFeedback:
    """Test LLMGenerator.generate_from_task() error_feedback parameter."""

    def test_generate_from_task_accepts_error_feedback(self) -> None:
        """Test that generate_from_task accepts error_feedback parameter."""
        import inspect

        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.llm_generator import (
            LLMGeneratorSubWorkflow,
        )

        sig = inspect.signature(LLMGeneratorSubWorkflow.generate_from_task)
        params = list(sig.parameters.keys())

        assert "error_feedback" in params, (
            "generate_from_task should accept error_feedback parameter"
        )

    def test_error_feedback_has_default_empty_string(self) -> None:
        """Test that error_feedback defaults to empty string."""
        import inspect

        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.llm_generator import (
            LLMGeneratorSubWorkflow,
        )

        sig = inspect.signature(LLMGeneratorSubWorkflow.generate_from_task)
        param = sig.parameters.get("error_feedback")

        assert param is not None, "error_feedback parameter should exist"
        assert param.default == "", "error_feedback should default to empty string"


class TestPromptBuilderErrorFeedback:
    """Test PromptBuilder.build() error_feedback parameter."""

    def test_build_accepts_error_feedback(self) -> None:
        """Test that PromptBuilder.build() accepts error_feedback parameter."""
        import inspect

        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder import (
            PromptBuilderSubWorkflow,
        )

        sig = inspect.signature(PromptBuilderSubWorkflow.build)
        params = list(sig.parameters.keys())

        assert "error_feedback" in params, (
            "PromptBuilder.build should accept error_feedback parameter"
        )

    def test_build_error_feedback_has_default(self) -> None:
        """Test that build error_feedback defaults to empty string."""
        import inspect

        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder import (
            PromptBuilderSubWorkflow,
        )

        sig = inspect.signature(PromptBuilderSubWorkflow.build)
        param = sig.parameters.get("error_feedback")

        assert param is not None
        assert param.default == "", "error_feedback should default to empty string"

    def test_build_passes_error_feedback_to_prompt(self) -> None:
        """Test that build passes error_feedback to the WorkflowPrompt."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder import (
            PromptBuilderSubWorkflow,
        )

        builder = PromptBuilderSubWorkflow()
        error_feedback = "## Previous Errors\n- Error 1: timeout issue"

        prompt = builder.build(
            task_name="test_task",
            task_description="Test description",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            error_feedback=error_feedback,
        )

        # The error_feedback should be in the prompt
        assert prompt.error_feedback == error_feedback


class TestAssemblerErrorFeedback:
    """Test assemble_prompt() error_feedback parameter."""

    def test_assemble_prompt_accepts_error_feedback(self) -> None:
        """Test that assemble_prompt accepts error_feedback parameter."""
        import inspect

        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.assembler import (
            assemble_prompt,
        )

        sig = inspect.signature(assemble_prompt)
        params = list(sig.parameters.keys())

        assert "error_feedback" in params, (
            "assemble_prompt should accept error_feedback parameter"
        )

    def test_assemble_prompt_sets_error_feedback(self) -> None:
        """Test that assemble_prompt sets error_feedback in WorkflowPrompt."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.assembler import (
            assemble_prompt,
        )

        error_feedback = "## Errors\n- Fix timeout"

        prompt = assemble_prompt(
            task_name="test",
            task_description="Test",
            input_schema={},
            output_schema={},
            error_feedback=error_feedback,
        )

        assert prompt.error_feedback == error_feedback


class TestWorkflowPromptRender:
    """Test WorkflowPrompt.render() includes error_feedback."""

    def test_render_includes_error_feedback(self) -> None:
        """Test that render() includes error_feedback in output."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.assembler import (
            WorkflowPrompt,
        )

        error_feedback = "## Previous Errors\n- Error 1"
        prompt = WorkflowPrompt(
            system="System prompt",
            rules="Rules",
            api_constraints="API constraints",
            examples=[],
            task_context="Task context",
            error_feedback=error_feedback,
        )

        rendered = prompt.render()

        assert error_feedback in rendered

    def test_render_without_error_feedback(self) -> None:
        """Test that render() works without error_feedback."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.assembler import (
            WorkflowPrompt,
        )

        prompt = WorkflowPrompt(
            system="System prompt",
            rules="Rules",
            api_constraints="API constraints",
            examples=[],
            task_context="Task context",
            error_feedback="",
        )

        rendered = prompt.render()

        # Should render without issues
        assert "Rules" in rendered
        assert "Task context" in rendered


class TestEndToEndPropagation:
    """Test end-to-end error_feedback propagation."""

    @pytest.mark.asyncio
    async def test_error_feedback_reaches_prompt(self) -> None:
        """Test that error_feedback flows from generate_from_task to prompt."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.llm_generator import (
            LLMGeneratorSubWorkflow,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.assembler import (
            WorkflowPrompt,
        )

        error_feedback = "## Previous Errors\n- Timeout in seconds, use milliseconds"

        # Mock the generate method to capture the prompt
        captured_prompt: WorkflowPrompt | None = None

        async def mock_generate(
            self: Any, prompt: WorkflowPrompt, context: Any = None
        ) -> Any:
            nonlocal captured_prompt
            captured_prompt = prompt
            # Return a mock result
            from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.llm_generator import (
                LLMGenerationResult,
            )

            return LLMGenerationResult(
                yaml_content="version: '0.5'\nnodes: {}",
                workflow_name="test",
                model_name="test-model",
                node_count=0,
            )

        generator = LLMGeneratorSubWorkflow()

        with patch.object(LLMGeneratorSubWorkflow, "generate", mock_generate):
            await generator.generate_from_task(
                task_name="test_task",
                task_description="Test",
                input_schema={},
                output_schema={},
                error_feedback=error_feedback,
            )

        assert captured_prompt is not None, "Prompt should be captured"
        assert captured_prompt.error_feedback == error_feedback, (
            "error_feedback should be passed to the prompt"
        )
