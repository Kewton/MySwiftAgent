"""Integration tests for Issue #338 derived_fields validation.

This module tests the graceful degradation of derived_fields validation
in the context of the interface_definition workflow node.
"""

from aiagent.langgraph.jobTaskGeneratorAgents.prompts.interface_schema import (
    InterfaceSchemaDefinition,
    InterfaceSchemaResponse,
    get_derived_fields_degradation_count,
    reset_derived_fields_degradation_count,
)


class TestIssue338DerivedFieldsIntegration:
    """Integration tests for derived_fields validation in workflow context."""

    def setup_method(self):
        """Reset degradation counter before each test."""
        reset_derived_fields_degradation_count()

    def test_interface_response_with_mixed_derived_fields(self):
        """Workflow should handle interfaces with mixed valid/invalid derived_fields."""
        # Simulate LLM response with mixed derived_fields formats
        data = {
            "interfaces": [
                # Valid derived_fields
                {
                    "task_id": "task_001",
                    "interface_name": "search_interface",
                    "description": "Search interface",
                    "input_schema": {"type": "object", "properties": {}},
                    "output_schema": {"type": "object", "properties": {}},
                    "derived_fields": {
                        "result_count": {"template": "{count} found", "type": "string"}
                    },
                },
                # Invalid derived_fields (string format - common LLM error)
                {
                    "task_id": "task_002",
                    "interface_name": "email_interface",
                    "description": "Email interface",
                    "input_schema": {"type": "object", "properties": {}},
                    "output_schema": {"type": "object", "properties": {}},
                    "derived_fields": "email_subject -> task_001.output.summary",
                },
                # Empty derived_fields (valid)
                {
                    "task_id": "task_003",
                    "interface_name": "final_interface",
                    "description": "Final interface",
                    "input_schema": {"type": "object", "properties": {}},
                    "output_schema": {"type": "object", "properties": {}},
                    "derived_fields": {},
                },
            ]
        }

        # Parse response - should NOT raise exception
        result = InterfaceSchemaResponse.model_validate(data)

        # Verify all interfaces were parsed
        assert len(result.interfaces) == 3

        # Verify valid derived_fields preserved
        assert "result_count" in result.interfaces[0].derived_fields
        assert (
            result.interfaces[0].derived_fields["result_count"].template
            == "{count} found"
        )

        # Verify invalid derived_fields gracefully degraded to empty dict
        assert result.interfaces[1].derived_fields == {}

        # Verify empty derived_fields preserved
        assert result.interfaces[2].derived_fields == {}

        # Verify degradation was tracked
        assert get_derived_fields_degradation_count() == 1

    def test_workflow_continues_after_derived_fields_degradation(self):
        """Workflow processing should continue even after derived_fields degradation."""
        # Simulate multiple interface definitions with invalid derived_fields
        interfaces_data = [
            {
                "task_id": f"task_{i:03d}",
                "interface_name": f"interface_{i}",
                "description": f"Interface {i}",
                "input_schema": {"type": "object", "properties": {}},
                "output_schema": {"type": "object", "properties": {}},
                "derived_fields": f"field_{i} -> task_{i + 1}.input.data",  # All invalid
            }
            for i in range(5)
        ]

        response_data = {"interfaces": interfaces_data}

        # Parse should succeed with graceful degradation
        result = InterfaceSchemaResponse.model_validate(response_data)

        # All interfaces should be present
        assert len(result.interfaces) == 5

        # All derived_fields should be empty dicts
        for interface in result.interfaces:
            assert interface.derived_fields == {}

        # All degradations should be tracked
        assert get_derived_fields_degradation_count() == 5

    def test_interface_definition_node_simulation(self):
        """Simulate interface_definition_node processing with invalid LLM output."""
        # This simulates what happens in interface_definition_node when
        # LLM returns invalid derived_fields format

        # Simulated LLM raw output (what Gemini might return)
        llm_output = {
            "interfaces": [
                {
                    "task_id": "task_001",
                    "interface_name": "gmail_search_interface",
                    "description": "Gmail search interface",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"],
                    },
                    "output_schema": {
                        "type": "object",
                        "properties": {
                            "emails": {"type": "array"},
                            "count": {"type": "integer"},
                        },
                    },
                    # Invalid format that LLM commonly produces
                    "derived_fields": "search_results -> task_002.input.data, "
                    "email_count -> task_002.input.total",
                },
                {
                    "task_id": "task_002",
                    "interface_name": "email_send_interface",
                    "description": "Email send interface",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "data": {"type": "array"},
                            "total": {"type": "integer"},
                        },
                    },
                    "output_schema": {
                        "type": "object",
                        "properties": {"success": {"type": "boolean"}},
                    },
                    "derived_fields": {},  # Valid empty
                },
            ]
        }

        # Parse response - should NOT raise exception
        response = InterfaceSchemaResponse.model_validate(llm_output)

        # Workflow can continue processing
        interface_masters = {}
        for interface in response.interfaces:
            # Simulate creating interface master
            interface_masters[interface.task_id] = {
                "interface_name": interface.interface_name,
                "input_schema": interface.input_schema,
                "output_schema": interface.output_schema,
                # derived_fields is empty due to graceful degradation, but workflow continues
                "has_derived_fields": len(interface.derived_fields) > 0,
            }

        # Verify workflow produced results
        assert len(interface_masters) == 2
        assert (
            interface_masters["task_001"]["interface_name"] == "gmail_search_interface"
        )
        assert interface_masters["task_002"]["interface_name"] == "email_send_interface"

        # First interface had invalid derived_fields (degraded)
        assert interface_masters["task_001"]["has_derived_fields"] is False
        # Second interface had empty derived_fields (valid)
        assert interface_masters["task_002"]["has_derived_fields"] is False

        # Verify degradation was tracked
        assert get_derived_fields_degradation_count() == 1

    def test_metrics_tracking_for_langfuse(self):
        """Verify metrics are tracked for Langfuse observability."""
        # Reset counter
        reset_derived_fields_degradation_count()
        assert get_derived_fields_degradation_count() == 0

        # Simulate processing multiple job generations
        for job_id in range(3):
            response_data = {
                "interfaces": [
                    {
                        "task_id": f"job{job_id}_task_001",
                        "interface_name": f"interface_{job_id}",
                        "description": "Test",
                        "input_schema": {"type": "object"},
                        "output_schema": {"type": "object"},
                        # Each job has invalid derived_fields
                        "derived_fields": "field -> next_task.input",
                    }
                ]
            }
            InterfaceSchemaResponse.model_validate(response_data)

        # Verify cumulative count for Langfuse metrics
        total_degradations = get_derived_fields_degradation_count()
        assert total_degradations == 3

        # This count can be sent to Langfuse for tracking
        langfuse_metric = {
            "name": "derived_fields_graceful_degradation_count",
            "value": total_degradations,
            "type": "counter",
        }
        assert langfuse_metric["value"] == 3


class TestDerivedFieldsEdgeCases:
    """Edge case tests for derived_fields validation."""

    def setup_method(self):
        """Reset degradation counter before each test."""
        reset_derived_fields_degradation_count()

    def test_nested_dict_derived_fields(self):
        """Nested dict with DerivedFieldDefinition should work."""
        data = {
            "task_id": "task_001",
            "interface_name": "test",
            "description": "Test",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "derived_fields": {
                "field1": {
                    "template": "{a} and {b}",
                    "type": "string",
                    "description": "Combined field",
                    "source_mapping": {"a": "source.a", "b": "source.b"},
                },
                "field2": {
                    "template": "{count}",
                    "type": "integer",
                },
            },
        }
        result = InterfaceSchemaDefinition.model_validate(data)
        assert len(result.derived_fields) == 2
        assert result.derived_fields["field1"].source_mapping == {
            "a": "source.a",
            "b": "source.b",
        }

    def test_unicode_in_derived_fields_string(self, caplog):
        """Unicode strings in invalid derived_fields should be handled."""
        data = {
            "task_id": "task_001",
            "interface_name": "test",
            "description": "Test",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "derived_fields": "メール件名 -> task_002.input.subject",
        }
        result = InterfaceSchemaDefinition.model_validate(data)
        assert result.derived_fields == {}
        assert get_derived_fields_degradation_count() == 1
        assert "メール件名" in caplog.text

    def test_very_long_derived_fields_string(self, caplog):
        """Very long string should be truncated in warning."""
        long_string = "field_" + "x" * 200 + " -> task.input"
        data = {
            "task_id": "task_001",
            "interface_name": "test",
            "description": "Test",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "derived_fields": long_string,
        }
        result = InterfaceSchemaDefinition.model_validate(data)
        assert result.derived_fields == {}
        # Only first 50 chars should appear in log
        assert "field_" in caplog.text
        assert long_string not in caplog.text
