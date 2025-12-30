"""Unit tests for standardAiAgent schema (Issue #333).

Tests for system_prompt field correction and backward compatibility with system_imput.
"""

import pytest
from pydantic import ValidationError

from app.schemas.standardAiAgent import ExpertAiAgentRequest


class TestExpertAiAgentRequest:
    """Tests for ExpertAiAgentRequest schema."""

    def test_system_prompt_field_exists(self):
        """system_prompt field should be available."""
        request = ExpertAiAgentRequest(
            user_input="test",
            system_prompt="You are a helpful assistant",
        )
        assert request.system_prompt == "You are a helpful assistant"

    def test_system_prompt_is_optional(self):
        """system_prompt field should be optional."""
        request = ExpertAiAgentRequest(user_input="test")
        assert request.system_prompt is None

    def test_user_input_is_required(self):
        """user_input field should be required."""
        with pytest.raises(ValidationError):
            ExpertAiAgentRequest()  # type: ignore[call-arg]

    def test_all_fields_work_together(self):
        """All fields should work correctly together."""
        request = ExpertAiAgentRequest(
            user_input="test input",
            system_prompt="system prompt text",
            model_name="gpt-4o-mini",
            project="test_project",
            test_mode=True,
        )
        assert request.user_input == "test input"
        assert request.system_prompt == "system prompt text"
        assert request.model_name == "gpt-4o-mini"
        assert request.project == "test_project"
        assert request.test_mode is True


class TestBackwardCompatibility:
    """Tests for backward compatibility with system_imput."""

    def test_system_imput_still_works_for_backward_compatibility(self):
        """system_imput should still work for backward compatibility."""
        # This test checks that old code using system_imput still works
        # The implementation may use alias or __init__ override
        request = ExpertAiAgentRequest(
            user_input="test",
            system_imput="backward compatible prompt",
        )
        # Either system_imput or system_prompt should contain the value
        has_value = (
            getattr(request, "system_imput", None) == "backward compatible prompt"
            or request.system_prompt == "backward compatible prompt"
        )
        assert has_value

    def test_system_prompt_takes_precedence_over_system_imput(self):
        """When both are provided, system_prompt should take precedence."""
        request = ExpertAiAgentRequest(
            user_input="test",
            system_prompt="new prompt",
            system_imput="old prompt",
        )
        # system_prompt should be the value used
        assert request.system_prompt == "new prompt"


class TestSchemaFieldTypes:
    """Tests for schema field types."""

    def test_user_input_accepts_string(self):
        """user_input should accept string type."""
        request = ExpertAiAgentRequest(user_input="string value")
        assert request.user_input == "string value"

    def test_system_prompt_accepts_none(self):
        """system_prompt should accept None."""
        request = ExpertAiAgentRequest(user_input="test", system_prompt=None)
        assert request.system_prompt is None

    def test_model_name_accepts_string_or_none(self):
        """model_name should accept string or None."""
        request_with_model = ExpertAiAgentRequest(
            user_input="test", model_name="gpt-4o"
        )
        assert request_with_model.model_name == "gpt-4o"

        request_without_model = ExpertAiAgentRequest(user_input="test")
        assert request_without_model.model_name is None
