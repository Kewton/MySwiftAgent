"""Unit tests for interface validator (Issue #338 Phase 7).

Tests for validating interface compatibility between consecutive tasks
in a task chain.
"""

from aiagent.langgraph.workflowGeneratorAgents.utils.interface_validator import (
    InterfaceIssue,
    InterfaceValidationResult,
    format_interface_issues,
    validate_interface_compatibility,
    validate_task_chain_interfaces,
)


class TestInterfaceIssue:
    """Tests for InterfaceIssue model."""

    def test_create_issue(self):
        """Should create an interface issue."""
        issue = InterfaceIssue(
            field="results",
            issue_type="missing_required",
            message="Field is missing",
            severity="error",
        )
        assert issue.field == "results"
        assert issue.issue_type == "missing_required"
        assert issue.severity == "error"

    def test_default_severity_is_error(self):
        """Default severity should be 'error'."""
        issue = InterfaceIssue(
            field="data",
            issue_type="type_mismatch",
            message="Type mismatch",
        )
        assert issue.severity == "error"


class TestInterfaceValidationResult:
    """Tests for InterfaceValidationResult model."""

    def test_compatible_result(self):
        """Should represent a compatible result."""
        result = InterfaceValidationResult(is_compatible=True, issues=[])
        assert result.is_compatible is True
        assert len(result.issues) == 0
        assert bool(result) is True

    def test_incompatible_result(self):
        """Should represent an incompatible result."""
        result = InterfaceValidationResult(
            is_compatible=False,
            issues=[
                InterfaceIssue(
                    field="x",
                    issue_type="missing_required",
                    message="Field x missing",
                )
            ],
        )
        assert result.is_compatible is False
        assert len(result.issues) == 1
        assert bool(result) is False


class TestValidateInterfaceCompatibility:
    """Tests for validate_interface_compatibility function."""

    def test_compatible_interfaces(self):
        """Should return compatible when all required fields are provided."""
        prev_output = {
            "schema": {
                "properties": {
                    "results": {"type": "array"},
                    "total": {"type": "integer"},
                }
            }
        }
        next_input = {
            "schema": {
                "properties": {
                    "results": {"type": "array"},
                },
                "required": ["results"],
            }
        }

        result = validate_interface_compatibility(prev_output, next_input)

        assert result.is_compatible is True
        # No errors, but might have warnings for unused fields
        assert all(issue.severity != "error" for issue in result.issues)

    def test_missing_required_field(self):
        """Should return incompatible when required field is missing."""
        prev_output = {
            "schema": {
                "properties": {
                    "data": {"type": "object"},
                }
            }
        }
        next_input = {
            "schema": {
                "properties": {
                    "results": {"type": "array"},
                },
                "required": ["results"],
            }
        }

        result = validate_interface_compatibility(prev_output, next_input)

        assert result.is_compatible is False
        assert len(result.issues) >= 1

        # Find the missing_required issue
        missing_issues = [
            i for i in result.issues if i.issue_type == "missing_required"
        ]
        assert len(missing_issues) == 1
        assert missing_issues[0].field == "results"

    def test_type_mismatch(self):
        """Should return incompatible when types don't match."""
        prev_output = {
            "schema": {
                "properties": {
                    "count": {"type": "string"},  # Wrong type
                }
            }
        }
        next_input = {
            "schema": {
                "properties": {
                    "count": {"type": "array"},
                },
                "required": ["count"],
            }
        }

        result = validate_interface_compatibility(prev_output, next_input)

        assert result.is_compatible is False

        # Find type mismatch issue
        type_issues = [i for i in result.issues if i.issue_type == "type_mismatch"]
        assert len(type_issues) == 1
        assert type_issues[0].field == "count"

    def test_number_integer_compatibility(self):
        """Number and integer types should be compatible."""
        prev_output = {
            "schema": {
                "properties": {
                    "value": {"type": "integer"},
                }
            }
        }
        next_input = {
            "schema": {
                "properties": {
                    "value": {"type": "number"},
                },
                "required": ["value"],
            }
        }

        result = validate_interface_compatibility(prev_output, next_input)

        # Should be compatible
        type_issues = [i for i in result.issues if i.issue_type == "type_mismatch"]
        assert len(type_issues) == 0

    def test_empty_schemas(self):
        """Should handle empty schemas gracefully."""
        prev_output = {"schema": {}}
        next_input = {"schema": {}}

        result = validate_interface_compatibility(prev_output, next_input)

        assert result.is_compatible is True
        assert len(result.issues) == 0

    def test_empty_output_with_requirements(self):
        """Empty output should fail when next task has requirements."""
        prev_output = {"schema": {}}
        next_input = {
            "schema": {
                "properties": {"data": {"type": "object"}},
                "required": ["data"],
            }
        }

        result = validate_interface_compatibility(prev_output, next_input)

        assert result.is_compatible is False
        assert any(i.issue_type == "missing_required" for i in result.issues)

    def test_optional_field_not_provided_is_warning(self):
        """Missing optional fields should generate warnings, not errors."""
        prev_output = {
            "schema": {
                "properties": {
                    "required_field": {"type": "string"},
                }
            }
        }
        next_input = {
            "schema": {
                "properties": {
                    "required_field": {"type": "string"},
                    "optional_field": {"type": "string"},
                },
                "required": ["required_field"],
            }
        }

        result = validate_interface_compatibility(prev_output, next_input)

        assert result.is_compatible is True  # No errors
        # Should have warning for optional field
        warnings = [i for i in result.issues if i.severity == "warning"]
        assert len(warnings) >= 1

    def test_missing_interface_keys(self):
        """Should handle missing interface keys."""
        # No schema key
        prev_output = {}
        next_input = {}

        result = validate_interface_compatibility(prev_output, next_input)

        assert result.is_compatible is True
        assert len(result.issues) == 0

    def test_multiple_issues(self):
        """Should report multiple issues."""
        prev_output = {
            "schema": {
                "properties": {
                    "wrong_type": {"type": "string"},
                }
            }
        }
        next_input = {
            "schema": {
                "properties": {
                    "missing": {"type": "array"},
                    "wrong_type": {"type": "integer"},
                },
                "required": ["missing", "wrong_type"],
            }
        }

        result = validate_interface_compatibility(prev_output, next_input)

        assert result.is_compatible is False
        assert len(result.issues) >= 2


class TestValidateTaskChainInterfaces:
    """Tests for validate_task_chain_interfaces function."""

    def test_empty_chain(self):
        """Should handle empty task list."""
        result = validate_task_chain_interfaces([])
        assert result == []

    def test_single_task(self):
        """Should handle single task (no pairs to validate)."""
        tasks = [{"input_interface": {}, "output_interface": {}}]
        result = validate_task_chain_interfaces(tasks)
        assert result == []

    def test_compatible_chain(self):
        """Should return empty list for compatible chain."""
        tasks = [
            {
                "input_interface": {},
                "output_interface": {
                    "schema": {
                        "properties": {"data": {"type": "string"}},
                    }
                },
            },
            {
                "input_interface": {
                    "schema": {
                        "properties": {"data": {"type": "string"}},
                        "required": ["data"],
                    }
                },
                "output_interface": {},
            },
        ]

        results = validate_task_chain_interfaces(tasks)

        # Compatible chain should have no issues
        incompatible = [(i, j, r) for i, j, r in results if not r.is_compatible]
        assert len(incompatible) == 0

    def test_incompatible_chain(self):
        """Should report issues for incompatible chain."""
        tasks = [
            {
                "input_interface": {},
                "output_interface": {
                    "schema": {
                        "properties": {"wrong_field": {"type": "string"}},
                    }
                },
            },
            {
                "input_interface": {
                    "schema": {
                        "properties": {"required_field": {"type": "string"}},
                        "required": ["required_field"],
                    }
                },
                "output_interface": {},
            },
        ]

        results = validate_task_chain_interfaces(tasks)

        # Should have at least one result
        assert len(results) >= 1
        # First pair (0, 1) should have issues
        pair_result = next((r for i, j, r in results if i == 0 and j == 1), None)
        assert pair_result is not None
        assert not pair_result.is_compatible

    def test_multi_task_chain(self):
        """Should validate all consecutive pairs."""
        tasks = [
            {
                "input_interface": {},
                "output_interface": {
                    "schema": {"properties": {"a": {"type": "string"}}}
                },
            },
            {
                "input_interface": {
                    "schema": {"properties": {"a": {"type": "string"}}}
                },
                "output_interface": {
                    "schema": {"properties": {"b": {"type": "integer"}}}
                },
            },
            {
                "input_interface": {
                    "schema": {
                        "properties": {"c": {"type": "array"}},  # Mismatch
                        "required": ["c"],
                    }
                },
                "output_interface": {},
            },
        ]

        results = validate_task_chain_interfaces(tasks)

        # Should have issue for pair (1, 2)
        pair_1_2 = [r for i, j, r in results if i == 1 and j == 2]
        assert len(pair_1_2) > 0


class TestFormatInterfaceIssues:
    """Tests for format_interface_issues function."""

    def test_no_issues(self):
        """Should return appropriate message for no issues."""
        result = format_interface_issues([])
        assert "No interface issues found" in result

    def test_format_errors(self):
        """Should format error issues."""
        issues = [
            InterfaceIssue(
                field="data",
                issue_type="missing_required",
                message="Field 'data' is missing",
                severity="error",
            )
        ]

        result = format_interface_issues(issues)

        assert "Errors" in result
        assert "missing_required" in result
        assert "data" in result

    def test_format_warnings(self):
        """Should format warning issues."""
        issues = [
            InterfaceIssue(
                field="optional",
                issue_type="field_not_provided",
                message="Optional field not provided",
                severity="warning",
            )
        ]

        result = format_interface_issues(issues)

        assert "Warnings" in result
        assert "field_not_provided" in result

    def test_format_mixed_issues(self):
        """Should format both errors and warnings."""
        issues = [
            InterfaceIssue(
                field="required",
                issue_type="missing_required",
                message="Required missing",
                severity="error",
            ),
            InterfaceIssue(
                field="optional",
                issue_type="field_not_provided",
                message="Optional missing",
                severity="warning",
            ),
        ]

        result = format_interface_issues(issues)

        assert "Errors (1)" in result
        assert "Warnings (1)" in result


class TestIntegration:
    """Integration tests for interface validation."""

    def test_real_world_task_chain_compatible(self):
        """Test with realistic task chain interfaces."""
        # Task 0: Search task
        task0_output = {
            "schema": {
                "type": "object",
                "properties": {
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "url": {"type": "string"},
                            },
                        },
                    },
                    "total_count": {"type": "integer"},
                },
            }
        }

        # Task 1: Summarize task
        task1_input = {
            "schema": {
                "type": "object",
                "properties": {
                    "results": {"type": "array"},
                },
                "required": ["results"],
            }
        }

        result = validate_interface_compatibility(task0_output, task1_input)

        assert result.is_compatible is True

    def test_real_world_task_chain_incompatible(self):
        """Test with incompatible realistic task chain interfaces."""
        # Task 0 outputs 'search_results'
        task0_output = {
            "schema": {
                "type": "object",
                "properties": {
                    "search_results": {"type": "array"},  # Note: different name
                },
            }
        }

        # Task 1 expects 'results'
        task1_input = {
            "schema": {
                "type": "object",
                "properties": {
                    "results": {"type": "array"},  # Note: different name
                },
                "required": ["results"],  # Required!
            }
        }

        result = validate_interface_compatibility(task0_output, task1_input)

        # Should fail because 'results' is required but not provided
        assert result.is_compatible is False
        assert any(
            i.issue_type == "missing_required" and i.field == "results"
            for i in result.issues
        )
