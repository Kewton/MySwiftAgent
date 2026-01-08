"""Unit tests for JobGeneratorV2Adapter conversion logic.

Issue #342: Tests for _convert_tasks_to_breakdown() and _convert_interfaces() methods.
"""

import pytest

from aiagent.langgraph.jobGeneratorV2.adapter import JobGeneratorV2Adapter
from aiagent.langgraph.jobGeneratorV2.types import (
    InterfaceSchema,
    JobGenerationResult,
    TaskDefinition,
)


class TestConvertTasksToBreakdown:
    """Tests for _convert_tasks_to_breakdown method."""

    @pytest.fixture
    def adapter(self) -> JobGeneratorV2Adapter:
        """Create adapter instance for testing."""
        return JobGeneratorV2Adapter(max_retry=3)

    def test_convert_single_task(self, adapter: JobGeneratorV2Adapter) -> None:
        """Test converting a single task."""
        tasks = [
            TaskDefinition(
                id="task_001",
                name="Search Gmail",
                description="Search for emails matching the query",
                task_type="gmail_search",
                recommended_api="/v1/utility/gmail/search",
                priority=1,
                dependencies=[],
            )
        ]

        result = adapter._convert_tasks_to_breakdown(tasks)

        assert len(result) == 1
        assert result[0]["task_id"] == "task_001"
        assert result[0]["name"] == "Search Gmail"
        assert result[0]["description"] == "Search for emails matching the query"
        assert result[0]["task_type"] == "gmail_search"
        assert result[0]["recommended_api"] == "/v1/utility/gmail/search"
        assert result[0]["priority"] == 1
        assert result[0]["dependencies"] == []

    def test_convert_multiple_tasks(self, adapter: JobGeneratorV2Adapter) -> None:
        """Test converting multiple tasks."""
        tasks = [
            TaskDefinition(
                id="task_001",
                name="Search",
                description="Search task",
                task_type="search",
                recommended_api="/api/search",
                priority=1,
                dependencies=[],
            ),
            TaskDefinition(
                id="task_002",
                name="Process",
                description="Process task",
                task_type="process",
                recommended_api="/api/process",
                priority=2,
                dependencies=["task_001"],
            ),
            TaskDefinition(
                id="task_003",
                name="Send",
                description="Send task",
                task_type="send",
                recommended_api="/api/send",
                priority=3,
                dependencies=["task_001", "task_002"],
            ),
        ]

        result = adapter._convert_tasks_to_breakdown(tasks)

        assert len(result) == 3
        assert result[0]["task_id"] == "task_001"
        assert result[1]["task_id"] == "task_002"
        assert result[2]["task_id"] == "task_003"
        assert result[2]["dependencies"] == ["task_001", "task_002"]

    def test_convert_empty_tasks(self, adapter: JobGeneratorV2Adapter) -> None:
        """Test converting empty task list."""
        result = adapter._convert_tasks_to_breakdown([])
        assert result == []


class TestConvertInterfaces:
    """Tests for _convert_interfaces method."""

    @pytest.fixture
    def adapter(self) -> JobGeneratorV2Adapter:
        """Create adapter instance for testing."""
        return JobGeneratorV2Adapter(max_retry=3)

    def test_convert_single_interface(self, adapter: JobGeneratorV2Adapter) -> None:
        """Test converting a single interface."""
        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
                output_schema={
                    "type": "object",
                    "properties": {"results": {"type": "array"}},
                },
                description="Gmail search interface",
            )
        }

        result = adapter._convert_interfaces(interfaces)

        assert len(result) == 1
        assert "task_001" in result
        assert result["task_001"]["input_schema"]["type"] == "object"
        assert "query" in result["task_001"]["input_schema"]["properties"]
        assert result["task_001"]["output_schema"]["type"] == "object"
        assert result["task_001"]["description"] == "Gmail search interface"

    def test_convert_multiple_interfaces(self, adapter: JobGeneratorV2Adapter) -> None:
        """Test converting multiple interfaces."""
        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                description="Interface 1",
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={"type": "object"},
                output_schema={"type": "array"},
                description="Interface 2",
            ),
        }

        result = adapter._convert_interfaces(interfaces)

        assert len(result) == 2
        assert "task_001" in result
        assert "task_002" in result
        assert result["task_001"]["description"] == "Interface 1"
        assert result["task_002"]["description"] == "Interface 2"

    def test_convert_empty_interfaces(self, adapter: JobGeneratorV2Adapter) -> None:
        """Test converting empty interfaces dict."""
        result = adapter._convert_interfaces({})
        assert result == {}


class TestConvertResultIntegration:
    """Integration tests for _convert_result with task/interface data."""

    @pytest.fixture
    def adapter(self) -> JobGeneratorV2Adapter:
        """Create adapter instance for testing."""
        return JobGeneratorV2Adapter(max_retry=3)

    def test_convert_successful_result_with_tasks(
        self, adapter: JobGeneratorV2Adapter
    ) -> None:
        """Test converting successful result includes task_breakdown."""
        tasks = [
            TaskDefinition(
                id="task_001",
                name="Test Task",
                description="Test description",
                task_type="test",
                recommended_api="/api/test",
                priority=1,
                dependencies=[],
            )
        ]
        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                description="Test interface",
            )
        }

        result = JobGenerationResult(
            success=True,
            job_id="job-123",
            job_master_id="master-123",
            task_master_ids=["tm-001"],
            workflow_yaml="nodes: {}",
            tasks=tasks,
            interfaces=interfaces,
        )

        response = adapter._convert_result(result, "job-123")

        assert response.status == "success"
        assert response.task_breakdown is not None
        assert len(response.task_breakdown) == 1
        assert response.task_breakdown[0]["task_id"] == "task_001"
        assert response.interface_definitions is not None
        assert "task_001" in response.interface_definitions

    def test_convert_successful_result_without_tasks(
        self, adapter: JobGeneratorV2Adapter
    ) -> None:
        """Test converting successful result with empty tasks returns None."""
        result = JobGenerationResult(
            success=True,
            job_id="job-123",
            job_master_id="master-123",
            task_master_ids=[],
            workflow_yaml="nodes: {}",
            tasks=[],  # Empty tasks
            interfaces={},  # Empty interfaces
        )

        response = adapter._convert_result(result, "job-123")

        assert response.status == "success"
        assert response.task_breakdown is None
        assert response.interface_definitions is None

    def test_convert_failed_result(self, adapter: JobGeneratorV2Adapter) -> None:
        """Test converting failed result does not include task_breakdown."""
        result = JobGenerationResult(
            success=False,
            job_id="job-123",
            error="Generation failed",
            tasks=[
                TaskDefinition(
                    id="task_001",
                    name="Task",
                    description="Desc",
                    task_type="test",
                    recommended_api="/api",
                )
            ],
            interfaces={},
        )

        response = adapter._convert_result(result, "job-123")

        assert response.status == "failed"
        assert response.task_breakdown is None
        assert response.interface_definitions is None
        assert response.error_message == "Generation failed"
