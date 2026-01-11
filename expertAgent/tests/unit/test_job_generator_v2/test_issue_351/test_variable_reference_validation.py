"""Unit tests for TaskFlow V2 variable reference validation.

Issue #351: Tests for variable reference handling in JSON fields.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.schemas.taskflow_schema import (
    TaskFlowStep,
    TaskFlowWorkflow,
    UnifiedStepConfig,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.schemas.variable_patterns import (
    TASKFLOW_VARIABLE_PATTERN,
    contains_variable_reference,
    mask_secret_references,
    replace_variables_with_placeholder,
    validate_variable_syntax,
)


class TestVariablePatternModule:
    """Tests for variable_patterns.py module."""

    def test_pattern_matches_simple_reference(self) -> None:
        """Pattern should match simple variable references."""
        assert TASKFLOW_VARIABLE_PATTERN.search("${inputs.query}")
        assert TASKFLOW_VARIABLE_PATTERN.search("${step_001.output}")

    def test_pattern_matches_nested_reference(self) -> None:
        """Pattern should match nested variable references."""
        assert TASKFLOW_VARIABLE_PATTERN.search("${step.output.data.name}")
        assert TASKFLOW_VARIABLE_PATTERN.search(
            "${fetch_user.output.user.profile.email}"
        )

    def test_pattern_matches_hyphenated_step_id(self) -> None:
        """Pattern should match step IDs with hyphens."""
        assert TASKFLOW_VARIABLE_PATTERN.search("${step-001.output}")
        assert TASKFLOW_VARIABLE_PATTERN.search("${my-step.output.data}")

    def test_pattern_matches_secrets_reference(self) -> None:
        """Pattern should match secrets references."""
        assert TASKFLOW_VARIABLE_PATTERN.search("${secrets.API_KEY}")
        assert TASKFLOW_VARIABLE_PATTERN.search("${secrets.GOOGLE_API_TOKEN}")

    def test_pattern_rejects_invalid_start(self) -> None:
        """Pattern should not match references starting with numbers."""
        match = TASKFLOW_VARIABLE_PATTERN.search("${123step.output}")
        assert match is None

    def test_contains_variable_reference_true(self) -> None:
        """contains_variable_reference returns True for strings with variables."""
        assert contains_variable_reference('{"result": "${step.output}"}') is True
        assert contains_variable_reference("URL: ${inputs.url}") is True

    def test_contains_variable_reference_false(self) -> None:
        """contains_variable_reference returns False for static strings."""
        assert contains_variable_reference('{"result": "static"}') is False
        assert contains_variable_reference("No variables here") is False

    def test_replace_variables_with_placeholder(self) -> None:
        """replace_variables_with_placeholder replaces all variable references."""
        result = replace_variables_with_placeholder('{"a": "${x.y}", "b": "${z}"}')
        assert "${" not in result
        assert "__TASKFLOW_VAR_PLACEHOLDER__" in result

    def test_mask_secret_references(self) -> None:
        """mask_secret_references masks secret key names."""
        result = mask_secret_references("Bearer ${secrets.API_TOKEN}")
        assert result == "Bearer ${secrets.***}"
        assert "API_TOKEN" not in result

    def test_mask_secret_preserves_non_secrets(self) -> None:
        """mask_secret_references preserves non-secret references."""
        result = mask_secret_references("${inputs.query} and ${secrets.KEY}")
        assert "${inputs.query}" in result
        assert "${secrets.***}" in result

    def test_validate_variable_syntax_valid(self) -> None:
        """validate_variable_syntax returns empty list for valid syntax."""
        assert validate_variable_syntax("${step.output}") == []
        assert validate_variable_syntax("${a.b.c.d}") == []
        assert validate_variable_syntax("${step-001.output}") == []

    def test_validate_variable_syntax_invalid(self) -> None:
        """validate_variable_syntax returns invalid references."""
        invalid = validate_variable_syntax("${123.invalid}")
        assert "${123.invalid}" in invalid

        invalid = validate_variable_syntax("${valid} and ${.invalid}")
        assert "${.invalid}" in invalid
        assert "${valid}" not in invalid


class TestVariableReferenceInOutput:
    """Tests for variable reference handling in TaskFlowWorkflow output field."""

    def _create_minimal_step(self) -> TaskFlowStep:
        """Create a minimal valid step for testing."""
        return TaskFlowStep(
            id="step_001",
            type="transform",
            config=UnifiedStepConfig(
                step_type="transform",
                mode="template",
                template="${inputs.query}",
            ),
        )

    def test_output_with_simple_variable(self) -> None:
        """Simple variable reference should be accepted."""
        workflow = TaskFlowWorkflow(
            workflow_name="test_workflow",
            input_schema='{"query": "string"}',
            output_schema='{"result": "string"}',
            steps=[self._create_minimal_step()],
            output='{"result": "${step_001.output}"}',
        )
        assert workflow.output == '{"result": "${step_001.output}"}'

    def test_output_with_nested_variable(self) -> None:
        """Nested variable reference should be accepted."""
        workflow = TaskFlowWorkflow(
            workflow_name="test_workflow",
            input_schema='{"query": "string"}',
            output_schema='{"data": "object"}',
            steps=[self._create_minimal_step()],
            output='{"data": "${step_001.output.data.items}"}',
        )
        assert workflow.output == '{"data": "${step_001.output.data.items}"}'

    def test_output_with_hyphenated_step_id(self) -> None:
        """Variable reference with hyphenated step ID should be accepted."""
        step = TaskFlowStep(
            id="fetch-user",
            type="transform",
            config=UnifiedStepConfig(
                step_type="transform",
                mode="template",
                template="${inputs.query}",
            ),
        )
        workflow = TaskFlowWorkflow(
            workflow_name="test_workflow",
            input_schema='{"query": "string"}',
            output_schema='{"result": "string"}',
            steps=[step],
            output='{"result": "${fetch-user.output}"}',
        )
        assert workflow.output == '{"result": "${fetch-user.output}"}'

    def test_output_with_mixed_content(self) -> None:
        """Mixed static and variable content should be accepted."""
        workflow = TaskFlowWorkflow(
            workflow_name="test_workflow",
            input_schema='{"query": "string"}',
            output_schema='{"status": "string", "data": "object"}',
            steps=[self._create_minimal_step()],
            output='{"status": "success", "data": "${step_001.output}"}',
        )
        assert '"status": "success"' in workflow.output
        assert "${step_001.output}" in workflow.output

    def test_output_with_multiple_variables(self) -> None:
        """Multiple variable references should be accepted."""
        step1 = TaskFlowStep(
            id="step_001",
            type="transform",
            config=UnifiedStepConfig(
                step_type="transform",
                mode="template",
                template="${inputs.query}",
            ),
        )
        step2 = TaskFlowStep(
            id="step_002",
            type="transform",
            config=UnifiedStepConfig(
                step_type="transform",
                mode="template",
                template="${step_001.output}",
            ),
        )
        workflow = TaskFlowWorkflow(
            workflow_name="test_workflow",
            input_schema='{"query": "string"}',
            output_schema='{"a": "string", "b": "string"}',
            steps=[step1, step2],
            output='{"a": "${step_001.output}", "b": "${step_002.output}"}',
        )
        assert "${step_001.output}" in workflow.output
        assert "${step_002.output}" in workflow.output

    def test_invalid_json_structure_with_variable(self) -> None:
        """Invalid JSON structure should still fail even with variables."""
        with pytest.raises(ValidationError) as exc_info:
            TaskFlowWorkflow(
                workflow_name="test_workflow",
                input_schema='{"query": "string"}',
                output_schema='{"result": "string"}',
                steps=[self._create_minimal_step()],
                output='{"result": ${step_001.output}}',  # Missing quotes around value
            )
        error_str = str(exc_info.value).lower()
        assert "json" in error_str

    def test_invalid_json_missing_brace(self) -> None:
        """Missing closing brace should fail validation."""
        with pytest.raises(ValidationError):
            TaskFlowWorkflow(
                workflow_name="test_workflow",
                input_schema='{"query": "string"}',
                output_schema='{"result": "string"}',
                steps=[self._create_minimal_step()],
                output='{"result": "${step.output}"',  # Missing closing }
            )

    def test_output_pure_static_json_still_works(self) -> None:
        """Pure static JSON without variables should still work."""
        workflow = TaskFlowWorkflow(
            workflow_name="test_workflow",
            input_schema='{"query": "string"}',
            output_schema='{"message": "string"}',
            steps=[self._create_minimal_step()],
            output='{"message": "Hello, World!"}',
        )
        assert workflow.output == '{"message": "Hello, World!"}'


class TestVariableReferenceInInputOutputSchema:
    """Tests for variable reference handling in input_schema and output_schema."""

    def _create_minimal_step(self) -> TaskFlowStep:
        """Create a minimal valid step for testing."""
        return TaskFlowStep(
            id="step_001",
            type="transform",
            config=UnifiedStepConfig(
                step_type="transform",
                mode="template",
                template="${inputs.query}",
            ),
        )

    def test_input_schema_static_only(self) -> None:
        """input_schema typically contains static type definitions."""
        workflow = TaskFlowWorkflow(
            workflow_name="test_workflow",
            input_schema='{"query": "string", "limit": "number"}',
            output_schema='{"result": "string"}',
            steps=[self._create_minimal_step()],
            output='{"result": "${step_001.output}"}',
        )
        assert workflow.input_schema == '{"query": "string", "limit": "number"}'

    def test_output_schema_static_only(self) -> None:
        """output_schema typically contains static type definitions."""
        workflow = TaskFlowWorkflow(
            workflow_name="test_workflow",
            input_schema='{"query": "string"}',
            output_schema='{"result": "array", "count": "number"}',
            steps=[self._create_minimal_step()],
            output='{"result": "${step_001.output}"}',
        )
        assert workflow.output_schema == '{"result": "array", "count": "number"}'


class TestLangfuseErrorScenario:
    """Reproduce the exact error scenario from Langfuse trace.

    Trace ID: e5eff2c5134442999d725b36f105a4dd
    Error: output field validation failed for variable reference.
    """

    def test_google_search_workflow_scenario(self) -> None:
        """Reproduce the Google search workflow that failed in production."""
        google_search_step = TaskFlowStep(
            id="google_search",
            type="api_rest",
            config=UnifiedStepConfig(
                step_type="api_rest",
                method="POST",
                url="http://localhost:8004/v1/utility/google_search",
                headers={"Content-Type": "application/json"},
                body='{"queries": ["${inputs.query}"], "num": 10}',
            ),
        )

        # This was failing before the fix
        workflow = TaskFlowWorkflow(
            workflow_name="google_search_workflow",
            description="Search Google and return results",
            input_schema='{"query": "string"}',
            output_schema='{"search_results": "array"}',
            steps=[google_search_step],
            output='{"search_results": "${google_search.output.search_results}"}',
        )

        # Verify the workflow was created successfully
        assert workflow.workflow_name == "google_search_workflow"
        assert "${google_search.output.search_results}" in workflow.output

    def test_exact_langfuse_error_value(self) -> None:
        """Test the exact value that caused the Langfuse error."""
        step = TaskFlowStep(
            id="google_search",
            type="transform",
            config=UnifiedStepConfig(
                step_type="transform",
                mode="template",
                template="${inputs.query}",
            ),
        )

        # Exact input value pattern from Langfuse trace (corrected JSON)
        workflow = TaskFlowWorkflow(
            workflow_name="search_workflow",
            input_schema='{"query": "string"}',
            output_schema='{"search_results": "array"}',
            steps=[step],
            output='{"search_results": "${google_search.output.search_results}"}',
        )

        assert "${google_search.output.search_results}" in workflow.output


class TestSecretMaskingInErrorMessages:
    """Tests for secret masking in error messages."""

    def test_secret_references_are_masked_in_custom_error_part(self) -> None:
        """Secret references should be masked in our custom error message part.

        Note: Pydantic's error message includes the original input_value which
        we cannot control. This test verifies that our custom "Input:" portion
        of the error message has secrets masked.
        """
        # Create invalid JSON that contains a secret reference
        with pytest.raises(ValidationError) as exc_info:
            TaskFlowWorkflow(
                workflow_name="test_workflow",
                input_schema='{"query": "string"}',
                output_schema='{"result": "string"}',
                steps=[
                    TaskFlowStep(
                        id="step_001",
                        type="transform",
                        config=UnifiedStepConfig(
                            step_type="transform",
                            mode="template",
                            template="${inputs.query}",
                        ),
                    )
                ],
                # Invalid JSON structure with secret reference
                output='{"auth": Bearer ${secrets.API_KEY}}',  # Missing quotes
            )

        error_str = str(exc_info.value)
        # The error message should contain our custom message with masked secrets
        # Format: "Input: {...${secrets.***}...}"
        assert "Input:" in error_str
        assert "${secrets.***}" in error_str
        # Verify the error mentions JSON structure issue
        assert "json" in error_str.lower()

    def test_mask_secret_references_function_directly(self) -> None:
        """Test that mask_secret_references function works correctly."""
        # Test various secret patterns
        assert mask_secret_references("${secrets.API_KEY}") == "${secrets.***}"
        assert mask_secret_references("${secrets.MY_SECRET}") == "${secrets.***}"
        assert (
            mask_secret_references("Bearer ${secrets.TOKEN}") == "Bearer ${secrets.***}"
        )

        # Non-secrets should not be masked
        assert mask_secret_references("${inputs.query}") == "${inputs.query}"
        assert mask_secret_references("${step.output}") == "${step.output}"
