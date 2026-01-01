"""Test workflow output node validation (Issue #338 Phase 1).

This module tests the validation of generated workflow YAML to ensure
it follows the output node naming convention:
- Output node MUST be named 'output'
- Output node MUST have isResult: true

These tests verify the enforcement mechanism for task chain interface contracts.
"""

from aiagent.langgraph.workflowGeneratorAgents.prompts.workflow_generation import (
    WORKFLOW_GENERATION_SYSTEM_PROMPT,
    create_workflow_generation_prompt,
)

# Import the validation function - will be implemented in workflow_generation.py
from aiagent.langgraph.workflowGeneratorAgents.utils.workflow_validator import (
    ValidationResult,
    validate_output_node_convention,
)


class TestOutputNodeValidation:
    """Test output node naming convention validation."""

    def test_valid_output_node_with_is_result(self):
        """Test that a workflow with 'output' node and isResult: true passes validation."""
        yaml_content = """
version: 0.5
nodes:
  source: {}

  process_data:
    agent: copyAgent
    inputs:
      data: :source.user_input

  output:
    agent: copyAgent
    inputs:
      result: :process_data.data
    isResult: true
"""
        result = validate_output_node_convention(yaml_content)

        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_missing_output_node(self):
        """Test that a workflow without 'output' node fails validation."""
        yaml_content = """
version: 0.5
nodes:
  source: {}

  format_results:
    agent: copyAgent
    inputs:
      result: :source.user_input
    isResult: true
"""
        result = validate_output_node_convention(yaml_content)

        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("output" in error.lower() for error in result.errors)

    def test_output_node_without_is_result(self):
        """Test that 'output' node without isResult: true fails validation."""
        yaml_content = """
version: 0.5
nodes:
  source: {}

  output:
    agent: copyAgent
    inputs:
      result: :source.user_input
"""
        result = validate_output_node_convention(yaml_content)

        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("isResult" in error for error in result.errors)

    def test_output_node_with_is_result_false(self):
        """Test that 'output' node with isResult: false fails validation."""
        yaml_content = """
version: 0.5
nodes:
  source: {}

  output:
    agent: copyAgent
    inputs:
      result: :source.user_input
    isResult: false
"""
        result = validate_output_node_convention(yaml_content)

        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_multiple_is_result_nodes_warning(self):
        """Test that multiple nodes with isResult: true generate a warning."""
        yaml_content = """
version: 0.5
nodes:
  source: {}

  intermediate:
    agent: copyAgent
    inputs:
      data: :source.user_input
    isResult: true

  output:
    agent: copyAgent
    inputs:
      result: :intermediate.data
    isResult: true
"""
        result = validate_output_node_convention(yaml_content)

        # Should still be valid but with a warning
        assert result.is_valid is True
        assert len(result.warnings) > 0
        assert any("multiple" in warning.lower() for warning in result.warnings)

    def test_invalid_yaml_syntax(self):
        """Test that invalid YAML syntax is handled gracefully."""
        yaml_content = """
version: 0.5
nodes:
  source: {}
  output:
    agent: copyAgent
    inputs:
      result: :source.user_input
    isResult: true
    invalid: yaml: syntax:
"""
        result = validate_output_node_convention(yaml_content)

        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_empty_yaml_content(self):
        """Test that empty YAML content fails validation."""
        yaml_content = ""

        result = validate_output_node_convention(yaml_content)

        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_no_nodes_section(self):
        """Test that YAML without nodes section fails validation."""
        yaml_content = """
version: 0.5
"""
        result = validate_output_node_convention(yaml_content)

        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_alternative_node_names_fail(self):
        """Test that common alternative node names fail validation."""
        alternative_names = ["format_results", "final_output", "result", "final"]

        for name in alternative_names:
            yaml_content = f"""
version: 0.5
nodes:
  source: {{}}

  {name}:
    agent: copyAgent
    inputs:
      result: :source.user_input
    isResult: true
"""
            result = validate_output_node_convention(yaml_content)

            assert result.is_valid is False, (
                f"Node name '{name}' should fail validation"
            )
            assert any("output" in error.lower() for error in result.errors)


class TestPromptContainsOutputNodeRequirement:
    """Test that workflow generation prompt contains output node requirements."""

    def test_system_prompt_contains_output_node_requirement(self):
        """Test that system prompt mentions output node naming convention."""
        prompt = WORKFLOW_GENERATION_SYSTEM_PROMPT

        # Should mention the output node requirement
        assert "output" in prompt.lower()
        # Should mention isResult requirement
        assert "isResult" in prompt or "isresult" in prompt.lower()

    def test_user_prompt_contains_output_node_section(self):
        """Test that user prompt contains output node section."""
        task_data = {
            "name": "Test Task",
            "description": "A test task",
            "input_interface": {"schema": {}},
            "output_interface": {"schema": {}},
        }
        graphai_capabilities = {"agents": []}
        expert_agent_capabilities = {"utility_apis": [], "ai_agent_apis": []}

        prompt = create_workflow_generation_prompt(
            task_data, graphai_capabilities, expert_agent_capabilities
        )

        # The prompt should contain output node requirement
        # This will be added in Phase 1.1
        assert "output" in prompt.lower()


class TestValidationResultDataClass:
    """Test ValidationResult data class."""

    def test_validation_result_success(self):
        """Test creating a successful validation result."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])

        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_validation_result_failure(self):
        """Test creating a failed validation result."""
        errors = ["Missing output node", "isResult not set"]
        warnings = ["Multiple isResult nodes"]
        result = ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        assert result.is_valid is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
