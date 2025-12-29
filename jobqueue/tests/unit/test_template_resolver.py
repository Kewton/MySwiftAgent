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


class MockJob:
    """Mock job object for testing."""

    def __init__(
        self,
        body: dict[str, Any] | None = None,
        input_data: dict[str, Any] | None = None,
    ):
        self.body = body
        self.input_data = input_data


class TestTemplateResolverJobVariables:
    """Tests for job variable resolution."""

    def test_resolve_job_body_entire(self) -> None:
        """{{job.body}} resolves to entire body dict."""
        tasks: list[MockTask] = []
        job = MockJob(body={"user_input": "test query", "config": {"key": "value"}})
        template = "{{job.body}}"
        result = TemplateResolver.resolve_template(template, tasks, job=job)
        assert result == {"user_input": "test query", "config": {"key": "value"}}

    def test_resolve_job_body_field(self) -> None:
        """{{job.body.user_input}} resolves to specific field."""
        tasks: list[MockTask] = []
        job = MockJob(body={"user_input": "分析対象の企業名"})
        template = "{{job.body.user_input}}"
        result = TemplateResolver.resolve_template(template, tasks, job=job)
        assert result == "分析対象の企業名"

    def test_resolve_job_body_nested(self) -> None:
        """{{job.body.config.setting}} resolves nested fields."""
        tasks: list[MockTask] = []
        job = MockJob(body={"config": {"setting": {"enabled": True}}})
        template = "{{job.body.config.setting.enabled}}"
        result = TemplateResolver.resolve_template(template, tasks, job=job)
        assert result is True

    def test_resolve_job_body_missing_field(self) -> None:
        """Missing field returns None."""
        tasks: list[MockTask] = []
        job = MockJob(body={"other": "value"})
        template = "{{job.body.missing}}"
        result = TemplateResolver.resolve_template(template, tasks, job=job)
        assert result is None

    def test_resolve_job_none(self) -> None:
        """job=None returns None for job variables."""
        tasks: list[MockTask] = []
        template = "{{job.body.user_input}}"
        result = TemplateResolver.resolve_template(template, tasks, job=None)
        assert result is None

    def test_resolve_job_input_data(self) -> None:
        """{{job.input_data}} resolves correctly."""
        tasks: list[MockTask] = []
        job = MockJob(input_data={"param": "value"})
        template = "{{job.input_data.param}}"
        result = TemplateResolver.resolve_template(template, tasks, job=job)
        assert result == "value"

    def test_resolve_job_body_in_dict(self) -> None:
        """job.body resolves within dict template."""
        tasks: list[MockTask] = []
        job = MockJob(body={"user_input": "query"})
        template = {
            "user_input": "{{job.body.user_input}}",
            "model_name": "taskmaster/tm_001/workflow",
        }
        result = TemplateResolver.resolve_template(template, tasks, job=job)
        assert result == {
            "user_input": "query",
            "model_name": "taskmaster/tm_001/workflow",
        }


class TestTemplateResolverCurrentTaskVariables:
    """Tests for current task variable resolution."""

    def test_resolve_task_input_data_entire(self) -> None:
        """{{task.input_data}} resolves to entire input_data."""
        tasks: list[MockTask] = []
        current_task = MockTask(input_data={"key": "value"}, output_data=None)
        template = "{{task.input_data}}"
        result = TemplateResolver.resolve_template(
            template, tasks, current_task=current_task
        )
        assert result == {"key": "value"}

    def test_resolve_task_input_data_field(self) -> None:
        """{{task.input_data.field}} resolves to specific field."""
        tasks: list[MockTask] = []
        current_task = MockTask(
            input_data={"field": "specific value"}, output_data=None
        )
        template = "{{task.input_data.field}}"
        result = TemplateResolver.resolve_template(
            template, tasks, current_task=current_task
        )
        assert result == "specific value"

    def test_resolve_current_task_none(self) -> None:
        """current_task=None returns None."""
        tasks: list[MockTask] = []
        template = "{{task.input_data.field}}"
        result = TemplateResolver.resolve_template(template, tasks, current_task=None)
        assert result is None


class TestTemplateResolverMixedVariables:
    """Tests for mixed variable types in same template."""

    def test_resolve_job_and_tasks_variables(self) -> None:
        """Template with both {{job.body}} and {{tasks[0].output_data}}."""
        tasks = [MockTask(None, {"result": "task_output"})]
        job = MockJob(body={"user_input": "job_input"})
        template = {
            "from_job": "{{job.body.user_input}}",
            "from_task": "{{tasks[0].output_data.result}}",
        }
        result = TemplateResolver.resolve_template(template, tasks, job=job)
        assert result == {
            "from_job": "job_input",
            "from_task": "task_output",
        }

    def test_resolve_all_variable_types(self) -> None:
        """Template with job, tasks, and current task variables."""
        tasks = [MockTask(None, {"step1_result": "done"})]
        job = MockJob(body={"user_input": "initial"})
        current_task = MockTask(input_data={"task_param": "current"}, output_data=None)
        template = {
            "job_input": "{{job.body.user_input}}",
            "prev_output": "{{tasks[0].output_data.step1_result}}",
            "current_input": "{{task.input_data.task_param}}",
        }
        result = TemplateResolver.resolve_template(
            template, tasks, job=job, current_task=current_task
        )
        assert result == {
            "job_input": "initial",
            "prev_output": "done",
            "current_input": "current",
        }

    def test_has_template_variables_job_pattern(self) -> None:
        """has_template_variables detects {{job.body.*}} pattern."""
        assert TemplateResolver.has_template_variables("{{job.body.user_input}}")
        assert TemplateResolver.has_template_variables({"key": "{{job.body.x}}"})

    def test_has_template_variables_task_pattern(self) -> None:
        """has_template_variables detects {{task.input_data.*}} pattern."""
        assert TemplateResolver.has_template_variables("{{task.input_data.field}}")
        assert TemplateResolver.has_template_variables({"key": "{{task.input_data}}"})


class TestTemplateResolverLogContext:
    """Tests for log_context parameter."""

    def test_resolve_with_log_context(self) -> None:
        """log_context parameter is passed through resolution."""
        tasks = [MockTask(None, {"result": "value"})]
        log_context = {
            "task_id": "t_123",
            "task_master_name": "test_task_master",
            "job_id": "job_456",
        }
        template = "{{tasks[0].output_data.result}}"
        result = TemplateResolver.resolve_template(
            template, tasks, log_context=log_context
        )
        assert result == "value"

    def test_resolve_with_partial_log_context(self) -> None:
        """Partial log_context works correctly."""
        tasks = [MockTask(None, {"result": "value"})]
        log_context = {"task_id": "t_123"}
        template = "{{tasks[0].output_data.result}}"
        result = TemplateResolver.resolve_template(
            template, tasks, log_context=log_context
        )
        assert result == "value"

    def test_resolve_with_empty_log_context(self) -> None:
        """Empty log_context works correctly."""
        tasks = [MockTask(None, {"result": "value"})]
        log_context: dict[str, str] = {}
        template = "{{tasks[0].output_data.result}}"
        result = TemplateResolver.resolve_template(
            template, tasks, log_context=log_context
        )
        assert result == "value"

    def test_format_log_context(self) -> None:
        """_format_log_context produces correct output."""
        log_context = {
            "task_id": "t_123",
            "task_master_name": "my_task",
            "job_id": "job_456",
        }
        result = TemplateResolver._format_log_context(log_context)
        assert "Task: t_123" in result
        assert "TaskMaster: my_task" in result
        assert "Job: job_456" in result

    def test_format_log_context_none(self) -> None:
        """_format_log_context handles None."""
        result = TemplateResolver._format_log_context(None)
        assert result == ""

    def test_format_log_context_empty(self) -> None:
        """_format_log_context handles empty dict."""
        result = TemplateResolver._format_log_context({})
        assert result == ""


class TestTemplateResolverPatternsFromSharedModule:
    """Tests verifying patterns are from shared TemplatePatterns module."""

    def test_patterns_are_from_shared_module(self) -> None:
        """Verify patterns reference TemplatePatterns module."""
        from app.services.template_patterns import TemplatePatterns

        # These should be the same compiled pattern objects
        assert TemplateResolver.VARIABLE_PATTERN is TemplatePatterns.TASK_VARIABLE
        assert TemplateResolver.JOB_VARIABLE_PATTERN is TemplatePatterns.JOB_VARIABLE
        assert (
            TemplateResolver.CURRENT_TASK_PATTERN
            is TemplatePatterns.CURRENT_TASK_VARIABLE
        )
        assert TemplateResolver.ANY_VARIABLE_PATTERN is TemplatePatterns.ANY_VARIABLE
