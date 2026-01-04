"""Integration test for task chain transformation (Issue #338 Phase 2.5).

This module tests the end-to-end task chain transformation flow:
- GraphAI result extraction
- Interface transformation
- Data flow to subsequent tasks
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.worker import _extract_graphai_output, _transform_to_interface


class TestTaskChainTransformation:
    """Integration tests for task chain transformation."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.scalar = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.result_max_bytes = 1048576
        return settings

    @pytest.mark.asyncio
    async def test_graphai_output_is_transformed_before_task_chain(
        self, mock_session, mock_settings
    ):
        """Test that GraphAI output is transformed before being passed to next task."""
        # Simulate output_interface (stored as JSON or retrieved separately)
        output_interface = {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "search_results": {"type": "array"},
                "error_message": {"type": "string"},
            },
            "required": ["success", "search_results"],
        }

        # Simulate GraphAI response
        graphai_response = {
            "results": {
                "source": {"user_input": {"query": "AI news"}},
                "execute_search": {
                    "search_results": [
                        {"title": "AI News 1", "link": "https://example.com/1"},
                        {"title": "AI News 2", "link": "https://example.com/2"},
                    ],
                    "search_results_count": 2,
                    "status": "ok",
                },
                "output": {
                    "success": True,
                    "search_results": [
                        {"title": "AI News 1", "link": "https://example.com/1"},
                        {"title": "AI News 2", "link": "https://example.com/2"},
                    ],
                    "error_message": "",
                },
            },
            "errors": {},
            "logs": [],
        }

        # Step 1: Extract GraphAI output
        extracted = _extract_graphai_output(graphai_response)

        # Should extract from output node
        assert extracted["success"] is True
        assert len(extracted["search_results"]) == 2

        # Step 2: Transform to interface
        transformed = _transform_to_interface(extracted, output_interface)

        # Transformed output should match interface schema
        assert transformed["success"] is True
        assert len(transformed["search_results"]) == 2
        assert transformed["error_message"] == ""

    @pytest.mark.asyncio
    async def test_transformation_with_nested_graphai_structure(
        self, mock_session, mock_settings
    ):
        """Test transformation when GraphAI output has deeply nested structure."""
        output_interface = {
            "type": "object",
            "properties": {
                "file_id": {"type": "string"},
                "web_view_link": {"type": "string"},
                "success": {"type": "boolean"},
            },
            "required": ["file_id", "web_view_link"],
        }

        # Nested GraphAI response without standard output node
        graphai_response = {
            "results": {
                "source": {"user_input": {"file_path": "/tmp/audio.mp3"}},
                "upload_to_drive": {
                    "file_id": "drive_123",
                    "file_name": "audio.mp3",
                    "web_view_link": "https://drive.google.com/file/d/drive_123",
                    "web_content_link": "https://drive.google.com/uc?id=drive_123",
                },
            },
            "errors": {},
        }

        # Extract (will return full results since no output node)
        extracted = _extract_graphai_output(graphai_response)

        # Transform using recursive search
        transformed = _transform_to_interface(extracted, output_interface)

        # Should find fields recursively
        assert transformed["file_id"] == "drive_123"
        assert "drive.google.com" in transformed["web_view_link"]

    @pytest.mark.asyncio
    async def test_transformation_preserves_data_types(self):
        """Test that transformation preserves data types correctly."""
        output_interface = {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
                "ratio": {"type": "number"},
                "active": {"type": "boolean"},
                "items": {"type": "array"},
                "metadata": {"type": "object"},
            },
        }

        raw_output = {
            "count": 42,
            "ratio": 3.14,
            "active": True,
            "items": [1, 2, 3],
            "metadata": {"key": "value"},
        }

        transformed = _transform_to_interface(raw_output, output_interface)

        assert isinstance(transformed["count"], int)
        assert isinstance(transformed["ratio"], float)
        assert isinstance(transformed["active"], bool)
        assert isinstance(transformed["items"], list)
        assert isinstance(transformed["metadata"], dict)

    @pytest.mark.asyncio
    async def test_chained_task_receives_transformed_data(
        self, mock_session, mock_settings
    ):
        """Test that subsequent task in chain receives transformed data."""
        # Task 1 output interface
        task1_output_interface = {
            "type": "object",
            "properties": {
                "search_results": {"type": "array"},
                "success": {"type": "boolean"},
            },
            "required": ["search_results"],
        }

        # Task 1 GraphAI response
        task1_graphai_response = {
            "results": {
                "output": {
                    "search_results": [{"title": "Result"}],
                    "success": True,
                    "extra_field": "not in interface",
                }
            }
        }

        # Extract and transform Task 1 output
        task1_extracted = _extract_graphai_output(task1_graphai_response)
        task1_output = _transform_to_interface(task1_extracted, task1_output_interface)

        # Verify Task 1 output is clean (only interface fields)
        assert "search_results" in task1_output
        assert "success" in task1_output
        # Extra field should still be present (transformation doesn't remove fields)
        # This is by design - we extract defined fields, but don't strip others

        # Task 2 should be able to use this data
        task2_user_input = task1_output
        assert task2_user_input["search_results"] == [{"title": "Result"}]

    @pytest.mark.asyncio
    async def test_transformation_handles_missing_fields_gracefully(self):
        """Test that missing fields don't cause transformation to fail."""
        output_interface = {
            "type": "object",
            "properties": {
                "required_field": {"type": "string"},
                "optional_field": {"type": "string"},
            },
            "required": ["required_field"],
        }

        raw_output = {
            "some_other_field": "value",
            # required_field and optional_field are missing
        }

        # Should not raise exception
        transformed = _transform_to_interface(raw_output, output_interface)

        # Missing fields should be None
        assert transformed.get("required_field") is None
        assert transformed.get("optional_field") is None

    @pytest.mark.asyncio
    async def test_real_world_google_search_to_summarize_flow(self):
        """Test real-world flow: Google Search -> Summarize."""
        # Task 1: Google Search
        search_output_interface = {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "search_results": {"type": "array"},
                "search_results_count": {"type": "integer"},
                "error_message": {"type": "string"},
            },
            "required": ["success", "search_results"],
        }

        search_graphai_response = {
            "results": {
                "source": {"user_input": {"query": "Python best practices"}},
                "fetch_search": {
                    "search_results": [
                        {
                            "title": "PEP 8",
                            "link": "https://peps.python.org/pep-0008/",
                            "knowledge": "Style guide",
                        },
                        {
                            "title": "Clean Code",
                            "link": "https://example.com/clean-code",
                            "knowledge": "Best practices",
                        },
                    ],
                    "search_results_count": 2,
                    "status": "ok",
                },
                "output": {
                    "success": True,
                    "search_results": [
                        {
                            "title": "PEP 8",
                            "link": "https://peps.python.org/pep-0008/",
                            "knowledge": "Style guide",
                        },
                        {
                            "title": "Clean Code",
                            "link": "https://example.com/clean-code",
                            "knowledge": "Best practices",
                        },
                    ],
                    "search_results_count": 2,
                    "error_message": "",
                },
            }
        }

        # Extract and transform search results
        search_extracted = _extract_graphai_output(search_graphai_response)
        search_output = _transform_to_interface(
            search_extracted, search_output_interface
        )

        # Verify search output
        assert search_output["success"] is True
        assert len(search_output["search_results"]) == 2
        assert search_output["search_results_count"] == 2

        # Task 2: Summarize would receive this as user_input
        summarize_input = search_output

        # Summarize task can access the data
        assert len(summarize_input["search_results"]) == 2
        assert summarize_input["search_results"][0]["title"] == "PEP 8"


class TestEdgeCases:
    """Test edge cases in task chain transformation."""

    def test_empty_graphai_response(self):
        """Test handling of empty GraphAI response."""
        graphai_response: dict = {}

        extracted = _extract_graphai_output(graphai_response)

        assert extracted == {}

    def test_null_values_in_output(self):
        """Test handling of null values in output."""
        output_interface = {
            "type": "object",
            "properties": {
                "nullable_field": {"type": "string"},
                "non_null_field": {"type": "string"},
            },
        }

        raw_output = {
            "nullable_field": None,
            "non_null_field": "value",
        }

        transformed = _transform_to_interface(raw_output, output_interface)

        assert transformed["nullable_field"] is None
        assert transformed["non_null_field"] == "value"

    def test_array_values_are_preserved(self):
        """Test that array values are preserved correctly."""
        output_interface = {
            "type": "object",
            "properties": {
                "items": {"type": "array"},
            },
        }

        raw_output = {
            "items": [
                {"id": 1, "name": "Item 1"},
                {"id": 2, "name": "Item 2"},
                {"id": 3, "name": "Item 3"},
            ]
        }

        transformed = _transform_to_interface(raw_output, output_interface)

        assert len(transformed["items"]) == 3
        assert transformed["items"][0]["id"] == 1
        assert transformed["items"][2]["name"] == "Item 3"

    def test_deeply_nested_array_extraction(self):
        """Test extraction of arrays from deeply nested structures."""
        output_interface = {
            "type": "object",
            "properties": {
                "results": {"type": "array"},
            },
        }

        raw_output = {
            "level1": {"level2": {"results": [{"data": "value1"}, {"data": "value2"}]}}
        }

        transformed = _transform_to_interface(raw_output, output_interface)

        assert transformed["results"] == [{"data": "value1"}, {"data": "value2"}]
