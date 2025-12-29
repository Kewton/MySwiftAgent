"""Unit tests for task_breakdown prompt module - Issue #270, #321.

Tests for:
1. Schema hint generation for LLM prompts
2. Expert agent capabilities building with schema information
3. Issue #321: JobBodyParameter model for automatic parameter extraction
"""

import pytest

from aiagent.langgraph.jobTaskGeneratorAgents.prompts.task_breakdown import (
    _build_expert_agent_capabilities,
    _build_schema_hint,
    _build_task_breakdown_system_prompt,
    create_task_breakdown_prompt,
)


class TestBuildSchemaHint:
    """Test schema hint generation for task breakdown prompt."""

    def test_build_schema_hint_with_required_fields(self) -> None:
        """Test building schema hint with required fields."""
        api = {
            "name": "Test API",
            "endpoint": "/v1/test",
            "request_schema": {
                "query": {"type": "string", "required": True},
                "max_results": {"type": "integer", "default": 10},
            },
        }
        hint = _build_schema_hint(api)
        assert hint != ""
        assert "query" in hint

    def test_build_schema_hint_no_required_fields(self) -> None:
        """Test building schema hint when no required fields."""
        api = {
            "name": "Test API",
            "endpoint": "/v1/test",
            "request_schema": {
                "optional_field": {"type": "string", "default": "default"},
            },
        }
        hint = _build_schema_hint(api)
        # Should return empty or minimal hint when no required fields
        assert "required" not in hint.lower() or hint == ""

    def test_build_schema_hint_no_request_schema(self) -> None:
        """Test building schema hint when no request_schema."""
        api = {
            "name": "Test API",
            "endpoint": "/v1/test",
        }
        hint = _build_schema_hint(api)
        assert hint == ""

    def test_build_schema_hint_multiple_required_fields(self) -> None:
        """Test building schema hint with multiple required fields."""
        api = {
            "name": "Test API",
            "endpoint": "/v1/test",
            "request_schema": {
                "field1": {"type": "string", "required": True},
                "field2": {"type": "string", "required": True},
                "field3": {"type": "string"},  # Not required
            },
        }
        hint = _build_schema_hint(api)
        assert "field1" in hint
        assert "field2" in hint


class TestBuildExpertAgentCapabilities:
    """Test expert agent capabilities building with schema hints."""

    def test_build_capabilities_includes_apis(self) -> None:
        """Test that capabilities includes API list."""
        capabilities = _build_expert_agent_capabilities()
        assert "expertAgent Direct API" in capabilities
        assert "Gmail" in capabilities

    def test_build_capabilities_includes_schema_hints(self) -> None:
        """Test that capabilities includes schema hints for APIs."""
        capabilities = _build_expert_agent_capabilities()
        # Should include hints about required fields
        # This will be populated after YAML is updated
        assert "Utility API" in capabilities or "AI Agent API" in capabilities

    def test_build_capabilities_includes_utility_apis(self) -> None:
        """Test that capabilities includes utility APIs section."""
        capabilities = _build_expert_agent_capabilities()
        assert "Utility API" in capabilities

    def test_build_capabilities_includes_ai_agent_apis(self) -> None:
        """Test that capabilities includes AI agent APIs section."""
        capabilities = _build_expert_agent_capabilities()
        assert "AI Agent API" in capabilities

    def test_build_capabilities_includes_task_api_mapping(self) -> None:
        """Test that capabilities includes task-to-API mapping section.

        Issue #305: task_api_mapping should be included in prompt to guide
        LLM in selecting appropriate APIs for specific task types.
        """
        capabilities = _build_expert_agent_capabilities()
        # Should include the task-to-API mapping section header
        assert "タスク種別ごとの推奨API" in capabilities

    def test_build_capabilities_includes_file_reader_mapping(self) -> None:
        """Test that task_api_mapping includes File Reader Agent mapping.

        Issue #305: File Reader Agent should be recommended for file reading tasks.
        """
        capabilities = _build_expert_agent_capabilities()
        # Should include file reading task mapping
        assert "ファイル読み取り" in capabilities
        assert "File Reader Agent" in capabilities
        assert "/v1/aiagent/utility/file_reader" in capabilities

    def test_build_capabilities_includes_tts_mapping(self) -> None:
        """Test that task_api_mapping includes TTS mapping."""
        capabilities = _build_expert_agent_capabilities()
        # Should include TTS task mapping
        assert "音声合成" in capabilities
        assert "Text-to-Speech" in capabilities

    def test_build_capabilities_includes_mapping_table_format(self) -> None:
        """Test that task_api_mapping is formatted as a markdown table."""
        capabilities = _build_expert_agent_capabilities()
        # Should have table headers
        assert "| タスク種別 |" in capabilities
        assert "| 推奨API |" in capabilities or "推奨API" in capabilities
        # Should have table separator
        assert "|---" in capabilities


class TestBuildTaskBreakdownSystemPrompt:
    """Test task breakdown system prompt building."""

    def test_system_prompt_not_empty(self) -> None:
        """Test that system prompt is generated."""
        prompt = _build_task_breakdown_system_prompt()
        assert prompt != ""
        assert len(prompt) > 100

    def test_system_prompt_includes_expert_agent_capabilities(self) -> None:
        """Test that system prompt includes expert agent capabilities."""
        prompt = _build_task_breakdown_system_prompt()
        # Should include API information
        assert "expertAgent" in prompt or "Gmail" in prompt


class TestCreateTaskBreakdownPrompt:
    """Test task breakdown prompt creation."""

    def test_create_prompt_includes_user_requirement(self) -> None:
        """Test that created prompt includes user requirement."""
        requirement = "Test requirement for Gmail search"
        prompt = create_task_breakdown_prompt(requirement)
        assert requirement in prompt

    def test_create_prompt_includes_instructions(self) -> None:
        """Test that created prompt includes instructions."""
        requirement = "Test requirement"
        prompt = create_task_breakdown_prompt(requirement)
        assert "JSON形式" in prompt or "json" in prompt.lower()


class TestConvertStringApisToObjects:
    """Test backward compatibility converter for recommended_apis field.

    Issue #305: Ensure the field_validator correctly extracts endpoints
    from legacy string formats like 'fetchAgent (utility API: /v1/utility/gmail/send)'.
    """

    def test_string_format_with_embedded_endpoint(self) -> None:
        """Test extraction of endpoint from legacy string format."""
        from aiagent.langgraph.jobTaskGeneratorAgents.prompts.task_breakdown import (
            TaskBreakdownItem,
        )

        # Create item with legacy string format containing endpoint
        item = TaskBreakdownItem(
            task_id="task_1",
            name="Send email",
            description="Send email via Gmail API",
            expected_output="Email sent confirmation",
            recommended_apis=["fetchAgent (utility API: /v1/utility/gmail/send)"],
        )

        # The endpoint should be extracted
        assert len(item.recommended_apis) == 1
        api = item.recommended_apis[0]
        assert api.endpoint == "/v1/utility/gmail/send"
        assert "自動抽出" in api.reason

    def test_string_format_without_endpoint(self) -> None:
        """Test legacy string format that does not contain a valid endpoint."""
        from aiagent.langgraph.jobTaskGeneratorAgents.prompts.task_breakdown import (
            TaskBreakdownItem,
        )

        item = TaskBreakdownItem(
            task_id="task_1",
            name="Custom task",
            description="Task without specific API",
            expected_output="Task result",
            recommended_apis=["customAgent"],
        )

        assert len(item.recommended_apis) == 1
        api = item.recommended_apis[0]
        assert api.endpoint == ""  # No endpoint found
        assert "レガシー形式" in api.reason

    def test_dict_format_with_empty_endpoint_but_api_name_has_endpoint(self) -> None:
        """Test dict format where endpoint is empty but api_name contains one."""
        from aiagent.langgraph.jobTaskGeneratorAgents.prompts.task_breakdown import (
            TaskBreakdownItem,
        )

        item = TaskBreakdownItem(
            task_id="task_1",
            name="Search emails",
            description="Search Gmail",
            expected_output="List of matching emails",
            recommended_apis=[
                {
                    "api_name": "fetchAgent (utility API: /v1/utility/gmail/search)",
                    "endpoint": "",  # Empty endpoint
                    "method": "POST",
                    "reason": "For email search",
                }
            ],
        )

        assert len(item.recommended_apis) == 1
        api = item.recommended_apis[0]
        # Endpoint should be extracted from api_name
        assert api.endpoint == "/v1/utility/gmail/search"

    def test_dict_format_with_existing_endpoint_unchanged(self) -> None:
        """Test that dict format with existing endpoint is not modified."""
        from aiagent.langgraph.jobTaskGeneratorAgents.prompts.task_breakdown import (
            TaskBreakdownItem,
        )

        item = TaskBreakdownItem(
            task_id="task_1",
            name="Send email",
            description="Send Gmail",
            expected_output="Email sent status",
            recommended_apis=[
                {
                    "api_name": "Gmail Send API",
                    "endpoint": "/v1/utility/gmail/send",
                    "method": "POST",
                    "reason": "Original reason",
                }
            ],
        )

        assert len(item.recommended_apis) == 1
        api = item.recommended_apis[0]
        # Existing endpoint should remain unchanged
        assert api.endpoint == "/v1/utility/gmail/send"
        assert api.reason == "Original reason"  # Not modified

    def test_direct_endpoint_in_string(self) -> None:
        """Test string format that is just an endpoint."""
        from aiagent.langgraph.jobTaskGeneratorAgents.prompts.task_breakdown import (
            TaskBreakdownItem,
        )

        item = TaskBreakdownItem(
            task_id="task_1",
            name="Send email",
            description="Send email",
            expected_output="Email sent confirmation",
            recommended_apis=["/v1/utility/gmail/send"],
        )

        assert len(item.recommended_apis) == 1
        api = item.recommended_apis[0]
        assert api.endpoint == "/v1/utility/gmail/send"


class TestJobBodyParameter:
    """Test JobBodyParameter model for Issue #321.

    Tests for automatic extraction of parameters from user requirements.
    """

    def test_job_body_parameter_creation_with_string(self) -> None:
        """Test creating JobBodyParameter with string value."""
        from aiagent.langgraph.jobTaskGeneratorAgents.prompts.task_breakdown import (
            JobBodyParameter,
        )

        param = JobBodyParameter(
            name="recipient_email",
            value="test@example.com",
            source="user_requirement",
        )
        assert param.name == "recipient_email"
        assert param.value == "test@example.com"
        assert param.source == "user_requirement"

    def test_job_body_parameter_creation_with_integer(self) -> None:
        """Test creating JobBodyParameter with integer value."""
        from aiagent.langgraph.jobTaskGeneratorAgents.prompts.task_breakdown import (
            JobBodyParameter,
        )

        param = JobBodyParameter(
            name="num_results",
            value=10,
            source="user_requirement",
        )
        assert param.name == "num_results"
        assert param.value == 10

    def test_job_body_parameter_creation_with_list(self) -> None:
        """Test creating JobBodyParameter with list value."""
        from aiagent.langgraph.jobTaskGeneratorAgents.prompts.task_breakdown import (
            JobBodyParameter,
        )

        param = JobBodyParameter(
            name="keywords",
            value=["keyword1", "keyword2"],
            source="user_requirement",
        )
        assert param.name == "keywords"
        assert param.value == ["keyword1", "keyword2"]

    def test_job_body_parameter_sensitive_parameter_rejected(self) -> None:
        """Test that sensitive parameter names are rejected."""
        from aiagent.langgraph.jobTaskGeneratorAgents.prompts.task_breakdown import (
            JobBodyParameter,
        )

        # password should be rejected
        with pytest.raises(ValueError, match="sensitive"):
            JobBodyParameter(
                name="password",
                value="secret123",
                source="user_requirement",
            )

        # api_key should be rejected
        with pytest.raises(ValueError, match="sensitive"):
            JobBodyParameter(
                name="api_key",
                value="sk-xxx",
                source="user_requirement",
            )

        # secret should be rejected
        with pytest.raises(ValueError, match="sensitive"):
            JobBodyParameter(
                name="my_secret",
                value="secret_value",
                source="user_requirement",
            )

    def test_job_body_parameter_optional_description(self) -> None:
        """Test JobBodyParameter with optional description."""
        from aiagent.langgraph.jobTaskGeneratorAgents.prompts.task_breakdown import (
            JobBodyParameter,
        )

        param = JobBodyParameter(
            name="query",
            value="search term",
            source="user_requirement",
            description="Search query extracted from user request",
        )
        assert param.description == "Search query extracted from user request"


class TestTaskBreakdownResponseWithJobBodyParameters:
    """Test TaskBreakdownResponse with job_body_parameters field - Issue #321."""

    def test_task_breakdown_response_with_job_body_parameters(self) -> None:
        """Test TaskBreakdownResponse includes job_body_parameters field."""
        from aiagent.langgraph.jobTaskGeneratorAgents.prompts.task_breakdown import (
            JobBodyParameter,
            TaskBreakdownResponse,
        )

        response = TaskBreakdownResponse(
            tasks=[],
            overall_summary="Test workflow",
            job_body_parameters=[
                JobBodyParameter(
                    name="recipient_email",
                    value="test@example.com",
                    source="user_requirement",
                ),
                JobBodyParameter(
                    name="query",
                    value="test query",
                    source="user_requirement",
                ),
            ],
        )
        assert len(response.job_body_parameters) == 2
        assert response.job_body_parameters[0].name == "recipient_email"
        assert response.job_body_parameters[1].name == "query"

    def test_task_breakdown_response_job_body_parameters_optional(self) -> None:
        """Test job_body_parameters is optional for backward compatibility."""
        from aiagent.langgraph.jobTaskGeneratorAgents.prompts.task_breakdown import (
            TaskBreakdownResponse,
        )

        # Should work without job_body_parameters (backward compatibility)
        response = TaskBreakdownResponse(
            tasks=[],
            overall_summary="Test workflow",
        )
        assert response.job_body_parameters == []

    def test_task_breakdown_response_with_dict_input(self) -> None:
        """Test TaskBreakdownResponse accepts dict format for job_body_parameters."""
        from aiagent.langgraph.jobTaskGeneratorAgents.prompts.task_breakdown import (
            TaskBreakdownResponse,
        )

        response = TaskBreakdownResponse(
            tasks=[],
            overall_summary="Test workflow",
            job_body_parameters=[
                {
                    "name": "recipient_email",
                    "value": "test@example.com",
                    "source": "user_requirement",
                }
            ],
        )
        assert len(response.job_body_parameters) == 1
        assert response.job_body_parameters[0].name == "recipient_email"


class TestSystemPromptIncludesParameterExtraction:
    """Test that system prompt includes parameter extraction instructions - Issue #321."""

    def test_system_prompt_includes_parameter_extraction_section(self) -> None:
        """Test that system prompt includes job_body_parameters extraction instructions."""
        prompt = _build_task_breakdown_system_prompt()

        # Should mention job_body_parameters in the prompt
        assert "job_body_parameters" in prompt

    def test_system_prompt_mentions_email_extraction(self) -> None:
        """Test that system prompt mentions email address extraction."""
        prompt = _build_task_breakdown_system_prompt()

        # Should mention email extraction
        assert "email" in prompt.lower() or "recipient" in prompt.lower()

    def test_system_prompt_mentions_sensitive_exclusion(self) -> None:
        """Test that system prompt mentions excluding sensitive parameters."""
        prompt = _build_task_breakdown_system_prompt()

        # Should mention sensitive/password/api_key exclusion
        assert (
            "sensitive" in prompt.lower()
            or "password" in prompt.lower()
            or "api_key" in prompt.lower()
        )
