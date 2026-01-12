"""Unit tests for taskflow_validator.py - Security validation.

Issue #350 Task 3.1: TaskFlow validator implementation.

Test cases (10 total):
- test_validate_https_url
- test_reject_http_url
- test_reject_private_ip_127
- test_reject_private_ip_10
- test_reject_private_ip_192_168
- test_reject_localhost
- test_code_js_allowed_function
- test_code_js_disallowed_function
- test_path_traversal_rejection
- test_validation_pipeline_integration
"""

from __future__ import annotations

import pytest

from aiagent.langgraph.jobGeneratorV2.validators.taskflow_validator import (
    TaskFlowSchemaValidator,
    TaskFlowSecurityValidator,
)


class TestTaskFlowSecurityValidator:
    """Tests for TaskFlowSecurityValidator."""

    @pytest.fixture
    def validator(self) -> TaskFlowSecurityValidator:
        """Create a security validator instance."""
        return TaskFlowSecurityValidator()

    # URL validation tests
    def test_validate_https_url(self, validator: TaskFlowSecurityValidator) -> None:
        """HTTPS URLs should be accepted."""
        result = validator.validate_url("https://api.example.com/endpoint")
        assert result.is_valid is True

    def test_reject_http_url(self, validator: TaskFlowSecurityValidator) -> None:
        """HTTP URLs should be rejected."""
        result = validator.validate_url("http://api.example.com/endpoint")
        assert result.is_valid is False
        assert "https" in result.errors[0].message.lower()

    def test_reject_private_ip_127(self, validator: TaskFlowSecurityValidator) -> None:
        """127.x.x.x IPs should be rejected (SSRF protection)."""
        result = validator.validate_url("https://127.0.0.1/api")
        assert result.is_valid is False
        assert "private" in result.errors[0].message.lower() or "ssrf" in result.errors[0].message.lower()

    def test_reject_private_ip_10(self, validator: TaskFlowSecurityValidator) -> None:
        """10.x.x.x IPs should be rejected (SSRF protection)."""
        result = validator.validate_url("https://10.0.0.1/api")
        assert result.is_valid is False

    def test_reject_private_ip_192_168(self, validator: TaskFlowSecurityValidator) -> None:
        """192.168.x.x IPs should be rejected (SSRF protection)."""
        result = validator.validate_url("https://192.168.1.1/api")
        assert result.is_valid is False

    def test_reject_localhost(self, validator: TaskFlowSecurityValidator) -> None:
        """localhost should be rejected (SSRF protection)."""
        result = validator.validate_url("https://localhost/api")
        assert result.is_valid is False
        result2 = validator.validate_url("https://localhost:8080/api")
        assert result2.is_valid is False

    # code_js validation tests
    def test_code_js_allowed_function(self, validator: TaskFlowSecurityValidator) -> None:
        """Allowed functions should pass validation."""
        allowed_functions = [
            "formatDate",
            "parseJson",
            "stringConcat",
            "arrayFilter",
            "objectMerge",
        ]
        for func_name in allowed_functions:
            result = validator.validate_code_js_function(func_name)
            assert result.is_valid is True, f"Function {func_name} should be allowed"

    def test_code_js_disallowed_function(self, validator: TaskFlowSecurityValidator) -> None:
        """Disallowed functions should be rejected."""
        disallowed_functions = [
            "eval",
            "exec",
            "require",
            "import",
            "customFunction",
            "fs.readFile",
        ]
        for func_name in disallowed_functions:
            result = validator.validate_code_js_function(func_name)
            assert result.is_valid is False, f"Function {func_name} should be rejected"
            assert "allowed" in result.errors[0].message.lower()

    # Path traversal tests
    def test_path_traversal_rejection(self, validator: TaskFlowSecurityValidator) -> None:
        """Path traversal attempts should be rejected."""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "/scripts/../../../etc/passwd",
            "./../../sensitive/data",
        ]
        for path in malicious_paths:
            result = validator.validate_path(path)
            assert result.is_valid is False, f"Path {path} should be rejected"
            assert "traversal" in result.errors[0].message.lower()

    def test_valid_path(self, validator: TaskFlowSecurityValidator) -> None:
        """Valid paths should be accepted."""
        valid_paths = [
            "/scripts/format.js",
            "scripts/helpers.js",
            "./utils/parser.js",
        ]
        for path in valid_paths:
            result = validator.validate_path(path)
            assert result.is_valid is True, f"Path {path} should be valid"


class TestTaskFlowSchemaValidator:
    """Tests for TaskFlowSchemaValidator."""

    @pytest.fixture
    def validator(self) -> TaskFlowSchemaValidator:
        """Create a schema validator instance."""
        return TaskFlowSchemaValidator()

    def test_valid_workflow(self, validator: TaskFlowSchemaValidator) -> None:
        """Valid workflow should pass validation."""
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": {"query": "string"},
            "output_schema": {"result": "string"},
            "steps": [
                {
                    "id": "fetch",
                    "type": "api_rest",
                    "config": {
                        "method": "GET",
                        "url": "https://api.example.com/data",
                    },
                },
            ],
            "output": {"result": "${fetch.data}"},
        }
        # validate() returns list of errors, empty = valid
        errors = validator.validate(workflow)
        assert errors == []

    def test_invalid_workflow_missing_steps(self, validator: TaskFlowSchemaValidator) -> None:
        """Workflow without steps should fail validation."""
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": {},
            "output_schema": {},
            "output": {},
        }
        # validate() returns list of errors
        errors = validator.validate(workflow)
        assert len(errors) > 0

    def test_workflow_with_http_url(self, validator: TaskFlowSchemaValidator) -> None:
        """Workflow with HTTP URL should fail security validation."""
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": {},
            "output_schema": {},
            "steps": [
                {
                    "id": "fetch",
                    "type": "api_rest",
                    "config": {
                        "method": "GET",
                        "url": "http://insecure.example.com/api",
                    },
                },
            ],
            "output": {},
        }
        # validate() returns list of errors
        errors = validator.validate(workflow)
        assert len(errors) > 0
        # Check for HTTPS error
        assert any("https" in err.message.lower() for err in errors)


class TestValidationPipelineIntegration:
    """Tests for ValidationPipeline integration."""

    def test_validation_pipeline_integration(self) -> None:
        """TaskFlowValidator should integrate with ValidationPipeline."""
        from aiagent.langgraph.jobGeneratorV2.pipeline import ValidationPipeline
        from aiagent.langgraph.jobGeneratorV2.validators.taskflow_validator import (
            TaskFlowSchemaValidator,
        )

        # Create pipeline with TaskFlow validator
        validator = TaskFlowSchemaValidator()
        pipeline = ValidationPipeline(validators=[validator])

        # Valid TaskFlow workflow
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": {"input": "string"},
            "output_schema": {"output": "string"},
            "steps": [
                {
                    "id": "step_001",
                    "type": "api_rest",
                    "config": {
                        "method": "POST",
                        "url": "https://api.example.com",
                    },
                },
            ],
            "output": {"output": "${step_001}"},
        }

        result = pipeline.validate(workflow)
        assert result.is_valid is True
