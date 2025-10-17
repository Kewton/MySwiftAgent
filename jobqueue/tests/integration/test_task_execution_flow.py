"""E2E tests for job-task execution flow."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient, Response

from app.models.interface_master import InterfaceMaster
from app.models.job import Job, JobStatus
from app.models.job_master import JobMaster
from app.models.task import Task, TaskStatus
from app.models.task_master import TaskMaster
from app.models.task_master_interface import TaskMasterInterface


class TestTaskExecutionFlow:
    """E2E test suite for job-task execution flow."""

    @pytest.mark.asyncio
    async def test_create_job_with_tasks(self, client: AsyncClient, db_session) -> None:
        """Test creating a job with tasks."""
        # Create job master
        job_master = JobMaster(
            id="jm_test",
            name="Test Job",
            method="POST",
            url="https://api.example.com/job",
            timeout_sec=30,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        # Create task masters
        task_master1 = TaskMaster(
            id="tm1",
            name="Task 1",
            method="POST",
            url="https://api.example.com/task1",
            body_template={"step": 1},
            timeout_sec=30,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        task_master2 = TaskMaster(
            id="tm2",
            name="Task 2",
            method="POST",
            url="https://api.example.com/task2",
            body_template={"step": 2, "prev_result": "{{tasks[0].output_data.result}}"},
            timeout_sec=30,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        db_session.add_all([job_master, task_master1, task_master2])
        await db_session.commit()

        # Create job with tasks
        payload = {
            "master_id": "jm_test",
            "priority": 5,
            "tags": {"test": "true"},
            "tasks": [
                {"master_id": "tm1", "order": 1, "input_data": {"param": "value1"}},
                {"master_id": "tm2", "order": 2, "input_data": {"param": "value2"}},
            ],
        }
        response = await client.post("/api/v1/jobs/from-master", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "job_id" in data

        # Verify tasks were created
        job_id = data["job_id"]
        tasks_response = await client.get(f"/api/v1/jobs/{job_id}/tasks")
        assert tasks_response.status_code == status.HTTP_200_OK
        tasks_data = tasks_response.json()
        assert tasks_data["total"] == 2
        assert tasks_data["tasks"][0]["order"] == 1
        assert tasks_data["tasks"][1]["order"] == 2

    @pytest.mark.asyncio
    async def test_task_execution_with_template_resolution(self, db_session) -> None:
        """Test task execution with template variable resolution."""
        from app.core.worker import JobExecutor

        # Create job
        job = Job(
            id="job_exec",
            name="Execution Test",
            master_id="jm_exec",
            method="POST",
            url="https://api.example.com/test",
            status=JobStatus.RUNNING,
            started_at=datetime.now(UTC),
            priority=5,
            timeout_sec=30,
            max_attempts=1,
            attempt=1,
        )
        # Create task masters
        tm1 = TaskMaster(
            id="tm_exec1",
            name="Step 1",
            method="POST",
            url="https://api.example.com/step1",
            body_template={"action": "get_user"},
            timeout_sec=30,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        tm2 = TaskMaster(
            id="tm_exec2",
            name="Step 2",
            method="POST",
            url="https://api.example.com/step2",
            body_template={"user_id": "{{tasks[0].output_data.id}}"},
            timeout_sec=30,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        # Create tasks
        task1 = Task(
            id="t1",
            job_id="job_exec",
            master_id="tm_exec1",
            order=1,
            status=TaskStatus.QUEUED,
            input_data={},
        )
        task2 = Task(
            id="t2",
            job_id="job_exec",
            master_id="tm_exec2",
            order=2,
            status=TaskStatus.QUEUED,
            input_data={},
        )
        db_session.add_all([job, tm1, tm2, task1, task2])
        await db_session.commit()

        # Mock HTTP responses
        mock_response1 = AsyncMock(spec=Response)
        mock_response1.status_code = 200
        mock_response1.is_success = True
        mock_response1.content = b'{"id": "user123", "name": "Alice"}'
        mock_response1.json.return_value = {"id": "user123", "name": "Alice"}

        mock_response2 = AsyncMock(spec=Response)
        mock_response2.status_code = 200
        mock_response2.is_success = True
        mock_response2.content = b'{"status": "processed"}'
        mock_response2.json.return_value = {"status": "processed"}

        # Execute job with mocked HTTP client
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = mock_client_class.return_value.__aenter__.return_value
            mock_client.request.side_effect = [mock_response1, mock_response2]

            executor = JobExecutor(db_session, AsyncMock(result_max_bytes=1024 * 1024))
            await executor.execute_job(job)

        # Verify task execution results
        await db_session.refresh(task1)
        await db_session.refresh(task2)
        await db_session.refresh(job)

        assert task1.status == TaskStatus.SUCCEEDED
        assert task1.output_data == {"id": "user123", "name": "Alice"}

        assert task2.status == TaskStatus.SUCCEEDED
        # Verify template was resolved correctly
        assert (
            mock_client.request.call_args_list[1].kwargs["json"]["user_id"] == "user123"
        )

        assert job.status == JobStatus.SUCCEEDED

    @pytest.mark.asyncio
    async def test_task_failure_skips_remaining_tasks(self, db_session) -> None:
        """Test that task failure skips all subsequent tasks."""
        from app.core.worker import JobExecutor

        # Create job and tasks
        job = Job(
            id="job_fail",
            name="Failure Test",
            master_id="jm_fail",
            method="POST",
            url="https://api.example.com/test",
            status=JobStatus.RUNNING,
            started_at=datetime.now(UTC),
            priority=5,
            timeout_sec=30,
            max_attempts=1,
            attempt=1,
        )
        tm1 = TaskMaster(
            id="tm_f1",
            name="Success Task",
            method="GET",
            url="https://api.example.com/success",
            timeout_sec=30,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        tm2 = TaskMaster(
            id="tm_f2",
            name="Failing Task",
            method="GET",
            url="https://api.example.com/fail",
            timeout_sec=30,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        tm3 = TaskMaster(
            id="tm_f3",
            name="Skipped Task",
            method="GET",
            url="https://api.example.com/skip",
            timeout_sec=30,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        task1 = Task(
            id="tf1",
            job_id="job_fail",
            master_id="tm_f1",
            order=1,
            status=TaskStatus.QUEUED,
        )
        task2 = Task(
            id="tf2",
            job_id="job_fail",
            master_id="tm_f2",
            order=2,
            status=TaskStatus.QUEUED,
        )
        task3 = Task(
            id="tf3",
            job_id="job_fail",
            master_id="tm_f3",
            order=3,
            status=TaskStatus.QUEUED,
        )
        db_session.add_all([job, tm1, tm2, tm3, task1, task2, task3])
        await db_session.commit()

        # Mock responses: success, failure, (skip)
        mock_success = AsyncMock(spec=Response)
        mock_success.status_code = 200
        mock_success.is_success = True
        mock_success.content = b'{"result": "ok"}'
        mock_success.json.return_value = {"result": "ok"}

        mock_failure = AsyncMock(spec=Response)
        mock_failure.status_code = 500
        mock_failure.is_success = False
        mock_failure.text = "Internal Server Error"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = mock_client_class.return_value.__aenter__.return_value
            mock_client.request.side_effect = [mock_success, mock_failure]

            executor = JobExecutor(db_session, AsyncMock(result_max_bytes=1024 * 1024))
            await executor.execute_job(job)

        # Verify results
        await db_session.refresh(task1)
        await db_session.refresh(task2)
        await db_session.refresh(task3)
        await db_session.refresh(job)

        assert task1.status == TaskStatus.SUCCEEDED
        assert task2.status == TaskStatus.FAILED
        assert task3.status == TaskStatus.SKIPPED  # Should be skipped
        assert job.status == JobStatus.FAILED

    @pytest.mark.asyncio
    async def test_task_with_interface_validation(
        self, client: AsyncClient, db_session
    ) -> None:
        """Test task creation with interface validation."""
        # Create interface master
        interface = InterfaceMaster(
            id="if_valid",
            name="User Input",
            input_schema={
                "type": "object",
                "properties": {"user_id": {"type": "string"}},
                "required": ["user_id"],
            },
            output_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
            is_active=True,
        )
        # Create task master
        task_master = TaskMaster(
            id="tm_valid",
            name="Validated Task",
            method="POST",
            url="https://api.example.com/user",
            timeout_sec=30,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        # Associate interface
        assoc = TaskMasterInterface(
            task_master_id="tm_valid", interface_id="if_valid", required=True
        )
        # Create job master
        job_master = JobMaster(
            id="jm_valid",
            name="Validation Job",
            method="POST",
            url="https://api.example.com/job",
            timeout_sec=30,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        db_session.add_all([interface, task_master, assoc, job_master])
        await db_session.commit()

        # Create job with valid task input
        payload = {
            "master_id": "jm_valid",
            "priority": 5,
            "tasks": [
                {"master_id": "tm_valid", "order": 1, "input_data": {"user_id": "123"}}
            ],
        }
        response = await client.post("/api/v1/jobs/from-master", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_task_with_invalid_interface_input(
        self, client: AsyncClient, db_session
    ) -> None:
        """Test task creation with invalid interface input."""
        # Create interface master
        interface = InterfaceMaster(
            id="if_invalid",
            name="User Input",
            input_schema={
                "type": "object",
                "properties": {"user_id": {"type": "string"}},
                "required": ["user_id"],
            },
            is_active=True,
        )
        # Create task master
        task_master = TaskMaster(
            id="tm_invalid",
            name="Invalid Task",
            method="POST",
            url="https://api.example.com/user",
            timeout_sec=30,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        # Associate interface
        assoc = TaskMasterInterface(
            task_master_id="tm_invalid", interface_id="if_invalid", required=True
        )
        # Create job master
        job_master = JobMaster(
            id="jm_invalid",
            name="Invalid Job",
            method="POST",
            url="https://api.example.com/job",
            timeout_sec=30,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        db_session.add_all([interface, task_master, assoc, job_master])
        await db_session.commit()

        # Create job with invalid task input (missing user_id)
        payload = {
            "master_id": "jm_invalid",
            "priority": 5,
            "tasks": [{"master_id": "tm_invalid", "order": 1, "input_data": {}}],
        }
        response = await client.post("/api/v1/jobs/from-master", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "validation failed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_retry_failed_task(self, client: AsyncClient, db_session) -> None:
        """Test retrying a failed task."""
        # Create job and task
        job = Job(
            id="job_retry",
            name="Retry Job",
            master_id="jm_retry",
            method="POST",
            url="https://api.example.com/test",
            status=JobStatus.FAILED,
            priority=5,
            timeout_sec=30,
            max_attempts=3,
            attempt=1,
        )
        task = Task(
            id="task_retry",
            job_id="job_retry",
            master_id="tm_retry",
            order=1,
            status=TaskStatus.FAILED,
            error="HTTP 500: Internal Server Error",
            attempt=1,
        )
        db_session.add_all([job, task])
        await db_session.commit()

        # Retry the failed task
        response = await client.post("/api/v1/tasks/task_retry/retry")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == TaskStatus.QUEUED

        # Verify task status reset
        await db_session.refresh(task)
        await db_session.refresh(job)
        assert task.status == TaskStatus.QUEUED
        assert task.error is None
        assert task.attempt == 2
        assert job.status == JobStatus.QUEUED
