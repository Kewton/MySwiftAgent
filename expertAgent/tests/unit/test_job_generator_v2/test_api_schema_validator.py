"""Tests for APISchemaValidator.

Issue #344: API Schema validation for workflow generation.

This module tests:
- API parameter name validation
- Parameter type validation
- Missing required parameter detection
- Similar parameter name suggestions (typo detection)
- Integration with ValidationPipeline
"""

import pytest

from aiagent.langgraph.jobGeneratorV2.validators import (
    ValidationErrorCode,
)


class TestAPISchemaValidatorBasic:
    """Basic tests for APISchemaValidator."""

    @pytest.fixture
    def validator(self):
        """Create APISchemaValidator instance."""
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            APISchemaValidator,
        )

        return APISchemaValidator()

    # ========== Valid Workflow Tests ==========

    def test_validate_valid_google_search_workflow(self, validator):
        """Valid workflow with correct google_search parameters."""
        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "queries": [":source.user_input.query"],
                            "num": 3,
                        },
                    },
                    "timeout": 60000,
                },
            }
        }
        errors = validator.validate(workflow)
        assert len(errors) == 0

    def test_validate_valid_fetch_web_content_workflow(self, validator):
        """Valid workflow with correct fetch_web_content parameters."""
        workflow = {
            "nodes": {
                "source": {},
                "fetch": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/fetch_web_content",
                        "method": "POST",
                        "body": {
                            "url": ":source.user_input.target_url",
                            "upload_to_drive": False,
                        },
                    },
                    "timeout": 60000,
                },
            }
        }
        errors = validator.validate(workflow)
        assert len(errors) == 0

    def test_validate_valid_json_stringify_workflow(self, validator):
        """Valid workflow with correct json_stringify parameters."""
        workflow = {
            "nodes": {
                "source": {},
                "stringify": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/json_stringify",
                        "method": "POST",
                        "body": {
                            "data": ":source.user_input.data",
                        },
                    },
                    "timeout": 30000,
                },
            }
        }
        errors = validator.validate(workflow)
        assert len(errors) == 0

    # ========== Unknown Parameter Tests ==========

    def test_validate_unknown_parameter_google_search(self, validator):
        """Detect parameter name mismatch 'query' in google_search (should be 'queries').

        Issue #344: When a parameter is a known alias (typo), use PARAMETER_NAME_MISMATCH
        instead of UNKNOWN_API_PARAMETER.
        """
        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "query": ":source.user_input.query",  # Wrong! Should be 'queries'
                            "num": 3,
                        },
                    },
                    "timeout": 60000,
                },
            }
        }
        errors = validator.validate(workflow)
        assert len(errors) >= 1
        error = errors[0]
        # Issue #344: Use PARAMETER_NAME_MISMATCH for known typos (alias exists)
        assert error.code == ValidationErrorCode.PARAMETER_NAME_MISMATCH
        assert "query" in error.message.lower()
        # Should suggest 'queries' as the correct parameter
        assert "queries" in error.suggestion.lower()

    def test_validate_unknown_parameter_num_results(self, validator):
        """Detect parameter name mismatch 'num_results' (should be 'num').

        Issue #344: When a parameter is a known alias (typo), use PARAMETER_NAME_MISMATCH
        instead of UNKNOWN_API_PARAMETER.
        """
        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "queries": [":source.user_input.query"],
                            "num_results": 3,  # Wrong! Should be 'num'
                        },
                    },
                    "timeout": 60000,
                },
            }
        }
        errors = validator.validate(workflow)
        assert len(errors) >= 1
        error = errors[0]
        # Issue #344: Use PARAMETER_NAME_MISMATCH for known typos (alias exists)
        assert error.code == ValidationErrorCode.PARAMETER_NAME_MISMATCH
        assert "num_results" in error.message.lower()
        # Should suggest 'num' as the correct parameter
        assert "num" in error.suggestion.lower()

    def test_validate_unknown_parameter_no_suggestion(self, validator):
        """Detect completely unknown parameter with no suggestion."""
        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "queries": [":source.user_input.query"],
                            "random_param": "value",  # Completely unknown
                        },
                    },
                    "timeout": 60000,
                },
            }
        }
        errors = validator.validate(workflow)
        assert len(errors) >= 1
        error = errors[0]
        assert error.code == ValidationErrorCode.UNKNOWN_API_PARAMETER

    # ========== Missing Required Parameter Tests ==========

    def test_validate_missing_required_queries(self, validator):
        """Detect missing required parameter 'queries' in google_search."""
        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "num": 3,  # Missing 'queries' which is required
                        },
                    },
                    "timeout": 60000,
                },
            }
        }
        errors = validator.validate(workflow)
        assert len(errors) >= 1
        error = errors[0]
        assert error.code == ValidationErrorCode.MISSING_REQUIRED_PARAMETER
        assert "queries" in error.message.lower()

    def test_validate_missing_required_url_fetch_content(self, validator):
        """Detect missing required parameter 'url' in fetch_web_content."""
        workflow = {
            "nodes": {
                "source": {},
                "fetch": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/fetch_web_content",
                        "method": "POST",
                        "body": {
                            "upload_to_drive": True,  # Missing 'url' which is required
                        },
                    },
                    "timeout": 60000,
                },
            }
        }
        errors = validator.validate(workflow)
        assert len(errors) >= 1
        error = errors[0]
        assert error.code == ValidationErrorCode.MISSING_REQUIRED_PARAMETER
        assert "url" in error.message.lower()

    # ========== Multiple Error Tests ==========

    def test_validate_multiple_errors(self, validator):
        """Detect multiple errors in a single workflow."""
        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "query": ":source.user_input.query",  # Wrong: should be queries
                            "num_results": 3,  # Wrong: should be num
                        },
                    },
                    "timeout": 60000,
                },
            }
        }
        errors = validator.validate(workflow)
        # Should have at least 2 errors (unknown params) + 1 error (missing required)
        assert len(errors) >= 2

    # ========== Non-fetchAgent Node Tests ==========

    def test_skip_non_fetch_agent_nodes(self, validator):
        """Skip validation for non-fetchAgent nodes."""
        workflow = {
            "nodes": {
                "source": {},
                "template": {
                    "agent": "stringTemplateAgent",
                    "inputs": {
                        "data": ":source.user_input.data",
                    },
                    "params": {
                        "template": "Result: ${data}",
                    },
                },
            }
        }
        errors = validator.validate(workflow)
        assert len(errors) == 0

    # ========== Non-API URL Tests ==========

    def test_skip_non_api_urls(self, validator):
        """Skip validation for non-expertAgent API URLs."""
        workflow = {
            "nodes": {
                "source": {},
                "external": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "https://api.external.com/endpoint",
                        "method": "POST",
                        "body": {
                            "any_param": "value",  # External API, no validation
                        },
                    },
                    "timeout": 30000,
                },
            }
        }
        errors = validator.validate(workflow)
        assert len(errors) == 0


class TestAPISchemaValidatorParameterAliases:
    """Test parameter alias detection (typo suggestions)."""

    @pytest.fixture
    def validator(self):
        """Create APISchemaValidator instance."""
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            APISchemaValidator,
        )

        return APISchemaValidator()

    def test_alias_query_to_queries(self, validator):
        """'query' should suggest 'queries'."""
        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "query": ":source.query",
                            "num": 3,
                        },
                    },
                },
            }
        }
        errors = validator.validate(workflow)
        assert len(errors) >= 1
        # Check suggestion contains 'queries'
        assert any("queries" in e.suggestion.lower() for e in errors)

    def test_alias_num_results_to_num(self, validator):
        """'num_results' should suggest 'num'."""
        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "queries": [":source.query"],
                            "num_results": 5,
                        },
                    },
                },
            }
        }
        errors = validator.validate(workflow)
        assert len(errors) >= 1
        assert any("num" in e.suggestion.lower() for e in errors)


class TestAPISchemaValidatorEdgeCases:
    """Edge case tests for APISchemaValidator."""

    @pytest.fixture
    def validator(self):
        """Create APISchemaValidator instance."""
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            APISchemaValidator,
        )

        return APISchemaValidator()

    def test_empty_workflow(self, validator):
        """Empty workflow should return no errors."""
        errors = validator.validate({})
        assert len(errors) == 0

    def test_no_nodes(self, validator):
        """Workflow with no nodes should return no errors."""
        errors = validator.validate({"nodes": {}})
        assert len(errors) == 0

    def test_empty_body(self, validator):
        """FetchAgent with empty body should check for required params."""
        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {},  # Empty body, missing required 'queries'
                    },
                },
            }
        }
        errors = validator.validate(workflow)
        assert len(errors) >= 1
        assert errors[0].code == ValidationErrorCode.MISSING_REQUIRED_PARAMETER

    def test_no_body(self, validator):
        """FetchAgent with no body should check for required params."""
        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        # No body at all
                    },
                },
            }
        }
        errors = validator.validate(workflow)
        assert len(errors) >= 1
        assert errors[0].code == ValidationErrorCode.MISSING_REQUIRED_PARAMETER

    def test_url_with_localhost(self, validator):
        """URL with localhost should also be validated."""
        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "http://localhost:8004/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "query": ":source.query",  # Wrong!
                        },
                    },
                },
            }
        }
        errors = validator.validate(workflow)
        assert len(errors) >= 1


class TestAPISchemaValidatorTypeMismatch:
    """Test type mismatch detection (Issue #344)."""

    @pytest.fixture
    def validator(self):
        """Create APISchemaValidator instance."""
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            APISchemaValidator,
        )

        return APISchemaValidator()

    def test_type_mismatch_queries_should_be_array(self, validator):
        """Detect type mismatch when 'queries' is string instead of array."""
        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "queries": "single string query",  # Wrong! Should be array
                            "num": 3,
                        },
                    },
                    "timeout": 60000,
                },
            }
        }
        errors = validator.validate(workflow)
        assert len(errors) >= 1
        type_errors = [e for e in errors if e.code == ValidationErrorCode.PARAMETER_TYPE_MISMATCH]
        assert len(type_errors) >= 1
        assert "queries" in type_errors[0].message.lower()
        assert "array" in type_errors[0].message.lower()

    def test_type_mismatch_skip_reference(self, validator):
        """References (starting with ':') should be skipped for type validation."""
        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "queries": ":source.user_input.queries",  # Reference - should be valid
                            "num": 3,
                        },
                    },
                    "timeout": 60000,
                },
            }
        }
        errors = validator.validate(workflow)
        # No type mismatch errors for references
        type_errors = [e for e in errors if e.code == ValidationErrorCode.PARAMETER_TYPE_MISMATCH]
        assert len(type_errors) == 0

    def test_type_mismatch_integer_as_string(self, validator):
        """Detect type mismatch when integer param gets wrong type."""
        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "queries": [":source.query"],
                            "num": "not_a_number",  # Wrong! Should be integer
                        },
                    },
                    "timeout": 60000,
                },
            }
        }
        errors = validator.validate(workflow)
        type_errors = [e for e in errors if e.code == ValidationErrorCode.PARAMETER_TYPE_MISMATCH]
        assert len(type_errors) >= 1
        assert "num" in type_errors[0].message.lower()
        assert "integer" in type_errors[0].message.lower()

    def test_type_mismatch_integer_as_digit_string_allowed(self, validator):
        """Digit strings like '5' should be allowed for integer params."""
        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "queries": [":source.query"],
                            "num": "5",  # Digit string - should be allowed
                        },
                    },
                    "timeout": 60000,
                },
            }
        }
        errors = validator.validate(workflow)
        type_errors = [e for e in errors if e.code == ValidationErrorCode.PARAMETER_TYPE_MISMATCH]
        assert len(type_errors) == 0


class TestValidationErrorCodeExtension:
    """Test new ValidationErrorCode values exist."""

    def test_unknown_api_parameter_exists(self):
        """UNKNOWN_API_PARAMETER error code should exist."""
        assert hasattr(ValidationErrorCode, "UNKNOWN_API_PARAMETER")
        assert ValidationErrorCode.UNKNOWN_API_PARAMETER.value == "UNKNOWN_API_PARAMETER"

    def test_missing_required_parameter_exists(self):
        """MISSING_REQUIRED_PARAMETER error code should exist."""
        assert hasattr(ValidationErrorCode, "MISSING_REQUIRED_PARAMETER")
        assert (
            ValidationErrorCode.MISSING_REQUIRED_PARAMETER.value
            == "MISSING_REQUIRED_PARAMETER"
        )

    def test_parameter_type_mismatch_exists(self):
        """PARAMETER_TYPE_MISMATCH error code should exist."""
        assert hasattr(ValidationErrorCode, "PARAMETER_TYPE_MISMATCH")
        assert (
            ValidationErrorCode.PARAMETER_TYPE_MISMATCH.value == "PARAMETER_TYPE_MISMATCH"
        )

    def test_parameter_name_mismatch_exists(self):
        """PARAMETER_NAME_MISMATCH error code should exist."""
        assert hasattr(ValidationErrorCode, "PARAMETER_NAME_MISMATCH")
        assert (
            ValidationErrorCode.PARAMETER_NAME_MISMATCH.value == "PARAMETER_NAME_MISMATCH"
        )
