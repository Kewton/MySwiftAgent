"""Extended unit tests for SchemaGeneratorSubWorkflow.

Issue #342 Phase C.1: Additional tests for coverage improvement.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aiagent.langgraph.jobGeneratorV2.types import (
    Phase,
    TaskDefinition,
)
from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext


class TestNormalizeJsonSchemaPropertiesExtended:
    """Extended tests for normalize_json_schema_properties function."""

    def test_normalize_null_value(self):
        """Should handle null value for property."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            normalize_json_schema_properties,
        )

        schema = {"properties": {"name": None}}
        result = normalize_json_schema_properties(schema)

        assert result["properties"]["name"] == {"type": "string"}

    def test_normalize_integer_value(self):
        """Should handle integer value for property."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            normalize_json_schema_properties,
        )

        schema = {"properties": {"count": 5}}
        result = normalize_json_schema_properties(schema)

        assert result["properties"]["count"] == {"type": "integer", "default": 5}

    def test_normalize_float_value(self):
        """Should handle float value for property."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            normalize_json_schema_properties,
        )

        schema = {"properties": {"rate": 3.14}}
        result = normalize_json_schema_properties(schema)

        assert result["properties"]["rate"] == {"type": "number", "default": 3.14}

    def test_normalize_non_type_string(self):
        """Should handle non-type string value."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            normalize_json_schema_properties,
        )

        schema = {"properties": {"desc": "This is a description"}}
        result = normalize_json_schema_properties(schema)

        assert result["properties"]["desc"]["type"] == "string"
        assert "description" in result["properties"]["desc"]

    def test_normalize_malformed_enum_pattern(self):
        """Should handle malformed enum pattern from LLM."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            normalize_json_schema_properties,
        )

        # LLM sometimes generates this pattern instead of proper enum
        schema = {
            "properties": {
                "status": [
                    {"type": "string", "description": "ACTIVE"},
                    {"type": "string", "description": "INACTIVE"},
                ]
            }
        }
        result = normalize_json_schema_properties(schema)

        assert result["properties"]["status"]["type"] == "string"
        assert result["properties"]["status"]["enum"] == ["ACTIVE", "INACTIVE"]

    def test_normalize_removes_metadata_fields(self):
        """Should remove metadata fields from schema."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            normalize_json_schema_properties,
        )

        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "task_id": "task_001",  # Should be removed
            "interface_name": "test_interface",  # Should be removed
        }
        result = normalize_json_schema_properties(schema)

        assert "task_id" not in result
        assert "interface_name" not in result
        assert "type" in result

    def test_normalize_non_dict_properties(self):
        """Should handle non-dict properties value."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            normalize_json_schema_properties,
        )

        schema = {"properties": "invalid"}
        result = normalize_json_schema_properties(schema)

        assert result["properties"] == {}

    def test_normalize_items_in_array(self):
        """Should normalize items in array schema."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            normalize_json_schema_properties,
        )

        schema = {
            "properties": {
                "tags": {
                    "type": "array",
                    "items": "string"  # Should be normalized
                }
            }
        }
        result = normalize_json_schema_properties(schema)

        assert result["properties"]["tags"]["items"] == {"type": "string"}

    def test_normalize_nested_dict(self):
        """Should recursively normalize nested objects."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            normalize_json_schema_properties,
        )

        schema = {
            "properties": {
                "data": {
                    "type": "object",
                    "properties": {
                        "nested": "string"
                    }
                }
            }
        }
        result = normalize_json_schema_properties(schema)

        assert result["properties"]["data"]["properties"]["nested"] == {"type": "string"}

    def test_normalize_preserves_string_array_keywords(self):
        """Should preserve string array keywords like required, enum."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            normalize_json_schema_properties,
        )

        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
            "enum": ["A", "B"],
            "default": [1, 2, 3],
        }
        result = normalize_json_schema_properties(schema)

        assert result["required"] == ["name"]
        assert result["enum"] == ["A", "B"]
        assert result["default"] == [1, 2, 3]

    def test_normalize_non_dict_schema(self):
        """Should return non-dict schema unchanged."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            normalize_json_schema_properties,
        )

        result = normalize_json_schema_properties("not a dict")
        assert result == "not a dict"

    def test_normalize_list_in_properties(self):
        """Should handle list values in properties."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            normalize_json_schema_properties,
        )

        # A generic list (not shorthand type)
        schema = {
            "properties": {
                "items": [{"type": "string"}, {"type": "number"}]
            }
        }
        result = normalize_json_schema_properties(schema)

        # Each item should be normalized
        assert len(result["properties"]["items"]) == 2


class TestValidateSchemaResponse:
    """Tests for _validate_schema_response function."""

    def test_validate_none_response(self):
        """Should raise ValueError for None response."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            _validate_schema_response,
        )

        with pytest.raises(ValueError) as exc_info:
            _validate_schema_response(None)

        assert "empty" in str(exc_info.value).lower()

    def test_validate_empty_interfaces(self):
        """Should raise ValueError for empty interfaces."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            _validate_schema_response,
        )

        mock_response = MagicMock()
        mock_response.interfaces = []

        with pytest.raises(ValueError) as exc_info:
            _validate_schema_response(mock_response)

        assert "no interfaces" in str(exc_info.value).lower()

    def test_validate_valid_response(self):
        """Should return valid response."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            _validate_schema_response,
        )

        mock_response = MagicMock()
        mock_response.interfaces = [MagicMock()]

        result = _validate_schema_response(mock_response)
        assert result == mock_response


class TestSchemaGeneratorLLMError:
    """Tests for SchemaGeneratorSubWorkflow error handling."""

    @pytest.fixture
    def sample_task(self) -> TaskDefinition:
        """Create sample task."""
        return TaskDefinition(
            id="task_001",
            name="Test Task",
            description="Test task description",
            task_type="test",
            recommended_api="/test",
            priority=1,
        )

    @pytest.fixture
    def mock_context(self) -> ExecutionContext:
        """Create mock context."""
        return ExecutionContext(
            job_id="test-job",
            user_requirement="Test requirement",
        )

    @pytest.mark.asyncio
    async def test_generate_handles_llm_error(
        self, sample_task: TaskDefinition, mock_context: ExecutionContext
    ):
        """generate() should raise WorkflowError on LLM failure."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            SchemaGeneratorSubWorkflow,
        )
        from aiagent.langgraph.jobGeneratorV2.protocols import WorkflowError
        from aiagent.langgraph.jobGeneratorV2.llm_utils import (
            StructuredLLMError,
        )

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator.invoke_structured_llm"
        ) as mock_llm:
            mock_llm.side_effect = StructuredLLMError("LLM call failed")

            generator = SchemaGeneratorSubWorkflow()

            with pytest.raises(WorkflowError) as exc_info:
                await generator.generate([sample_task], mock_context)

            assert "LLM" in str(exc_info.value)
