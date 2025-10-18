"""Unit tests for TemplateResolver service."""

from typing import Any

import pytest

from app.services.template_resolver import TemplateResolver, TemplateResolverError


class MockTask:
    """Mock task object for testing."""

    def __init__(
        self, input_data: dict[str, Any] | None, output_data: dict[str, Any] | None
    ):
        self.input_data = input_data
        self.output_data = output_data


class TestTemplateResolver:
    """Test suite for TemplateResolver."""

    def test_variable_pattern_basic(self) -> None:
        """Test basic variable pattern matching."""
        pattern = TemplateResolver.VARIABLE_PATTERN
        match = pattern.search("{{tasks[0].output_data.result}}")
        assert match is not None
        assert match.group(1) == "0"
        assert match.group(2) == "output_data"
        assert match.group(3) == ".result"

    def test_variable_pattern_nested_path(self) -> None:
        """Test variable pattern with nested path."""
        pattern = TemplateResolver.VARIABLE_PATTERN
        match = pattern.search("{{tasks[1].output_data.user.name.first}}")
        assert match is not None
        assert match.group(1) == "1"
        assert match.group(2) == "output_data"
        assert match.group(3) == ".user.name.first"

    def test_variable_pattern_input_data(self) -> None:
        """Test variable pattern with input_data."""
        pattern = TemplateResolver.VARIABLE_PATTERN
        match = pattern.search("{{tasks[2].input_data.params}}")
        assert match is not None
        assert match.group(1) == "2"
        assert match.group(2) == "input_data"
        assert match.group(3) == ".params"

    def test_resolve_string_single_variable(self) -> None:
        """Test resolving a string with a single variable returns actual value."""
        tasks = [MockTask(None, {"result": 42})]
        template = "{{tasks[0].output_data.result}}"
        result = TemplateResolver.resolve_template(template, tasks)
        assert result == 42  # Should return int, not string

    def test_resolve_string_interpolation(self) -> None:
        """Test resolving a string with interpolated variables."""
        tasks = [MockTask(None, {"name": "Alice", "age": 30})]
        template = (
            "Name: {{tasks[0].output_data.name}}, Age: {{tasks[0].output_data.age}}"
        )
        result = TemplateResolver.resolve_template(template, tasks)
        assert result == "Name: Alice, Age: 30"

    def test_resolve_dict(self) -> None:
        """Test resolving template variables in a dictionary."""
        tasks = [MockTask(None, {"user_id": "123", "status": "active"})]
        template = {
            "id": "{{tasks[0].output_data.user_id}}",
            "status": "{{tasks[0].output_data.status}}",
        }
        result = TemplateResolver.resolve_template(template, tasks)
        assert result == {"id": "123", "status": "active"}

    def test_resolve_list(self) -> None:
        """Test resolving template variables in a list."""
        tasks = [MockTask(None, {"item1": "apple", "item2": "banana"})]
        template = ["{{tasks[0].output_data.item1}}", "{{tasks[0].output_data.item2}}"]
        result = TemplateResolver.resolve_template(template, tasks)
        assert result == ["apple", "banana"]

    def test_resolve_nested_structure(self) -> None:
        """Test resolving template variables in nested dict/list."""
        tasks = [MockTask(None, {"name": "Bob", "score": 95})]
        template = {
            "student": {
                "name": "{{tasks[0].output_data.name}}",
                "scores": ["{{tasks[0].output_data.score}}"],
            },
        }
        result = TemplateResolver.resolve_template(template, tasks)
        assert result == {"student": {"name": "Bob", "scores": [95]}}

    def test_resolve_with_multiple_tasks(self) -> None:
        """Test resolving variables referencing multiple tasks."""
        tasks = [
            MockTask(None, {"result": "step1"}),
            MockTask(None, {"result": "step2"}),
        ]
        template = {
            "prev": "{{tasks[0].output_data.result}}",
            "curr": "{{tasks[1].output_data.result}}",
        }
        result = TemplateResolver.resolve_template(template, tasks)
        assert result == {"prev": "step1", "curr": "step2"}

    def test_resolve_input_data(self) -> None:
        """Test resolving variables from input_data."""
        tasks = [MockTask({"param": "value"}, None)]
        template = "{{tasks[0].input_data.param}}"
        result = TemplateResolver.resolve_template(template, tasks)
        assert result == "value"

    def test_resolve_entire_data_object(self) -> None:
        """Test resolving entire data object without path."""
        tasks = [MockTask(None, {"key1": "val1", "key2": "val2"})]
        template = "{{tasks[0].output_data}}"
        result = TemplateResolver.resolve_template(template, tasks)
        assert result == {"key1": "val1", "key2": "val2"}

    def test_resolve_none_template(self) -> None:
        """Test resolving None template."""
        tasks = [MockTask(None, {})]
        result = TemplateResolver.resolve_template(None, tasks)
        assert result is None

    def test_resolve_non_dict_non_string_template(self) -> None:
        """Test resolving non-dict/non-string template (passthrough)."""
        tasks = [MockTask(None, {})]
        result = TemplateResolver.resolve_template(123, tasks)  # type: ignore
        assert result == 123

    def test_error_task_index_out_of_range(self) -> None:
        """Test error when task index is out of range."""
        tasks = [MockTask(None, {"result": "ok"})]
        template = "{{tasks[5].output_data.result}}"
        with pytest.raises(TemplateResolverError, match="Task index 5 out of range"):
            TemplateResolver.resolve_template(template, tasks)

    def test_error_no_data(self) -> None:
        """Test handling when task has no data (returns None)."""
        tasks = [MockTask(None, None)]
        template = "{{tasks[0].output_data.result}}"
        result = TemplateResolver.resolve_template(template, tasks)
        assert result is None  # Should return None when data not found

    def test_error_field_not_found(self) -> None:
        """Test handling when field is not found (returns None)."""
        tasks = [MockTask(None, {"other": "value"})]
        template = "{{tasks[0].output_data.missing}}"
        result = TemplateResolver.resolve_template(template, tasks)
        assert result is None  # Should return None for missing field

    def test_error_accessing_non_dict_field(self) -> None:
        """Test error when accessing field in non-dict value."""
        tasks = [MockTask(None, {"result": "string_value"})]
        template = "{{tasks[0].output_data.result.field}}"
        with pytest.raises(
            TemplateResolverError, match="Cannot access field 'field' in non-dict value"
        ):
            TemplateResolver.resolve_template(template, tasks)

    def test_has_template_variables_string(self) -> None:
        """Test detecting template variables in string."""
        assert TemplateResolver.has_template_variables("{{tasks[0].output_data.x}}")
        assert not TemplateResolver.has_template_variables("plain string")

    def test_has_template_variables_dict(self) -> None:
        """Test detecting template variables in dict."""
        assert TemplateResolver.has_template_variables(
            {"key": "{{tasks[0].output_data.x}}"}
        )
        assert not TemplateResolver.has_template_variables({"key": "plain"})

    def test_has_template_variables_list(self) -> None:
        """Test detecting template variables in list."""
        assert TemplateResolver.has_template_variables(["{{tasks[0].output_data.x}}"])
        assert not TemplateResolver.has_template_variables(["plain"])

    def test_has_template_variables_nested(self) -> None:
        """Test detecting template variables in nested structure."""
        assert TemplateResolver.has_template_variables(
            {"nested": ["{{tasks[0].output_data.x}}"]}
        )
        assert not TemplateResolver.has_template_variables({"nested": ["plain"]})

    def test_has_template_variables_none(self) -> None:
        """Test detecting template variables in None."""
        assert not TemplateResolver.has_template_variables(None)
