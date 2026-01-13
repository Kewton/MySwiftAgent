"""Unit tests for template_variable_extractor.py.

Issue #358: Tests for extracting template variables from body_template.

Test cases:
1. Extract job.body references ({{job.body.field}})
2. Extract tasks[N].output_data references
3. Handle nested paths
4. Return empty set for no templates
5. Handle malformed templates
"""


class TestExtractTemplateVariables:
    """Test extract_template_variables() function."""

    def test_extract_job_body_simple_reference(self) -> None:
        """Extract simple job.body.field reference."""
        from aiagent.langgraph.jobGeneratorV2.validators.template_variable_extractor import (
            extract_template_variables,
        )

        body_template = {"user_input": "{{job.body.user_input}}"}

        result = extract_template_variables(body_template)

        assert "job.body.user_input" in result.job_body_refs
        assert len(result.task_output_refs) == 0

    def test_extract_job_body_nested_reference(self) -> None:
        """Extract nested job.body reference like {{job.body.config.api_key}}."""
        from aiagent.langgraph.jobGeneratorV2.validators.template_variable_extractor import (
            extract_template_variables,
        )

        body_template = {"api_key": "{{job.body.config.api_key}}"}

        result = extract_template_variables(body_template)

        assert "job.body.config.api_key" in result.job_body_refs

    def test_extract_task_output_reference(self) -> None:
        """Extract tasks[N].output_data reference."""
        from aiagent.langgraph.jobGeneratorV2.validators.template_variable_extractor import (
            extract_template_variables,
        )

        body_template = {"inputs": "{{tasks[0].output_data}}"}

        result = extract_template_variables(body_template)

        assert len(result.task_output_refs) == 1
        assert result.task_output_refs[0].task_index == 0
        assert result.task_output_refs[0].field_path == ""

    def test_extract_task_output_with_field_path(self) -> None:
        """Extract tasks[N].output_data.field reference."""
        from aiagent.langgraph.jobGeneratorV2.validators.template_variable_extractor import (
            extract_template_variables,
        )

        body_template = {"result": "{{tasks[1].output_data.summary}}"}

        result = extract_template_variables(body_template)

        assert len(result.task_output_refs) == 1
        assert result.task_output_refs[0].task_index == 1
        assert result.task_output_refs[0].field_path == "summary"

    def test_extract_multiple_references(self) -> None:
        """Extract multiple references from body_template."""
        from aiagent.langgraph.jobGeneratorV2.validators.template_variable_extractor import (
            extract_template_variables,
        )

        body_template = {
            "workflow_name": "test_workflow",
            "inputs": "{{job.body}}",
            "project": "{{job.project}}",
            "previous_result": "{{tasks[0].output_data}}",
        }

        result = extract_template_variables(body_template)

        assert "job.body" in result.job_body_refs
        assert "job.project" in result.job_refs
        assert len(result.task_output_refs) == 1

    def test_empty_template_returns_empty(self) -> None:
        """Empty template returns empty result."""
        from aiagent.langgraph.jobGeneratorV2.validators.template_variable_extractor import (
            extract_template_variables,
        )

        result = extract_template_variables({})

        assert len(result.job_body_refs) == 0
        assert len(result.task_output_refs) == 0

    def test_no_template_variables_returns_empty(self) -> None:
        """Template without {{}} returns empty result."""
        from aiagent.langgraph.jobGeneratorV2.validators.template_variable_extractor import (
            extract_template_variables,
        )

        body_template = {
            "workflow_name": "static_name",
            "static_value": 42,
        }

        result = extract_template_variables(body_template)

        assert len(result.job_body_refs) == 0
        assert len(result.task_output_refs) == 0
        assert len(result.job_refs) == 0

    def test_nested_dict_extraction(self) -> None:
        """Extract variables from nested dict structure."""
        from aiagent.langgraph.jobGeneratorV2.validators.template_variable_extractor import (
            extract_template_variables,
        )

        body_template = {
            "outer": {
                "inner": "{{job.body.field}}",
            }
        }

        result = extract_template_variables(body_template)

        assert "job.body.field" in result.job_body_refs

    def test_list_extraction(self) -> None:
        """Extract variables from list values."""
        from aiagent.langgraph.jobGeneratorV2.validators.template_variable_extractor import (
            extract_template_variables,
        )

        body_template = {
            "items": ["{{job.body.item1}}", "{{job.body.item2}}"],
        }

        result = extract_template_variables(body_template)

        assert "job.body.item1" in result.job_body_refs
        assert "job.body.item2" in result.job_body_refs


class TestTemplateVariableResult:
    """Test TemplateVariableResult dataclass."""

    def test_get_required_job_body_fields(self) -> None:
        """Test extracting required job body fields."""
        from aiagent.langgraph.jobGeneratorV2.validators.template_variable_extractor import (
            extract_template_variables,
        )

        body_template = {
            "user_input": "{{job.body.user_input}}",
            "email": "{{job.body.recipient_email}}",
        }

        result = extract_template_variables(body_template)
        required_fields = result.get_required_job_body_fields()

        assert "user_input" in required_fields
        assert "recipient_email" in required_fields

    def test_get_max_task_index(self) -> None:
        """Test getting maximum task index referenced."""
        from aiagent.langgraph.jobGeneratorV2.validators.template_variable_extractor import (
            extract_template_variables,
        )

        body_template = {
            "task0": "{{tasks[0].output_data}}",
            "task2": "{{tasks[2].output_data.result}}",
        }

        result = extract_template_variables(body_template)

        assert result.get_max_task_index() == 2
