"""Unit tests for Issue #357: JSON Schema Single Source of Truth.

This module tests:
1. JSON Schema file existence and validity
2. Schema structure compliance with Draft 2020-12
3. Required definitions ($defs) existence
4. Schema properties and types

TDD Phase: RED - These tests should fail initially.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

# Path to the JSON Schema file
# expertAgent/tests/unit/test_issue_357_json_schema.py -> MySwiftAgent/shared
SCHEMA_PATH = (
    Path(__file__).parents[3] / "shared" / "schemas" / "taskflow" / "v1" / "workflow.schema.json"
)


# =============================================================================
# Module-level Fixtures (DRY: Avoid duplicate fixtures across test classes)
# =============================================================================


@pytest.fixture
def loaded_schema() -> dict[str, Any]:
    """Load and return the JSON Schema.

    This is a module-level fixture to avoid duplication across test classes.
    All classes that need the schema use this single fixture.
    """
    if not SCHEMA_PATH.exists():
        pytest.skip("Schema file does not exist yet")
    result: dict[str, Any] = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return result


# =============================================================================
# Test Classes
# =============================================================================


class TestJsonSchemaExistence:
    """Tests for JSON Schema file existence and validity."""

    def test_schema_file_exists(self) -> None:
        """Verify JSON Schema file exists at expected location.

        Acceptance Criteria:
        - shared/schemas/taskflow/v1/workflow.schema.json exists
        """
        assert SCHEMA_PATH.exists(), (
            f"JSON Schema file not found at {SCHEMA_PATH}. "
            "Expected: shared/schemas/taskflow/v1/workflow.schema.json"
        )

    def test_schema_file_is_valid_json(self) -> None:
        """Verify JSON Schema file contains valid JSON."""
        if not SCHEMA_PATH.exists():
            pytest.skip("Schema file does not exist yet")

        content = SCHEMA_PATH.read_text(encoding="utf-8")
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            pytest.fail(f"Schema file is not valid JSON: {e}")

    def test_schema_is_not_empty(self) -> None:
        """Verify JSON Schema file is not empty."""
        if not SCHEMA_PATH.exists():
            pytest.skip("Schema file does not exist yet")

        content = SCHEMA_PATH.read_text(encoding="utf-8")
        data = json.loads(content)
        assert data, "Schema file is empty"
        assert isinstance(data, dict), "Schema must be a JSON object"


class TestJsonSchemaDraft:
    """Tests for JSON Schema Draft 2020-12 compliance."""

    def test_schema_has_schema_property(self, loaded_schema: dict[str, Any]) -> None:
        """Verify $schema property exists and uses Draft 2020-12."""
        assert "$schema" in loaded_schema, "Schema must have $schema property"
        assert "draft/2020-12" in loaded_schema["$schema"], (
            f"Schema must use Draft 2020-12, got: {loaded_schema['$schema']}"
        )

    def test_schema_has_id_property(self, loaded_schema: dict[str, Any]) -> None:
        """Verify $id property exists."""
        assert "$id" in loaded_schema, "Schema must have $id property"
        assert isinstance(loaded_schema["$id"], str), "$id must be a string"
        assert len(loaded_schema["$id"]) > 0, "$id must not be empty"

    def test_schema_has_title(self, loaded_schema: dict[str, Any]) -> None:
        """Verify title property exists."""
        assert "title" in loaded_schema, "Schema must have title property"
        assert "TaskFlow" in loaded_schema["title"], (
            f"Title should contain 'TaskFlow', got: {loaded_schema['title']}"
        )


class TestJsonSchemaStructure:
    """Tests for JSON Schema structure and properties."""

    def test_schema_type_is_object(self, loaded_schema: dict[str, Any]) -> None:
        """Verify schema type is object."""
        assert loaded_schema.get("type") == "object", "Schema type must be 'object'"

    def test_schema_has_required_fields(self, loaded_schema: dict[str, Any]) -> None:
        """Verify schema has required fields array."""
        assert "required" in loaded_schema, "Schema must have 'required' property"
        required = loaded_schema["required"]
        expected_required = ["workflow_name", "input_schema", "output_schema", "steps", "output"]
        for field in expected_required:
            assert field in required, f"'{field}' should be in required list"

    def test_schema_has_properties(self, loaded_schema: dict[str, Any]) -> None:
        """Verify schema has properties definition."""
        assert "properties" in loaded_schema, "Schema must have 'properties'"
        properties = loaded_schema["properties"]
        expected_properties = [
            "workflow_name",
            "description",
            "input_schema",
            "output_schema",
            "steps",
            "output",
        ]
        for prop in expected_properties:
            assert prop in properties, f"Property '{prop}' should be defined"

    def test_workflow_name_has_pattern(self, loaded_schema: dict[str, Any]) -> None:
        """Verify workflow_name has pattern validation."""
        properties = loaded_schema.get("properties", {})
        workflow_name = properties.get("workflow_name", {})
        assert "pattern" in workflow_name, "workflow_name should have pattern"
        # Pattern should match valid identifiers
        assert "a-zA-Z" in workflow_name["pattern"], "workflow_name pattern should include letters"

    def test_steps_is_array(self, loaded_schema: dict[str, Any]) -> None:
        """Verify steps is defined as array."""
        properties = loaded_schema.get("properties", {})
        steps = properties.get("steps", {})
        assert steps.get("type") == "array", "steps should be array type"
        assert "items" in steps, "steps should have items definition"


class TestJsonSchemaDefinitions:
    """Tests for $defs (definitions) in JSON Schema."""

    def test_schema_has_defs(self, loaded_schema: dict[str, Any]) -> None:
        """Verify $defs property exists."""
        assert "$defs" in loaded_schema, "Schema must have '$defs' property"

    def test_defs_has_step(self, loaded_schema: dict[str, Any]) -> None:
        """Verify Step definition exists."""
        defs = loaded_schema.get("$defs", {})
        assert "Step" in defs, "'Step' should be defined in $defs"
        step = defs["Step"]
        assert step.get("type") == "object", "Step should be object type"

    def test_defs_has_api_rest_config(self, loaded_schema: dict[str, Any]) -> None:
        """Verify ApiRestConfig definition exists."""
        defs = loaded_schema.get("$defs", {})
        assert "ApiRestConfig" in defs, "'ApiRestConfig' should be defined in $defs"
        config = defs["ApiRestConfig"]
        assert config.get("type") == "object", "ApiRestConfig should be object type"
        # Check required fields
        assert "method" in config.get("properties", {}), (
            "ApiRestConfig should have 'method' property"
        )
        assert "url" in config.get("properties", {}), "ApiRestConfig should have 'url' property"

    def test_defs_has_code_js_config(self, loaded_schema: dict[str, Any]) -> None:
        """Verify CodeJsConfig definition exists."""
        defs = loaded_schema.get("$defs", {})
        assert "CodeJsConfig" in defs, "'CodeJsConfig' should be defined in $defs"
        config = defs["CodeJsConfig"]
        assert config.get("type") == "object", "CodeJsConfig should be object type"
        assert "path" in config.get("properties", {}), "CodeJsConfig should have 'path' property"

    def test_defs_has_transform_config(self, loaded_schema: dict[str, Any]) -> None:
        """Verify TransformConfig definition exists."""
        defs = loaded_schema.get("$defs", {})
        assert "TransformConfig" in defs, "'TransformConfig' should be defined in $defs"
        config = defs["TransformConfig"]
        assert config.get("type") == "object", "TransformConfig should be object type"
        assert "mode" in config.get("properties", {}), "TransformConfig should have 'mode' property"

    def test_defs_has_io_schema(self, loaded_schema: dict[str, Any]) -> None:
        """Verify IOSchema definition exists."""
        defs = loaded_schema.get("$defs", {})
        assert "IOSchema" in defs, "'IOSchema' should be defined in $defs"

    def test_defs_has_simple_type(self, loaded_schema: dict[str, Any]) -> None:
        """Verify SimpleType definition exists."""
        defs = loaded_schema.get("$defs", {})
        assert "SimpleType" in defs, "'SimpleType' should be defined in $defs"
        simple_type = defs["SimpleType"]
        # Should be enum with string, number, boolean, array, object, null
        assert "enum" in simple_type, "SimpleType should be an enum"
        expected_types = ["string", "number", "boolean", "array", "object", "null"]
        for t in expected_types:
            assert t in simple_type["enum"], f"'{t}' should be in SimpleType enum"


class TestJsonSchemaValidation:
    """Tests for JSON Schema validation using jsonschema library."""

    def test_schema_is_valid_json_schema(self, loaded_schema: dict[str, Any]) -> None:
        """Verify the schema itself is a valid JSON Schema."""
        try:
            from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

            Draft202012Validator.check_schema(loaded_schema)
        except ImportError:
            pytest.skip("jsonschema library not installed")

    def test_valid_workflow_passes_validation(self, loaded_schema: dict[str, Any]) -> None:
        """Verify a valid workflow passes schema validation."""
        try:
            from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
        except ImportError:
            pytest.skip("jsonschema library not installed")

        valid_workflow = {
            "workflow_name": "test_workflow",
            "description": "A test workflow",
            "input_schema": {"query": "string"},
            "output_schema": {"result": "string"},
            "steps": [
                {
                    "id": "step_001",
                    "type": "api_rest",
                    "config": {
                        "step_type": "api_rest",
                        "method": "GET",
                        "url": "https://api.example.com/data",
                    },
                }
            ],
            "output": {"result": "${step_001.output}"},
        }

        validator = Draft202012Validator(loaded_schema)
        errors = list(validator.iter_errors(valid_workflow))
        assert not errors, f"Valid workflow should pass validation: {errors}"

    def test_invalid_workflow_fails_validation(self, loaded_schema: dict[str, Any]) -> None:
        """Verify an invalid workflow fails schema validation."""
        try:
            from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
        except ImportError:
            pytest.skip("jsonschema library not installed")

        invalid_workflow = {
            "workflow_name": "123invalid",  # Invalid: starts with number
            "steps": [],  # Invalid: empty steps
        }

        validator = Draft202012Validator(loaded_schema)
        errors = list(validator.iter_errors(invalid_workflow))
        assert errors, "Invalid workflow should fail validation"
