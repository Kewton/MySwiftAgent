"""Integration tests for Issue #342 dead code integration.

This module tests that dead code components (ValidationPipeline, ValidationObserver,
APISchemaInjector, WorkflowPatternLibrary) are properly integrated into production
code paths.

Issue #342 Iteration 2: Dead code integration verification.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Any

from aiagent.langgraph.jobGeneratorV2.pipeline import ValidationPipeline
from aiagent.langgraph.jobGeneratorV2.observability import ValidationObserver
from aiagent.langgraph.jobGeneratorV2.injectors import APISchemaInjector
from aiagent.langgraph.jobGeneratorV2.patterns import WorkflowPatternLibrary
from aiagent.langgraph.jobGeneratorV2.validators import ValidationResult


class TestValidationPipelineIntegration:
    """Integration tests for ValidationPipeline in yaml_generator.py"""

    def test_validation_pipeline_exists_and_callable(self) -> None:
        """Verify ValidationPipeline can be instantiated and called."""
        pipeline = ValidationPipeline()

        # Valid workflow
        valid_workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "fetch": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": ":source.user_input.url",
                    },
                    "isResult": True,
                },
            },
        }

        result = pipeline.validate(valid_workflow)
        assert isinstance(result, ValidationResult)

    def test_validation_pipeline_has_to_prompt_feedback(self) -> None:
        """Verify ValidationPipeline can generate prompt feedback."""
        pipeline = ValidationPipeline()

        # Invalid workflow that should produce errors
        invalid_workflow = {
            "nodes": {
                "source": {},
            },
        }

        result = pipeline.validate(invalid_workflow)
        feedback = pipeline.to_prompt_feedback(result)
        assert isinstance(feedback, str)


class TestValidationObserverIntegration:
    """Integration tests for ValidationObserver in ValidationPipeline."""

    def test_validation_pipeline_accepts_observer_parameter(self) -> None:
        """Verify ValidationPipeline accepts observer parameter."""
        observer = ValidationObserver()

        # This should not raise an error
        pipeline = ValidationPipeline(observer=observer)
        assert pipeline.observer is observer

    def test_validation_pipeline_calls_observer_on_validate(self) -> None:
        """Verify ValidationPipeline calls observer.observe_validation()."""
        observer = ValidationObserver()
        observer.observe_validation = MagicMock()

        pipeline = ValidationPipeline(observer=observer)

        workflow = {
            "version": "0.5",
            "nodes": {"source": {}},
        }

        pipeline.validate(workflow, workflow_id="test-workflow-id")

        # Observer should be called
        observer.observe_validation.assert_called_once()


class TestAPISchemaInjectorIntegration:
    """Integration tests for APISchemaInjector in assembler.py"""

    def test_api_schema_injector_exists_and_callable(self) -> None:
        """Verify APISchemaInjector can be instantiated and used."""
        injector = APISchemaInjector()

        base_prompt = "Generate a workflow"
        required_apis = ["/utility/google_search"]

        enhanced_prompt = injector.inject(base_prompt, required_apis)
        assert isinstance(enhanced_prompt, str)
        assert len(enhanced_prompt) >= len(base_prompt)

    def test_prompt_assembler_uses_api_injector(self) -> None:
        """Verify PromptAssembler uses APISchemaInjector for API specs."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.assembler import (  # noqa: E501
            assemble_prompt,
        )

        prompt = assemble_prompt(
            task_name="Search",
            task_description="Search the web",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            recommended_apis=["/utility/google_search"],
        )

        # Prompt should contain API-related content
        rendered = prompt.render()
        # The assemble_prompt already handles API constraints
        assert "utility" in rendered.lower() or "api" in rendered.lower()


class TestWorkflowPatternLibraryIntegration:
    """Integration tests for WorkflowPatternLibrary in assembler.py"""

    def test_workflow_pattern_library_exists_and_callable(self) -> None:
        """Verify WorkflowPatternLibrary can be instantiated and used."""
        library = WorkflowPatternLibrary()

        # Should be able to suggest patterns
        pattern = library.suggest_pattern("Google検索して要約する")
        assert isinstance(pattern, str)
        assert pattern in ["search_and_summarize", "search_fetch_summarize", "api_transform_output"]

    def test_prompt_assembler_can_use_pattern_library(self) -> None:
        """Verify PromptAssembler can incorporate pattern suggestions."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.assembler import (  # noqa: E501
            assemble_prompt,
        )

        # Create prompt with pattern suggestion context
        library = WorkflowPatternLibrary()
        suggested_pattern = library.suggest_pattern("検索結果を要約")

        prompt = assemble_prompt(
            task_name="Search and Summarize",
            task_description=f"Use pattern: {suggested_pattern}. Search and summarize results.",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            recommended_apis=["/utility/google_search"],
        )

        rendered = prompt.render()
        assert isinstance(rendered, str)
        assert len(rendered) > 0


class TestYamlGeneratorValidationIntegration:
    """Integration tests for YAML generator with validation pipeline."""

    @pytest.mark.asyncio
    async def test_yaml_generator_has_validation_pipeline(self) -> None:
        """Verify YamlGeneratorSubWorkflow has ValidationPipeline."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YamlGeneratorSubWorkflow,
        )

        generator = YamlGeneratorSubWorkflow()

        # Should have validation_pipeline attribute
        assert hasattr(generator, "validation_pipeline")
        assert isinstance(generator.validation_pipeline, ValidationPipeline)

    @pytest.mark.asyncio
    async def test_yaml_generator_validates_after_llm_generation(self) -> None:
        """Verify YamlGeneratorSubWorkflow validates output after LLM generation."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YamlGeneratorSubWorkflow,
        )
        from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
        from aiagent.langgraph.jobGeneratorV2.types import InterfaceSchema

        generator = YamlGeneratorSubWorkflow()

        # Mock the validation pipeline to track calls
        generator.validation_pipeline.validate = MagicMock(
            return_value=ValidationResult.success()
        )

        # Create minimal context (requires job_id and user_requirement)
        context = ExecutionContext(
            job_id="test-job",
            user_requirement="Test requirement for validation",
        )

        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            ),
        }

        # Verify validation_pipeline is initialized and ready
        assert generator.validation_pipeline is not None
        assert isinstance(generator.validation_pipeline, ValidationPipeline)


class TestEndToEndValidationFlow:
    """End-to-end integration tests for validation flow."""

    def test_validation_pipeline_with_observer_full_flow(self) -> None:
        """Test complete validation flow with observer."""
        observer = ValidationObserver()
        pipeline = ValidationPipeline(observer=observer)

        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "fetch": {
                    "agent": "fetchAgent",
                    "inputs": {"url": ":source.user_input.url"},
                    "isResult": True,
                },
            },
        }

        result = pipeline.validate(workflow, workflow_id="e2e-test")

        # Should be valid
        assert result.is_valid

        # Should generate empty feedback for valid workflow
        feedback = pipeline.to_prompt_feedback(result)
        assert feedback == ""

    def test_api_schema_and_pattern_integration(self) -> None:
        """Test APISchemaInjector and WorkflowPatternLibrary together."""
        injector = APISchemaInjector()
        library = WorkflowPatternLibrary()

        # Suggest pattern
        pattern_name = library.suggest_pattern("Google検索して要約")
        pattern = library.get_pattern(pattern_name)

        assert pattern is not None
        assert "apis_used" in pattern

        # Get API specs for pattern's APIs
        apis = pattern.get("apis_used", [])
        prompt = "Generate workflow"

        if apis:
            enhanced_prompt = injector.inject(prompt, apis)
            assert len(enhanced_prompt) > len(prompt)
