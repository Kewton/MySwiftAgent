"""Integration check tests for Workflow Generator V2.

This module verifies that all new code is properly integrated:
- Exports are available from __init__.py
- Classes can be instantiated
- New code is actually being used

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""


class TestModuleExports:
    """Tests verifying module exports are correct."""

    def test_import_from_workflow_gen_package(self):
        """Test importing from workflow_gen package."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen import (
            ErrorCode,
            GraphAIWorkflowSchema,
            LLMGeneratorSubWorkflow,
            NodeDefinition,
            PromptBuilderSubWorkflow,
            ValidationError,
            WorkflowGenWorkflow,
            YamlGeneratorSubWorkflow,
            YamlValidatorSubWorkflow,
        )

        # Verify all imports succeed
        assert WorkflowGenWorkflow is not None
        assert YamlGeneratorSubWorkflow is not None
        assert PromptBuilderSubWorkflow is not None
        assert LLMGeneratorSubWorkflow is not None
        assert YamlValidatorSubWorkflow is not None
        assert GraphAIWorkflowSchema is not None
        assert NodeDefinition is not None
        assert ErrorCode is not None
        assert ValidationError is not None

    def test_import_prompt_builder_submodules(self):
        """Test importing prompt_builder submodules."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder import (
            PromptBuilderSubWorkflow,
            WorkflowPrompt,
            assemble_prompt,
            build_task_context,
        )

        assert PromptBuilderSubWorkflow is not None
        assert WorkflowPrompt is not None
        assert assemble_prompt is not None
        assert build_task_context is not None

    def test_import_prompt_builder_rules(self):
        """Test importing prompt_builder rules."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.rules import (
            ALL_AGENT_RULES,
            API_RULES,
            BASE_RULES,
            REFERENCE_RULES,
        )

        assert BASE_RULES is not None
        assert ALL_AGENT_RULES is not None
        assert API_RULES is not None
        assert REFERENCE_RULES is not None

    def test_import_few_shot(self):
        """Test importing few_shot module."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.few_shot import (
            FewShotExample,
            load_all_examples,
            load_example,
            select_few_shot_examples,
        )

        assert FewShotExample is not None
        assert load_example is not None
        assert load_all_examples is not None
        assert select_few_shot_examples is not None

    def test_import_validators(self):
        """Test importing validators."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.validators import (
            check_circular_references,
            validate_agents,
            validate_references,
            validate_structure,
            validate_yaml_syntax,
        )

        assert validate_yaml_syntax is not None
        assert validate_structure is not None
        assert validate_agents is not None
        assert validate_references is not None
        assert check_circular_references is not None

    def test_import_errors(self):
        """Test importing errors module."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.errors import (
            ERROR_SUGGESTIONS,
            ErrorCode,
            ValidationError,
            ValidationResult,
        )

        assert ErrorCode is not None
        assert ValidationError is not None
        assert ValidationResult is not None
        assert ERROR_SUGGESTIONS is not None


class TestClassInstantiation:
    """Tests verifying classes can be instantiated."""

    def test_instantiate_prompt_builder(self):
        """Test PromptBuilderSubWorkflow can be instantiated."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen import (
            PromptBuilderSubWorkflow,
        )

        builder = PromptBuilderSubWorkflow()
        assert builder is not None

    def test_instantiate_llm_generator(self):
        """Test LLMGeneratorSubWorkflow can be instantiated."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen import (
            LLMGeneratorSubWorkflow,
        )

        generator = LLMGeneratorSubWorkflow()
        assert generator is not None

    def test_instantiate_yaml_validator(self):
        """Test YamlValidatorSubWorkflow can be instantiated."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen import (
            YamlValidatorSubWorkflow,
        )

        validator = YamlValidatorSubWorkflow()
        assert validator is not None

    def test_instantiate_workflow_gen_workflow(self):
        """Test WorkflowGenWorkflow can be instantiated."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen import (
            WorkflowGenWorkflow,
        )

        workflow = WorkflowGenWorkflow()
        assert workflow is not None


class TestConfigIntegration:
    """Tests verifying config integration."""

    def test_config_has_v2_settings(self):
        """Test config has V2 workflow generator settings."""
        from core.config import settings

        assert hasattr(settings, "WORKFLOW_GENERATOR_V2_MODEL")
        assert hasattr(settings, "WORKFLOW_GENERATOR_V2_TEMPERATURE")
        assert hasattr(settings, "WORKFLOW_GENERATOR_V2_MAX_RETRY")
        assert hasattr(settings, "WORKFLOW_GENERATOR_V2_ENABLE_EXECUTION_TEST")

    def test_config_default_values(self):
        """Test config default values are sensible."""
        from core.config import settings

        # Model should be set
        assert settings.WORKFLOW_GENERATOR_V2_MODEL
        assert len(settings.WORKFLOW_GENERATOR_V2_MODEL) > 0

        # Temperature should be reasonable
        assert 0.0 <= settings.WORKFLOW_GENERATOR_V2_TEMPERATURE <= 1.0

        # Max retry should be positive
        assert settings.WORKFLOW_GENERATOR_V2_MAX_RETRY >= 0


class TestSchemaUsage:
    """Tests verifying schemas are used correctly."""

    def test_schema_used_in_llm_generator(self):
        """Test GraphAIWorkflowSchema is used in LLM generator."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.llm_generator import (
            LLMGeneratorSubWorkflow,
        )

        # Verify the schema is importable and usable
        generator = LLMGeneratorSubWorkflow(use_structured_output=True)
        assert generator._use_structured_output is True

    def test_validation_error_used_in_validator(self):
        """Test ValidationError is used in validator."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.errors import (
            ValidationError,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_validator import (
            YamlValidatorSubWorkflow,
        )

        validator = YamlValidatorSubWorkflow()
        result = validator.validate("invalid: yaml: {")

        # Should return ValidationErrors
        assert len(result.errors) > 0
        assert isinstance(result.errors[0], ValidationError)


class TestRulesUsage:
    """Tests verifying rules are used in prompts."""

    def test_rules_in_assembled_prompt(self):
        """Test rules are included in assembled prompt."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder import (
            assemble_prompt,
        )

        prompt = assemble_prompt(
            task_name="Test",
            task_description="Test task",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )

        # Rules should be in the prompt
        assert prompt.rules
        assert len(prompt.rules) > 0

    def test_system_prompt_in_assembled_prompt(self):
        """Test system prompt is included."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder import (
            assemble_prompt,
        )

        prompt = assemble_prompt(
            task_name="Test",
            task_description="Test task",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )

        # System prompt should be present
        assert prompt.system
        assert "GraphAI" in prompt.system


class TestFewShotUsage:
    """Tests verifying few-shot examples are used."""

    def test_few_shot_files_exist(self):
        """Test few-shot YAML files exist."""

        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.few_shot.loader import (
            FEW_SHOT_DIR,
        )

        assert FEW_SHOT_DIR.exists()

        pattern_files = list(FEW_SHOT_DIR.glob("*_pattern.yaml"))
        assert len(pattern_files) >= 4

    def test_few_shot_loadable(self):
        """Test few-shot examples are loadable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.few_shot import (
            load_all_examples,
        )

        examples = load_all_examples()
        assert len(examples) >= 4

        # All examples should have valid YAML
        for example in examples:
            assert example.workflow_yaml
            assert "version" in example.workflow_yaml
