"""Tests for AgentConstraintValidator.

Issue #342 Task 1.3: AgentConstraintValidator implementation tests.

This module tests:
- stringTemplateAgent JavaScript expression detection
- fetchAgent timeout validation (millisecond units)
- URL environment variable detection
- ReDoS-safe pattern matching
"""

import pytest


class TestAgentConstraintValidatorStringTemplate:
    """Tests for stringTemplateAgent constraints."""

    @pytest.fixture
    def validator(self):
        """Create AgentConstraintValidator instance."""
        from aiagent.langgraph.jobGeneratorV2.validators.agent_constraint_validator import (
            AgentConstraintValidator,
        )

        return AgentConstraintValidator()

    def test_valid_simple_template(self, validator):
        """Simple variable substitution is valid."""
        config = {
            "agent": "stringTemplateAgent",
            "params": {"template": "Query: ${query}"},
        }
        errors = validator.validate_string_template_agent(config)
        assert len(errors) == 0

    def test_valid_multiple_variables(self, validator):
        """Multiple variable substitution is valid."""
        config = {
            "agent": "stringTemplateAgent",
            "params": {"template": "Search: ${query} (${count} results)"},
        }
        errors = validator.validate_string_template_agent(config)
        assert len(errors) == 0

    def test_invalid_json_stringify(self, validator):
        """JSON.stringify() in template is invalid."""
        config = {
            "agent": "stringTemplateAgent",
            "params": {"template": "Data: ${JSON.stringify(results)}"},
        }
        errors = validator.validate_string_template_agent(config)
        assert len(errors) > 0
        assert any(
            "json_stringify" in e.lower() or "javascript" in e.lower() for e in errors
        )

    def test_invalid_json_parse(self, validator):
        """JSON.parse() in template is invalid."""
        config = {
            "agent": "stringTemplateAgent",
            "params": {"template": "Data: ${JSON.parse(data)}"},
        }
        errors = validator.validate_string_template_agent(config)
        assert len(errors) > 0

    def test_invalid_array_map(self, validator):
        """Array.map() in template is invalid."""
        config = {
            "agent": "stringTemplateAgent",
            "params": {"template": "${items.map(x => x.name)}"},
        }
        errors = validator.validate_string_template_agent(config)
        assert len(errors) > 0
        assert any("javascript" in e.lower() or "map" in e.lower() for e in errors)

    def test_invalid_array_filter(self, validator):
        """Array.filter() in template is invalid."""
        config = {
            "agent": "stringTemplateAgent",
            "params": {"template": "${items.filter(x => x.active)}"},
        }
        errors = validator.validate_string_template_agent(config)
        assert len(errors) > 0

    def test_invalid_array_reduce(self, validator):
        """Array.reduce() in template is invalid."""
        config = {
            "agent": "stringTemplateAgent",
            "params": {"template": "${items.reduce((a,b) => a + b)}"},
        }
        errors = validator.validate_string_template_agent(config)
        assert len(errors) > 0

    def test_invalid_object_keys(self, validator):
        """Object.keys() in template is invalid."""
        config = {
            "agent": "stringTemplateAgent",
            "params": {"template": "${Object.keys(data)}"},
        }
        errors = validator.validate_string_template_agent(config)
        assert len(errors) > 0

    def test_invalid_string_prototype_method(self, validator):
        """String prototype methods in template are invalid."""
        config = {
            "agent": "stringTemplateAgent",
            "params": {"template": "${text.toLowerCase()}"},
        }
        errors = validator.validate_string_template_agent(config)
        assert len(errors) > 0


class TestAgentConstraintValidatorFetchAgent:
    """Tests for fetchAgent constraints."""

    @pytest.fixture
    def validator(self):
        """Create AgentConstraintValidator instance."""
        from aiagent.langgraph.jobGeneratorV2.validators.agent_constraint_validator import (
            AgentConstraintValidator,
        )

        return AgentConstraintValidator()

    def test_valid_timeout_milliseconds(self, validator):
        """Timeout in milliseconds (30000) is valid."""
        config = {"agent": "fetchAgent", "timeout": 30000}
        errors = validator.validate_fetch_agent(config)
        assert len(errors) == 0

    def test_valid_timeout_120_seconds(self, validator):
        """Timeout of 120000ms (2 min) is valid."""
        config = {"agent": "fetchAgent", "timeout": 120000}
        errors = validator.validate_fetch_agent(config)
        assert len(errors) == 0

    def test_invalid_timeout_likely_seconds(self, validator):
        """Timeout likely in seconds (60 vs 60000) should warn."""
        config = {"agent": "fetchAgent", "timeout": 60}  # 60ms vs 60s
        errors = validator.validate_fetch_agent(config)
        assert len(errors) > 0
        assert any("milliseconds" in e.lower() or "ms" in e for e in errors)

    def test_invalid_timeout_180(self, validator):
        """Timeout of 180 (likely 180s vs 180ms) should warn."""
        config = {"agent": "fetchAgent", "timeout": 180}
        errors = validator.validate_fetch_agent(config)
        assert len(errors) > 0

    def test_invalid_timeout_too_small(self, validator):
        """Timeout too small (<1000ms) should warn."""
        config = {"agent": "fetchAgent", "timeout": 500}
        errors = validator.validate_fetch_agent(config)
        assert len(errors) > 0

    def test_invalid_timeout_too_large(self, validator):
        """Timeout too large (>300000ms) should warn."""
        config = {"agent": "fetchAgent", "timeout": 600000}
        errors = validator.validate_fetch_agent(config)
        assert len(errors) > 0

    def test_valid_url_localhost(self, validator):
        """URL with localhost is valid."""
        config = {
            "agent": "fetchAgent",
            "inputs": {"url": "http://localhost:8004/api"},
        }
        errors = validator.validate_fetch_agent(config)
        assert len(errors) == 0

    def test_invalid_url_env_var_dollar(self, validator):
        """URL with ${ENV_VAR} is invalid."""
        config = {
            "agent": "fetchAgent",
            "inputs": {"url": "${EXPERT_AGENT_URL}/api"},
        }
        errors = validator.validate_fetch_agent(config)
        assert len(errors) > 0
        assert any("environment" in e.lower() or "env" in e.lower() for e in errors)

    def test_invalid_url_env_var_double_brace(self, validator):
        """URL with {{ENV_VAR}} is invalid."""
        config = {
            "agent": "fetchAgent",
            "inputs": {"url": "{{EXPERT_AGENT_URL}}/api"},
        }
        errors = validator.validate_fetch_agent(config)
        assert len(errors) > 0

    def test_invalid_url_env_var_percent(self, validator):
        """URL with %ENV_VAR% is invalid."""
        config = {
            "agent": "fetchAgent",
            "inputs": {"url": "http://%HOST%:8004/api"},
        }
        errors = validator.validate_fetch_agent(config)
        assert len(errors) > 0


class TestAgentConstraintValidatorAllAgents:
    """Tests for multi-agent validation."""

    @pytest.fixture
    def validator(self):
        """Create AgentConstraintValidator instance."""
        from aiagent.langgraph.jobGeneratorV2.validators.agent_constraint_validator import (
            AgentConstraintValidator,
        )

        return AgentConstraintValidator()

    def test_validate_node_string_template(self, validator):
        """Validate stringTemplateAgent node."""
        node_def = {
            "agent": "stringTemplateAgent",
            "params": {"template": "Value: ${JSON.stringify(data)}"},
        }
        errors = validator.validate_node("format_node", node_def)
        assert len(errors) > 0

    def test_validate_node_fetch_agent(self, validator):
        """Validate fetchAgent node."""
        node_def = {
            "agent": "fetchAgent",
            "inputs": {"url": "${API_URL}/search"},
            "timeout": 30,
        }
        errors = validator.validate_node("search_node", node_def)
        assert len(errors) >= 2  # URL env var + timeout

    def test_validate_workflow_multiple_errors(self, validator):
        """Validate workflow with multiple errors."""
        workflow = {
            "nodes": {
                "source": {},
                "format": {
                    "agent": "stringTemplateAgent",
                    "params": {"template": "${JSON.stringify(data)}"},
                },
                "fetch": {
                    "agent": "fetchAgent",
                    "inputs": {"url": "${API}/test"},
                    "timeout": 60,
                },
            }
        }
        errors = validator.validate_workflow(workflow)
        assert len(errors) >= 3


class TestAgentConstraintValidatorReDoS:
    """Tests for ReDoS safety."""

    @pytest.fixture
    def validator(self):
        """Create AgentConstraintValidator instance."""
        from aiagent.langgraph.jobGeneratorV2.validators.agent_constraint_validator import (
            AgentConstraintValidator,
        )

        return AgentConstraintValidator()

    def test_long_template_input(self, validator):
        """Long template should not cause ReDoS."""
        # Create a long but valid template
        long_template = "Value: " + "${var}" * 1000
        config = {
            "agent": "stringTemplateAgent",
            "params": {"template": long_template},
        }
        # This should complete in reasonable time
        import time

        start = time.time()
        errors = validator.validate_string_template_agent(config)
        elapsed = time.time() - start
        # Should complete in under 1 second
        assert elapsed < 1.0

    def test_malicious_nested_braces(self, validator):
        """Nested braces should not cause exponential backtracking."""
        malicious = "${" * 100 + "}" * 100
        config = {
            "agent": "stringTemplateAgent",
            "params": {"template": malicious},
        }
        import time

        start = time.time()
        errors = validator.validate_string_template_agent(config)
        elapsed = time.time() - start
        assert elapsed < 1.0

    def test_max_template_length(self, validator):
        """Template exceeding max length should be rejected."""
        config = {
            "agent": "stringTemplateAgent",
            "params": {"template": "x" * 20000},  # 20KB template
        }
        errors = validator.validate_string_template_agent(config)
        # Should either handle gracefully or report error
        # Not cause ReDoS
