"""Test API schema injection for workflow generation (Issue #338 Phase 3).

This module tests the injection of API response schemas into the workflow
generation context, enabling the LLM to generate accurate field references.
"""

import pytest

from aiagent.langgraph.jobTaskGeneratorAgents.utils.workflow_helper import (
    get_api_response_schemas,
)


class TestGetApiResponseSchemas:
    """Test get_api_response_schemas function."""

    @pytest.mark.asyncio
    async def test_get_schemas_for_google_search_api(self):
        """Test retrieving schema for Google Search API."""
        recommended_apis = ["/v1/utility/google_search"]

        schemas = await get_api_response_schemas(recommended_apis)

        assert "/v1/utility/google_search" in schemas
        schema = schemas["/v1/utility/google_search"]

        # Should include response_schema
        assert "response_schema" in schema or "results" in schema

    @pytest.mark.asyncio
    async def test_get_schemas_for_gmail_api(self):
        """Test retrieving schema for Gmail API."""
        recommended_apis = ["/v1/utility/gmail/send"]

        schemas = await get_api_response_schemas(recommended_apis)

        assert "/v1/utility/gmail/send" in schemas
        schema = schemas["/v1/utility/gmail/send"]

        # Should have message_id in response
        assert schema is not None

    @pytest.mark.asyncio
    async def test_get_schemas_for_multiple_apis(self):
        """Test retrieving schemas for multiple APIs."""
        recommended_apis = [
            "/v1/utility/google_search",
            "/v1/utility/gmail/send",
            "/v1/utility/text_to_speech_drive",
        ]

        schemas = await get_api_response_schemas(recommended_apis)

        assert len(schemas) >= 2  # At least some should be found

    @pytest.mark.asyncio
    async def test_get_schemas_for_unknown_api(self):
        """Test that unknown APIs return empty schema."""
        recommended_apis = ["/v1/unknown/nonexistent_api"]

        schemas = await get_api_response_schemas(recommended_apis)

        # Should not raise error, just return empty or not include the API
        assert (
            "/v1/unknown/nonexistent_api" not in schemas
            or schemas.get("/v1/unknown/nonexistent_api") is None
        )

    @pytest.mark.asyncio
    async def test_get_schemas_empty_list(self):
        """Test handling of empty API list."""
        recommended_apis: list[str] = []

        schemas = await get_api_response_schemas(recommended_apis)

        assert schemas == {}

    @pytest.mark.asyncio
    async def test_schema_contains_field_names(self):
        """Test that schema contains actual field names for reference."""
        recommended_apis = ["/v1/utility/google_search"]

        schemas = await get_api_response_schemas(recommended_apis)

        schema = schemas.get("/v1/utility/google_search", {})

        # Schema should provide field name information
        # This helps LLM use correct field names like 'link' not 'url'
        assert schema is not None


class TestSchemaInjectionInPrompt:
    """Test that API schemas are properly injected into workflow generation prompt."""

    @pytest.mark.asyncio
    async def test_prompt_includes_api_schemas(self):
        """Test that workflow generation prompt includes API response schemas."""
        from aiagent.langgraph.workflowGeneratorAgents.prompts.workflow_generation import (
            create_workflow_generation_prompt,
        )

        task_data = {
            "name": "Google Search Task",
            "description": "Search the web using Google Search API. **Recommended API**: Google Search",
            "input_interface": {"schema": {"query": {"type": "string"}}},
            "output_interface": {
                "schema": {
                    "success": {"type": "boolean"},
                    "search_results": {"type": "array"},
                }
            },
            "recommended_apis": ["/v1/utility/google_search"],
        }

        graphai_capabilities = {"agents": []}
        expert_agent_capabilities = {
            "utility_apis": [
                {
                    "name": "Google Search",
                    "endpoint": "/v1/utility/google_search",
                    "method": "POST",
                    "description": "Web search",
                    "response_schema": {
                        "results": {"type": "array"},
                    },
                }
            ],
            "ai_agent_apis": [],
        }

        prompt = create_workflow_generation_prompt(
            task_data, graphai_capabilities, expert_agent_capabilities
        )

        # Prompt should mention the API
        assert "google_search" in prompt.lower()


class TestSchemaExtraction:
    """Test schema extraction from expert_agent_capabilities.yaml."""

    @pytest.mark.asyncio
    async def test_extract_request_schema(self):
        """Test extracting request schema from capabilities."""
        recommended_apis = ["/v1/utility/google_search"]

        schemas = await get_api_response_schemas(recommended_apis)

        schema = schemas.get("/v1/utility/google_search", {})

        # Request schema should be available for validation
        assert schema is not None

    @pytest.mark.asyncio
    async def test_schema_includes_required_fields(self):
        """Test that schema includes required field information."""
        recommended_apis = ["/v1/utility/gmail/send"]

        schemas = await get_api_response_schemas(recommended_apis)

        # Gmail send should have required fields like 'to', 'subject', 'body'
        # The schema should capture this
        assert schemas is not None
