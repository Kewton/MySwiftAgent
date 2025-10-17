"""Mock data generator for JSON Schema-based interface testing.

This module provides utilities to generate mock data that conforms to JSON Schema
specifications, primarily used for testing Interface Validation functionality.
"""

import random
import string
from datetime import UTC, datetime
from typing import Any


class InterfaceMockGenerator:
    """Generate mock data conforming to JSON Schema specifications."""

    @staticmethod
    def generate_mock_data(schema: dict[str, Any]) -> dict[str, Any]:
        """Generate mock data based on JSON Schema.

        Args:
            schema: JSON Schema definition (JSON Schema Draft 7)

        Returns:
            Mock data dictionary conforming to the schema

        Examples:
            >>> schema = {
            ...     "type": "object",
            ...     "properties": {
            ...         "name": {"type": "string"},
            ...         "age": {"type": "number"}
            ...     },
            ...     "required": ["name"]
            ... }
            >>> data = InterfaceMockGenerator.generate_mock_data(schema)
            >>> isinstance(data, dict)
            True
            >>> "name" in data
            True
        """
        schema_type = schema.get("type", "object")

        if schema_type == "object":
            return InterfaceMockGenerator._generate_object(schema)
        elif schema_type == "array":
            return InterfaceMockGenerator._generate_array(schema)
        elif schema_type == "string":
            return InterfaceMockGenerator._generate_string(schema)
        elif schema_type == "number" or schema_type == "integer":
            return InterfaceMockGenerator._generate_number(schema)
        elif schema_type == "boolean":
            return InterfaceMockGenerator._generate_boolean(schema)
        else:
            return None

    @staticmethod
    def _generate_object(schema: dict[str, Any]) -> dict[str, Any]:
        """Generate mock object data."""
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        result = {}

        # Generate all required properties
        for prop_name in required:
            if prop_name in properties:
                prop_schema = properties[prop_name]
                result[prop_name] = InterfaceMockGenerator.generate_mock_data(
                    prop_schema
                )

        # Optionally generate some non-required properties (50% chance)
        for prop_name, prop_schema in properties.items():
            if prop_name not in required and random.random() > 0.5:
                result[prop_name] = InterfaceMockGenerator.generate_mock_data(
                    prop_schema
                )

        return result

    @staticmethod
    def _generate_array(schema: dict[str, Any]) -> list[Any]:
        """Generate mock array data."""
        items_schema = schema.get("items", {"type": "string"})
        min_items = schema.get("minItems", 1)
        max_items = schema.get("maxItems", 5)

        # Generate random number of items within constraints
        num_items = random.randint(min_items, max_items)

        return [
            InterfaceMockGenerator.generate_mock_data(items_schema)
            for _ in range(num_items)
        ]

    @staticmethod
    def _generate_string(schema: dict[str, Any]) -> str:
        """Generate mock string data."""
        # Check for format hints
        format_type = schema.get("format")

        if format_type == "date-time":
            return datetime.now(UTC).isoformat()
        elif format_type == "email":
            return f"test_{InterfaceMockGenerator._random_string(8)}@example.com"
        elif format_type == "uri":
            return f"https://example.com/{InterfaceMockGenerator._random_string(8)}"
        elif format_type == "uuid":
            import uuid

            return str(uuid.uuid4())

        # Check for enum values
        enum_values = schema.get("enum")
        if enum_values:
            return random.choice(enum_values)

        # Generate random string with length constraints
        min_length = schema.get("minLength", 5)
        max_length = schema.get("maxLength", 20)
        length = random.randint(min_length, max_length)

        return InterfaceMockGenerator._random_string(length)

    @staticmethod
    def _generate_number(schema: dict[str, Any]) -> int | float:
        """Generate mock number data."""
        schema_type = schema.get("type")
        minimum = schema.get("minimum", 0)
        maximum = schema.get("maximum", 1000)

        if schema_type == "integer":
            return random.randint(int(minimum), int(maximum))
        else:
            return round(random.uniform(minimum, maximum), 2)

    @staticmethod
    def _generate_boolean(schema: dict[str, Any]) -> bool:
        """Generate mock boolean data."""
        return random.choice([True, False])

    @staticmethod
    def _random_string(length: int) -> str:
        """Generate random alphanumeric string."""
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


class InterfaceMockBuilder:
    """Fluent builder for creating mock interface data with custom values.

    Examples:
        >>> builder = InterfaceMockBuilder(schema)
        >>> data = builder.with_field("name", "John").with_field("age", 30).build()
    """

    def __init__(self, schema: dict[str, Any]):
        """Initialize builder with schema.

        Args:
            schema: JSON Schema definition
        """
        self.schema = schema
        self.overrides: dict[str, Any] = {}

    def with_field(self, field_name: str, value: Any) -> "InterfaceMockBuilder":
        """Set custom value for a field.

        Args:
            field_name: Field name to override
            value: Custom value

        Returns:
            Self for method chaining
        """
        self.overrides[field_name] = value
        return self

    def build(self) -> dict[str, Any]:
        """Build mock data with overrides applied.

        Returns:
            Mock data dictionary with custom values
        """
        base_data = InterfaceMockGenerator.generate_mock_data(self.schema)

        # Apply overrides
        for field_name, value in self.overrides.items():
            base_data[field_name] = value

        return base_data
