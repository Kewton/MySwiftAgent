"""Unit tests for workflow generation prompts (Issue #333).

Tests for TYPE_VALIDATION_RULES constant and its integration into
the workflow generation prompt.
"""

from aiagent.langgraph.workflowGeneratorAgents.prompts.workflow_generation import (
    TYPE_VALIDATION_RULES,
    WORKFLOW_GENERATION_SYSTEM_PROMPT,
    create_workflow_generation_prompt,
)


class TestTypeValidationRules:
    """Tests for TYPE_VALIDATION_RULES constant."""

    def test_type_validation_rules_exists(self):
        """TYPE_VALIDATION_RULES constant should exist."""
        assert TYPE_VALIDATION_RULES is not None
        assert isinstance(TYPE_VALIDATION_RULES, str)
        assert len(TYPE_VALIDATION_RULES) > 0

    def test_type_validation_rules_contains_fetch_agent_type_info(self):
        """TYPE_VALIDATION_RULES should explain fetchAgent output type."""
        assert "fetchAgent" in TYPE_VALIDATION_RULES
        assert "Object" in TYPE_VALIDATION_RULES or "object" in TYPE_VALIDATION_RULES

    def test_type_validation_rules_contains_user_input_type_info(self):
        """TYPE_VALIDATION_RULES should explain user_input expected type."""
        assert "user_input" in TYPE_VALIDATION_RULES
        assert "String" in TYPE_VALIDATION_RULES or "string" in TYPE_VALIDATION_RULES

    def test_type_validation_rules_contains_string_template_agent_pattern(self):
        """TYPE_VALIDATION_RULES should explain stringTemplateAgent conversion pattern."""
        assert "stringTemplateAgent" in TYPE_VALIDATION_RULES

    def test_type_validation_rules_contains_field_name_validation(self):
        """TYPE_VALIDATION_RULES should mention field name validation."""
        assert "system_prompt" in TYPE_VALIDATION_RULES

    def test_type_validation_rules_contains_json_stringify_pattern(self):
        """TYPE_VALIDATION_RULES should mention JSON.stringify pattern."""
        assert "JSON.stringify" in TYPE_VALIDATION_RULES


class TestPromptIntegration:
    """Tests for TYPE_VALIDATION_RULES integration into prompts."""

    def test_system_prompt_contains_type_validation_rules(self):
        """WORKFLOW_GENERATION_SYSTEM_PROMPT should contain type validation rules."""
        # Type validation rules should be present in the system prompt
        assert "fetchAgent" in WORKFLOW_GENERATION_SYSTEM_PROMPT
        assert "user_input" in WORKFLOW_GENERATION_SYSTEM_PROMPT

    def test_create_workflow_generation_prompt_includes_validation_rules(self):
        """create_workflow_generation_prompt should include type validation info."""
        task_data = {
            "name": "Test Task",
            "description": "Test description",
            "input_interface": {"type": "json_schema", "schema": {}},
            "output_interface": {"type": "json_schema", "schema": {}},
        }
        graphai_capabilities = {"agents": []}
        expert_agent_capabilities = {"utility_apis": [], "ai_agent_apis": []}

        prompt = create_workflow_generation_prompt(
            task_data, graphai_capabilities, expert_agent_capabilities
        )

        # The prompt should contain references to validation rules
        assert "fetchAgent" in prompt or "user_input" in prompt


class TestTypeValidationRulesContent:
    """Detailed tests for TYPE_VALIDATION_RULES content quality."""

    def test_contains_object_to_string_conversion_example(self):
        """TYPE_VALIDATION_RULES should contain example of Object to String conversion."""
        # Should have an example showing how to convert Object to String
        assert "convert" in TYPE_VALIDATION_RULES.lower()

    def test_contains_reference_syntax_explanation(self):
        """TYPE_VALIDATION_RULES should explain :previous_node reference syntax."""
        assert (
            ":previous_node" in TYPE_VALIDATION_RULES
            or ":node" in TYPE_VALIDATION_RULES
        )

    def test_contains_capability_reference(self):
        """TYPE_VALIDATION_RULES should reference capabilities.yaml."""
        assert "capabilities" in TYPE_VALIDATION_RULES.lower()
