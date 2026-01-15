"""Extended unit tests for SchemaEnricherSubWorkflow.

Issue #342 Phase C.3: Additional tests for coverage improvement.
"""

import pytest

from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
from aiagent.langgraph.jobGeneratorV2.types import (
    InterfaceSchema,
    TaskDefinition,
)


class TestExtractOpenapiConstraints:
    """Tests for _extract_openapi_constraints helper function."""

    def test_extract_constraints_exact_match(self):
        """Should extract constraints from exact endpoint match."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.enricher import (
            _extract_openapi_constraints,
        )

        specs = {
            "/v1/test": {
                "parameters": {
                    "query": {"type": "string", "maxLength": 100},
                    "limit": {"type": "integer", "default": 10},
                }
            }
        }

        result = _extract_openapi_constraints("/v1/test", specs)

        assert "query" in result
        assert result["query"]["maxLength"] == 100
        assert "limit" in result
        assert result["limit"]["default"] == 10

    def test_extract_constraints_prefix_match(self):
        """Should extract constraints from prefix match."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.enricher import (
            _extract_openapi_constraints,
        )

        specs = {
            "/v1/utility": {
                "parameters": {
                    "timeout": {"type": "integer", "minimum": 1},
                }
            }
        }

        result = _extract_openapi_constraints("/v1/utility/gmail/search", specs)

        assert "timeout" in result
        assert result["timeout"]["minimum"] == 1

    def test_extract_constraints_no_match(self):
        """Should return empty dict when no match."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.enricher import (
            _extract_openapi_constraints,
        )

        specs = {"/v1/other": {"parameters": {}}}

        result = _extract_openapi_constraints("/v1/test", specs)

        assert result == {}

    def test_extract_constraints_empty_specs(self):
        """Should return empty dict for empty specs."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.enricher import (
            _extract_openapi_constraints,
        )

        result = _extract_openapi_constraints("/v1/test", {})
        assert result == {}

    def test_extract_constraints_empty_endpoint(self):
        """Should return empty dict for empty endpoint."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.enricher import (
            _extract_openapi_constraints,
        )

        result = _extract_openapi_constraints("", {"/v1/test": {}})
        assert result == {}

    def test_extract_constraints_various_fields(self):
        """Should extract all supported constraint fields."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.enricher import (
            _extract_openapi_constraints,
        )

        specs = {
            "/v1/test": {
                "parameters": {
                    "text": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 1000,
                        "pattern": "^[a-z]+$",
                        "default": "hello",
                    },
                    "count": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                    },
                }
            }
        }

        result = _extract_openapi_constraints("/v1/test", specs)

        assert result["text"]["minLength"] == 1
        assert result["text"]["maxLength"] == 1000
        assert result["text"]["pattern"] == "^[a-z]+$"
        assert result["text"]["default"] == "hello"
        assert result["count"]["minimum"] == 0
        assert result["count"]["maximum"] == 100


class TestApplyConstraintsToSchema:
    """Tests for _apply_constraints_to_schema helper function."""

    def test_apply_constraints_to_existing_properties(self):
        """Should merge constraints into existing properties."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.enricher import (
            _apply_constraints_to_schema,
        )

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
        }
        constraints = {
            "name": {"maxLength": 100},
        }

        result = _apply_constraints_to_schema(schema, constraints)

        assert result["properties"]["name"]["type"] == "string"
        assert result["properties"]["name"]["maxLength"] == 100

    def test_apply_constraints_no_override(self):
        """Should not override existing values."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.enricher import (
            _apply_constraints_to_schema,
        )

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "maxLength": 50},  # Already has maxLength
            },
        }
        constraints = {
            "name": {"maxLength": 100},  # Different value
        }

        result = _apply_constraints_to_schema(schema, constraints)

        # Should keep original value
        assert result["properties"]["name"]["maxLength"] == 50

    def test_apply_constraints_empty(self):
        """Should return schema unchanged for empty constraints."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.enricher import (
            _apply_constraints_to_schema,
        )

        schema = {"type": "object", "properties": {"name": {"type": "string"}}}

        result = _apply_constraints_to_schema(schema, {})

        assert result == schema

    def test_apply_constraints_non_dict_schema(self):
        """Should return non-dict schema unchanged."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.enricher import (
            _apply_constraints_to_schema,
        )

        result = _apply_constraints_to_schema("not a dict", {"name": {}})
        assert result == "not a dict"

    def test_apply_constraints_missing_property(self):
        """Should ignore constraints for non-existing properties."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.enricher import (
            _apply_constraints_to_schema,
        )

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
        }
        constraints = {
            "other_field": {"maxLength": 100},  # Property doesn't exist
        }

        result = _apply_constraints_to_schema(schema, constraints)

        assert "other_field" not in result["properties"]


class TestSchemaEnricherWithOpenAPI:
    """Tests for SchemaEnricherSubWorkflow with OpenAPI specs."""

    @pytest.fixture
    def sample_task(self) -> TaskDefinition:
        """Create sample task."""
        return TaskDefinition(
            id="task_001",
            name="Test Task",
            description="Test",
            task_type="test",
            recommended_api="/v1/utility/gmail/search",
            priority=1,
        )

    @pytest.fixture
    def sample_interface(self) -> InterfaceSchema:
        """Create sample interface."""
        return InterfaceSchema(
            task_id="task_001",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
            },
            output_schema={"type": "object"},
        )

    @pytest.fixture
    def mock_context(self) -> ExecutionContext:
        """Create mock context."""
        return ExecutionContext(
            job_id="test-job",
            user_requirement="Test",
        )

    @pytest.mark.asyncio
    async def test_enrich_with_openapi_specs(
        self,
        sample_task: TaskDefinition,
        sample_interface: InterfaceSchema,
        mock_context: ExecutionContext,
    ):
        """Should enrich interface with OpenAPI constraints."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.enricher import (
            SchemaEnricherSubWorkflow,
        )

        openapi_specs = {
            "/v1/utility/gmail/search": {
                "parameters": {
                    "query": {"type": "string", "maxLength": 500},
                }
            }
        }

        enricher = SchemaEnricherSubWorkflow()
        enriched, report = await enricher.enrich(
            [sample_task], {"task_001": sample_interface}, openapi_specs, mock_context
        )

        assert (
            enriched["task_001"].input_schema["properties"]["query"]["maxLength"] == 500
        )
        assert report.enriched_count == 1
        assert len(report.details) == 1

    @pytest.mark.asyncio
    async def test_enrich_task_not_in_lookup(
        self,
        sample_interface: InterfaceSchema,
        mock_context: ExecutionContext,
    ):
        """Should handle interface without matching task."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.enricher import (
            SchemaEnricherSubWorkflow,
        )

        # Empty task list but interface exists
        enricher = SchemaEnricherSubWorkflow()
        enriched, report = await enricher.enrich(
            [], {"task_001": sample_interface}, {"/v1/test": {}}, mock_context
        )

        assert "task_001" in enriched
        assert report.skipped_count >= 1
