"""Tests for timeout unit consistency (milliseconds).

Issue #343 Task 2.1: Verify timeout values are in milliseconds.

GraphAI expects timeout values in milliseconds. This test ensures
that the prompt examples use milliseconds, not seconds.
"""



class TestTimeoutUnitConsistency:
    """Test that timeout values are in milliseconds."""

    def test_fetch_agent_rules_uses_milliseconds(self) -> None:
        """Test that FETCH_AGENT_RULES uses milliseconds for timeout."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.rules.agent_rules import (
            FETCH_AGENT_RULES,
        )

        # Timeout should be in milliseconds (>= 1000 for 1+ second)
        # Check for "timeout: 30000" (30 seconds in ms)
        assert "timeout: 30000" in FETCH_AGENT_RULES, (
            "FETCH_AGENT_RULES should use timeout: 30000 (milliseconds), "
            "not timeout: 30 (seconds)"
        )

    def test_timeout_description_mentions_milliseconds(self) -> None:
        """Test that timeout descriptions mention milliseconds unit."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.rules.agent_rules import (
            FETCH_AGENT_RULES,
        )

        # The rules should explicitly mention the unit
        assert "millisecond" in FETCH_AGENT_RULES.lower() or "ms" in FETCH_AGENT_RULES, (
            "FETCH_AGENT_RULES should explicitly mention that timeout is in milliseconds"
        )

    def test_all_agent_rules_uses_milliseconds(self) -> None:
        """Test that ALL_AGENT_RULES includes millisecond timeout."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.rules.agent_rules import (
            ALL_AGENT_RULES,
        )

        # ALL_AGENT_RULES aggregates all rules, should contain ms timeout
        assert "timeout: 30000" in ALL_AGENT_RULES, (
            "ALL_AGENT_RULES should include timeout: 30000 (milliseconds)"
        )

    def test_get_agent_rules_for_fetch_uses_milliseconds(self) -> None:
        """Test that get_agent_rules() returns ms timeout for fetch agents."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.rules.agent_rules import (
            get_agent_rules,
        )

        rules = get_agent_rules(["fetchAgent"])
        assert "timeout: 30000" in rules, (
            "get_agent_rules(['fetchAgent']) should return rules with timeout: 30000"
        )

    def test_no_seconds_timeout_in_rules(self) -> None:
        """Test that rules don't contain seconds-based timeout (30)."""
        # Should NOT contain "timeout: 30" followed by non-digit
        # (which would indicate seconds, not milliseconds)
        import re

        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.rules.agent_rules import (
            FETCH_AGENT_RULES,
        )

        # Match "timeout: 30" NOT followed by another digit
        seconds_pattern = r"timeout:\s*30(?!\d)"
        matches = re.findall(seconds_pattern, FETCH_AGENT_RULES)
        assert len(matches) == 0, (
            f"Found {len(matches)} instances of 'timeout: 30' (seconds). "
            "All timeouts should be in milliseconds (e.g., timeout: 30000)"
        )
