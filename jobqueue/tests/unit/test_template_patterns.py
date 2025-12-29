"""Unit tests for TemplatePatterns module."""

from app.services.template_patterns import TemplatePatterns


class TestTemplatePatterns:
    """Test suite for TemplatePatterns class."""

    # === TASK_VARIABLE pattern tests ===

    def test_task_variable_basic_output(self) -> None:
        """Test matching basic task output variable."""
        match = TemplatePatterns.TASK_VARIABLE.search("{{tasks[0].output_data.result}}")
        assert match is not None
        assert match.group(1) == "0"
        assert match.group(2) == "output_data"
        assert match.group(3) == ".result"

    def test_task_variable_nested_path(self) -> None:
        """Test matching task variable with nested path."""
        match = TemplatePatterns.TASK_VARIABLE.search(
            "{{tasks[1].output_data.user.profile.name}}"
        )
        assert match is not None
        assert match.group(1) == "1"
        assert match.group(2) == "output_data"
        assert match.group(3) == ".user.profile.name"

    def test_task_variable_input_data(self) -> None:
        """Test matching task input_data variable."""
        match = TemplatePatterns.TASK_VARIABLE.search("{{tasks[2].input_data.params}}")
        assert match is not None
        assert match.group(1) == "2"
        assert match.group(2) == "input_data"
        assert match.group(3) == ".params"

    def test_task_variable_no_path(self) -> None:
        """Test matching task variable without field path."""
        match = TemplatePatterns.TASK_VARIABLE.search("{{tasks[0].output_data}}")
        assert match is not None
        assert match.group(1) == "0"
        assert match.group(2) == "output_data"
        assert match.group(3) is None

    def test_task_variable_large_index(self) -> None:
        """Test matching task variable with large index."""
        match = TemplatePatterns.TASK_VARIABLE.search("{{tasks[99].output_data.x}}")
        assert match is not None
        assert match.group(1) == "99"

    # === JOB_VARIABLE pattern tests ===

    def test_job_variable_body(self) -> None:
        """Test matching job body variable."""
        match = TemplatePatterns.JOB_VARIABLE.search("{{job.body.user_input}}")
        assert match is not None
        assert match.group(1) == "body"
        assert match.group(2) == ".user_input"

    def test_job_variable_input_data(self) -> None:
        """Test matching job input_data variable."""
        match = TemplatePatterns.JOB_VARIABLE.search("{{job.input_data.param}}")
        assert match is not None
        assert match.group(1) == "input_data"
        assert match.group(2) == ".param"

    def test_job_variable_nested_path(self) -> None:
        """Test matching job variable with nested path."""
        match = TemplatePatterns.JOB_VARIABLE.search(
            "{{job.body.config.settings.value}}"
        )
        assert match is not None
        assert match.group(1) == "body"
        assert match.group(2) == ".config.settings.value"

    def test_job_variable_entire_body(self) -> None:
        """Test matching entire job body."""
        match = TemplatePatterns.JOB_VARIABLE.search("{{job.body}}")
        assert match is not None
        assert match.group(1) == "body"
        assert match.group(2) is None

    # === CURRENT_TASK_VARIABLE pattern tests ===

    def test_current_task_variable(self) -> None:
        """Test matching current task variable."""
        match = TemplatePatterns.CURRENT_TASK_VARIABLE.search(
            "{{task.input_data.field}}"
        )
        assert match is not None
        assert match.group(1) == "input_data"
        assert match.group(2) == ".field"

    def test_current_task_variable_entire(self) -> None:
        """Test matching entire current task input_data."""
        match = TemplatePatterns.CURRENT_TASK_VARIABLE.search("{{task.input_data}}")
        assert match is not None
        assert match.group(1) == "input_data"
        assert match.group(2) is None

    # === ANY_VARIABLE pattern tests ===

    def test_any_variable_matches_task(self) -> None:
        """Test ANY_VARIABLE matches task variables."""
        assert TemplatePatterns.ANY_VARIABLE.search("{{tasks[0].output_data.x}}")

    def test_any_variable_matches_job(self) -> None:
        """Test ANY_VARIABLE matches job variables."""
        assert TemplatePatterns.ANY_VARIABLE.search("{{job.body.x}}")

    def test_any_variable_matches_current_task(self) -> None:
        """Test ANY_VARIABLE matches current task variables."""
        assert TemplatePatterns.ANY_VARIABLE.search("{{task.input_data.x}}")

    def test_any_variable_no_match(self) -> None:
        """Test ANY_VARIABLE does not match invalid patterns."""
        assert not TemplatePatterns.ANY_VARIABLE.search("plain text")
        assert not TemplatePatterns.ANY_VARIABLE.search("{{invalid}}")
        assert not TemplatePatterns.ANY_VARIABLE.search("{{job.other}}")

    # === extract_all_variables tests ===

    def test_extract_all_variables_empty(self) -> None:
        """Test extracting from text with no variables."""
        result = TemplatePatterns.extract_all_variables("plain text without variables")
        assert result == []

    def test_extract_all_variables_single(self) -> None:
        """Test extracting single variable."""
        result = TemplatePatterns.extract_all_variables("{{job.body.email}}")
        assert result == ["{{job.body.email}}"]

    def test_extract_all_variables_multiple_types(self) -> None:
        """Test extracting variables of different types."""
        text = (
            "User: {{job.body.user}}, "
            "Result: {{tasks[0].output_data.result}}, "
            "Input: {{task.input_data.param}}"
        )
        result = TemplatePatterns.extract_all_variables(text)
        assert "{{job.body.user}}" in result
        assert "{{tasks[0].output_data.result}}" in result
        assert "{{task.input_data.param}}" in result
        assert len(result) == 3

    def test_extract_all_variables_multiple_same_type(self) -> None:
        """Test extracting multiple variables of same type."""
        text = "{{job.body.a}} and {{job.body.b}}"
        result = TemplatePatterns.extract_all_variables(text)
        assert "{{job.body.a}}" in result
        assert "{{job.body.b}}" in result
        assert len(result) == 2

    # === has_variables tests ===

    def test_has_variables_true(self) -> None:
        """Test detecting variables in text."""
        assert TemplatePatterns.has_variables("{{job.body.email}}")
        assert TemplatePatterns.has_variables("Hello {{tasks[0].output_data.name}}")
        assert TemplatePatterns.has_variables("{{task.input_data}}")

    def test_has_variables_false(self) -> None:
        """Test detecting no variables in text."""
        assert not TemplatePatterns.has_variables("plain text")
        assert not TemplatePatterns.has_variables("{{ not_valid }}")
        assert not TemplatePatterns.has_variables("{job.body.x}")

    # === get_path_depth tests ===

    def test_get_path_depth_no_path(self) -> None:
        """Test path depth for variable without path."""
        assert TemplatePatterns.get_path_depth("{{job.body}}") == 0
        assert TemplatePatterns.get_path_depth("{{tasks[0].output_data}}") == 0

    def test_get_path_depth_single_level(self) -> None:
        """Test path depth for single-level path."""
        assert TemplatePatterns.get_path_depth("{{job.body.email}}") == 1
        assert TemplatePatterns.get_path_depth("{{tasks[0].output_data.result}}") == 1

    def test_get_path_depth_nested(self) -> None:
        """Test path depth for nested path."""
        assert TemplatePatterns.get_path_depth("{{job.body.user.profile}}") == 2
        assert TemplatePatterns.get_path_depth("{{job.body.a.b.c.d}}") == 4

    def test_get_path_depth_invalid(self) -> None:
        """Test path depth for invalid variable returns 0."""
        assert TemplatePatterns.get_path_depth("invalid") == 0
        assert TemplatePatterns.get_path_depth("{{invalid}}") == 0


class TestTemplatePatternsConsistency:
    """Test pattern consistency across the module."""

    def test_patterns_are_compiled(self) -> None:
        """Verify all patterns are compiled regex objects."""
        import re

        assert isinstance(TemplatePatterns.TASK_VARIABLE, re.Pattern)
        assert isinstance(TemplatePatterns.JOB_VARIABLE, re.Pattern)
        assert isinstance(TemplatePatterns.CURRENT_TASK_VARIABLE, re.Pattern)
        assert isinstance(TemplatePatterns.ANY_VARIABLE, re.Pattern)

    def test_any_variable_covers_all_types(self) -> None:
        """Verify ANY_VARIABLE detects all variable types."""
        test_cases = [
            "{{tasks[0].output_data}}",
            "{{tasks[5].input_data.x}}",
            "{{job.body}}",
            "{{job.body.field}}",
            "{{job.input_data}}",
            "{{job.input_data.x}}",
            "{{task.input_data}}",
            "{{task.input_data.field}}",
        ]
        for case in test_cases:
            assert TemplatePatterns.ANY_VARIABLE.search(case), f"Failed for: {case}"
