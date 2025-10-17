"""Integration tests for Job creation with interface validation (Phase 2.2.4)."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import new as ulid_new

from app.core.worker import JobExecutor
from app.models.interface_master import InterfaceMaster
from app.models.job import Job, JobStatus
from app.models.task import Task, TaskStatus
from app.models.task_master import TaskMaster


class TestJobCreationValidation:
    """Test suite for Job creation with interface validation."""

    @pytest.mark.asyncio
    async def test_create_job_with_validation_enabled(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test job creation with validation enabled (default) and compatible interfaces."""
        # Create compatible interfaces
        search_interface_id = f"if_{ulid_new()}"
        search_interface = InterfaceMaster(
            id=search_interface_id,
            name="SearchInterface",
            description="Search interface",
            output_schema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {"results": {"type": "array"}},
                "required": ["results"],
            },
            is_active=True,
        )

        analysis_interface_id = f"if_{ulid_new()}"
        analysis_interface = InterfaceMaster(
            id=analysis_interface_id,
            name="AnalysisInterface",
            description="Analysis interface",
            input_schema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {"results": {"type": "array"}},
                "required": ["results"],
            },
            is_active=True,
        )

        db_session.add_all([search_interface, analysis_interface])

        # Create task masters
        search_master_id = f"tm_{ulid_new()}"
        search_master = TaskMaster(
            id=search_master_id,
            name="search_task",
            description="Search",
            method="GET",
            url="https://api.example.com/search",
            timeout_sec=30,
            output_interface_id=search_interface_id,
            is_active=True,
            current_version=1,
            created_by="test",
            updated_by="test",
        )

        analyzer_master_id = f"tm_{ulid_new()}"
        analyzer_master = TaskMaster(
            id=analyzer_master_id,
            name="analyzer_task",
            description="Analyzer",
            method="POST",
            url="https://api.example.com/analyze",
            timeout_sec=30,
            input_interface_id=analysis_interface_id,
            is_active=True,
            current_version=1,
            created_by="test",
            updated_by="test",
        )

        db_session.add_all([search_master, analyzer_master])
        await db_session.commit()

        # Create job with validation enabled (default)
        response = await client.post(
            "/api/v1/jobs",
            json={
                "name": "Validation Test Job",
                "method": "GET",
                "url": "https://api.example.com/test",
                "tasks": [
                    {"master_id": search_master_id, "sequence": 0},
                    {"master_id": analyzer_master_id, "sequence": 1},
                ],
                "validate_interfaces": True,  # Explicit (default is True)
            },
        )

        assert response.status_code == 201
        data = response.json()

        # Job should be created successfully
        job_id = data["job_id"]
        assert data["status"] == "queued"

        # Check that validation tag exists and is valid
        job = await db_session.get(Job, job_id)
        assert job is not None
        assert job.tags is not None
        assert len(job.tags) > 0

        # Find validation tag
        validation_tag = next(
            (tag for tag in job.tags if tag.get("type") == "interface_validation"),
            None,
        )
        assert validation_tag is not None
        assert validation_tag["is_valid"] is True
        assert validation_tag["error_count"] == 0

    @pytest.mark.asyncio
    async def test_create_job_with_validation_warnings(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test job creation with incompatible interfaces (validation warnings)."""
        # Create incompatible interfaces
        output_interface_id = f"if_{ulid_new()}"
        output_interface = InterfaceMaster(
            id=output_interface_id,
            name="OutputInterface",
            output_schema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {"result": {"type": "string"}},
                "required": ["result"],
            },
            is_active=True,
        )

        input_interface_id = f"if_{ulid_new()}"
        input_interface = InterfaceMaster(
            id=input_interface_id,
            name="InputInterface",
            input_schema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {"data": {"type": "object"}},
                "required": ["data"],
            },
            is_active=True,
        )

        db_session.add_all([output_interface, input_interface])

        # Create task masters
        task1_master_id = f"tm_{ulid_new()}"
        task1_master = TaskMaster(
            id=task1_master_id,
            name="output_task",
            method="GET",
            url="https://api.example.com/task1",
            timeout_sec=30,
            output_interface_id=output_interface_id,
            is_active=True,
            current_version=1,
            created_by="test",
            updated_by="test",
        )

        task2_master_id = f"tm_{ulid_new()}"
        task2_master = TaskMaster(
            id=task2_master_id,
            name="input_task",
            method="POST",
            url="https://api.example.com/task2",
            timeout_sec=30,
            input_interface_id=input_interface_id,
            is_active=True,
            current_version=1,
            created_by="test",
            updated_by="test",
        )

        db_session.add_all([task1_master, task2_master])
        await db_session.commit()

        # Create job - should succeed but with validation warnings
        response = await client.post(
            "/api/v1/jobs",
            json={
                "name": "Incompatible Job",
                "method": "GET",
                "url": "https://api.example.com/test",
                "tasks": [
                    {"master_id": task1_master_id, "sequence": 0},
                    {"master_id": task2_master_id, "sequence": 1},
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()

        # Job created but validation failed
        job_id = data["job_id"]
        job = await db_session.get(Job, job_id)
        assert job is not None

        # Check validation tag
        validation_tag = next(
            (tag for tag in job.tags if tag.get("type") == "interface_validation"),
            None,
        )
        assert validation_tag is not None
        assert validation_tag["is_valid"] is False
        assert validation_tag["error_count"] > 0
        assert len(validation_tag["errors"]) > 0

    @pytest.mark.asyncio
    async def test_create_job_with_validation_disabled(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test job creation with validation explicitly disabled."""
        # Create task master
        task_master_id = f"tm_{ulid_new()}"
        task_master = TaskMaster(
            id=task_master_id,
            name="simple_task",
            method="GET",
            url="https://api.example.com/task",
            timeout_sec=30,
            is_active=True,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        db_session.add(task_master)
        await db_session.commit()

        # Create job with validation disabled
        response = await client.post(
            "/api/v1/jobs",
            json={
                "name": "No Validation Job",
                "method": "GET",
                "url": "https://api.example.com/test",
                "tasks": [{"master_id": task_master_id, "sequence": 0}],
                "validate_interfaces": False,
            },
        )

        assert response.status_code == 201
        data = response.json()

        # Job created successfully
        job_id = data["job_id"]
        job = await db_session.get(Job, job_id)
        assert job is not None

        # No validation tag should exist
        if job.tags:
            validation_tag = next(
                (tag for tag in job.tags if tag.get("type") == "interface_validation"),
                None,
            )
            assert validation_tag is None

    @pytest.mark.asyncio
    async def test_execute_job_with_failed_validation(
        self, db_session: AsyncSession
    ) -> None:
        """Test worker blocks execution of job with failed validation."""
        # Create job with failed validation tag
        job_id = f"j_{ulid_new()}"
        job = Job(
            id=job_id,
            name="Failed Validation Job",
            status=JobStatus.QUEUED,
            method="GET",
            url="https://api.example.com/test",
            timeout_sec=30,
            tags=[
                {
                    "type": "interface_validation",
                    "validated_at": "2025-10-17T10:00:00Z",
                    "is_valid": False,
                    "error_count": 2,
                    "warning_count": 0,
                    "errors": [
                        "Incompatible interfaces: Task 0 -> Task 1",
                        "Missing property: data (type: object)",
                    ],
                    "warnings": [],
                }
            ],
        )
        db_session.add(job)
        await db_session.commit()

        # Try to execute the job
        from app.core.config import get_settings

        settings = get_settings()
        executor = JobExecutor(db_session, settings)

        # Execution should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            await executor.execute_job(job)

        # Check error message
        assert "Job execution blocked" in str(exc_info.value)
        assert "failed interface validation" in str(exc_info.value)

        # Job should be marked as FAILED
        await db_session.refresh(job)
        assert job.status == JobStatus.FAILED
        assert job.finished_at is not None

    @pytest.mark.asyncio
    async def test_execute_job_without_validation_tag(
        self, db_session: AsyncSession
    ) -> None:
        """Test worker allows execution of job without validation tag (backward compatibility)."""
        # Create task master
        task_master_id = f"tm_{ulid_new()}"
        task_master = TaskMaster(
            id=task_master_id,
            name="simple_task",
            method="GET",
            url="https://httpbin.org/status/200",  # Use real endpoint
            timeout_sec=30,
            is_active=True,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        db_session.add(task_master)

        # Create job without validation tag (old job)
        job_id = f"j_{ulid_new()}"
        job = Job(
            id=job_id,
            name="Legacy Job",
            status=JobStatus.QUEUED,
            method="GET",
            url="https://httpbin.org/status/200",
            timeout_sec=30,
            tags=None,  # No tags
        )
        db_session.add(job)

        # Create task
        task_id = f"t_{ulid_new()}"
        task = Task(
            id=task_id,
            job_id=job_id,
            master_id=task_master_id,
            order=0,
            status=TaskStatus.QUEUED,
        )
        db_session.add(task)
        await db_session.commit()

        # Try to execute the job - should succeed
        from app.core.config import get_settings

        settings = get_settings()
        executor = JobExecutor(db_session, settings)

        # Execution should succeed (no validation tag = allowed)
        await executor.execute_job(job)

        # Job should complete successfully
        await db_session.refresh(job)
        assert job.status in [JobStatus.SUCCEEDED, JobStatus.FAILED]  # Either is OK
        assert job.finished_at is not None

    @pytest.mark.asyncio
    async def test_execute_job_with_passed_validation(
        self, db_session: AsyncSession
    ) -> None:
        """Test worker allows execution of job with passed validation."""
        # Create task master
        task_master_id = f"tm_{ulid_new()}"
        task_master = TaskMaster(
            id=task_master_id,
            name="simple_task",
            method="GET",
            url="https://httpbin.org/status/200",
            timeout_sec=30,
            is_active=True,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        db_session.add(task_master)

        # Create job with passed validation tag
        job_id = f"j_{ulid_new()}"
        job = Job(
            id=job_id,
            name="Passed Validation Job",
            status=JobStatus.QUEUED,
            method="GET",
            url="https://httpbin.org/status/200",
            timeout_sec=30,
            tags=[
                {
                    "type": "interface_validation",
                    "validated_at": "2025-10-17T10:00:00Z",
                    "is_valid": True,
                    "error_count": 0,
                    "warning_count": 0,
                    "errors": [],
                    "warnings": [],
                }
            ],
        )
        db_session.add(job)

        # Create task
        task_id = f"t_{ulid_new()}"
        task = Task(
            id=task_id,
            job_id=job_id,
            master_id=task_master_id,
            order=0,
            status=TaskStatus.QUEUED,
        )
        db_session.add(task)
        await db_session.commit()

        # Execute the job - should succeed
        from app.core.config import get_settings

        settings = get_settings()
        executor = JobExecutor(db_session, settings)

        await executor.execute_job(job)

        # Job should complete
        await db_session.refresh(job)
        assert job.status in [JobStatus.SUCCEEDED, JobStatus.FAILED]
        assert job.finished_at is not None
