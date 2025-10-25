"""Unit tests for schema_matcher module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from aiagent.langgraph.jobTaskGeneratorAgents.utils.jobqueue_client import (
    JobqueueClient,
)
from aiagent.langgraph.jobTaskGeneratorAgents.utils.schema_matcher import SchemaMatcher


@pytest.fixture
def mock_jobqueue_client():
    """Create a mock JobqueueClient."""
    client = MagicMock(spec=JobqueueClient)
    # Make async methods return AsyncMock
    client.list_task_masters = AsyncMock()
    client.create_task_master = AsyncMock()
    return client


@pytest.fixture
def schema_matcher(mock_jobqueue_client):
    """Create a SchemaMatcher instance with mock client."""
    return SchemaMatcher(mock_jobqueue_client)


class TestFindTaskMasterByNameUrlAndInterfaces:
    """Tests for find_task_master_by_name_url_and_interfaces method."""

    @pytest.mark.asyncio
    async def test_find_exact_match(self, schema_matcher, mock_jobqueue_client):
        """Test finding TaskMaster with exact name, URL, and interface IDs match."""
        # Arrange
        task_name = "Test Task"
        task_url = "http://localhost:8104/api/v1/tasks/task1"
        input_interface_id = "if_test_input_123"
        output_interface_id = "if_test_output_456"

        existing_task_master = {
            "id": "tm_test_001",
            "name": task_name,
            "url": task_url,
            "input_interface_id": input_interface_id,
            "output_interface_id": output_interface_id,
        }

        mock_jobqueue_client.list_task_masters.return_value = {
            "masters": [existing_task_master],
            "total": 1,
        }

        # Act
        result = await schema_matcher.find_task_master_by_name_url_and_interfaces(
            task_name, task_url, input_interface_id, output_interface_id
        )

        # Assert
        assert result is not None
        assert result["id"] == "tm_test_001"
        assert result["input_interface_id"] == input_interface_id
        assert result["output_interface_id"] == output_interface_id
        mock_jobqueue_client.list_task_masters.assert_called_once_with(
            name=task_name, page=1, size=10
        )

    @pytest.mark.asyncio
    async def test_find_different_input_interface(
        self, schema_matcher, mock_jobqueue_client
    ):
        """Test that TaskMaster with different input_interface_id is not matched."""
        # Arrange
        task_name = "Test Task"
        task_url = "http://localhost:8104/api/v1/tasks/task1"
        search_input_interface_id = "if_test_input_NEW"
        search_output_interface_id = "if_test_output_456"

        existing_task_master = {
            "id": "tm_test_001",
            "name": task_name,
            "url": task_url,
            "input_interface_id": "if_test_input_OLD",  # Different
            "output_interface_id": search_output_interface_id,
        }

        mock_jobqueue_client.list_task_masters.return_value = {
            "masters": [existing_task_master],
            "total": 1,
        }

        # Act
        result = await schema_matcher.find_task_master_by_name_url_and_interfaces(
            task_name, task_url, search_input_interface_id, search_output_interface_id
        )

        # Assert
        assert result is None  # Should not match

    @pytest.mark.asyncio
    async def test_find_different_output_interface(
        self, schema_matcher, mock_jobqueue_client
    ):
        """Test that TaskMaster with different output_interface_id is not matched."""
        # Arrange
        task_name = "Test Task"
        task_url = "http://localhost:8104/api/v1/tasks/task1"
        search_input_interface_id = "if_test_input_123"
        search_output_interface_id = "if_test_output_NEW"

        existing_task_master = {
            "id": "tm_test_001",
            "name": task_name,
            "url": task_url,
            "input_interface_id": search_input_interface_id,
            "output_interface_id": "if_test_output_OLD",  # Different
        }

        mock_jobqueue_client.list_task_masters.return_value = {
            "masters": [existing_task_master],
            "total": 1,
        }

        # Act
        result = await schema_matcher.find_task_master_by_name_url_and_interfaces(
            task_name, task_url, search_input_interface_id, search_output_interface_id
        )

        # Assert
        assert result is None  # Should not match

    @pytest.mark.asyncio
    async def test_find_different_url(self, schema_matcher, mock_jobqueue_client):
        """Test that TaskMaster with different URL is not matched."""
        # Arrange
        task_name = "Test Task"
        search_url = "http://localhost:8104/api/v1/tasks/task2"
        input_interface_id = "if_test_input_123"
        output_interface_id = "if_test_output_456"

        existing_task_master = {
            "id": "tm_test_001",
            "name": task_name,
            "url": "http://localhost:8104/api/v1/tasks/task1",  # Different
            "input_interface_id": input_interface_id,
            "output_interface_id": output_interface_id,
        }

        mock_jobqueue_client.list_task_masters.return_value = {
            "masters": [existing_task_master],
            "total": 1,
        }

        # Act
        result = await schema_matcher.find_task_master_by_name_url_and_interfaces(
            task_name, search_url, input_interface_id, output_interface_id
        )

        # Assert
        assert result is None  # Should not match

    @pytest.mark.asyncio
    async def test_find_no_masters_returned(self, schema_matcher, mock_jobqueue_client):
        """Test when no TaskMasters are returned from API."""
        # Arrange
        mock_jobqueue_client.list_task_masters.return_value = {
            "masters": [],
            "total": 0,
        }

        # Act
        result = await schema_matcher.find_task_master_by_name_url_and_interfaces(
            "Test Task",
            "http://localhost:8104/api/v1/tasks/task1",
            "if_test_input_123",
            "if_test_output_456",
        )

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_find_with_exception(self, schema_matcher, mock_jobqueue_client):
        """Test error handling when API call fails."""
        # Arrange
        mock_jobqueue_client.list_task_masters.side_effect = Exception("API Error")

        # Act
        result = await schema_matcher.find_task_master_by_name_url_and_interfaces(
            "Test Task",
            "http://localhost:8104/api/v1/tasks/task1",
            "if_test_input_123",
            "if_test_output_456",
        )

        # Assert
        assert result is None  # Should return None on exception

    @pytest.mark.asyncio
    async def test_find_multiple_masters_first_match(
        self, schema_matcher, mock_jobqueue_client
    ):
        """Test that first matching TaskMaster is returned when multiple exist."""
        # Arrange
        task_name = "Test Task"
        task_url = "http://localhost:8104/api/v1/tasks/task1"
        input_interface_id = "if_test_input_123"
        output_interface_id = "if_test_output_456"

        matching_master_1 = {
            "id": "tm_test_001",
            "name": task_name,
            "url": task_url,
            "input_interface_id": input_interface_id,
            "output_interface_id": output_interface_id,
        }

        matching_master_2 = {
            "id": "tm_test_002",
            "name": task_name,
            "url": task_url,
            "input_interface_id": input_interface_id,
            "output_interface_id": output_interface_id,
        }

        mock_jobqueue_client.list_task_masters.return_value = {
            "masters": [matching_master_1, matching_master_2],
            "total": 2,
        }

        # Act
        result = await schema_matcher.find_task_master_by_name_url_and_interfaces(
            task_name, task_url, input_interface_id, output_interface_id
        )

        # Assert
        assert result is not None
        assert result["id"] == "tm_test_001"  # First matching master


class TestFindOrCreateTaskMaster:
    """Tests for find_or_create_task_master method."""

    @pytest.mark.asyncio
    async def test_reuse_existing_task_master(
        self, schema_matcher, mock_jobqueue_client
    ):
        """Test that existing TaskMaster is reused when all fields match."""
        # Arrange
        task_name = "Test Task"
        task_url = "http://localhost:8104/api/v1/tasks/task1"
        input_interface_id = "if_test_input_123"
        output_interface_id = "if_test_output_456"

        existing_task_master = {
            "id": "tm_test_001",
            "name": task_name,
            "url": task_url,
            "input_interface_id": input_interface_id,
            "output_interface_id": output_interface_id,
        }

        mock_jobqueue_client.list_task_masters.return_value = {
            "masters": [existing_task_master],
            "total": 1,
        }

        # Act
        result = await schema_matcher.find_or_create_task_master(
            name=task_name,
            description="Test description",
            method="POST",
            url=task_url,
            input_interface_id=input_interface_id,
            output_interface_id=output_interface_id,
            timeout_sec=60,
        )

        # Assert
        assert result["id"] == "tm_test_001"
        mock_jobqueue_client.create_task_master.assert_not_called()  # Should not create

    @pytest.mark.asyncio
    async def test_create_new_task_master_when_interface_differs(
        self, schema_matcher, mock_jobqueue_client
    ):
        """Test that new TaskMaster is created when interface_id differs."""
        # Arrange
        task_name = "Test Task"
        task_url = "http://localhost:8104/api/v1/tasks/task1"
        new_input_interface_id = "if_test_input_NEW"
        new_output_interface_id = "if_test_output_NEW"

        # Existing TaskMaster with old interface IDs
        existing_task_master = {
            "id": "tm_test_001",
            "name": task_name,
            "url": task_url,
            "input_interface_id": "if_test_input_OLD",
            "output_interface_id": "if_test_output_OLD",
        }

        mock_jobqueue_client.list_task_masters.return_value = {
            "masters": [existing_task_master],
            "total": 1,
        }

        # New TaskMaster to be created
        new_task_master = {
            "id": "tm_test_002",
            "name": task_name,
            "url": task_url,
            "input_interface_id": new_input_interface_id,
            "output_interface_id": new_output_interface_id,
        }

        mock_jobqueue_client.create_task_master.return_value = new_task_master

        # Act
        result = await schema_matcher.find_or_create_task_master(
            name=task_name,
            description="Test description",
            method="POST",
            url=task_url,
            input_interface_id=new_input_interface_id,
            output_interface_id=new_output_interface_id,
            timeout_sec=60,
        )

        # Assert
        assert result["id"] == "tm_test_002"  # New TaskMaster created
        mock_jobqueue_client.create_task_master.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_new_task_master_when_no_existing(
        self, schema_matcher, mock_jobqueue_client
    ):
        """Test that new TaskMaster is created when no existing TaskMaster found."""
        # Arrange
        task_name = "Test Task"
        task_url = "http://localhost:8104/api/v1/tasks/task1"
        input_interface_id = "if_test_input_123"
        output_interface_id = "if_test_output_456"

        mock_jobqueue_client.list_task_masters.return_value = {
            "masters": [],
            "total": 0,
        }

        new_task_master = {
            "id": "tm_test_001",
            "name": task_name,
            "url": task_url,
            "input_interface_id": input_interface_id,
            "output_interface_id": output_interface_id,
        }

        mock_jobqueue_client.create_task_master.return_value = new_task_master

        # Act
        result = await schema_matcher.find_or_create_task_master(
            name=task_name,
            description="Test description",
            method="POST",
            url=task_url,
            input_interface_id=input_interface_id,
            output_interface_id=output_interface_id,
            timeout_sec=60,
        )

        # Assert
        assert result["id"] == "tm_test_001"
        mock_jobqueue_client.create_task_master.assert_called_once()
