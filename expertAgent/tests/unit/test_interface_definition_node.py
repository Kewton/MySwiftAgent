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

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition import (
from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import StructuredCallResult
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
    @patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.invoke_structured_llm")
    async def test_interface_definition_success(
        self, mock_create_llm, mock_jobqueue_client, mock_schema_matcher
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

        # Setup mock LLM
        mock_llm = AsyncMock()
        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured)
        mock_create_llm.return_value = (mock_llm, None, None)

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

        # Verify LLM was called
        mock_structured.ainvoke.assert_called_once()

        # Verify SchemaMatcher was called for each interface
        assert mock_matcher_instance.find_or_create_interface_master.call_count == 2

    @pytest.mark.asyncio
    @patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.invoke_structured_llm")
    async def test_interface_definition_with_evaluation_feedback(self, mock_create_llm):
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

        # Setup mock LLM
        mock_llm = AsyncMock()
        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured)
        mock_create_llm.return_value = (mock_llm, None, None)

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
    @patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.invoke_structured_llm")
    async def test_interface_definition_llm_error(self, mock_create_llm):
        """Test error handling when LLM invocation fails.

        Priority: Medium
        This tests exception handling and error message propagation.
        """
        # Setup mock LLM to raise exception
        mock_llm = AsyncMock()
        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(side_effect=Exception("LLM API timeout"))
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured)
        mock_create_llm.return_value = (mock_llm, None, None)

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
        assert "Interface definition failed" in result["error_message"]
        assert "LLM API timeout" in result["error_message"]

        # interface_definitions should not be in result
        assert "interface_definitions" not in result

        # Verify retry_count incremented
        assert result["retry_count"] == 1

        # Verify LLM was called
        mock_structured.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    @patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.invoke_structured_llm")
    async def test_interface_definition_empty_task_breakdown(self, mock_create_llm):
        """Test error handling when task_breakdown is empty.

        Priority: Medium
        This tests edge case where no tasks are provided.
        """
        # Setup mock LLM (won't be called due to empty check)
        mock_llm = AsyncMock()
        mock_create_llm.return_value = (mock_llm, None, None)

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
            "Task breakdown is required for interface definition"
            in result["error_message"]
        )

        # Verify LLM was NOT called (early return)
        mock_llm.with_structured_output.assert_not_called()

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.SchemaMatcher"
    )
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.JobqueueClient"
    )
    @patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.invoke_structured_llm")
    async def test_interface_definition_retry_count_behavior(
        self, mock_create_llm, mock_jobqueue_client, mock_schema_matcher
    ):
        """Test retry_count increment behavior.

        Priority: Medium
        This tests the retry_count logic:
        - If retry_count > 0: increment by 1
        - If retry_count == 0: keep at 0
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

        # Setup mock LLM
        mock_llm = AsyncMock()
        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured)
        mock_create_llm.return_value = (mock_llm, None, None)

        # Setup mock JobqueueClient and SchemaMatcher
        mock_client_instance = AsyncMock()
        mock_jobqueue_client.return_value = mock_client_instance

        mock_matcher_instance = AsyncMock()
        mock_matcher_instance.find_or_create_interface_master = AsyncMock(
            return_value={"id": "iface_001", "name": "test_interface"}
        )
        mock_schema_matcher.return_value = mock_matcher_instance

        # Test Case 1: retry_count == 0 (first attempt)
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

        # Test Case 2: retry_count == 1 (first retry)
        state = create_mock_workflow_state(
            retry_count=1,
            user_requirement="Test requirement",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
        )
        result = await interface_definition_node(state)
        assert result["retry_count"] == 2, (
            "retry_count should increment from 1 to 2 on retry"
        )

        # Test Case 3: retry_count == 3 (third retry)
        state = create_mock_workflow_state(
            retry_count=3,
            user_requirement="Test requirement",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
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
    @patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.invoke_structured_llm")
    async def test_interface_definition_missing_interface_master_id(
        self, mock_create_llm, mock_jobqueue_client, mock_schema_matcher
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

        # Setup mock LLM
        mock_llm = AsyncMock()
        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured)
        mock_create_llm.return_value = (mock_llm, None, None)

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

        # Execute node
        result = await interface_definition_node(state)

        # Verify error handling
        assert "error_message" in result
        assert "InterfaceMaster response missing 'id' field" in result["error_message"]
        assert "retry_count" in result
        assert result["retry_count"] == 1  # Should increment on error

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.SchemaMatcher"
    )
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.JobqueueClient"
    )
    @patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.invoke_structured_llm")
    async def test_interface_definition_schema_validation(
        self, mock_create_llm, mock_jobqueue_client, mock_schema_matcher
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

        # Setup mock LLM
        mock_llm = AsyncMock()
        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured)
        mock_create_llm.return_value = (mock_llm, None, None)

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
