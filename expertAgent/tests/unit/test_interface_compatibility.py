"""Test interface compatibility check (Issue #338 Phase 4).

This module tests the check_interface_compatibility function that validates
task chain interface contracts - ensuring output_interface of task N
provides all required fields for input_interface of task N+1.
"""

from aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator import (
    check_interface_compatibility,
)


class TestCheckInterfaceCompatibility:
    """Test check_interface_compatibility function."""

    def test_compatible_interfaces(self):
        """Test that compatible interfaces return no warnings."""
        tasks = [
            {
                "task_id": "task_1",
                "name": "Search Task",
                "output_interface": {
                    "properties": {
                        "search_results": {"type": "array"},
                        "success": {"type": "boolean"},
                        "error_message": {"type": "string"},
                    }
                },
            },
            {
                "task_id": "task_2",
                "name": "Summarize Task",
                "input_interface": {
                    "required": ["search_results"],
                    "properties": {
                        "search_results": {"type": "array"},
                    },
                },
                "output_interface": {
                    "properties": {
                        "summary": {"type": "string"},
                    }
                },
            },
        ]

        warnings = check_interface_compatibility(tasks)

        assert len(warnings) == 0

    def test_missing_required_field(self):
        """Test that missing required fields generate warnings."""
        tasks = [
            {
                "task_id": "task_1",
                "name": "Search Task",
                "output_interface": {
                    "properties": {
                        "success": {"type": "boolean"},
                        # Missing search_results
                    }
                },
            },
            {
                "task_id": "task_2",
                "name": "Summarize Task",
                "input_interface": {
                    "required": ["search_results", "query"],
                    "properties": {
                        "search_results": {"type": "array"},
                        "query": {"type": "string"},
                    },
                },
            },
        ]

        warnings = check_interface_compatibility(tasks)

        assert len(warnings) >= 1
        assert any("search_results" in w for w in warnings)
        assert any("query" in w for w in warnings)

    def test_multiple_task_chain(self):
        """Test interface compatibility across multiple tasks."""
        tasks = [
            {
                "task_id": "task_1",
                "name": "Fetch Data",
                "output_interface": {
                    "properties": {
                        "data": {"type": "object"},
                        "status": {"type": "string"},
                    }
                },
            },
            {
                "task_id": "task_2",
                "name": "Process Data",
                "input_interface": {
                    "required": ["data"],
                    "properties": {"data": {"type": "object"}},
                },
                "output_interface": {
                    "properties": {
                        "processed_data": {"type": "object"},
                        "metrics": {"type": "object"},
                    }
                },
            },
            {
                "task_id": "task_3",
                "name": "Generate Report",
                "input_interface": {
                    "required": ["processed_data", "title"],
                    "properties": {
                        "processed_data": {"type": "object"},
                        "title": {"type": "string"},
                    },
                },
            },
        ]

        warnings = check_interface_compatibility(tasks)

        # task_2 output is missing 'title' required by task_3
        assert len(warnings) >= 1
        assert any("title" in w for w in warnings)

    def test_empty_task_list(self):
        """Test handling of empty task list."""
        tasks: list[dict] = []

        warnings = check_interface_compatibility(tasks)

        assert warnings == []

    def test_single_task(self):
        """Test that single task returns no warnings."""
        tasks = [
            {
                "task_id": "task_1",
                "name": "Single Task",
                "output_interface": {"properties": {"result": {"type": "string"}}},
            }
        ]

        warnings = check_interface_compatibility(tasks)

        assert warnings == []

    def test_missing_output_interface(self):
        """Test handling when output_interface is missing."""
        tasks = [
            {
                "task_id": "task_1",
                "name": "Task Without Output Interface",
                # No output_interface defined
            },
            {
                "task_id": "task_2",
                "name": "Task With Input",
                "input_interface": {
                    "required": ["data"],
                    "properties": {"data": {"type": "object"}},
                },
            },
        ]

        warnings = check_interface_compatibility(tasks)

        # Should warn about missing required field 'data'
        assert len(warnings) >= 1

    def test_missing_input_interface(self):
        """Test handling when input_interface is missing."""
        tasks = [
            {
                "task_id": "task_1",
                "name": "Task With Output",
                "output_interface": {"properties": {"data": {"type": "object"}}},
            },
            {
                "task_id": "task_2",
                "name": "Task Without Input Interface",
                # No input_interface defined
            },
        ]

        warnings = check_interface_compatibility(tasks)

        # No warnings expected - no required fields to check
        assert len(warnings) == 0

    def test_no_required_fields(self):
        """Test when input_interface has no required fields."""
        tasks = [
            {
                "task_id": "task_1",
                "name": "Task 1",
                "output_interface": {
                    "properties": {"optional_data": {"type": "object"}}
                },
            },
            {
                "task_id": "task_2",
                "name": "Task 2",
                "input_interface": {
                    # No required fields
                    "properties": {"optional_data": {"type": "object"}},
                },
            },
        ]

        warnings = check_interface_compatibility(tasks)

        assert len(warnings) == 0

    def test_warning_message_format(self):
        """Test that warning messages contain useful information."""
        tasks = [
            {
                "task_id": "task_1",
                "name": "Producer Task",
                "output_interface": {"properties": {"field_a": {"type": "string"}}},
            },
            {
                "task_id": "task_2",
                "name": "Consumer Task",
                "input_interface": {
                    "required": ["field_b"],
                    "properties": {"field_b": {"type": "string"}},
                },
            },
        ]

        warnings = check_interface_compatibility(tasks)

        assert len(warnings) == 1
        warning = warnings[0]

        # Warning should mention the missing field
        assert "field_b" in warning
        # Warning should identify which tasks are involved
        assert "1" in warning and "2" in warning


class TestRealWorldScenarios:
    """Test with real-world task chain scenarios."""

    def test_google_search_to_summarize_chain(self):
        """Test Google Search -> Summarize task chain."""
        tasks = [
            {
                "task_id": "search_task",
                "name": "Google Search",
                "output_interface": {
                    "properties": {
                        "success": {"type": "boolean"},
                        "search_results": {"type": "array"},
                        "error_message": {"type": "string"},
                    }
                },
            },
            {
                "task_id": "summarize_task",
                "name": "Summarize Results",
                "input_interface": {
                    "required": ["search_results"],
                    "properties": {
                        "search_results": {"type": "array"},
                    },
                },
                "output_interface": {
                    "properties": {
                        "summary": {"type": "string"},
                        "key_points": {"type": "array"},
                    }
                },
            },
        ]

        warnings = check_interface_compatibility(tasks)

        # Should be compatible
        assert len(warnings) == 0

    def test_fetch_summarize_email_chain(self):
        """Test Fetch -> Summarize -> Email task chain."""
        tasks = [
            {
                "task_id": "fetch_task",
                "name": "Fetch Data",
                "output_interface": {
                    "properties": {
                        "data": {"type": "object"},
                        "status": {"type": "string"},
                    }
                },
            },
            {
                "task_id": "summarize_task",
                "name": "Generate Summary",
                "input_interface": {
                    "required": ["data"],
                    "properties": {"data": {"type": "object"}},
                },
                "output_interface": {
                    "properties": {
                        "summary": {"type": "string"},
                        "email_subject": {"type": "string"},
                        "email_body": {"type": "string"},
                    }
                },
            },
            {
                "task_id": "email_task",
                "name": "Send Email",
                "input_interface": {
                    "required": ["email_subject", "email_body", "recipient"],
                    "properties": {
                        "email_subject": {"type": "string"},
                        "email_body": {"type": "string"},
                        "recipient": {"type": "string"},
                    },
                },
            },
        ]

        warnings = check_interface_compatibility(tasks)

        # Should warn about missing 'recipient' field
        assert len(warnings) >= 1
        assert any("recipient" in w for w in warnings)

    def test_tts_upload_notify_chain(self):
        """Test TTS -> Upload -> Notify task chain."""
        tasks = [
            {
                "task_id": "tts_task",
                "name": "Generate Audio",
                "output_interface": {
                    "properties": {
                        "audio_file_path": {"type": "string"},
                        "duration_seconds": {"type": "number"},
                    }
                },
            },
            {
                "task_id": "upload_task",
                "name": "Upload to Drive",
                "input_interface": {
                    "required": ["audio_file_path"],
                    "properties": {"audio_file_path": {"type": "string"}},
                },
                "output_interface": {
                    "properties": {
                        "file_id": {"type": "string"},
                        "web_view_link": {"type": "string"},
                    }
                },
            },
            {
                "task_id": "notify_task",
                "name": "Send Notification",
                "input_interface": {
                    "required": ["web_view_link", "recipient_email"],
                    "properties": {
                        "web_view_link": {"type": "string"},
                        "recipient_email": {"type": "string"},
                    },
                },
            },
        ]

        warnings = check_interface_compatibility(tasks)

        # Should warn about missing 'recipient_email'
        assert len(warnings) >= 1
        assert any("recipient_email" in w for w in warnings)
