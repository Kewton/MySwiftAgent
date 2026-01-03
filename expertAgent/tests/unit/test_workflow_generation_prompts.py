"""Unit tests for workflow generation prompts (Issue #333).

Tests for TYPE_VALIDATION_RULES constant and its integration into
the workflow generation prompt.
"""

from aiagent.langgraph.workflowGeneratorAgents.prompts.workflow_generation import (
    EXPERTAGENT_API_URL,
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

    def test_contains_object_to_string_handling_example(self):
        """TYPE_VALIDATION_RULES should contain example of Object to String handling."""
        # Should have examples showing how to handle Object type data for LLM prompts
        # Check for the pattern examples in the rules
        assert "stringTemplateAgent" in TYPE_VALIDATION_RULES
        # Should explain correct usage pattern
        assert "inputs:" in TYPE_VALIDATION_RULES
        assert "template:" in TYPE_VALIDATION_RULES

    def test_contains_reference_syntax_explanation(self):
        """TYPE_VALIDATION_RULES should explain :previous_node reference syntax."""
        assert (
            ":previous_node" in TYPE_VALIDATION_RULES
            or ":node" in TYPE_VALIDATION_RULES
        )

    def test_contains_capability_reference(self):
        """TYPE_VALIDATION_RULES should reference capabilities.yaml."""
        assert "capabilities" in TYPE_VALIDATION_RULES.lower()

    def test_contains_string_template_agent_limitations(self):
        """TYPE_VALIDATION_RULES should document stringTemplateAgent limitations."""
        # Should clearly state that JS functions don't work
        assert (
            "JavaScript" in TYPE_VALIDATION_RULES
            or "javascript" in TYPE_VALIDATION_RULES.lower()
        )
        # Should prohibit JSON.stringify usage
        assert "JSON.stringify" in TYPE_VALIDATION_RULES

    def test_contains_correct_syntax_examples(self):
        """TYPE_VALIDATION_RULES should show correct ${variable} syntax."""
        # Should have examples of correct simple variable syntax
        assert "${" in TYPE_VALIDATION_RULES
        # Should explain that only simple substitution works
        assert (
            "variable" in TYPE_VALIDATION_RULES.lower()
            or "変数" in TYPE_VALIDATION_RULES
        )

    def test_contains_reference_syntax_location_rule(self):
        """TYPE_VALIDATION_RULES should document where :reference syntax works."""
        # Should explain that :reference only works in inputs: block
        assert "inputs" in TYPE_VALIDATION_RULES.lower()
        # Should warn about string literals
        assert (
            "文字列" in TYPE_VALIDATION_RULES
            or "string" in TYPE_VALIDATION_RULES.lower()
        )
        # Should have the mandatory rule
        assert "MANDATORY" in TYPE_VALIDATION_RULES or "必須" in TYPE_VALIDATION_RULES


class TestArrayTypeConstraints:
    """Tests for array type constraints in TYPE_VALIDATION_RULES (Issue #340)."""

    def test_type_validation_rules_contains_array_constraint(self):
        """TYPE_VALIDATION_RULES should contain array type constraint warning.

        Issue #340: stringTemplateAgent converts object arrays to [object Object].
        The prompt should warn about this limitation.
        """
        # Should mention array type constraints
        assert (
            "配列" in TYPE_VALIDATION_RULES or "array" in TYPE_VALIDATION_RULES.lower()
        )

    def test_type_validation_rules_mentions_object_object(self):
        """TYPE_VALIDATION_RULES should mention [object Object] issue."""
        # Should warn about [object Object] conversion
        assert "[object Object]" in TYPE_VALIDATION_RULES

    def test_type_validation_rules_mentions_primitive_types(self):
        """TYPE_VALIDATION_RULES should recommend primitive types for arrays."""
        # Should mention that arrays should contain primitive types
        assert (
            "プリミティブ" in TYPE_VALIDATION_RULES
            or "primitive" in TYPE_VALIDATION_RULES.lower()
            or "string" in TYPE_VALIDATION_RULES.lower()
        )


class TestApiUrlConfiguration:
    """Tests for API URL configuration (Issue #333 fix)."""

    def test_expertagent_api_url_has_no_aiagent_api_prefix(self):
        """EXPERTAGENT_API_URL should NOT contain /aiagent-api prefix.

        The correct path is /v1/aiagent/utility/jsonoutput, not
        /aiagent-api/v1/aiagent/utility/jsonoutput.
        """
        assert "/aiagent-api/" not in EXPERTAGENT_API_URL
        # Should contain the correct path
        assert "/v1/aiagent/utility/jsonoutput" in EXPERTAGENT_API_URL

    def test_expertagent_api_url_format(self):
        """EXPERTAGENT_API_URL should have correct format."""
        # Should end with the endpoint path
        assert EXPERTAGENT_API_URL.endswith("/v1/aiagent/utility/jsonoutput")

    def test_create_prompt_does_not_include_aiagent_api_prefix(self):
        """Generated prompt should not contain /aiagent-api prefix in URLs."""
        task_data = {
            "name": "Test Task",
            "description": "Test description **推奨API**: google_search",
            "input_interface": {"type": "json_schema", "schema": {}},
            "output_interface": {"type": "json_schema", "schema": {}},
        }
        graphai_capabilities = {"agents": []}
        expert_agent_capabilities = {"utility_apis": [], "ai_agent_apis": []}

        prompt = create_workflow_generation_prompt(
            task_data, graphai_capabilities, expert_agent_capabilities
        )

        # The prompt should not contain the incorrect prefix
        assert "/aiagent-api/v1/" not in prompt
