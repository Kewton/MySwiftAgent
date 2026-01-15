"""Tests for YamlValidatorSubWorkflow.

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.errors import ErrorCode
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.validators import (
    check_circular_references,
    validate_agents,
    validate_references,
    validate_structure,
    validate_yaml_syntax,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_validator import (
    YamlValidationResult,
    YamlValidatorSubWorkflow,
)


class TestYamlSyntaxValidator:
    """Tests for YAML syntax validation."""

    def test_valid_yaml(self):
        """Test valid YAML passes syntax check."""
        yaml_content = """
version: "0.5"
nodes:
  source: {}
"""
        parsed, errors = validate_yaml_syntax(yaml_content)
        assert parsed is not None
        assert len(errors) == 0

    def test_empty_yaml(self):
        """Test empty YAML fails."""
        parsed, errors = validate_yaml_syntax("")
        assert parsed is None
        assert len(errors) > 0
        assert errors[0].code == ErrorCode.YAML_SYNTAX

    def test_invalid_yaml_syntax(self):
        """Test invalid YAML syntax is caught."""
        yaml_content = """
version: "0.5"
nodes:
  source: {
    invalid
"""
        parsed, errors = validate_yaml_syntax(yaml_content)
        assert parsed is None
        assert len(errors) > 0
        assert errors[0].code == ErrorCode.YAML_SYNTAX

    def test_yaml_not_dict(self):
        """Test YAML that parses to non-dict fails."""
        yaml_content = "- item1\n- item2"
        parsed, errors = validate_yaml_syntax(yaml_content)
        assert parsed is None
        assert len(errors) > 0


class TestStructureValidator:
    """Tests for structure validation."""

    def test_valid_structure(self):
        """Test valid structure passes."""
        parsed = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "output": {"agent": "copyAgent", "isResult": True},
            },
        }
        errors = validate_structure(parsed)
        assert len(errors) == 0

    def test_missing_version(self):
        """Test missing version is caught."""
        parsed = {
            "nodes": {
                "source": {},
                "output": {"agent": "copyAgent", "isResult": True},
            },
        }
        errors = validate_structure(parsed)
        assert any(e.code == ErrorCode.INVALID_VERSION for e in errors)

    def test_invalid_version(self):
        """Test invalid version is caught."""
        parsed = {
            "version": "0.6",  # Wrong version
            "nodes": {
                "source": {},
                "output": {"agent": "copyAgent", "isResult": True},
            },
        }
        errors = validate_structure(parsed)
        assert any(e.code == ErrorCode.INVALID_VERSION for e in errors)

    def test_missing_source_node(self):
        """Test missing source node is caught."""
        parsed = {
            "version": "0.5",
            "nodes": {
                "output": {"agent": "copyAgent", "isResult": True},
            },
        }
        errors = validate_structure(parsed)
        assert any(e.code == ErrorCode.MISSING_SOURCE for e in errors)

    def test_missing_is_result(self):
        """Test missing isResult node is caught."""
        parsed = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "process": {"agent": "fetchAgent"},
            },
        }
        errors = validate_structure(parsed)
        assert any(e.code == ErrorCode.MISSING_RESULT for e in errors)

    def test_empty_nodes(self):
        """Test empty nodes is caught."""
        parsed = {
            "version": "0.5",
            "nodes": {},
        }
        errors = validate_structure(parsed)
        assert any(e.code == ErrorCode.EMPTY_NODES for e in errors)


class TestAgentValidator:
    """Tests for agent validation."""

    def test_valid_agents(self):
        """Test valid agents pass."""
        nodes = {
            "source": {},
            "fetch": {"agent": "fetchAgent"},
            "output": {"agent": "copyAgent", "isResult": True},
        }
        errors = validate_agents(nodes)
        assert len(errors) == 0

    def test_unknown_agent(self):
        """Test unknown agent is caught."""
        nodes = {
            "source": {},
            "invalid": {"agent": "nonExistentAgent"},
        }
        errors = validate_agents(nodes)
        assert any(e.code == ErrorCode.UNKNOWN_AGENT for e in errors)

    def test_nested_agent_validation(self):
        """Test nested agents are validated."""
        nodes = {
            "source": {},
            "map": {
                "agent": "mapAgent",
                "graph": {
                    "nodes": {
                        "item_source": {},
                        "process": {"agent": "invalidNestedAgent"},
                    },
                },
            },
        }
        errors = validate_agents(nodes)
        assert any(e.code == ErrorCode.UNKNOWN_AGENT for e in errors)


class TestReferenceValidator:
    """Tests for reference validation."""

    def test_valid_references(self):
        """Test valid references pass."""
        nodes = {
            "source": {},
            "process": {
                "agent": "fetchAgent",
                "inputs": {"data": ":source.query"},
            },
            "output": {
                "agent": "copyAgent",
                "inputs": {"result": ":process.result"},
                "isResult": True,
            },
        }
        errors = validate_references(nodes)
        assert len(errors) == 0

    def test_undefined_reference(self):
        """Test undefined reference is caught."""
        nodes = {
            "source": {},
            "output": {
                "agent": "copyAgent",
                "inputs": {"data": ":undefined_node.result"},
                "isResult": True,
            },
        }
        errors = validate_references(nodes)
        assert any(e.code == ErrorCode.UNDEFINED_NODE_REFERENCE for e in errors)


class TestCircularReferenceCheck:
    """Tests for circular reference detection."""

    def test_no_circular_reference(self):
        """Test no circular reference passes."""
        nodes = {
            "source": {},
            "step1": {
                "agent": "fetchAgent",
                "inputs": {"data": ":source"},
            },
            "step2": {
                "agent": "copyAgent",
                "inputs": {"data": ":step1"},
                "isResult": True,
            },
        }
        errors = check_circular_references(nodes)
        assert len(errors) == 0


class TestYamlValidatorSubWorkflow:
    """Tests for YamlValidatorSubWorkflow class."""

    def test_create_validator(self):
        """Test creating validator."""
        validator = YamlValidatorSubWorkflow()
        assert validator is not None

    def test_validate_valid_yaml(self):
        """Test validating valid YAML."""
        yaml_content = """
version: "0.5"
nodes:
  source: {}
  output:
    agent: copyAgent
    isResult: true
"""
        validator = YamlValidatorSubWorkflow()
        result = validator.validate(yaml_content)

        assert isinstance(result, YamlValidationResult)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_invalid_yaml_syntax(self):
        """Test validating invalid YAML syntax."""
        yaml_content = """
invalid yaml {
"""
        validator = YamlValidatorSubWorkflow()
        result = validator.validate(yaml_content)

        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_validate_missing_source(self):
        """Test validating YAML without source."""
        yaml_content = """
version: "0.5"
nodes:
  output:
    agent: copyAgent
    isResult: true
"""
        validator = YamlValidatorSubWorkflow()
        result = validator.validate(yaml_content)

        assert result.is_valid is False
        assert any(e.code == ErrorCode.MISSING_SOURCE for e in result.errors)

    def test_validate_unknown_agent(self):
        """Test validating YAML with unknown agent."""
        yaml_content = """
version: "0.5"
nodes:
  source: {}
  invalid:
    agent: fakeAgent
    isResult: true
"""
        validator = YamlValidatorSubWorkflow()
        result = validator.validate(yaml_content)

        assert result.is_valid is False
        assert any(e.code == ErrorCode.UNKNOWN_AGENT for e in result.errors)

    def test_quick_validate(self):
        """Test quick_validate returns simple tuple."""
        yaml_content = """
version: "0.5"
nodes:
  source: {}
  output:
    agent: copyAgent
    isResult: true
"""
        validator = YamlValidatorSubWorkflow()
        is_valid, messages = validator.quick_validate(yaml_content)

        assert is_valid is True
        assert len(messages) == 0

    def test_validation_result_to_validation_result(self):
        """Test YamlValidationResult converts to ValidationResult."""
        yaml_content = """
version: "0.5"
nodes:
  source: {}
"""  # Missing isResult
        validator = YamlValidatorSubWorkflow()
        result = validator.validate(yaml_content)
        validation_result = result.to_validation_result()

        assert validation_result.is_valid is False
        assert len(validation_result.errors) > 0
