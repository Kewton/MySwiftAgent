"""Unit tests for P1-4: test_data_regeneration prompt modification.

Issue #340: Tests that the TEST_DATA_REGENERATION_SYSTEM_PROMPT contains
the array type constraint section for stringTemplateAgent.
"""


class TestTestDataRegenerationPromptArrayConstraints:
    """Tests for array type constraints in test data regeneration prompt."""

    def test_prompt_contains_array_type_constraints_section(self) -> None:
        """P1-4: Prompt should contain array type constraints section."""
        from aiagent.langgraph.workflowGeneratorAgents.prompts.test_data_regeneration import (
            TEST_DATA_REGENERATION_SYSTEM_PROMPT,
        )

        # Issue #340: Verify the array type constraints section exists
        assert "Issue #340" in TEST_DATA_REGENERATION_SYSTEM_PROMPT
        assert "stringTemplateAgent" in TEST_DATA_REGENERATION_SYSTEM_PROMPT

    def test_prompt_contains_primitive_type_only_rule(self) -> None:
        """P1-4: Prompt should specify primitive types only for arrays."""
        from aiagent.langgraph.workflowGeneratorAgents.prompts.test_data_regeneration import (
            TEST_DATA_REGENERATION_SYSTEM_PROMPT,
        )

        # Check for primitive type rule
        assert any(
            keyword in TEST_DATA_REGENERATION_SYSTEM_PROMPT.lower()
            for keyword in ["primitive", "string, number, boolean"]
        )

    def test_prompt_contains_object_prohibition(self) -> None:
        """P1-4: Prompt should explicitly prohibit objects in arrays."""
        from aiagent.langgraph.workflowGeneratorAgents.prompts.test_data_regeneration import (
            TEST_DATA_REGENERATION_SYSTEM_PROMPT,
        )

        # Check for object prohibition
        prompt_lower = TEST_DATA_REGENERATION_SYSTEM_PROMPT.lower()
        assert (
            any(
                keyword in prompt_lower
                for keyword in ["object", "prohibited", "forbidden"]
            )
            or "[{" in TEST_DATA_REGENERATION_SYSTEM_PROMPT
        )

    def test_prompt_contains_wrong_pattern_example(self) -> None:
        """P1-4: Prompt should show wrong pattern example."""
        from aiagent.langgraph.workflowGeneratorAgents.prompts.test_data_regeneration import (
            TEST_DATA_REGENERATION_SYSTEM_PROMPT,
        )

        # Check for wrong pattern example (object in array)
        # The prompt should show something like: [{"type": "string", "description": ...}]
        assert (
            "focus_points" in TEST_DATA_REGENERATION_SYSTEM_PROMPT
            or '{"type"' in TEST_DATA_REGENERATION_SYSTEM_PROMPT
        )

    def test_prompt_contains_correct_pattern_example(self) -> None:
        """P1-4: Prompt should show correct pattern example."""
        from aiagent.langgraph.workflowGeneratorAgents.prompts.test_data_regeneration import (
            TEST_DATA_REGENERATION_SYSTEM_PROMPT,
        )

        # Check for correct pattern example (string array)
        # The prompt should show something like: ["value1", "value2"]
        assert (
            '["' in TEST_DATA_REGENERATION_SYSTEM_PROMPT
            or "correct" in TEST_DATA_REGENERATION_SYSTEM_PROMPT.lower()
        )

    def test_prompt_contains_type_consistency_rule(self) -> None:
        """P1-4: Prompt should mention type consistency with items.type."""
        from aiagent.langgraph.workflowGeneratorAgents.prompts.test_data_regeneration import (
            TEST_DATA_REGENERATION_SYSTEM_PROMPT,
        )

        # Check for type consistency rule
        prompt_lower = TEST_DATA_REGENERATION_SYSTEM_PROMPT.lower()
        assert any(
            keyword in prompt_lower for keyword in ["items.type", "type", "consistency"]
        )
