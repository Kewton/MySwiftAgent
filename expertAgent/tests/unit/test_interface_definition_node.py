"""Unit tests for interface_definition_node.

These tests verify the interface definition node's behavior including:
- Successful interface schema generation with valid LLM responses
- Error handling for LLM failures
- Edge cases (empty task breakdown, invalid responses)
- Evaluation feedback integration
- Retry count management
- Schema validation and InterfaceMaster creation

Issue #111: Comprehensive test coverage for all workflow nodes.
"""

from unittest.mock import AsyncMock, patch

import pytest

from aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition import (
    interface_definition_node,
)
from aiagent.langgraph.jobTaskGeneratorAgents.prompts.interface_schema import (
    InterfaceSchemaDefinition,
    InterfaceSchemaResponse,
)
from tests.utils.mock_helpers import (
    create_mock_task_breakdown,
    create_mock_workflow_state,
)


@pytest.mark.unit
class TestInterfaceDefinitionNode:
    """Unit tests for interface_definition_node."""

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.SchemaMatcher"
    )
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.JobqueueClient"
    )
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.invoke_structured_llm"
    )
    async def test_interface_definition_success(
        self, mock_invoke_llm, mock_jobqueue_client, mock_schema_matcher
    ):
        """Test successful interface definition with valid LLM response.

        Priority: High
        This is the happy path test case.
        """
        # Create mock interface schema response
        mock_interfaces = [
            InterfaceSchemaDefinition(
                task_id="task_001",
                interface_name="gmail_search_interface",
                description="Gmail search interface",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "emails": {"type": "array", "items": {"type": "object"}},
                    },
                    "required": ["success", "emails"],
                },
            ),
            InterfaceSchemaDefinition(
                task_id="task_002",
                interface_name="email_extract_interface",
                description="Email content extraction interface",
                input_schema={
                    "type": "object",
                    "properties": {
                        "emails": {"type": "array", "items": {"type": "object"}}
                    },
                    "required": ["emails"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "content": {"type": "string"},
                    },
                    "required": ["success", "content"],
                },
            ),
        ]
        mock_response = InterfaceSchemaResponse(interfaces=mock_interfaces)

        # Setup mock invoke_structured_llm

        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        mock_invoke_llm.return_value = StructuredCallResult(
            result=mock_response,
            recovered_via_json=False,
            raw_text=None,
            model_name="test-model",
        )

        # Setup mock JobqueueClient and SchemaMatcher
        mock_client_instance = AsyncMock()
        mock_jobqueue_client.return_value = mock_client_instance

        mock_matcher_instance = AsyncMock()
        mock_matcher_instance.find_or_create_interface_master = AsyncMock(
            side_effect=[
                {"id": "iface_001", "name": "gmail_search_interface"},
                {"id": "iface_002", "name": "email_extract_interface"},
            ]
        )
        mock_schema_matcher.return_value = mock_matcher_instance

        # Create test state
        task_breakdown = create_mock_task_breakdown(2)
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Search Gmail and extract content",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
        )

        # Execute node
        result = await interface_definition_node(state)

        # Verify results
        assert "interface_definitions" in result
        assert len(result["interface_definitions"]) == 2
        assert (
            result["interface_definitions"]["task_001"]["interface_master_id"]
            == "iface_001"
        )
        assert (
            result["interface_definitions"]["task_002"]["interface_master_id"]
            == "iface_002"
        )

        assert result["evaluator_stage"] == "after_interface_definition"
        assert result["retry_count"] == 0  # Should remain 0 on first success

        # Verify invoke_structured_llm was called
        mock_invoke_llm.assert_called_once()

        # Verify SchemaMatcher was called for each interface
        assert mock_matcher_instance.find_or_create_interface_master.call_count == 2

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.invoke_structured_llm"
    )
    async def test_interface_definition_with_evaluation_feedback(self, mock_invoke_llm):
        """Test interface definition with evaluation feedback (retry scenario).

        Priority: Medium
        This tests the feedback-enhanced prompt path.
        """
        # This test is similar to requirement_analysis test but for interface definition
        # Interface definition node doesn't use evaluation_feedback in prompt,
        # but we test that it works correctly even when feedback is present
        mock_interfaces = [
            InterfaceSchemaDefinition(
                task_id="task_001",
                interface_name="improved_gmail_search_interface",
                description="Improved Gmail search interface based on feedback",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_results": {"type": "integer", "default": 10},
                    },
                    "required": ["query"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "emails": {"type": "array"},
                    },
                    "required": ["success", "emails"],
                },
            ),
        ]
        mock_response = InterfaceSchemaResponse(interfaces=mock_interfaces)

        # Setup mock invoke_structured_llm

        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        mock_invoke_llm.return_value = StructuredCallResult(
            result=mock_response,
            recovered_via_json=False,
            raw_text=None,
            model_name="test-model",
        )

        # Mock SchemaMatcher (even though we have evaluation_feedback)
        with patch(
            "aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.SchemaMatcher"
        ) as mock_matcher_class:
            mock_matcher_instance = AsyncMock()
            mock_matcher_instance.find_or_create_interface_master = AsyncMock(
                return_value={
                    "id": "iface_001",
                    "name": "improved_gmail_search_interface",
                }
            )
            mock_matcher_class.return_value = mock_matcher_instance

            # Create test state with evaluation feedback
            task_breakdown = create_mock_task_breakdown(1)
            state = create_mock_workflow_state(
                retry_count=1,  # This is a retry
                user_requirement="Create a workflow for Gmail search",
                task_breakdown=task_breakdown,
                evaluation_feedback="Previous interface schema was too simple. "
                "Please add more validation constraints.",
                evaluator_stage="after_task_breakdown",
            )

            # Execute node
            result = await interface_definition_node(state)

            # Verify results
            assert "interface_definitions" in result
            assert len(result["interface_definitions"]) == 1
            assert (
                result["interface_definitions"]["task_001"]["interface_name"]
                == "improved_gmail_search_interface"
            )

            # Verify retry_count incremented (retry_count=1 → 2)
            assert result["retry_count"] == 2

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.invoke_structured_llm"
    )
    async def test_interface_definition_llm_error(self, mock_invoke_llm):
        """Test error handling when LLM invocation fails.

        Priority: Medium
        This tests exception handling and error message propagation.
        """
        # Setup mock invoke_structured_llm to raise exception
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredLLMError,
        )

        mock_invoke_llm.side_effect = StructuredLLMError("LLM API timeout")

        # Create test state
        task_breakdown = create_mock_task_breakdown(2)
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Define interfaces for tasks",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
        )

        # Execute node
        result = await interface_definition_node(state)

        # Verify error handling
        assert "error_message" in result
        assert "LLM API timeout" in result["error_message"]

        # interface_definitions should not be in result
        assert "interface_definitions" not in result

        # Verify retry_count incremented
        assert result["retry_count"] == 1

        # Verify invoke_structured_llm was called 3 times (internal retry)
        assert mock_invoke_llm.call_count == 3

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.invoke_structured_llm"
    )
    async def test_interface_definition_empty_task_breakdown(self, mock_invoke_llm):
        """Test error handling when task_breakdown is empty.

        Priority: Medium
        This tests edge case where no tasks are provided.
        """
        # Note: mock_invoke_llm won't be called due to empty check in interface_definition_node

        # Create test state with empty task_breakdown
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Some requirement",
            task_breakdown=[],  # Empty
            evaluator_stage="after_task_breakdown",
        )

        # Execute node
        result = await interface_definition_node(state)

        # Verify error handling
        assert "error_message" in result
        assert (
            "Interface definition requires a task breakdown" in result["error_message"]
        )

        # Verify invoke_structured_llm was NOT called (early return)
        mock_invoke_llm.assert_not_called()

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.SchemaMatcher"
    )
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.JobqueueClient"
    )
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.invoke_structured_llm"
    )
    async def test_interface_definition_retry_count_behavior(
        self, mock_invoke_llm, mock_jobqueue_client, mock_schema_matcher
    ):
        """Test retry_count increment behavior.

        Priority: Medium
        This tests the retry_count logic:
        - If evaluation_feedback exists: increment retry_count
        - If no evaluation_feedback: set retry_count to 0
        """
        # Create mock interface schema response
        mock_interfaces = [
            InterfaceSchemaDefinition(
                task_id="task_001",
                interface_name="test_interface",
                description="Test interface",
                input_schema={"type": "object", "properties": {}},
                output_schema={"type": "object", "properties": {}},
            ),
        ]
        mock_response = InterfaceSchemaResponse(interfaces=mock_interfaces)

        # Setup mock invoke_structured_llm

        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        mock_invoke_llm.return_value = StructuredCallResult(
            result=mock_response,
            recovered_via_json=False,
            raw_text=None,
            model_name="test-model",
        )

        # Setup mock JobqueueClient and SchemaMatcher
        mock_client_instance = AsyncMock()
        mock_jobqueue_client.return_value = mock_client_instance

        mock_matcher_instance = AsyncMock()
        mock_matcher_instance.find_or_create_interface_master = AsyncMock(
            return_value={"id": "iface_001", "name": "test_interface"}
        )
        mock_schema_matcher.return_value = mock_matcher_instance

        # Test Case 1: retry_count == 0 (first attempt, no evaluation_feedback)
        task_breakdown = create_mock_task_breakdown(1)
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Test requirement",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
        )
        result = await interface_definition_node(state)
        assert result["retry_count"] == 0, (
            "retry_count should remain 0 on first successful attempt"
        )

        # Test Case 2: retry_count == 1 (retry with evaluation_feedback)
        state = create_mock_workflow_state(
            retry_count=1,
            user_requirement="Test requirement",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
            evaluation_feedback="Need improvements",  # This indicates a retry scenario
        )
        result = await interface_definition_node(state)
        assert result["retry_count"] == 2, (
            "retry_count should increment from 1 to 2 on retry"
        )

        # Test Case 3: retry_count == 3 (retry with evaluation_feedback)
        state = create_mock_workflow_state(
            retry_count=3,
            user_requirement="Test requirement",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
            evaluation_feedback="Need improvements",  # This indicates a retry scenario
        )
        result = await interface_definition_node(state)
        assert result["retry_count"] == 4, (
            "retry_count should increment from 3 to 4 on retry"
        )

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.SchemaMatcher"
    )
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.JobqueueClient"
    )
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.invoke_structured_llm"
    )
    async def test_interface_definition_missing_interface_master_id(
        self, mock_invoke_llm, mock_jobqueue_client, mock_schema_matcher
    ):
        """Test error handling when InterfaceMaster response is missing 'id' field.

        Priority: Low
        This tests defensive programming for unexpected API responses.
        """
        # Create mock interface schema response
        mock_interfaces = [
            InterfaceSchemaDefinition(
                task_id="task_001",
                interface_name="test_interface",
                description="Test interface",
                input_schema={"type": "object", "properties": {}},
                output_schema={"type": "object", "properties": {}},
            ),
        ]
        mock_response = InterfaceSchemaResponse(interfaces=mock_interfaces)

        # Setup mock invoke_structured_llm

        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        mock_invoke_llm.return_value = StructuredCallResult(
            result=mock_response,
            recovered_via_json=False,
            raw_text=None,
            model_name="test-model",
        )

        # Setup mock JobqueueClient and SchemaMatcher
        mock_client_instance = AsyncMock()
        mock_jobqueue_client.return_value = mock_client_instance

        # Mock SchemaMatcher to return response WITHOUT 'id' field
        mock_matcher_instance = AsyncMock()
        mock_matcher_instance.find_or_create_interface_master = AsyncMock(
            return_value={"name": "test_interface"}  # Missing 'id' field
        )
        mock_schema_matcher.return_value = mock_matcher_instance

        # Create test state
        task_breakdown = create_mock_task_breakdown(1)
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Test requirement",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
        )

        # Execute node - should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            await interface_definition_node(state)

        # Verify error message
        assert "InterfaceMaster creation failed for task task_001" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.SchemaMatcher"
    )
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.JobqueueClient"
    )
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.invoke_structured_llm"
    )
    async def test_interface_definition_schema_validation(
        self, mock_invoke_llm, mock_jobqueue_client, mock_schema_matcher
    ):
        """Test schema validation with JSON Schema compliance.

        Priority: Low
        This tests that schemas follow JSON Schema specification.
        """
        # Create mock interface schema response with detailed schemas
        mock_interfaces = [
            InterfaceSchemaDefinition(
                task_id="task_001",
                interface_name="gmail_search_interface",
                description="Gmail search interface with schema validation",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query",
                            "minLength": 1,
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Max results",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 100,
                        },
                        "date_from": {
                            "type": "string",
                            "description": "Start date (YYYY-MM-DD)",
                            "pattern": "^\\d{4}-\\d{2}-\\d{2}$",  # Regex pattern
                        },
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "emails": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "subject": {"type": "string"},
                                },
                                "required": ["id", "subject"],
                            },
                        },
                        "count": {"type": "integer"},
                    },
                    "required": ["success", "emails", "count"],
                    "additionalProperties": False,
                },
            ),
        ]
        mock_response = InterfaceSchemaResponse(interfaces=mock_interfaces)

        # Setup mock invoke_structured_llm

        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        mock_invoke_llm.return_value = StructuredCallResult(
            result=mock_response,
            recovered_via_json=False,
            raw_text=None,
            model_name="test-model",
        )

        # Setup mock JobqueueClient and SchemaMatcher
        mock_client_instance = AsyncMock()
        mock_jobqueue_client.return_value = mock_client_instance

        mock_matcher_instance = AsyncMock()
        mock_matcher_instance.find_or_create_interface_master = AsyncMock(
            return_value={"id": "iface_001", "name": "gmail_search_interface"}
        )
        mock_schema_matcher.return_value = mock_matcher_instance

        # Create test state
        task_breakdown = create_mock_task_breakdown(1)
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Search Gmail with validation",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
        )

        # Execute node
        result = await interface_definition_node(state)

        # Verify results
        assert "interface_definitions" in result
        interface_def = result["interface_definitions"]["task_001"]

        # Verify schema structure
        assert "input_schema" in interface_def
        assert "output_schema" in interface_def

        # Verify input schema has required fields
        assert interface_def["input_schema"]["type"] == "object"
        assert "properties" in interface_def["input_schema"]
        assert "query" in interface_def["input_schema"]["properties"]
        assert "required" in interface_def["input_schema"]

        # Verify output schema has required fields
        assert interface_def["output_schema"]["type"] == "object"
        assert "properties" in interface_def["output_schema"]
        assert "success" in interface_def["output_schema"]["properties"]
        assert "required" in interface_def["output_schema"]

        # Verify regex pattern in input_schema was NOT over-escaped (should be \\d, not \\\\d)
        # fix_regex_over_escaping should have fixed any over-escaping
        date_pattern = interface_def["input_schema"]["properties"]["date_from"][
            "pattern"
        ]
        # After fix_regex_over_escaping, pattern should have double backslash (\\d)
        assert "\\d" in date_pattern

    @pytest.mark.asyncio
    async def test_interface_schema_definition_json_schema_generation(self):
        """Test that InterfaceSchemaDefinition generates JSON Schema with additionalProperties: false.

        Priority: High
        This is a regression test for OpenAI API compatibility (Issue #111).
        OpenAI's structured output API requires additionalProperties to be false.
        """
        # Generate JSON Schema from Pydantic model
        schema = InterfaceSchemaDefinition.model_json_schema()

        # Verify top-level additionalProperties is false
        assert schema.get("additionalProperties") is False, (
            "InterfaceSchemaDefinition must have additionalProperties: false for OpenAI API compatibility"
        )

        # Verify required fields are present
        assert "properties" in schema
        assert "required" in schema
        assert set(schema["required"]) == {
            "task_id",
            "interface_name",
            "description",
            "input_schema",
            "output_schema",
        }

        # Verify field types
        assert schema["properties"]["task_id"]["type"] == "string"
        assert schema["properties"]["interface_name"]["type"] == "string"
        assert schema["properties"]["description"]["type"] == "string"
        # input_schema and output_schema should be type: object (dict[str, Any])
        assert schema["properties"]["input_schema"]["type"] == "object"
        assert schema["properties"]["output_schema"]["type"] == "object"

    @pytest.mark.asyncio
    async def test_interface_schema_response_json_schema_generation(self):
        """Test that InterfaceSchemaResponse generates valid JSON Schema.

        Priority: Medium
        This ensures the wrapper model also produces OpenAI-compatible schemas.
        """
        # Generate JSON Schema from Pydantic model
        schema = InterfaceSchemaResponse.model_json_schema()

        # Verify schema structure
        assert "properties" in schema
        assert "interfaces" in schema["properties"]

        # Verify interfaces is an array
        assert schema["properties"]["interfaces"]["type"] == "array"
        assert "items" in schema["properties"]["interfaces"]

        # Verify items reference InterfaceSchemaDefinition
        # The $ref will point to definitions section
        items_schema = schema["properties"]["interfaces"]["items"]
        if "$ref" in items_schema:
            # Check that the reference exists in $defs
            ref_name = items_schema["$ref"].split("/")[-1]
            assert ref_name in schema.get("$defs", {})


@pytest.mark.unit
class TestNormalizeJsonSchemaProperties:
    """Unit tests for normalize_json_schema_properties function.

    Issue #310: Fix LLM-generated shorthand JSON Schema formats.
    """

    def test_normalize_shorthand_string_type(self):
        """Test normalizing ["string"] → {"type": "string"}."""
        from aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition import (
            normalize_json_schema_properties,
        )

        schema = {
            "type": "object",
            "properties": {
                "name": ["string"],
            },
        }

        result = normalize_json_schema_properties(schema)

        assert result["properties"]["name"] == {"type": "string"}

    def test_normalize_shorthand_boolean_type(self):
        """Test normalizing ["boolean"] → {"type": "boolean"}."""
        from aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition import (
            normalize_json_schema_properties,
        )

        schema = {
            "type": "object",
            "properties": {
                "active": ["boolean"],
            },
        }

        result = normalize_json_schema_properties(schema)

        assert result["properties"]["active"] == {"type": "boolean"}

    def test_normalize_multiple_shorthand_types(self):
        """Test normalizing multiple shorthand types in one schema."""
        from aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition import (
            normalize_json_schema_properties,
        )

        schema = {
            "type": "object",
            "properties": {
                "target_directory": ["string"],
                "recursive": ["boolean"],
                "allowed_extensions": ["array"],
                "max_depth": ["integer"],
                "config": ["object"],
            },
            "required": ["target_directory"],
            "additionalProperties": False,
        }

        result = normalize_json_schema_properties(schema)

        assert result["properties"]["target_directory"] == {"type": "string"}
        assert result["properties"]["recursive"] == {"type": "boolean"}
        assert result["properties"]["allowed_extensions"] == {"type": "array"}
        assert result["properties"]["max_depth"] == {"type": "integer"}
        assert result["properties"]["config"] == {"type": "object"}
        # Non-properties fields should be preserved
        assert result["required"] == ["target_directory"]
        assert result["additionalProperties"] is False

    def test_normalize_preserves_valid_schema(self):
        """Test that already-valid JSON Schema is preserved unchanged."""
        from aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition import (
            normalize_json_schema_properties,
        )

        schema = {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                    "minLength": 1,
                },
                "max_results": {
                    "type": "integer",
                    "default": 10,
                },
            },
            "required": ["query"],
        }

        result = normalize_json_schema_properties(schema)

        # Valid schema should be unchanged
        assert result == schema

    def test_normalize_nested_properties(self):
        """Test normalizing shorthand types in nested objects."""
        from aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition import (
            normalize_json_schema_properties,
        )

        schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": ["string"],
                            "count": ["integer"],
                        },
                    },
                },
            },
        }

        result = normalize_json_schema_properties(schema)

        # Check nested properties are normalized
        nested_props = result["properties"]["items"]["items"]["properties"]
        assert nested_props["id"] == {"type": "string"}
        assert nested_props["count"] == {"type": "integer"}

    def test_normalize_handles_empty_schema(self):
        """Test that empty schema is handled gracefully."""
        from aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition import (
            normalize_json_schema_properties,
        )

        schema: dict = {}
        result = normalize_json_schema_properties(schema)
        assert result == {}

    def test_normalize_handles_non_dict_input(self):
        """Test that non-dict input returns input unchanged."""
        from aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition import (
            normalize_json_schema_properties,
        )

        # Test with non-dict inputs
        assert normalize_json_schema_properties("string") == "string"  # type: ignore
        assert normalize_json_schema_properties(123) == 123  # type: ignore
        assert normalize_json_schema_properties(None) is None  # type: ignore

    def test_normalize_real_world_llm_output(self):
        """Test normalizing a real-world LLM-generated schema (Issue #310).

        This schema was actually generated by gemini-3-flash-preview and
        caused the error: 'boolean' is not of type 'object', 'boolean'
        """
        from aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition import (
            normalize_json_schema_properties,
        )

        # Real schema generated by LLM that caused validation failure
        schema = {
            "type": "object",
            "properties": {
                "target_directory": ["string"],
                "recursive": ["boolean"],
                "allowed_extensions": ["array"],
            },
            "required": ["target_directory"],
            "additionalProperties": False,
        }

        result = normalize_json_schema_properties(schema)

        # Verify the normalized schema is valid JSON Schema format
        assert result["type"] == "object"
        assert result["properties"]["target_directory"] == {"type": "string"}
        assert result["properties"]["recursive"] == {"type": "boolean"}
        assert result["properties"]["allowed_extensions"] == {"type": "array"}
        assert result["required"] == ["target_directory"]
        assert result["additionalProperties"] is False

    def test_normalize_bare_string_types(self):
        """Test normalizing bare string type names (Issue #310 follow-up).

        This schema pattern was also generated by gemini-3-flash-preview:
        {"properties": {"name": "string"}} instead of {"properties": {"name": {"type": "string"}}}
        """
        from aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition import (
            normalize_json_schema_properties,
        )

        # Real schema generated by LLM with bare string types
        schema = {
            "type": "object",
            "properties": {
                "directory_path": "string",
                "recursive": "boolean",
                "search_pattern": "string",
            },
            "required": ["directory_path"],
            "additionalProperties": False,
        }

        result = normalize_json_schema_properties(schema)

        # Verify the normalized schema is valid JSON Schema format
        assert result["type"] == "object"
        assert result["properties"]["directory_path"] == {"type": "string"}
        assert result["properties"]["recursive"] == {"type": "boolean"}
        assert result["properties"]["search_pattern"] == {"type": "string"}
        assert result["required"] == ["directory_path"]
        assert result["additionalProperties"] is False

    def test_normalize_mixed_formats(self):
        """Test normalizing a mix of shorthand and valid formats."""
        from aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition import (
            normalize_json_schema_properties,
        )

        schema = {
            "type": "object",
            "properties": {
                # Bare string format
                "name": "string",
                # Array shorthand format
                "active": ["boolean"],
                # Already valid format
                "count": {"type": "integer", "minimum": 0},
            },
        }

        result = normalize_json_schema_properties(schema)

        assert result["properties"]["name"] == {"type": "string"}
        assert result["properties"]["active"] == {"type": "boolean"}
        assert result["properties"]["count"] == {"type": "integer", "minimum": 0}

    def test_normalize_null_property_values(self):
        """Test normalizing null property values (Issue #310 follow-up).

        LLM sometimes generates null instead of a schema definition.
        """
        from aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition import (
            normalize_json_schema_properties,
        )

        schema = {
            "type": "object",
            "properties": {
                "directory_path": None,
            },
        }

        result = normalize_json_schema_properties(schema)

        # Null values should be normalized to {"type": "string"} as fallback
        assert result["properties"]["directory_path"] == {"type": "string"}

    def test_normalize_description_string_as_property(self):
        """Test normalizing description strings placed as property values (Issue #310 follow-up).

        LLM sometimes puts description text directly as property value instead of
        wrapping it in a proper schema object.
        """
        from aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition import (
            normalize_json_schema_properties,
        )

        schema = {
            "type": "object",
            "properties": {
                "user_request": {"type": "string"},
                "description": "ユーザーからの検索要求テキスト",
            },
        }

        result = normalize_json_schema_properties(schema)

        # The description string should be converted to a valid schema
        assert result["properties"]["user_request"] == {"type": "string"}
        assert result["properties"]["description"] == {
            "type": "string",
            "description": "ユーザーからの検索要求テキスト",
        }

    def test_normalize_numeric_property_values(self):
        """Test normalizing numeric property values (Issue #310 follow-up).

        LLM sometimes places numeric values (like minLength: 1) directly inside
        properties instead of wrapping them in proper schema objects.
        Error: 1 is not of type 'object', 'boolean'
        """
        from aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition import (
            normalize_json_schema_properties,
        )

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "count": 1,  # Numeric value directly as property (LLM error)
                "ratio": 3.14,  # Float value directly as property
            },
        }

        result = normalize_json_schema_properties(schema)

        # Numeric values should be converted to proper schema objects
        assert result["properties"]["name"] == {"type": "string"}
        assert result["properties"]["count"] == {"type": "integer", "default": 1}
        assert result["properties"]["ratio"] == {"type": "number", "default": 3.14}

    def test_normalize_malformed_enum_pattern(self):
        """Test normalizing malformed enum pattern (Issue #310 follow-up).

        LLM sometimes generates enum values as an array of objects like:
        [{'type': 'string', 'description': 'NEUTRAL'}, {'type': 'string', 'description': 'MALE'}]
        Instead of the correct JSON Schema format:
        {'type': 'string', 'enum': ['NEUTRAL', 'MALE']}
        Error: [...] is not of type 'object', 'boolean'
        """
        from aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition import (
            normalize_json_schema_properties,
        )

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "gender": [
                    {"type": "string", "description": "NEUTRAL"},
                    {"type": "string", "description": "MALE"},
                    {"type": "string", "description": "FEMALE"},
                ],
            },
        }

        result = normalize_json_schema_properties(schema)

        # Malformed enum should be converted to proper enum format
        assert result["properties"]["name"] == {"type": "string"}
        assert result["properties"]["gender"] == {
            "type": "string",
            "enum": ["NEUTRAL", "MALE", "FEMALE"],
        }
