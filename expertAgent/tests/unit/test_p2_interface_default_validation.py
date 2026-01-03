"""Unit tests for P2-9: interface_definition default validation (Issue #340).

Tests for Layer 0 validation: detecting and removing invalid default values
in array type properties where default contains objects but items.type is primitive.
"""

from aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition import (
    normalize_json_schema_properties,
)


class TestNormalizeJsonSchemaPropertiesDefaultValidation:
    """Tests for normalize_json_schema_properties default value validation."""

    def test_removes_object_array_default_for_string_items(self):
        """Should remove default with object array when items.type is string."""
        schema = {
            "type": "object",
            "properties": {
                "focus_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [
                        {"type": "string", "description": "latest news"},
                        {"type": "string", "description": "main topics"},
                    ],
                },
            },
        }

        result = normalize_json_schema_properties(schema)

        # default should be removed because it contains objects
        assert "default" not in result["properties"]["focus_points"]

    def test_keeps_valid_string_array_default(self):
        """Should keep valid string array default."""
        schema = {
            "type": "object",
            "properties": {
                "focus_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["latest news", "main topics"],
                },
            },
        }

        result = normalize_json_schema_properties(schema)

        # default should be preserved
        assert result["properties"]["focus_points"]["default"] == [
            "latest news",
            "main topics",
        ]

    def test_removes_object_array_default_for_number_items(self):
        """Should remove default with object array when items.type is number."""
        schema = {
            "type": "object",
            "properties": {
                "scores": {
                    "type": "array",
                    "items": {"type": "number"},
                    "default": [
                        {"value": 1.0},
                        {"value": 2.0},
                    ],
                },
            },
        }

        result = normalize_json_schema_properties(schema)

        # default should be removed because it contains objects
        assert "default" not in result["properties"]["scores"]

    def test_keeps_valid_number_array_default(self):
        """Should keep valid number array default."""
        schema = {
            "type": "object",
            "properties": {
                "scores": {
                    "type": "array",
                    "items": {"type": "number"},
                    "default": [1.0, 2.5, 3.7],
                },
            },
        }

        result = normalize_json_schema_properties(schema)

        # default should be preserved
        assert result["properties"]["scores"]["default"] == [1.0, 2.5, 3.7]

    def test_removes_object_array_default_for_integer_items(self):
        """Should remove default with object array when items.type is integer."""
        schema = {
            "type": "object",
            "properties": {
                "counts": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "default": [
                        {"count": 1},
                        {"count": 2},
                    ],
                },
            },
        }

        result = normalize_json_schema_properties(schema)

        # default should be removed because it contains objects
        assert "default" not in result["properties"]["counts"]

    def test_keeps_valid_integer_array_default(self):
        """Should keep valid integer array default."""
        schema = {
            "type": "object",
            "properties": {
                "counts": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "default": [1, 2, 3],
                },
            },
        }

        result = normalize_json_schema_properties(schema)

        # default should be preserved
        assert result["properties"]["counts"]["default"] == [1, 2, 3]

    def test_removes_object_array_default_for_boolean_items(self):
        """Should remove default with object array when items.type is boolean."""
        schema = {
            "type": "object",
            "properties": {
                "flags": {
                    "type": "array",
                    "items": {"type": "boolean"},
                    "default": [
                        {"flag": True},
                        {"flag": False},
                    ],
                },
            },
        }

        result = normalize_json_schema_properties(schema)

        # default should be removed because it contains objects
        assert "default" not in result["properties"]["flags"]

    def test_keeps_valid_boolean_array_default(self):
        """Should keep valid boolean array default."""
        schema = {
            "type": "object",
            "properties": {
                "flags": {
                    "type": "array",
                    "items": {"type": "boolean"},
                    "default": [True, False, True],
                },
            },
        }

        result = normalize_json_schema_properties(schema)

        # default should be preserved
        assert result["properties"]["flags"]["default"] == [True, False, True]

    def test_keeps_object_array_default_for_object_items(self):
        """Should keep object array default when items.type is object."""
        schema = {
            "type": "object",
            "properties": {
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                        },
                    },
                    "default": [
                        {"title": "Result 1"},
                        {"title": "Result 2"},
                    ],
                },
            },
        }

        result = normalize_json_schema_properties(schema)

        # default should be preserved for object items
        assert result["properties"]["results"]["default"] == [
            {"title": "Result 1"},
            {"title": "Result 2"},
        ]

    def test_non_array_type_untouched(self):
        """Should not affect non-array type properties."""
        schema = {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "default": "sample",
                },
                "count": {
                    "type": "integer",
                    "default": 10,
                },
            },
        }

        result = normalize_json_schema_properties(schema)

        # defaults should be preserved for non-array types
        assert result["properties"]["name"]["default"] == "sample"
        assert result["properties"]["count"]["default"] == 10

    def test_mixed_array_with_some_objects(self):
        """Should remove default when any element is an object (for primitive items)."""
        schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [
                        "valid string",
                        {"type": "string", "description": "invalid"},
                        "another valid string",
                    ],
                },
            },
        }

        result = normalize_json_schema_properties(schema)

        # default should be removed because it contains at least one object
        assert "default" not in result["properties"]["items"]

    def test_empty_default_array(self):
        """Should keep empty default array."""
        schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                },
            },
        }

        result = normalize_json_schema_properties(schema)

        # empty default should be preserved
        assert result["properties"]["items"]["default"] == []

    def test_array_without_items_type(self):
        """Should handle array without items.type defined."""
        schema = {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "default": [{"key": "value"}],
                },
            },
        }

        result = normalize_json_schema_properties(schema)

        # Without items.type, we cannot validate, so keep as-is
        assert result["properties"]["data"]["default"] == [{"key": "value"}]

    def test_preserves_other_array_properties(self):
        """Should preserve other array properties when removing default."""
        schema = {
            "type": "object",
            "properties": {
                "focus_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Points to focus on",
                    "minItems": 1,
                    "maxItems": 10,
                    "default": [{"type": "string", "description": "invalid"}],
                },
            },
        }

        result = normalize_json_schema_properties(schema)

        # default should be removed, but other properties should be preserved
        assert "default" not in result["properties"]["focus_points"]
        assert (
            result["properties"]["focus_points"]["description"] == "Points to focus on"
        )
        assert result["properties"]["focus_points"]["minItems"] == 1
        assert result["properties"]["focus_points"]["maxItems"] == 10
        assert result["properties"]["focus_points"]["items"] == {"type": "string"}

    def test_nested_properties_with_invalid_default(self):
        """Should handle nested properties with invalid default."""
        schema = {
            "type": "object",
            "properties": {
                "config": {
                    "type": "object",
                    "properties": {
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "default": [{"tag": "invalid"}],
                        },
                    },
                },
            },
        }

        result = normalize_json_schema_properties(schema)

        # nested default should be removed
        assert "default" not in result["properties"]["config"]["properties"]["tags"]
