"""Unit tests for YAML Generator output node naming rule.

Issue #342 Phase 1: Tests for output node naming rule.
- Final output node must be named 'output'
- This ensures Worker can correctly find the result node
"""

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.rules import (
    BASE_RULES,
    get_base_rules,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.rules.base_rules import (
    OUTPUT_NODE_RULE,
)


class TestOutputNodeNamingRule:
    """Tests for output node naming rule in prompts."""

    def test_output_node_rule_constant_exists(self) -> None:
        """Verify OUTPUT_NODE_RULE constant exists with correct content.

        This rule ensures LLM generates workflows where the final output
        node is named 'output', which is required for Worker compatibility.
        """
        assert OUTPUT_NODE_RULE is not None
        assert len(OUTPUT_NODE_RULE) > 0, "OUTPUT_NODE_RULE should not be empty"

    def test_output_node_rule_mentions_output_name(self) -> None:
        """OUTPUT_NODE_RULE should specify that output node must be named 'output'.

        The rule should clearly state that the final output node must be
        named 'output' (not 'format_output', 'result', etc.).
        """
        # Should mention the required name 'output'
        assert "output" in OUTPUT_NODE_RULE.lower(), (
            "OUTPUT_NODE_RULE should mention 'output' as required node name"
        )

    def test_base_rules_includes_output_node_rule(self) -> None:
        """BASE_RULES should include the output node naming rule.

        The base rules string should contain instructions about naming
        the final output node as 'output'.
        """
        # Check BASE_RULES contains output node naming instruction
        assert "output" in BASE_RULES.lower(), (
            "BASE_RULES should include output node naming rule"
        )

        # Should specifically mention naming convention
        # Look for phrases like "named output" or "name: output" or "node name"
        lower_rules = BASE_RULES.lower()
        has_naming_instruction = (
            "named `output`" in lower_rules
            or "name must be" in lower_rules
            or "output node" in lower_rules
            or "named output" in lower_rules
        )
        assert has_naming_instruction, (
            "BASE_RULES should have explicit output node naming instruction"
        )

    def test_get_base_rules_returns_output_node_rule(self) -> None:
        """get_base_rules() should return rules containing output node naming."""
        rules = get_base_rules()

        # Should include output node naming instruction
        assert "output" in rules.lower()

        # Should mention that final/result node should be named 'output'
        lower_rules = rules.lower()
        has_output_naming = "output" in lower_rules and (
            "final" in lower_rules or "result" in lower_rules or "last" in lower_rules
        )
        assert has_output_naming, (
            "get_base_rules() should mention output naming for final/result node"
        )

    def test_output_node_rule_content_clarity(self) -> None:
        """OUTPUT_NODE_RULE should have clear, actionable content for LLM.

        The rule should:
        1. Be clear about what to name the output node
        2. Explain why (Worker compatibility)
        3. Give examples of what NOT to do
        """
        # Check that the rule is substantial enough to guide LLM
        assert len(OUTPUT_NODE_RULE) > 50, (
            "OUTPUT_NODE_RULE should have substantial content for LLM guidance"
        )

        # Should mention the exact required name
        assert "`output`" in OUTPUT_NODE_RULE or "'output'" in OUTPUT_NODE_RULE, (
            "OUTPUT_NODE_RULE should explicitly show the required name 'output'"
        )


class TestOutputNodeRuleIntegration:
    """Integration tests verifying output node rule is in assembled prompts."""

    def test_output_node_rule_in_assembled_prompt(self) -> None:
        """Verify output node rule appears in fully assembled prompts.

        The rule should be included when prompts are assembled for LLM.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder import (
            PromptBuilderSubWorkflow,
        )

        builder = PromptBuilderSubWorkflow()
        prompt = builder.build(
            task_name="test_task",
            task_description="Test task description",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )

        # The rules section should contain output node naming rule
        assert "output" in prompt.rules.lower(), (
            "Assembled prompt rules should include output node naming"
        )
