"""Integration tests for LLM provider compatibility.

These tests verify that Pydantic models with structured output work correctly
across different LLM providers (OpenAI, Claude, Gemini).

Priority: Low (manual execution recommended)
These tests require actual API keys and make real API calls.
They are skipped by default and can be run manually with:
    pytest tests/integration/test_llm_provider_compatibility.py --run-integration

Issue #111: Regression tests for OpenAI additionalProperties requirement.
"""

import os

import pytest
from pydantic import BaseModel, ConfigDict, Field

from aiagent.langgraph.jobTaskGeneratorAgents.prompts.interface_schema import (
    InterfaceSchemaResponse,
)
from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_factory import (
    create_llm_with_fallback,
)


def pytest_configure(config):
    """Add custom marker for integration tests."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires API keys, skipped by default)",
    )


@pytest.fixture
def skip_if_no_api_keys():
    """Skip test if API keys are not available."""
    required_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
    missing_keys = [key for key in required_keys if not os.getenv(key)]

    if missing_keys:
        pytest.skip(
            f"Skipping integration test: missing API keys: {', '.join(missing_keys)}"
        )


@pytest.mark.integration
@pytest.mark.asyncio
class TestOpenAIProviderCompatibility:
    """Integration tests for OpenAI provider with structured output."""

    async def test_openai_gpt4o_mini_with_interface_schema(self, skip_if_no_api_keys):
        """Test OpenAI GPT-4o-mini with InterfaceSchemaResponse.

        Priority: High
        This is a regression test for the additionalProperties: false requirement.

        Expected behavior:
        - Pydantic model with ConfigDict(extra="forbid") should work
        - OpenAI API should accept the generated JSON Schema
        - Structured output should be returned successfully
        """
        # Create LLM with OpenAI GPT-4o-mini
        llm, _, _ = create_llm_with_fallback(
            model_name="gpt-4o-mini", temperature=0.0, max_tokens=1024
        )

        # Create structured LLM
        structured_llm = llm.with_structured_output(InterfaceSchemaResponse)

        # Simple test prompt
        messages = [
            {
                "role": "user",
                "content": "Define interface schema for a task that searches Gmail. "
                "Task ID: task_001, Interface name: gmail_search_interface. "
                "Input: query (string). Output: success (boolean), emails (array).",
            }
        ]

        # Invoke LLM
        response = await structured_llm.ainvoke(messages)

        # Verify response
        assert isinstance(response, InterfaceSchemaResponse)
        assert len(response.interfaces) > 0
        assert response.interfaces[0].task_id == "task_001"
        assert response.interfaces[0].interface_name == "gmail_search_interface"

        # Verify schema structure
        input_schema = response.interfaces[0].input_schema
        assert input_schema.get("type") == "object"
        assert "properties" in input_schema
        assert "query" in input_schema["properties"]

        output_schema = response.interfaces[0].output_schema
        assert output_schema.get("type") == "object"
        assert "properties" in output_schema
        assert "success" in output_schema["properties"]
        assert "emails" in output_schema["properties"]

    async def test_openai_json_schema_validation(self, skip_if_no_api_keys):
        """Test that OpenAI API validates additionalProperties correctly.

        Priority: High
        This test explicitly verifies the additionalProperties: false requirement.

        If this test fails with:
        "Invalid schema for response_format: additionalProperties is required to be false"
        then the Pydantic model configuration is incorrect.
        """

        # Create a test model with extra="forbid"
        class TestModel(BaseModel):
            model_config = ConfigDict(extra="forbid")
            name: str = Field(description="Name field")
            value: int = Field(description="Value field")

        # Verify JSON Schema has additionalProperties: false
        schema = TestModel.model_json_schema()
        assert schema.get("additionalProperties") is False, (
            "Model must generate additionalProperties: false"
        )

        # Create LLM
        llm, _, _ = create_llm_with_fallback(
            model_name="gpt-4o-mini", temperature=0.0, max_tokens=256
        )

        # Create structured LLM (this should NOT raise an error)
        structured_llm = llm.with_structured_output(TestModel)

        # Simple test prompt
        messages = [{"role": "user", "content": "Generate name='test' and value=42"}]

        # Invoke LLM (should succeed)
        response = await structured_llm.ainvoke(messages)

        # Verify response
        assert isinstance(response, TestModel)
        assert response.name == "test"
        assert response.value == 42


@pytest.mark.integration
@pytest.mark.asyncio
class TestClaudeProviderCompatibility:
    """Integration tests for Claude provider with structured output."""

    async def test_claude_haiku_with_interface_schema(self, skip_if_no_api_keys):
        """Test Claude Haiku with InterfaceSchemaResponse.

        Priority: Medium
        Claude is more permissive than OpenAI and accepts both
        additionalProperties: true and false.
        """
        # Create LLM with Claude Haiku
        llm, _, _ = create_llm_with_fallback(
            model_name="claude-haiku-4-5", temperature=0.0, max_tokens=1024
        )

        # Create structured LLM
        structured_llm = llm.with_structured_output(InterfaceSchemaResponse)

        # Simple test prompt
        messages = [
            {
                "role": "user",
                "content": "Define interface schema for a task that extracts PDF content. "
                "Task ID: task_002, Interface name: pdf_extract_interface. "
                "Input: pdf_url (string). Output: success (boolean), content (string).",
            }
        ]

        # Invoke LLM
        response = await structured_llm.ainvoke(messages)

        # Verify response
        assert isinstance(response, InterfaceSchemaResponse)
        assert len(response.interfaces) > 0
        assert response.interfaces[0].task_id == "task_002"
        assert response.interfaces[0].interface_name == "pdf_extract_interface"


@pytest.mark.integration
@pytest.mark.asyncio
class TestGeminiProviderCompatibility:
    """Integration tests for Gemini provider with structured output."""

    async def test_gemini_flash_with_interface_schema(self, skip_if_no_api_keys):
        """Test Gemini 2.5 Flash with InterfaceSchemaResponse.

        Priority: Medium
        Gemini accepts additionalProperties: true but works with false as well.
        """
        # Create LLM with Gemini Flash
        llm, _, _ = create_llm_with_fallback(
            model_name="gemini-2.5-flash", temperature=0.0, max_tokens=1024
        )

        # Create structured LLM
        structured_llm = llm.with_structured_output(InterfaceSchemaResponse)

        # Simple test prompt
        messages = [
            {
                "role": "user",
                "content": "Define interface schema for a task that uploads to Google Drive. "
                "Task ID: task_003, Interface name: drive_upload_interface. "
                "Input: file_path (string), folder_id (string). "
                "Output: success (boolean), file_id (string).",
            }
        ]

        # Invoke LLM
        response = await structured_llm.ainvoke(messages)

        # Verify response
        assert isinstance(response, InterfaceSchemaResponse)
        assert len(response.interfaces) > 0
        assert response.interfaces[0].task_id == "task_003"
        assert response.interfaces[0].interface_name == "drive_upload_interface"


@pytest.mark.integration
@pytest.mark.asyncio
class TestProviderFallbackBehavior:
    """Test LLM provider fallback behavior with structured output."""

    async def test_fallback_from_invalid_model(self, skip_if_no_api_keys):
        """Test that fallback works when primary model fails.

        Priority: Low
        This tests the robustness of create_llm_with_fallback.
        """
        # Try to create LLM with invalid model (should fallback)
        llm, _, _ = create_llm_with_fallback(
            model_name="invalid-model-name",
            temperature=0.0,
            max_tokens=256,
            fallback_models=["claude-haiku-4-5", "gpt-4o-mini", "gemini-2.5-flash"],
        )

        # Create structured LLM
        class SimpleModel(BaseModel):
            model_config = ConfigDict(extra="forbid")
            message: str = Field(description="Simple message")

        structured_llm = llm.with_structured_output(SimpleModel)

        # Test prompt
        messages = [{"role": "user", "content": "Generate message='hello'"}]

        # Invoke LLM (should succeed with fallback model)
        response = await structured_llm.ainvoke(messages)

        # Verify response
        assert isinstance(response, SimpleModel)
        assert response.message == "hello"
