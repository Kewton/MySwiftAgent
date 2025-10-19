"""Integration tests for TaskMaster API endpoints."""

import pytest
from fastapi import status
from httpx import AsyncClient

from app.models.task_master import TaskMaster


class TestTaskMasterAPI:
    """Test suite for TaskMaster API endpoints."""

    @pytest.mark.asyncio
    async def test_create_task_master(self, client: AsyncClient) -> None:
        """Test creating a new task master."""
        payload = {
            "name": "Test Task",
            "description": "Test task description",
            "method": "POST",
            "url": "https://api.example.com/test",
            "headers": {"Authorization": "Bearer token"},
            "body_template": {"message": "test"},
            "timeout_sec": 30,
            "created_by": "test_user",
        }
        response = await client.post("/api/v1/task-masters", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "master_id" in data
        assert data["name"] == "Test Task"
        assert data["current_version"] == 1

    @pytest.mark.asyncio
    async def test_list_task_masters(self, client: AsyncClient, db_session) -> None:
        """Test listing task masters with pagination."""
        # Create test task masters
        for i in range(5):
            master = TaskMaster(
                id=f"tm_test_{i}",
                name=f"Task {i}",
                description=f"Description {i}",
                method="GET",
                url=f"https://api.example.com/task{i}",
                timeout_sec=30,
                is_active=True,
                current_version=1,
                created_by="test",
                updated_by="test",
            )
            db_session.add(master)
        await db_session.commit()

        # Test pagination
        response = await client.get("/api/v1/task-masters?page=1&size=3")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 5
        assert data["page"] == 1
        assert data["size"] == 3
        assert len(data["masters"]) <= 3

    @pytest.mark.asyncio
    async def test_get_task_master(self, client: AsyncClient, db_session) -> None:
        """Test getting task master details."""
        # Create test task master
        master = TaskMaster(
            id="tm_detail_test",
            name="Detail Test Task",
            description="Test description",
            method="POST",
            url="https://api.example.com/detail",
            headers={"Content-Type": "application/json"},
            body_template={"key": "value"},
            timeout_sec=60,
            is_active=True,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        db_session.add(master)
        await db_session.commit()

        # Get task master
        response = await client.get("/api/v1/task-masters/tm_detail_test")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "tm_detail_test"
        assert data["name"] == "Detail Test Task"
        assert data["method"] == "POST"
        assert data["timeout_sec"] == 60

    @pytest.mark.asyncio
    async def test_update_task_master_with_versioning(
        self, client: AsyncClient, db_session
    ) -> None:
        """Test updating task master with automatic versioning."""
        # Create initial task master
        master = TaskMaster(
            id="tm_update_test",
            name="Update Test",
            description="Original",
            method="GET",
            url="https://api.example.com/v1",
            timeout_sec=30,
            is_active=True,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        db_session.add(master)

        # Create a task using this master (to trigger versioning logic)
        from app.models.job import Job, JobStatus
        from app.models.task import Task, TaskStatus

        job = Job(
            id="j_test",
            name="Test Job",
            master_id="jm_test",
            method="GET",
            url="https://api.example.com",
            status=JobStatus.QUEUED,
            priority=5,
            timeout_sec=30,
        )
        task = Task(
            id="t_test",
            job_id="j_test",
            master_id="tm_update_test",
            master_version=1,
            order=1,
            status=TaskStatus.QUEUED,
            attempt=0,
        )
        db_session.add(job)
        db_session.add(task)
        await db_session.commit()

        # Update critical field (URL) - should trigger versioning
        update_payload = {
            "url": "https://api.example.com/v2",
            "change_reason": "API version upgrade",
            "updated_by": "test_user",
        }
        response = await client.put(
            "/api/v1/task-masters/tm_update_test", json=update_payload
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["current_version"] == 2
        assert data["previous_version"] == 1
        assert data["auto_versioned"] is True

    @pytest.mark.asyncio
    async def test_update_task_master_without_versioning(
        self, client: AsyncClient, db_session
    ) -> None:
        """Test updating task master without triggering versioning."""
        # Create initial task master
        master = TaskMaster(
            id="tm_no_version_test",
            name="No Version Test",
            description="Original",
            method="GET",
            url="https://api.example.com/test",
            timeout_sec=30,
            is_active=True,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        db_session.add(master)
        await db_session.commit()

        # Update non-critical field (name) - should NOT trigger versioning
        update_payload = {
            "name": "Updated Name",
            "change_reason": "Name change",
            "updated_by": "test_user",
        }
        response = await client.put(
            "/api/v1/task-masters/tm_no_version_test", json=update_payload
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["current_version"] == 1  # Version should NOT increment
        assert data["previous_version"] == 1
        assert data["auto_versioned"] is False

    @pytest.mark.asyncio
    async def test_delete_task_master(self, client: AsyncClient, db_session) -> None:
        """Test logical deletion of task master."""
        # Create task master
        master = TaskMaster(
            id="tm_delete_test",
            name="Delete Test",
            description="To be deleted",
            method="GET",
            url="https://api.example.com/delete",
            timeout_sec=30,
            is_active=True,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        db_session.add(master)
        await db_session.commit()

        # Delete task master
        response = await client.delete("/api/v1/task-masters/tm_delete_test")
        assert response.status_code == status.HTTP_200_OK

        # Verify logical deletion
        await db_session.refresh(master)
        assert master.is_active is False

    @pytest.mark.asyncio
    async def test_get_nonexistent_task_master(self, client: AsyncClient) -> None:
        """Test getting a non-existent task master."""
        response = await client.get("/api/v1/task-masters/tm_nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_filter_by_is_active(self, client: AsyncClient, db_session) -> None:
        """Test filtering task masters by is_active status."""
        # Create active and inactive task masters
        active_master = TaskMaster(
            id="tm_active",
            name="Active",
            method="GET",
            url="https://api.example.com/active",
            timeout_sec=30,
            is_active=True,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        inactive_master = TaskMaster(
            id="tm_inactive",
            name="Inactive",
            method="GET",
            url="https://api.example.com/inactive",
            timeout_sec=30,
            is_active=False,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        db_session.add_all([active_master, inactive_master])
        await db_session.commit()

        # Filter for active only
        response = await client.get("/api/v1/task-masters?is_active=true")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(m["is_active"] for m in data["masters"])

        # Filter for inactive only
        response = await client.get("/api/v1/task-masters?is_active=false")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(not m["is_active"] for m in data["masters"])
